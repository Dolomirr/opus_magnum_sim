from unittest.mock import MagicMock

import pytest  # noqa: INP001

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.env import level_counter
from opus_magnum_sym.interpreter.sim_interpreter import SimInterpreter
from opus_magnum_sym.repl.meta import MetaInterpreter
from opus_magnum_sym.simulation.simulator import LevelFinished, Simulator


def _advance_sim(sim: Simulator, steps: int) -> None:
    for _ in range(steps):
        sim.next_step()


def _feed_exit_times(sim: Simulator, pos: Hex, times: int) -> None:
    for _ in range(times):
        sim.board.place_atom(pos, Atom(AtomType.BASIC))
        sim.next_step()


def _single_exit_flow_sim(target: int | None = None) -> tuple[Simulator, int]:
    """Entrance (2,3), exit (3,2), arm (3,3). Arm id is 2."""
    sim = Simulator((6, 6))
    sim.add_component(Hex(2, 3), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 3), ComponentType.ARM)
    if target is not None:
        sim.set_exit_target([1], target)

    arm_id = 2
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(arm_id, 2, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 3, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(arm_id, 4, StepActionType.RELEASE)
    return sim, arm_id


def test_level_not_finished_without_target():
    sim, _ = _single_exit_flow_sim(target=None)

    for _ in range(5):
        sim.next_step()

    assert not sim.finished


def test_level_finishes_when_single_target_met():
    sim, _ = _single_exit_flow_sim(target=1)

    with pytest.raises(LevelFinished):
        _advance_sim(sim, 5)

    assert sim.finished
    assert level_counter.finished({1}) == 1


def test_level_finishes_after_multiple_deliveries():
    sim, arm_id = _single_exit_flow_sim(target=2)

    # Cycle back to pick up the second atom.
    sim.assign_step_action(arm_id, 5, StepActionType.ROTATE_CLW)
    sim.assign_step_action(arm_id, 6, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 7, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(arm_id, 8, StepActionType.RELEASE)

    with pytest.raises(LevelFinished):
        _advance_sim(sim, 20)

    assert sim.finished
    assert level_counter.finished({1}) == 2


def test_level_does_not_finish_with_partial_progress():
    sim, _ = _single_exit_flow_sim(target=2)

    for _ in range(5):
        sim.next_step()

    assert not sim.finished
    assert level_counter.finished({1}) == 1


def test_level_targets_two_independent_clusters():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)  # id 0
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)  # id 1
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)  # id 2

    sim.set_exit_target([1], 2)
    sim.set_exit_target([2], 2)

    # Feed cluster {1} twice.
    for _ in range(2):
        sim.board.place_atom(Hex(3, 2), Atom(AtomType.BASIC))
        sim.next_step()

    assert not sim.finished

    # Feed cluster {2} twice; the final delivery finishes the level.
    with pytest.raises(LevelFinished):
        _feed_exit_times(sim, Hex(5, 5), 2)

    assert sim.finished
    assert level_counter.finished({1}) == 2
    assert level_counter.finished({2}) == 2


def test_level_target_uses_connected_exit_cluster():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)  # id 0
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)  # id 1
    sim.add_component(Hex(2, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)  # id 2
    assert sim.connect_components(1, 2) is True

    # Target set using only one exit id should apply to the whole cluster.
    sim.set_exit_target([1], 1)

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(3, 2), a)
    sim.board.place_atom(Hex(2, 2), b)
    sim.board.connect_atoms(Hex(3, 2), Hex(2, 2))

    with pytest.raises(LevelFinished):
        sim.next_step()

    assert sim.finished
    assert level_counter.finished({1, 2}) == 1


def test_next_step_raises_after_level_finished():
    sim, _ = _single_exit_flow_sim(target=1)

    with pytest.raises(LevelFinished):
        _advance_sim(sim, 5)

    with pytest.raises(LevelFinished):
        sim.next_step()


def test_reset_clears_targets_and_finished_flag():
    sim, _ = _single_exit_flow_sim(target=1)

    with pytest.raises(LevelFinished):
        _advance_sim(sim, 5)

    assert sim.finished

    sim.reset()

    assert not sim.finished
    assert sim.level.targets == {}


def test_dsl_target_command():
    sim = Simulator((6, 6))
    interp = SimInterpreter(sim)
    interp.evaluate_line("comp 2 3 entrance atom_type=basic")
    interp.evaluate_line("comp 3 2 exit atom_type=basic")
    interp.evaluate_line("target 2 1")

    assert sim.level.targets == {frozenset({1}): 2}


def test_dsl_target_command_requires_arguments():
    sim = Simulator((6, 6))
    interp = SimInterpreter(sim)

    interp.evaluate_line("target 2")

    assert sim.level.targets == {}


def test_target_roundtrips_through_save_and_load(tmp_path):
    sim = Simulator((6, 6))
    sim.add_component(Hex(2, 3), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.set_exit_target([1], 3)

    repl = MagicMock()
    repl.sim = sim

    meta = MetaInterpreter(repl)
    path = tmp_path / "level.oms"
    meta._save([str(path)])

    loaded = Simulator((6, 6))
    SimInterpreter(loaded).load_file(path)

    assert loaded.level.targets == {frozenset({1}): 3}
