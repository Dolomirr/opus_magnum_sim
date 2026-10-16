from itertools import pairwise

import pytest  # noqa: INP001

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.atoms.molecule import collect_molecule
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.simulation.simulator import Simulator


def _glyph_sim(comp_type: ComponentType, *cells: Hex) -> Simulator:
    """Entrance + far exit to satisfy init state, plus one glyph per cell."""
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)
    ids = []
    for cell in cells:
        sim.add_component(cell, comp_type, atom_type=AtomType.BASIC)
        ids.append(len(ids) + 2)  # entrance=0, exit=1
    for a, b in pairwise(ids):
        assert sim.connect_components(a, b) is True
    return sim


def test_connector_bonds_adjacent_atoms():
    sim = _glyph_sim(ComponentType.CONNECTOR, Hex(2, 2), Hex(2, 3))

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(2, 2), a)
    sim.board.place_atom(Hex(2, 3), b)

    sim.next_step()

    assert collect_molecule(a) == {a, b}


def test_connector_bonds_subset_of_group():
    # (2,2), (2,3), (3,2) form a triangle; only the first two are covered.
    sim = _glyph_sim(
        ComponentType.CONNECTOR,
        Hex(2, 2),
        Hex(2, 3),
        Hex(3, 2),
    )

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(2, 2), a)
    sim.board.place_atom(Hex(2, 3), b)

    sim.next_step()

    assert collect_molecule(a) == {a, b}


def test_connector_does_not_bond_non_adjacent():
    # Chain (2,2)-(2,3)-(2,4): endpoints are not adjacent.
    sim = _glyph_sim(
        ComponentType.CONNECTOR,
        Hex(2, 2),
        Hex(2, 3),
        Hex(2, 4),
    )

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(2, 2), a)
    sim.board.place_atom(Hex(2, 4), b)

    sim.next_step()

    assert collect_molecule(a) == {a}
    assert collect_molecule(b) == {b}


def test_connector_ignores_wrong_atom_type():
    sim = _glyph_sim(ComponentType.CONNECTOR, Hex(2, 2), Hex(2, 3))

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.NONE)
    sim.board.place_atom(Hex(2, 2), a)
    sim.board.place_atom(Hex(2, 3), b)

    sim.next_step()

    assert collect_molecule(a) == {a}


def test_disconnector_breaks_bond():
    sim = _glyph_sim(ComponentType.DISCONNECTOR, Hex(2, 2), Hex(2, 3))

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(2, 2), a)
    sim.board.place_atom(Hex(2, 3), b)
    sim.board.connect_atoms(Hex(2, 2), Hex(2, 3))

    sim.next_step()

    assert collect_molecule(a) == {a}
    assert collect_molecule(b) == {b}


def test_disconnector_breaks_only_covered_subset():
    # Triangle with a single bond on two covered cells; the empty cell is ignored.
    sim = _glyph_sim(
        ComponentType.DISCONNECTOR,
        Hex(2, 2),
        Hex(2, 3),
        Hex(3, 2),
    )

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(2, 2), a)
    sim.board.place_atom(Hex(2, 3), b)
    sim.board.connect_atoms(Hex(2, 2), Hex(2, 3))

    sim.next_step()

    assert collect_molecule(a) == {a}
    assert collect_molecule(b) == {b}


def test_connect_rejects_cross_glyph_types():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(2, 2), ComponentType.CONNECTOR, atom_type=AtomType.BASIC)
    sim.add_component(Hex(2, 3), ComponentType.DISCONNECTOR, atom_type=AtomType.BASIC)

    assert sim.connect_components(2, 3) is False
