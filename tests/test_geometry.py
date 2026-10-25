from math import sqrt

import pytest  # noqa: INP001

from opus_magnum_sym.elements.board import Direction, Hex
from opus_magnum_sym.elements.board.geometry import (
    ARM_BASE_RADIUS,
    ATOM_RADIUS,
    circles_overlap,
    hex_to_xy,
    rotate_offset,
    xy_to_hex,
)


def test_hex_to_xy_known_values():
    assert hex_to_xy(Hex(0, 0)) == pytest.approx((0.0, 0.0))
    assert hex_to_xy(Hex(0, 1)) == pytest.approx((1.0, 0.0))
    assert hex_to_xy(Hex(1, 0)) == pytest.approx((0.5, sqrt(3) / 2.0))


def test_hex_to_xy_adjacent_centers_are_unit_distance():
    center = hex_to_xy(Hex(3, 3))
    for i in range(6):
        neighbor = Direction().from_rotation(i).apply(Hex(3, 3))
        n_xy = hex_to_xy(neighbor)
        dist = sqrt((n_xy[0] - center[0]) ** 2 + (n_xy[1] - center[1]) ** 2)
        assert dist == pytest.approx(1.0)


def test_xy_to_hex_roundtrip():
    cells = [Hex(-2, -1), Hex(0, 0), Hex(3, -2), Hex(-1, 4), Hex(5, 5), Hex(2, 3)]
    for cell in cells:
        assert xy_to_hex(*hex_to_xy(cell)) == cell


def test_rotate_offset_full_steps():
    expected = [
        (0.5, sqrt(3) / 2.0),
        (-0.5, sqrt(3) / 2.0),
        (-1.0, 0.0),
        (-0.5, -sqrt(3) / 2.0),
        (0.5, -sqrt(3) / 2.0),
        (1.0, 0.0),
    ]
    for steps, exp in enumerate(expected, start=1):
        assert rotate_offset((1.0, 0.0), steps) == pytest.approx(exp)


def test_rotate_offset_fractional_step():
    # 0.5 steps == 30 degrees.
    assert rotate_offset((1.0, 0.0), 0.5) == pytest.approx((sqrt(3) / 2.0, 0.5))


def test_rotate_offset_negative_steps():
    assert rotate_offset((1.0, 0.0), -1) == pytest.approx(rotate_offset((1.0, 0.0), 5))


def test_rotate_offset_matches_hex_rotate_around():
    pivots = [Hex(3, 3), Hex(-1, 2), Hex(0, 0)]
    cells = [Hex(1, 5), Hex(2, 2), Hex(5, 5), Hex(-2, 0)]
    for pivot in pivots:
        for cell in cells:
            for steps in range(-3, 4):
                pivot_xy = hex_to_xy(pivot)
                cell_xy = hex_to_xy(cell)
                offset = (cell_xy[0] - pivot_xy[0], cell_xy[1] - pivot_xy[1])
                via_hex = hex_to_xy(cell.rotate_around(pivot, steps))
                via_offset = (
                    pivot_xy[0] + rotate_offset(offset, steps)[0],
                    pivot_xy[1] + rotate_offset(offset, steps)[1],
                )
                assert via_hex == pytest.approx(via_offset)


def test_circles_overlap():
    assert circles_overlap((0.0, 0.0), 1.0, (1.5, 0.0), 1.0) is True  # dist 1.5 < 2.0
    # Exactly touching (dist == r1 + r2) is NOT an overlap (strict inequality).
    assert circles_overlap((0.0, 0.0), 1.0, (2.0, 0.0), 1.0) is False
    assert circles_overlap((0.0, 0.0), 1.0, (3.0, 0.0), 1.0) is False
    assert circles_overlap((0.0, 0.0), 1.0, (0.0, 0.0), 1.0) is True  # concentric


def test_radius_constants_no_false_positives():
    # Adjacent atom centers are 1.0 apart; two atoms never overlap.
    assert 2 * ATOM_RADIUS < 1.0
    # A length-1 hand rotating never touches its own base.
    assert ATOM_RADIUS + ARM_BASE_RADIUS < 1.0
