import pytest  # noqa: INP001

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.atoms.molecule import collect_molecule


def test_collect_molecule_lone_atom():
    atom = Atom(AtomType.BASIC)

    assert collect_molecule(atom) == {atom}


def test_collect_molecule_chain_from_any_root():
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    c = Atom(AtomType.BASIC)
    a.connect(1, b)
    b.connect(2, c)

    for root in (a, b, c):
        assert collect_molecule(root) == {a, b, c}


def test_collect_molecule_excludes_unconnected():
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    c = Atom(AtomType.BASIC)
    d = Atom(AtomType.BASIC)
    a.connect(1, b)
    b.connect(2, c)

    assert collect_molecule(a) == {a, b, c}
    assert d not in collect_molecule(a)


def test_collect_molecule_cycle_terminates():
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    c = Atom(AtomType.BASIC)
    a.connect(1, b)
    b.connect(2, c)
    c.connect(3, a)  # close the ring

    assert collect_molecule(a) == {a, b, c}


def test_iter_connections_yields_rotation_pairs():
    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    a.connect(1, b)
    a.connect(3, b)

    pairs = list(a.iter_connections())

    assert (1, b) in pairs
    assert (3, b) in pairs
    assert len(pairs) == 2
