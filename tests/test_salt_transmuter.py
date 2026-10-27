import pytest  # noqa: INP001

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.atoms.molecule import collect_molecule
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.simulation.simulator import Simulator


def _transmuter_sim() -> Simulator:
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(2, 2), ComponentType.SALT_TRANSMUTER)
    return sim


@pytest.mark.parametrize(
    "atom_type",
    [AtomType.FIRE, AtomType.WATER, AtomType.AIR, AtomType.EARTH],
)
def test_transmutes_elemental_to_salt(atom_type):
    sim = _transmuter_sim()
    atom = Atom(atom_type)
    sim.board.place_atom(Hex(2, 2), atom)

    sim.next_step()

    assert atom.type is AtomType.SALT


@pytest.mark.parametrize("atom_type", [AtomType.BASIC, AtomType.SALT, AtomType.METAL])
def test_leaves_non_elemental_alone(atom_type):
    sim = _transmuter_sim()
    atom = Atom(atom_type)
    sim.board.place_atom(Hex(2, 2), atom)

    sim.next_step()

    assert atom.type is atom_type


def test_transmutes_atom_within_molecule():
    sim = _transmuter_sim()
    on_glyph = Atom(AtomType.FIRE)
    bonded = Atom(AtomType.WATER)
    sim.board.place_atom(Hex(2, 2), on_glyph)
    sim.board.place_atom(Hex(2, 3), bonded)
    sim.board.connect_atoms(Hex(2, 2), Hex(2, 3))

    sim.next_step()

    assert on_glyph.type is AtomType.SALT
    assert bonded.type is AtomType.WATER
    assert collect_molecule(on_glyph) == {on_glyph, bonded}


def test_ignores_empty_cell():
    sim = _transmuter_sim()

    sim.next_step()

    assert sim.board.get_atom(Hex(2, 2)) is None


def test_place_salt_transmuter_blueprint():
    sim = Simulator((6, 6))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)

    record = sim.place("salt_transmuter", Hex(3, 3))

    atom = Atom(AtomType.FIRE)
    sim.board.place_atom(Hex(3, 3), atom)

    sim.next_step()

    assert atom.type is AtomType.SALT
    assert len(record.component_ids) == 1
