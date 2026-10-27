import pytest  # noqa: INP001

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType


def test_default_connections_are_empty():
    atom = Atom(AtomType.BASIC)

    assert atom.type is AtomType.BASIC
    assert len(atom.connections) == 6
    assert all(slot is None for slot in atom.connections)


def test_all_atom_types_exist():
    assert AtomType.NONE.value == 0
    assert AtomType.BASIC.value == 1
    assert AtomType.FIRE.value == 2
    assert AtomType.WATER.value == 3
    assert AtomType.EARTH.value == 4
    assert AtomType.AIR.value == 5
    assert AtomType.SALT.value == 6
    assert AtomType.METAL.value == 7


def test_connect_mirrors_opposite_slot():
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)

    a.connect(2, b)

    assert a.connection_at(2) is b
    assert b.connection_at(5) is a


def test_connect_skips_when_already_connected():
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    c = Atom(AtomType.BASIC)

    a.connect(1, b)
    a.connect(1, c)  # a already bonded in slot 1 -> no-op

    assert a.connection_at(1) is b
    assert b.connection_at(4) is a
    assert c.connection_at(4) is None


def test_disconnect_clears_both_sides():
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    a.connect(3, b)

    a.disconnect(3)

    assert a.connection_at(3) is None
    assert b.connection_at(0) is None


def test_connection_at_wraps_rotation():
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    a.connect(0, b)

    assert a.connection_at(6) is b  # 6 % 6 == 0
