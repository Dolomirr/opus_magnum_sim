import pytest  # noqa: INP001

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.atoms.molecule import collect_molecule
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.env import level_counter
from opus_magnum_sym.simulation.collision import CollisionCategory
from opus_magnum_sym.simulation.errors import SimulationCollisionError
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


def test_entrance_does_not_spawn_under_hand():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)  # id 0
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)  # id 1
    sim.add_component(Hex(1, 0), ComponentType.ARM, rotation=5)  # id 2, hand -> (0, 0)
    arm_id = 2
    sim.assign_step_action(arm_id, 1, StepActionType.GRAB)

    sim.next_step()  # step 0: entrance spawns atom
    atom = sim.board.get_atom(Hex(0, 0))
    assert atom is not None

    sim.next_step()  # step 1: arm grabs; entrance must not re-spawn under the hand

    assert sim.components[arm_id].holding == {Hex(0, 0): atom}
    assert sim.board.get_atom(Hex(0, 0)) is None


def test_exit_consumes_matching_atom():
    sim = _flow_sim()
    sim.board.place_atom(Hex(3, 2), Atom(AtomType.BASIC))

    sim.next_step()

    assert sim.board.get_atom(Hex(3, 2)) is None
    assert level_counter.total_finished() == 1


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

    assert level_counter.total_finished() == 1
    assert sim.board.get_atom(Hex(3, 2)) is None


def test_arm_preserves_atom_type_when_moving():
    sim = _flow_sim(exit_pos=Hex(5, 5))
    arm_id = 2
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(arm_id, 2, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 3, StepActionType.ROTATE_CLW)
    sim.assign_step_action(arm_id, 4, StepActionType.RELEASE)

    for _ in range(5):
        sim.next_step()

    atom = sim.board.get_atom(Hex(2, 4))
    assert atom is not None
    assert atom.type is AtomType.BASIC


def test_entrance_spawns_non_basic_atom_type():
    sim = Simulator((6, 6))
    sim.add_component(Hex(2, 3), ComponentType.ENTRANCE, atom_type=AtomType.FIRE)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.FIRE)

    sim.next_step()

    atom = sim.board.get_atom(Hex(2, 3))
    assert atom is not None
    assert atom.type is AtomType.FIRE


def test_exit_consumes_only_matching_atom_type():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.WATER)
    water_exit_id = 1
    fire_exit_id = 2
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.WATER)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.FIRE)
    sim.board.place_atom(Hex(3, 2), Atom(AtomType.WATER))
    sim.board.place_atom(Hex(5, 5), Atom(AtomType.WATER))

    sim.next_step()

    assert sim.board.get_atom(Hex(3, 2)) is None
    assert level_counter.finished({water_exit_id}) == 1
    assert sim.board.get_atom(Hex(5, 5)) is not None
    assert level_counter.finished({fire_exit_id}) == 0
    assert level_counter.total_finished() == 1


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
    assert level_counter.total_finished() == 0


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
    assert level_counter.total_finished() == 1


def test_connected_exits_share_single_counter():
    sim = _connected_exit_sim()

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(3, 2), a)
    sim.board.place_atom(Hex(2, 2), b)
    sim.board.connect_atoms(Hex(3, 2), Hex(2, 2))

    sim.next_step()

    # The two exits form one cluster, counted under its full id set.
    assert level_counter.finished({1, 2}) == 1
    assert level_counter.finished({1}) == 0
    assert level_counter.finished({2}) == 0
    assert level_counter.total_finished() == 1


def test_separate_exit_clusters_have_separate_counters():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)  # id 0
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)  # id 1
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)  # id 2
    # Exits are not connected -> two independent clusters.

    sim.board.place_atom(Hex(3, 2), Atom(AtomType.BASIC))
    sim.board.place_atom(Hex(5, 5), Atom(AtomType.BASIC))

    sim.next_step()

    assert level_counter.finished({1}) == 1
    assert level_counter.finished({2}) == 1
    assert level_counter.total_finished() == 2
    assert level_counter.clusters() == {frozenset({1}): 1, frozenset({2}): 1}


