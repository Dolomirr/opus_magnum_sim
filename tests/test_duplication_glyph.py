import pytest  # noqa: INP001

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.atoms.molecule import collect_molecule
from opus_magnum_sym.elements.board import Direction, Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.simulation.errors import SimulationRuntimeError
from opus_magnum_sym.simulation.simulator import Simulator


def _glyph_sim(rotation: int = 0) -> Simulator:
    sim = Simulator((8, 8))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(7, 7), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.place("glyph_duplication", Hex(3, 3), rotation=rotation)
    return sim


def _glyph(sim: Simulator):
    return next(c for c in sim.entrypoints.values() if c.type is ComponentType.DUPLICATION_GLYPH)


@pytest.mark.parametrize(
    "element",
    [AtomType.FIRE, AtomType.WATER, AtomType.AIR, AtomType.EARTH],
)
def test_transmutes_salt_to_element(element):
    sim = _glyph_sim()
    glyph = _glyph(sim)
    salt = Atom(AtomType.SALT)
    example = Atom(element)
    sim.board.place_atom(glyph.transmuter_pos, salt)
    sim.board.place_atom(glyph.exemplar_pos, example)

    sim.next_step()

    assert salt.type is element


def test_exemplar_is_not_consumed():
    sim = _glyph_sim()
    glyph = _glyph(sim)
    salt = Atom(AtomType.SALT)
    example = Atom(AtomType.FIRE)
    sim.board.place_atom(glyph.transmuter_pos, salt)
    sim.board.place_atom(glyph.exemplar_pos, example)

    sim.next_step()

    assert sim.board.get_atom(glyph.exemplar_pos) is example
    assert example.type is AtomType.FIRE


@pytest.mark.parametrize("atom_type", [AtomType.BASIC, AtomType.SALT, AtomType.METAL])
def test_leaves_salt_when_exemplar_non_elemental(atom_type):
    sim = _glyph_sim()
    glyph = _glyph(sim)
    salt = Atom(AtomType.SALT)
    sim.board.place_atom(glyph.transmuter_pos, salt)
    sim.board.place_atom(glyph.exemplar_pos, Atom(atom_type))

    sim.next_step()

    assert salt.type is AtomType.SALT


def test_no_exemplar_does_nothing():
    sim = _glyph_sim()
    glyph = _glyph(sim)
    salt = Atom(AtomType.SALT)
    sim.board.place_atom(glyph.transmuter_pos, salt)

    sim.next_step()

    assert salt.type is AtomType.SALT


def test_no_salt_does_nothing():
    sim = _glyph_sim()
    glyph = _glyph(sim)
    sim.board.place_atom(glyph.exemplar_pos, Atom(AtomType.FIRE))

    sim.next_step()

    assert sim.board.get_atom(glyph.transmuter_pos) is None


def test_transmutes_bonded_salt():
    sim = _glyph_sim()
    glyph = _glyph(sim)
    salt = Atom(AtomType.SALT)
    bonded = Atom(AtomType.BASIC)
    sim.board.place_atom(glyph.transmuter_pos, salt)
    sim.board.place_atom(glyph.exemplar_pos, Atom(AtomType.WATER))
    bonded_cell = Direction().from_rotation(1).apply(glyph.transmuter_pos)
    sim.board.place_atom(bonded_cell, bonded)
    sim.board.connect_atoms(glyph.transmuter_pos, bonded_cell)

    sim.next_step()

    assert salt.type is AtomType.WATER
    assert collect_molecule(salt) == {salt, bonded}


def test_place_glyph_duplication_footprint():
    sim = Simulator((8, 8))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(7, 7), ComponentType.EXIT, atom_type=AtomType.BASIC)

    record = sim.place("glyph_duplication", Hex(3, 3))

    assert len(record.component_ids) == 1
    assert record.links == ()
    (cid,) = record.component_ids
    comp = sim.entrypoints[cid]
    assert comp.type is ComponentType.DUPLICATION_GLYPH
    assert comp.transmuter_pos == Hex(3, 3)
    assert comp.exemplar_pos == Direction().from_rotation(0).apply(Hex(3, 3))
    for cell in comp.footprint():
        assert sim.board.base_obj[cell] == ComponentType.DUPLICATION_GLYPH


@pytest.mark.parametrize("rotation", range(6))
def test_rotation_positions_exemplar(rotation):
    sim = _glyph_sim(rotation)
    glyph = _glyph(sim)

    expected = Direction().from_rotation(rotation).apply(Hex(3, 3))
    assert glyph.exemplar_pos == expected
    assert set(glyph.footprint()) == {Hex(3, 3), expected}


def test_place_rejects_occupied_exemplar_cell():
    sim = Simulator((8, 8))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(7, 7), ComponentType.EXIT, atom_type=AtomType.BASIC)
    exemplar = Direction().from_rotation(0).apply(Hex(3, 3))
    sim.add_component(exemplar, ComponentType.ENTRANCE, atom_type=AtomType.BASIC)

    with pytest.raises(SimulationRuntimeError):
        sim.place("glyph_duplication", Hex(3, 3))

    assert sim.board.base_obj[Hex(3, 3)] == ComponentType.EMPTY
    assert sim.placements == []


def test_place_rejects_overrides():
    sim = Simulator((8, 8))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(7, 7), ComponentType.EXIT, atom_type=AtomType.BASIC)

    with pytest.raises(SimulationRuntimeError, match="overrides"):
        sim.place("glyph_duplication", Hex(3, 3), atom_type=AtomType.FIRE)


def test_remove_placement():
    sim = _glyph_sim()
    record = sim.placements[0]
    cells = list(_glyph(sim).footprint())

    sim.remove_placement(record)

    assert record not in sim.placements
    for cell in cells:
        assert sim.board.base_obj[cell] == ComponentType.EMPTY
