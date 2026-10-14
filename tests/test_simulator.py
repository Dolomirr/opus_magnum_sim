import pytest  # noqa: INP001

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.atoms.molecule import collect_molecule
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.env import level_counter
from opus_magnum_sym.simulation.simulator import SimulationRuntimeError, Simulator


def _flow_sim(exit_pos=Hex(3, 2)):  # noqa: B008
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
    sim.assign_step_action(
        arm_id,
        1,
        StepActionType.ROTATE_CCLW,
    )  # hand -> entrance (2,3)
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
    sim.assign_step_action(arm_id, 3, StepActionType.ROTATE_CLW)  # hand -> (2,4)
    sim.assign_step_action(arm_id, 4, StepActionType.RELEASE)

    for _ in range(5):
        sim.next_step()

    assert sim.board.get_atom(Hex(2, 4)) is not None
    assert level_counter.CORRECT_FINISHED == 0


def _connected_exit_sim():
    """
    Entrance (0,0), two adjacent exits (3,2) and (2,2). Exit ids are 1 and 2.
    """
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(2, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)
    assert sim.connect_components(1, 2) is True
    return sim


def test_connected_entrances_spawn_bonded_molecule():
    sim = Simulator((6, 6))
    sim.add_component(Hex(2, 3), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(2, 4), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 3), ComponentType.EXIT, atom_type=AtomType.BASIC)
    assert sim.connect_components(0, 1) is True

    sim.next_step()

    atom_a = sim.board.get_atom(Hex(2, 3))
    atom_b = sim.board.get_atom(Hex(2, 4))
    assert atom_a is not None
    assert atom_b is not None
    assert collect_molecule(atom_a) == {atom_a, atom_b}


def test_connect_components_rejects_non_adjacent():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(2, 2), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)

    assert sim.connect_components(0, 1) is False


def test_connect_components_rejects_same_component():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)

    assert sim.connect_components(0, 0) is False


def test_connect_components_rejects_entrance_exit_link():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(0, 1), ComponentType.EXIT, atom_type=AtomType.BASIC)

    assert sim.connect_components(0, 1) is False


def test_connect_components_rejects_unknown_id():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)

    assert sim.connect_components(0, 99) is False


def test_connected_exits_consume_full_molecule():
    sim = _connected_exit_sim()

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(3, 2), a)
    sim.board.place_atom(Hex(2, 2), b)
    sim.board.connect_atoms(Hex(3, 2), Hex(2, 2))

    sim.next_step()

    assert sim.board.get_atom(Hex(3, 2)) is None
    assert sim.board.get_atom(Hex(2, 2)) is None
    assert level_counter.CORRECT_FINISHED == 1


def test_connected_exits_partial_molecule_not_consumed():
    sim = _connected_exit_sim()

    a = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(3, 2), a)  # only one exit covered

    sim.next_step()

    assert sim.board.get_atom(Hex(3, 2)) is a
    assert level_counter.CORRECT_FINISHED == 0


def test_connected_exits_reject_oversized_molecule():
    sim = _connected_exit_sim()

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    c = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(3, 2), a)
    sim.board.place_atom(Hex(2, 2), b)
    sim.board.place_atom(Hex(2, 3), c)
    sim.board.connect_atoms(Hex(3, 2), Hex(2, 2))
    sim.board.connect_atoms(Hex(2, 2), Hex(2, 3))

    sim.next_step()

    assert sim.board.get_atom(Hex(3, 2)) is a
    assert sim.board.get_atom(Hex(2, 2)) is b
    assert sim.board.get_atom(Hex(2, 3)) is c
    assert level_counter.CORRECT_FINISHED == 0


def test_connected_exits_reject_wrong_atom_type():
    sim = _connected_exit_sim()

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.NONE)
    sim.board.place_atom(Hex(3, 2), a)
    sim.board.place_atom(Hex(2, 2), b)
    sim.board.connect_atoms(Hex(3, 2), Hex(2, 2))

    sim.next_step()

    assert sim.board.get_atom(Hex(3, 2)) is a
    assert sim.board.get_atom(Hex(2, 2)) is b
    assert level_counter.CORRECT_FINISHED == 0


def test_lone_exit_rejects_multi_atom_molecule():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(3, 2), a)
    sim.board.place_atom(Hex(3, 3), b)
    sim.board.connect_atoms(Hex(3, 2), Hex(3, 3))

    sim.next_step()

    assert sim.board.get_atom(Hex(3, 2)) is a
    assert sim.board.get_atom(Hex(3, 3)) is b
    assert level_counter.CORRECT_FINISHED == 0


def test_remove_component_purges_links():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(0, 1), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    assert sim.connect_components(0, 1) is True

    sim.remove_component(0)

    assert sim.connections.links_of(1) == set()
    assert sim.entrypoints[1].group == []
