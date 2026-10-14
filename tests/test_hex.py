import pytest  # noqa: INP001

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Hex


def test_rotate_around_matches_hand_clw():
    assert Hex(0, 2).rotate_around(Hex(1, 1), 1) == Hex(1, 2)


def test_rotate_around_by_steps_matches_repeated_single_step():
    pivot = Hex(1, 1)
    start = Hex(0, 2)
    for steps in range(1, 6):
        expected = start
        for _ in range(steps):
            expected = expected.rotate_around(pivot, 1)
        assert start.rotate_around(pivot, steps) == expected


def test_rotate_around_six_steps_returns_start():
    pivot = Hex(1, 1)
    for start in [Hex(0, 0), Hex(0, 2), Hex(2, 2), Hex(4, 3)]:
        cell = start
        for _ in range(6):
            cell = cell.rotate_around(pivot, 1)
        assert cell == start


def test_rotate_around_by_six_is_identity():
    pivot = Hex(1, 1)
    for cell in [Hex(0, 0), Hex(0, 2), Hex(2, 2), Hex(4, 3)]:
        assert cell.rotate_around(pivot, 6) == cell


def test_rotate_connections_moves_bond_slot():
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    a.connect(1, b)
    steps = 2

    a.rotate_connections(steps)

    assert a.connection_at((1 + steps) % 6) is b


def test_rotate_connections_keeps_reciprocal_pair():
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    a.connect(1, b)
    steps = 2

    a.rotate_connections(steps)
    b.rotate_connections(steps)

    assert a.connection_at((1 + steps) % 6) is b
    assert b.connection_at((4 + steps) % 6) is a
