from pathlib import Path

import numpy as np
import pytest  # noqa: INP001

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.actions.base_action import ActionAssignmentError
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.env import level_counter
from opus_magnum_sym.interpreter.sim_interpreter import SimInterpreter
from opus_magnum_sym.simulation.simulator import SimulationRuntimeError, Simulator

FLOW_PATH = Path(__file__).parent / "fixtures" / "minimal_flow.oms"


def _flow_sim() -> Simulator:
    """
    Entrance (2,3), exit (3,2), arm (3,3) on 6x6 board
    """
    sim = Simulator((6, 6))
    sim.add_component(Hex(2, 3), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 3), ComponentType.ARM)
    return sim


def _arm_id(sim: Simulator) -> int:
    return next(cid for cid, comp in sim.components.items() if comp.type == ComponentType.ARM)


def test_full_flow_step_by_step_trace():
    sim = _flow_sim()
    arm_id = _arm_id(sim)
    arm = sim.components[arm_id]

    # hand -> entrance (2,3)
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(arm_id, 2, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 3, StepActionType.ROTATE_CCLW)  # hand -> exit (3,2)
    sim.assign_step_action(arm_id, 4, StepActionType.RELEASE)

    trace = []
    for _ in range(5):
        sim.next_step()
        trace.append(
            (
                frozenset(sim.board.atoms),
                arm.holding is not None,
                level_counter.total_finished(),
            ),
        )

    expected = [
        ({Hex(2, 3)}, False, 0),  # step 0: entrance spawns
        ({Hex(2, 3)}, False, 0),  # step 1: arm rotated to entrance, nothing else
        (set(), True, 0),  # step 2: grabbed, no re-spawn under the hand
        ({Hex(2, 3)}, True, 0),  # step 3: hand moved, entrance respawns
        ({Hex(2, 3)}, False, 1),  # step 4: released onto exit, consumed
    ]
    assert trace == expected


def test_atom_conservation_invariant():
    sim = Simulator((6, 6))
    sim.add_component(Hex(5, 5), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 3), ComponentType.ARM, rotation=5)  # hand -> (2,3)
    arm_id = _arm_id(sim)

    # block entrance forever
    sim.board.place_atom(Hex(5, 5), Atom(AtomType.BASIC))

    atom = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(2, 3), atom)
    sim.assign_step_action(arm_id, 1, StepActionType.GRAB)
    # hand -> exit (3,2)
    sim.assign_step_action(arm_id, 2, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(arm_id, 3, StepActionType.RELEASE)

    def total() -> int:
        held = sim.components[arm_id].holding is not None
        return len(sim.board.atoms) + int(held) + level_counter.total_finished()

    assert total() == 2
    for _ in range(4):
        sim.next_step()
        assert total() == 2

    assert level_counter.total_finished() == 1
    assert sim.board.get_atom(Hex(3, 2)) is None
    assert sim.board.get_atom(Hex(2, 3)) is None


def test_idle_entrance_blocks_at_one_atom():
    sim = _flow_sim()

    for _ in range(10):
        sim.next_step()

    assert len(sim.board.atoms) == 1
    assert level_counter.total_finished() == 0


def test_entrance_does_not_respawn_under_hand():
    sim = _flow_sim()
    arm_id = _arm_id(sim)
    arm = sim.components[arm_id]

    # hand -> entrance
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(arm_id, 2, StepActionType.GRAB)

    for _ in range(3):
        sim.next_step()

    assert arm.holding is not None
    assert sim.board.get_atom(Hex(2, 3)) is None


def test_repeated_production_increments_counter():
    sim = Simulator((6, 6))
    sim.add_component(Hex(2, 3), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 3), ComponentType.ARM, rotation=4)  # hand -> exit (3,2)
    arm_id = _arm_id(sim)

    cycles = 3
    for cycle in range(cycles):
        base = 1 + cycle * 4
        # hand -> entrance
        sim.assign_step_action(arm_id, base, StepActionType.ROTATE_CLW)
        sim.assign_step_action(arm_id, base + 1, StepActionType.GRAB)
        # hand -> exit
        sim.assign_step_action(arm_id, base + 2, StepActionType.ROTATE_CCLW)
        sim.assign_step_action(arm_id, base + 3, StepActionType.RELEASE)

    prev = 0
    for _ in range(cycles * 4 + 1):
        sim.next_step()
        assert prev <= level_counter.total_finished()
        prev = level_counter.total_finished()

    assert cycles == level_counter.total_finished()