def test_connected_exits_partial_molecule_not_consumed():
    sim = _connected_exit_sim()

    a = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(3, 2), a)  # only one exit covered

    sim.next_step()

    assert sim.board.get_atom(Hex(3, 2)) is a
    assert level_counter.total_finished() == 0


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
    assert level_counter.total_finished() == 0


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
    assert level_counter.total_finished() == 0


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
    assert level_counter.total_finished() == 0


def test_remove_component_purges_links():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(0, 1), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    assert sim.connect_components(0, 1) is True

    sim.remove_component(0)

    assert sim.connections.links_of(1) == set()
    assert sim.entrypoints[1].group == []


def test_arm_cannot_rotate_into_other_arms_held_cell():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)  # id 0
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)  # id 1
    sim.add_component(Hex(2, 2), ComponentType.ARM, rotation=0)  # id 2, hand -> (1, 3)
    sim.add_component(Hex(2, 4), ComponentType.ARM, rotation=4)  # id 3, hand -> (2, 3)

    arm_a, arm_b = 2, 3
    atom_a = Atom(AtomType.BASIC)
    atom_b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(1, 3), atom_a)
    sim.board.place_atom(Hex(2, 3), atom_b)

    sim.assign_step_action(arm_a, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_b, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_a, 2, StepActionType.ROTATE_CLW)  # hand -> (2, 3), held by arm_b

    sim.next_step()  # step 0: entrance spawns
    sim.next_step()  # step 1: both arms grab
    with pytest.raises(SimulationCollisionError) as excinfo:
        sim.next_step()  # step 2: arm A collides into arm B's held cell

    assert sim.components[arm_a].rotation == 0
    assert sim.components[arm_a].holding == {Hex(1, 3): atom_a}
    assert sim.components[arm_b].holding == {Hex(2, 3): atom_b}
    assert atom_a.held_by == {arm_a}
    assert atom_b.held_by == {arm_b}

    event = excinfo.value.event
    assert event is sim.collision
    assert event.category is CollisionCategory.ENDPOINT_OVERLAP
    assert event.owner_ids == (arm_a,)
    assert event.progress == 1.0
    assert event.cell == Hex(2, 3)
    # Step counter is not incremented on collision.
    assert sim.step == 2


def test_two_arms_cannot_move_into_same_cell():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)  # id 0
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)  # id 1
    sim.add_component(Hex(2, 2), ComponentType.ARM, rotation=0)  # id 2, hand -> (1, 3)
    sim.add_component(Hex(2, 4), ComponentType.ARM, rotation=3)  # id 3, hand -> (3, 3)

    arm_a, arm_b = 2, 3
    atom_a = Atom(AtomType.BASIC)
    atom_b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(1, 3), atom_a)
    sim.board.place_atom(Hex(3, 3), atom_b)

    sim.assign_step_action(arm_a, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_b, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_a, 2, StepActionType.ROTATE_CLW)  # hand -> (2, 3)
    sim.assign_step_action(arm_b, 2, StepActionType.ROTATE_CLW)  # hand -> (2, 3)

    sim.next_step()  # step 0: spawn
    sim.next_step()  # step 1: both arms grab
    with pytest.raises(SimulationCollisionError) as excinfo:
        sim.next_step()  # step 2: arm A claims (2,3); arm B raises

    # Arm A (runs first) commits; arm B is blocked and unchanged.
    assert sim.components[arm_a].rotation == 1
    assert sim.components[arm_a].holding == {Hex(2, 3): atom_a}
    assert sim.components[arm_b].rotation == 3
    assert sim.components[arm_b].holding == {Hex(3, 3): atom_b}

    event = excinfo.value.event
    assert sim.collision is event
    assert event.category is CollisionCategory.ENDPOINT_OVERLAP
    assert event.owner_ids == (arm_b,)  # arm B runs second, hits A's committed cell
    assert event.cell == Hex(2, 3)
    assert event.progress == 1.0
    assert sim.step == 2


