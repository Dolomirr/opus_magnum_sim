import pytest  # noqa: INP001

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Board, Hex
from opus_magnum_sym.elements.components.manipulator import Manipulator
from opus_magnum_sym.simulation.collision import (
    CollisionCategory,
    CollisionEvent,
    detect_collision,
)
from opus_magnum_sym.simulation.errors import SimulationCollisionError
from opus_magnum_sym.simulation.movement import Movement, MovementKind


def _arm(idx=0, pos=Hex(2, 2), rotation=0, length=1):  # noqa: B008
    return Manipulator(idx=idx, pos=pos, rotation=rotation, length=length)


def test_no_movements_returns_none():
    board = Board(6, 6)
    assert detect_collision(board, [_arm()], [], step=0) is None


def test_free_sweep_returns_none():
    board = Board(6, 6)
    arm = _arm(idx=0, pos=Hex(2, 2), length=1)
    atom = Atom(AtomType.BASIC)
    board.place_atom(Hex(1, 4), Atom(AtomType.BASIC))  # static, outside the arc
    movement = Movement(0, MovementKind.ARM_SWING, Hex(2, 2), 1, [(Hex(1, 3), atom)])
    assert detect_collision(board, [arm], [movement], step=0) is None


def test_sweep_atom_detected():
    board = Board(7, 7)
    arm = _arm(idx=0, pos=Hex(3, 3), length=2)
    blocker = Atom(AtomType.BASIC)
    board.place_atom(Hex(2, 5), blocker)
    atom = Atom(AtomType.BASIC)
    movement = Movement(0, MovementKind.ARM_SWING, Hex(3, 3), 1, [(Hex(1, 5), atom)])

    event = detect_collision(board, [arm], [movement], step=3)

    assert event is not None
    assert event.category is CollisionCategory.SWEEP_ATOM
    assert event.step == 3
    assert event.cell == Hex(2, 5)
    assert event.owner_ids == (0,)
    assert event.progress == pytest.approx(0.25)


def test_sweep_arm_base_detected():
    board = Board(7, 7)
    arm = _arm(idx=0, pos=Hex(3, 3), length=2)
    other_arm = _arm(idx=1, pos=Hex(2, 5))  # base sits on the sweep path, no holding
    atom = Atom(AtomType.BASIC)
    movement = Movement(0, MovementKind.ARM_SWING, Hex(3, 3), 1, [(Hex(1, 5), atom)])

    event = detect_collision(board, [arm, other_arm], [movement], step=0)

    assert event is not None
    assert event.category is CollisionCategory.SWEEP_ARM_BASE
    assert event.cell == Hex(2, 5)
    assert event.owner_ids == (0, 1)
    assert event.progress == pytest.approx(0.25)


def test_stationary_held_atom_is_static_collider():
    board = Board(7, 7)
    arm = _arm(idx=0, pos=Hex(3, 3), length=2)
    other_atom = Atom(AtomType.BASIC)
    other_arm = _arm(idx=1, pos=Hex(0, 0))
    other_arm.holding = {Hex(2, 5): other_atom}  # stationary, held off-board
    atom = Atom(AtomType.BASIC)
    movement = Movement(0, MovementKind.ARM_SWING, Hex(3, 3), 1, [(Hex(1, 5), atom)])

    event = detect_collision(board, [arm, other_arm], [movement], step=0)

    assert event is not None
    assert event.category is CollisionCategory.SWEEP_ATOM
    assert event.cell == Hex(2, 5)
    assert event.owner_ids == (0, 1)
    assert event.progress == pytest.approx(0.25)


def test_moving_atoms_excluded_from_statics():
    board = Board(6, 6)
    arm = _arm(idx=0, pos=Hex(2, 2))
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    movement = Movement(
        0,
        MovementKind.ARM_SWING,
        Hex(2, 2),
        1,
        [(Hex(1, 3), a), (Hex(1, 4), b)],
    )
    # No board atoms, no other arms; the molecule must not collide with its own cells.
    assert detect_collision(board, [arm], [movement], step=0) is None