def test_release_onto_exit_consumes_same_step():
    sim = _flow_sim()
    arm_id = _arm_id(sim)
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(arm_id, 2, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 3, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(arm_id, 4, StepActionType.RELEASE)

    for _ in range(4):
        sim.next_step()
    assert level_counter.total_finished() == 0

    sim.next_step()  # step 4: release -> consumed in the same step
    assert level_counter.total_finished() == 1
    assert sim.board.get_atom(Hex(3, 2)) is None


def test_wrong_type_atom_not_consumed():
    sim = _flow_sim()
    sim.board.place_atom(Hex(3, 2), Atom(AtomType.NONE))

    sim.next_step()

    assert sim.board.get_atom(Hex(3, 2)) is not None
    assert level_counter.total_finished() == 0


def test_counter_increments_once_per_atom():
    sim = _flow_sim()
    sim.board.place_atom(Hex(3, 2), Atom(AtomType.BASIC))

    sim.next_step()
    assert level_counter.total_finished() == 1

    sim.next_step()
    assert level_counter.total_finished() == 1


def test_actions_fire_only_at_assigned_step():
    sim = _flow_sim()
    arm_id = _arm_id(sim)
    arm = sim.components[arm_id]
    sim.assign_step_action(arm_id, 3, StepActionType.ROTATE_CCLW)

    for _ in range(3):
        sim.next_step()
        assert arm.rotation == 0

    sim.next_step()  # step 3
    assert arm.rotation == 5


def test_reassign_action_overwrites():
    sim = _flow_sim()
    arm_id = _arm_id(sim)
    arm = sim.components[arm_id]
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CLW)
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)

    for _ in range(2):
        sim.next_step()

    assert arm.rotation == 5


def test_assign_none_clears_action():
    sim = _flow_sim()
    arm_id = _arm_id(sim)
    arm = sim.components[arm_id]
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CLW)
    sim.assign_step_action(arm_id, 1, StepActionType.NONE)

    for _ in range(2):
        sim.next_step()

    assert arm.rotation == 0


def test_step_counter_increments_each_step():
    sim = _flow_sim()

    for expected in (1, 2, 3):
        sim.next_step()
        assert sim.step == expected


def test_failed_init_leaves_step_zero():
    sim = Simulator((4, 4))
    sim.add_component(Hex(2, 2), ComponentType.ARM)

    with pytest.raises(SimulationRuntimeError, match="EXIT is missing"):
        sim.next_step()
    assert sim.step == 0

    with pytest.raises(SimulationRuntimeError, match="EXIT is missing"):
        sim.next_step()
    assert sim.step == 0


def test_grab_out_of_bounds_is_noop():
    sim = Simulator((5, 5))
    sim.add_component(Hex(4, 4), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(4, 3), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(0, 0), ComponentType.ARM)  # rotation 0 -> hand (-1, 1)
    arm_id = _arm_id(sim)
    sim.assign_step_action(arm_id, 1, StepActionType.GRAB)

    for _ in range(2):
        sim.next_step()

    assert sim.components[arm_id].holding is None


def test_rotate_out_of_bounds_is_blocked():
    sim = Simulator((5, 5))
    sim.add_component(Hex(4, 4), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(4, 3), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(0, 0), ComponentType.ARM, rotation=2)  # hand -> (1, 0)
    arm_id = _arm_id(sim)
    arm = sim.components[arm_id]
    atom = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(1, 0), atom)
    sim.assign_step_action(arm_id, 1, StepActionType.GRAB)
    # rotation 3 -> hand (1, -1), out of bounds
    sim.assign_step_action(arm_id, 2, StepActionType.ROTATE_CLW)

    for _ in range(3):
        sim.next_step()

    assert arm.rotation == 2
    assert arm.holding == {Hex(1, 0): atom}


def test_rotation_wraparound():
    sim = _flow_sim()
    arm_id = _arm_id(sim)
    arm = sim.components[arm_id]
    start = arm.get_hand_pos

    for step in range(1, 7):
        sim.assign_step_action(arm_id, step, StepActionType.ROTATE_CLW)

    for _ in range(7):
        sim.next_step()

    assert arm.rotation == 0
    assert arm.get_hand_pos == start


@pytest.mark.xfail(reason="Blocked release is now a collision, not retry-until no-op", strict=True)
def test_release_onto_occupied_keeps_holding_until_free():
    sim = Simulator((5, 5))
    sim.add_component(Hex(4, 4), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(4, 3), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(1, 1), ComponentType.ARM)  # rotation 0 -> hand (0, 2)
    arm_id = _arm_id(sim)
    atom = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(0, 2), atom)
    sim.assign_step_action(arm_id, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 2, StepActionType.ROTATE_CLW)  # hand -> (1, 2)
    sim.assign_step_action(arm_id, 3, StepActionType.RELEASE)  # blocked
    sim.assign_step_action(arm_id, 4, StepActionType.ROTATE_CLW)  # hand -> (2, 1)
    sim.assign_step_action(arm_id, 5, StepActionType.RELEASE)  # succeeds

    for _ in range(3):
        sim.next_step()  # grab + rotate, hand now (1, 2)

    sim.board.place_atom(Hex(1, 2), Atom(AtomType.BASIC))  # blocker arrives late

    for _ in range(3):
        sim.next_step()  # blocked release, rotate to (2, 1), release

    assert sim.components[arm_id].holding is None
    assert sim.board.get_atom(Hex(2, 1)) is atom
    assert sim.board.get_atom(Hex(1, 2)) is not None  # blocker untouched