def _sweep_sim():
    """Entrance (0,0), exit (5,5), arm A (id 2) at (3,3) length 2 rotation 0 (hand -> (1,5))."""
    sim = Simulator((7, 7))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 3), ComponentType.ARM, rotation=0, length=2)
    return sim


def test_sweep_atom_collision_via_next_step():
    sim = _sweep_sim()
    arm_id = 2
    atom_a = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(1, 5), atom_a)
    sim.board.place_atom(Hex(2, 5), Atom(AtomType.BASIC))  # blocker on the sweep arc

    sim.assign_step_action(arm_id, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 2, StepActionType.ROTATE_CLW)  # (1,5) -> (3,5)

    sim.next_step()  # step 0: spawn
    sim.next_step()  # step 1: grab
    with pytest.raises(SimulationCollisionError) as excinfo:
        sim.next_step()  # step 2: sweep hits blocker

    assert sim.collision is not None
    assert excinfo.value.event is sim.collision
    assert sim.collision.category is CollisionCategory.SWEEP_ATOM
    assert sim.collision.cell == Hex(2, 5)
    assert sim.collision.owner_ids == (arm_id,)
    assert sim.collision.progress == 0.25
    assert sim.collision.step == 2


def test_sweep_collision_commits_final_pose():
    sim = _sweep_sim()
    arm_id = 2
    atom_a = Atom(AtomType.BASIC)
    blocker = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(1, 5), atom_a)
    sim.board.place_atom(Hex(2, 5), blocker)

    sim.assign_step_action(arm_id, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 2, StepActionType.ROTATE_CLW)

    sim.next_step()
    sim.next_step()
    with pytest.raises(SimulationCollisionError):
        sim.next_step()

    # Arm stays at its final pose past the collision point (documented semantics).
    assert sim.components[arm_id].rotation == 1
    assert sim.components[arm_id].holding == {Hex(3, 5): atom_a}
    assert sim.board.get_atom(Hex(2, 5)) is blocker
    assert sim.step == 2  # not incremented


def test_entrypoints_skipped_after_sweep_collision():
    # Entrance at (1,5); the arm grabs its spawn on step 1 (leaving the entrance empty)
    # and sweeps into a blocker on step 2. If entrypoints still ran after the collision,
    # the now-empty entrance would re-spawn an atom.
    sim = Simulator((7, 7))
    sim.add_component(Hex(1, 5), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)  # id 0
    sim.add_component(Hex(6, 6), ComponentType.EXIT, atom_type=AtomType.BASIC)  # id 1
    sim.add_component(Hex(3, 3), ComponentType.ARM, rotation=0, length=2)  # id 2, hand -> (1,5)
    arm_id = 2

    sim.board.place_atom(Hex(2, 5), Atom(AtomType.BASIC))  # blocker on the sweep arc

    sim.assign_step_action(arm_id, 1, StepActionType.GRAB)  # grabs the (1,5) spawn
    sim.assign_step_action(arm_id, 2, StepActionType.ROTATE_CLW)  # (1,5) -> (3,5), hits (2,5)

    sim.next_step()  # step 0: entrance spawns at (1,5)
    assert sim.board.get_atom(Hex(1, 5)) is not None
    sim.next_step()  # step 1: arm grabs, entrance cell empties
    assert sim.board.get_atom(Hex(1, 5)) is None

    with pytest.raises(SimulationCollisionError):
        sim.next_step()  # step 2: sweep collision

    assert sim.collision.category is CollisionCategory.SWEEP_ATOM
    assert sim.step == 2  # not incremented
    # The entrance cell is empty and eligible to spawn; it stays empty only because
    # the entrypoint phase was skipped after the collision.
    assert sim.board.get_atom(Hex(1, 5)) is None