def test_sweep_moving_detected():
    board = Board(6, 6)
    arm_a = _arm(idx=0, pos=Hex(2, 2), rotation=0)  # hand (1,3) -> (2,3)
    arm_b = _arm(idx=1, pos=Hex(1, 5), rotation=3)  # hand (2,4) -> (1,4)
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    m_a = Movement(0, MovementKind.ARM_SWING, Hex(2, 2), 1, [(Hex(1, 3), a)])
    m_b = Movement(1, MovementKind.ARM_SWING, Hex(1, 5), 1, [(Hex(2, 4), b)])

    event = detect_collision(board, [arm_a, arm_b], [m_a, m_b], step=0)

    assert event is not None
    assert event.category is CollisionCategory.SWEEP_MOVING
    assert event.owner_ids == (0, 1)
    assert event.progress == pytest.approx(0.625)
    assert event.cell == Hex(2, 3)


def test_lowest_t_wins_over_lowest_id():
    board = Board(7, 7)
    arm_5 = _arm(idx=5, pos=Hex(3, 3), length=2)
    arm_0 = _arm(idx=0, pos=Hex(2, 2), length=1)
    board.place_atom(Hex(2, 5), Atom(AtomType.BASIC))  # hit by arm 5 at t=0.25
    board.place_atom(Hex(2, 3), Atom(AtomType.BASIC))  # arm 0 endpoint at t=1.0

    m_5 = Movement(5, MovementKind.ARM_SWING, Hex(3, 3), 1, [(Hex(1, 5), Atom(AtomType.BASIC))])
    m_0 = Movement(0, MovementKind.ARM_SWING, Hex(2, 2), 1, [(Hex(1, 3), Atom(AtomType.BASIC))])

    event = detect_collision(board, [arm_5, arm_0], [m_5, m_0], step=0)

    assert event is not None
    assert event.progress == pytest.approx(0.25)
    assert event.owner_ids == (5,)


def test_static_preferred_over_moving_at_same_t():
    board = Board(3, 3)
    static_atom = Atom(AtomType.BASIC)
    board.place_atom(Hex(1, 1), static_atom)
    # Two movements whose atoms both end overlapping the stationary atom at the same t.
    m_0 = Movement(0, MovementKind.ARM_SWING, Hex(1, 1), 1, [(Hex(1, 1), Atom(AtomType.BASIC))])
    m_1 = Movement(1, MovementKind.ARM_SWING, Hex(1, 1), 0, [(Hex(1, 1), Atom(AtomType.BASIC))])

    event = detect_collision(board, [], [m_0, m_1], step=0)

    assert event is not None
    assert event.category is CollisionCategory.SWEEP_ATOM
    assert event.cell == Hex(1, 1)
    assert event.owner_ids == (0,)
    assert event.progress == pytest.approx(0.125)


def test_sweep_endpoint_hit_at_full_progress():
    board = Board(6, 6)
    arm = _arm(idx=0, pos=Hex(2, 2), length=1)
    board.place_atom(Hex(2, 3), Atom(AtomType.BASIC))  # destination cell
    movement = Movement(
        0,
        MovementKind.ARM_SWING,
        Hex(2, 2),
        1,
        [(Hex(1, 3), Atom(AtomType.BASIC))],
    )

    event = detect_collision(board, [arm], [movement], step=0)

    assert event is not None
    assert event.category is CollisionCategory.SWEEP_ATOM
    # The adjacent swing arcs over the destination cell before its endpoint.
    assert event.progress == pytest.approx(0.375)
    assert event.cell == Hex(2, 3)


def test_own_base_does_not_collide():
    board = Board(6, 6)
    arm = _arm(idx=0, pos=Hex(2, 2), length=1)
    movement = Movement(
        0,
        MovementKind.ARM_SWING,
        Hex(2, 2),
        1,
        [(Hex(1, 3), Atom(AtomType.BASIC))],
    )
    assert detect_collision(board, [arm], [movement], step=0) is None


def test_collision_error_message_and_event():
    event = CollisionEvent(
        category=CollisionCategory.SWEEP_ATOM,
        step=7,
        cell=Hex(2, 5),
        owner_ids=(0, 3),
        progress=0.25,
    )
    err = SimulationCollisionError(event)

    assert err.event is event
    assert err.step == 7
    assert "SWEEP_ATOM" in str(err)
    assert "step 7" in str(err)
    assert "(2, 5)" in str(err)
    assert "0" in str(err)
    assert "3" in str(err)