def test_extend_raises_for_basic_arm():
    sim = _flow_sim()
    arm_id = _arm_id(sim)
    sim.assign_step_action(arm_id, 1, StepActionType.EXTEND)

    sim.next_step()  # step 0
    with pytest.raises(ActionAssignmentError):
        sim.next_step()  # step 1: EXTEND unsupported


def test_action_on_unknown_component_raises():
    sim = _flow_sim()

    with pytest.raises(KeyError):
        sim.assign_step_action(999, 1, StepActionType.GRAB)


def test_remove_unknown_component_raises():
    sim = _flow_sim()

    with pytest.raises(SimulationRuntimeError):
        sim.remove_component(999)


def test_remove_component_frees_id_and_cell():
    sim = _flow_sim()
    arm_id = _arm_id(sim)

    sim.remove_component(arm_id)

    assert arm_id not in sim.components
    assert sim.board.base_obj[3, 3] == ComponentType.EMPTY
    assert sim.board.components_ids[3, 3] == -1


def test_reset_clears_state_and_ids():
    sim = _flow_sim()
    arm_id = _arm_id(sim)
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)
    sim.next_step()
    sim.next_step()
    assert sim.step == 2
    assert sim.board.get_atom(Hex(2, 3)) is not None

    sim.reset()

    assert sim.step == 0
    assert len(sim.board.atoms) == 0
    assert len(sim.components) == 0
    assert len(sim.entrypoints) == 0
    assert np.all(sim.board.base_obj == ComponentType.EMPTY)
    assert level_counter.total_finished() == 0
    assert sim.im.total_allocated() == 0

    with pytest.raises(SimulationRuntimeError, match="EXIT is missing"):
        sim.next_step()


def test_get_state_reflects_components_and_atoms():
    sim = _flow_sim()
    state = sim.board.get_state()

    assert state.shape == (2, 6, 6)
    assert state[0, 2, 3] == ComponentType.ENTRANCE
    assert state[0, 3, 2] == ComponentType.EXIT
    assert state[0, 3, 3] == ComponentType.ARM
    assert np.all(state[1] == AtomType.NONE)

    sim.next_step()
    assert sim.board.get_state()[1, 2, 3] == AtomType.BASIC


def test_deterministic_runs():
    def build_and_run() -> Simulator:
        sim = _flow_sim()
        arm_id = _arm_id(sim)
        sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)
        sim.assign_step_action(arm_id, 2, StepActionType.GRAB)
        sim.assign_step_action(arm_id, 3, StepActionType.ROTATE_CCLW)
        sim.assign_step_action(arm_id, 4, StepActionType.RELEASE)
        for _ in range(5):
            sim.next_step()
        return sim

    first = build_and_run()
    first_counter = level_counter.total_finished()
    second = build_and_run()
    second_counter = level_counter.total_finished()

    assert first_counter == 1
    assert second_counter == 2
    assert np.array_equal(first.board.get_state(), second.board.get_state())


def test_dsl_file_flow():
    sim = Simulator((6, 6))
    SimInterpreter(sim).load_file(FLOW_PATH)

    for _ in range(5):
        sim.next_step()
    assert level_counter.total_finished() == 1

    for _ in range(5):
        sim.next_step()
    assert level_counter.total_finished() == 2
    assert sim.board.get_atom(Hex(2, 3)) is not None


def test_dsl_inline_matches_file():
    lines = FLOW_PATH.read_text().splitlines()

    inline = Simulator((6, 6))
    interp = SimInterpreter(inline)
    for line in lines:
        interp.evaluate_line(line)
    for _ in range(10):
        inline.next_step()

    from_file = Simulator((6, 6))
    SimInterpreter(from_file).load_file(FLOW_PATH)
    for _ in range(10):
        from_file.next_step()

    assert np.array_equal(inline.board.get_state(), from_file.board.get_state())


def test_dsl_component_kwargs():
    sim = Simulator((6, 6))
    interp = SimInterpreter(sim)
    interp.evaluate_line("comp 2 3 entrance atom_type=basic")
    interp.evaluate_line("comp 3 2 exit atom_type=basic")
    interp.evaluate_line("comp 3 3 arm rotation=2 length=1")

    arm = sim.components[_arm_id(sim)]
    assert arm.rotation == 2
    assert arm.hand_length == 1