def test_sweep_arm_base_collision_via_next_step():
    sim = _sweep_sim()
    arm_a = 2
    sim.add_component(Hex(2, 5), ComponentType.ARM)  # arm B (id 3), base on the arc
    atom_a = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(1, 5), atom_a)

    sim.assign_step_action(arm_a, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_a, 2, StepActionType.ROTATE_CLW)

    sim.next_step()
    sim.next_step()
    with pytest.raises(SimulationCollisionError):
        sim.next_step()

    assert sim.collision.category is CollisionCategory.SWEEP_ARM_BASE
    assert sim.collision.cell == Hex(2, 5)
    assert sim.collision.owner_ids == (2, 3)
    assert sim.collision.progress == 0.25


def test_sweep_onto_other_arms_stationary_held_atom():
    sim = _sweep_sim()
    arm_a = 2
    # Arm B (id 3) at (2,4) rotation 1 -> hand (2,5).
    sim.add_component(Hex(2, 4), ComponentType.ARM, rotation=1)
    arm_b = 3
    atom_a = Atom(AtomType.BASIC)
    atom_b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(1, 5), atom_a)
    sim.board.place_atom(Hex(2, 5), atom_b)

    sim.assign_step_action(arm_a, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_b, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_a, 2, StepActionType.ROTATE_CLW)  # sweeps over (2,5)

    sim.next_step()
    sim.next_step()
    with pytest.raises(SimulationCollisionError):
        sim.next_step()

    assert sim.collision.category is CollisionCategory.SWEEP_ATOM
    assert sim.collision.cell == Hex(2, 5)
    assert sim.collision.owner_ids == (2, 3)


def test_sweep_moving_collision_via_next_step():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)  # id 0
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)  # id 1
    sim.add_component(Hex(2, 2), ComponentType.ARM, rotation=0)  # id 2, hand (1,3)
    sim.add_component(Hex(1, 5), ComponentType.ARM, rotation=3)  # id 3, hand (2,4)
    arm_a, arm_b = 2, 3
    atom_a = Atom(AtomType.BASIC)
    atom_b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(1, 3), atom_a)
    sim.board.place_atom(Hex(2, 4), atom_b)

    sim.assign_step_action(arm_a, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_b, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_a, 2, StepActionType.ROTATE_CLW)  # (1,3) -> (2,3)
    sim.assign_step_action(arm_b, 2, StepActionType.ROTATE_CLW)  # (2,4) -> (1,4)

    sim.next_step()
    sim.next_step()
    with pytest.raises(SimulationCollisionError):
        sim.next_step()

    assert sim.collision.category is CollisionCategory.SWEEP_MOVING
    assert sim.collision.owner_ids == (2, 3)
    assert sim.collision.progress == 0.625
    assert sim.collision.cell == Hex(2, 3)


def test_reset_clears_collision():
    sim = _sweep_sim()
    arm_id = 2
    atom_a = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(1, 5), atom_a)
    sim.board.place_atom(Hex(2, 5), Atom(AtomType.BASIC))

    sim.assign_step_action(arm_id, 1, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 2, StepActionType.ROTATE_CLW)

    sim.next_step()
    sim.next_step()
    with pytest.raises(SimulationCollisionError):
        sim.next_step()
    assert sim.collision is not None

    sim.reset()

    assert sim.collision is None
    assert sim.step == 0


def test_held_cells_aggregates_all_arms():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(2, 2), ComponentType.ARM, rotation=0)  # id 2
    sim.add_component(Hex(3, 4), ComponentType.ARM, rotation=0)  # id 3

    assert sim.held_cells() == set()

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.components[2].holding = {Hex(1, 3): a}
    sim.components[3].holding = {Hex(2, 5): b}

    assert sim.held_cells() == {Hex(1, 3), Hex(2, 5)}
