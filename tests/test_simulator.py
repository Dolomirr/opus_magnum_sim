import pytest  # noqa: INP001

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.env import level_counter
from opus_magnum_sym.simulation.simulator import SimulationRuntimeError, Simulator


def _flow_sim(exit_pos=Hex(3, 2)):
    """Entrance (2,3), exit, arm (3,3). Arm id is 2."""
    sim = Simulator((6, 6))
    sim.add_component(Hex(2, 3), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(exit_pos, ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 3), ComponentType.ARM)
    return sim


def test_missing_entrypoints_raise():
    sim = Simulator((4, 4))
    sim.add_component(Hex(2, 2), ComponentType.ARM)

    with pytest.raises(SimulationRuntimeError, match="EXIT is missing"):
        sim.next_step()


def test_entrance_spawns_atom():
    sim = _flow_sim()

    sim.next_step()

    assert sim.board.get_atom(Hex(2, 3)) is not None


def test_entrance_does_not_double_spawn():
    sim = _flow_sim()

    sim.next_step()
    sim.next_step()

    assert len(sim.board.atoms) == 1


def test_exit_consumes_matching_atom():
    sim = _flow_sim()
    sim.board.place_atom(Hex(3, 2), Atom(AtomType.BASIC))

    sim.next_step()

    assert sim.board.get_atom(Hex(3, 2)) is None
    assert level_counter.CORRECT_FINISHED == 1


def test_arm_moves_atom_to_exit():
    sim = _flow_sim()
    arm_id = 2
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)  # hand -> entrance (2,3)
    sim.assign_step_action(arm_id, 2, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 3, StepActionType.ROTATE_CCLW)  # hand -> exit (3,2)
    sim.assign_step_action(arm_id, 4, StepActionType.RELEASE)

    for _ in range(5):
        sim.next_step()

    assert level_counter.CORRECT_FINISHED == 1
    assert sim.board.get_atom(Hex(3, 2)) is None


def test_arm_moves_atom_between_cells():
    sim = _flow_sim(exit_pos=Hex(5, 5))  # exit far away, never consumed
    arm_id = 2
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)  # hand -> (2,3)
    sim.assign_step_action(arm_id, 2, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 3, StepActionType.ROTATE_CLW)   # hand -> (2,4)
    sim.assign_step_action(arm_id, 4, StepActionType.RELEASE)

    for _ in range(5):
        sim.next_step()

    assert sim.board.get_atom(Hex(2, 4)) is not None
    assert level_counter.CORRECT_FINISHED == 0
