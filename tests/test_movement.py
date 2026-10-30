from math import hypot

import pytest  # noqa: INP001

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.board.geometry import hex_to_xy, rotate_offset
from opus_magnum_sym.simulation.movement import Movement, MovementKind


def _arc_movement(kind=MovementKind.ARM_SWING, pivot=Hex(3, 3)):  # noqa: B008
    """Movement from (1,5) to (3,5) rotating CLW around `pivot`."""
    atom = Atom(AtomType.BASIC)
    return Movement(
        owner_id=0,
        kind=kind,
        pivot=pivot,
        rotation_steps=1,
        atoms=[(Hex(1, 5), atom)],
    )


def test_endpoints_match_hex_rotation():
    movement = _arc_movement()
    assert movement.atom_xy(Hex(1, 5), 0.0) == pytest.approx(hex_to_xy(Hex(1, 5)))
    assert movement.atom_xy(Hex(1, 5), 1.0) == pytest.approx(hex_to_xy(Hex(3, 5)))


def test_midpoint_is_on_arc():
    movement = _arc_movement()
    pivot_xy = hex_to_xy(Hex(3, 3))
    start_xy = hex_to_xy(Hex(1, 5))
    offset = (start_xy[0] - pivot_xy[0], start_xy[1] - pivot_xy[1])
    for t in (0.0, 0.125, 0.5, 1.0):
        expected = (
            pivot_xy[0] + rotate_offset(offset, t)[0],
            pivot_xy[1] + rotate_offset(offset, t)[1],
        )
        pos = movement.atom_xy(Hex(1, 5), t)
        assert pos == pytest.approx(expected)
        # Radius around the pivot stays constant (== 2.0, the arm length).
        assert hypot(pos[0] - pivot_xy[0], pos[1] - pivot_xy[1]) == pytest.approx(2.0)


def test_counterclockwise():
    atom = Atom(AtomType.BASIC)
    movement = Movement(
        owner_id=0,
        kind=MovementKind.ARM_SWING,
        pivot=Hex(3, 3),
        rotation_steps=-1,
        atoms=[(Hex(3, 5), atom)],
    )
    assert movement.atom_xy(Hex(3, 5), 0.0) == pytest.approx(hex_to_xy(Hex(3, 5)))
    assert movement.atom_xy(Hex(3, 5), 1.0) == pytest.approx(hex_to_xy(Hex(1, 5)))


def test_molecule_pivot_kind_uses_hand_pivot():
    arm_swing = _arc_movement(kind=MovementKind.ARM_SWING)
    pivot_swing = _arc_movement(kind=MovementKind.MOLECULE_PIVOT)
    # Kind only selects the pivot; interpolation math is identical.
    assert arm_swing.atom_xy(Hex(1, 5), 0.5) == pytest.approx(pivot_swing.atom_xy(Hex(1, 5), 0.5))


def test_swept_cells_include_start_and_landing():
    assert _arc_movement().swept_cells() == {Hex(1, 5), Hex(3, 5)}


def test_swept_cells_counterclockwise_steps():
    start = Hex(3, 5)
    movement = Movement(
        owner_id=0,
        kind=MovementKind.ARM_SWING,
        pivot=Hex(3, 3),
        rotation_steps=-2,
        atoms=[(start, Atom(AtomType.BASIC))],
    )
    expected = {start.rotate_around(Hex(3, 3), -step) for step in (0, 1, 2)}

    assert movement.swept_cells() == expected


def test_swept_cells_hand_slide():
    start = Hex(2, 2)
    movement = Movement(
        owner_id=0,
        kind=MovementKind.HAND_SLIDE,
        pivot=Hex(3, 3),
        rotation_steps=1,
        atoms=[(start, Atom(AtomType.BASIC))],
        slide_delta=Hex(0, 1),
    )

    assert movement.swept_cells() == {start, Hex(2, 3)}
