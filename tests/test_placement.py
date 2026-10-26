"""
Tests for the high-level placement API (`Simulator.place` / `remove_placement`).
"""

import pytest  # noqa: INP001

import opus_magnum_sym.elements.env.index_manager as im
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Direction, Hex
from opus_magnum_sym.elements.components import ComponentType, ManipulatorSpec
from opus_magnum_sym.simulation.errors import SimulationRuntimeError
from opus_magnum_sym.simulation.simulator import Simulator


def _y_cells(center: Hex, rotation: int = 0) -> list[Hex]:
    cells = [center]
    for r in (0, 2, 4):
        dr, ds = Direction().from_rotation(r).offset
        rel = Hex(dr, ds).rotate_around(Hex(0, 0), rotation)
        cells.append(Hex(center.r + rel.r, center.s + rel.s))
    return cells


def _make_sim(size=(8, 8)) -> Simulator:
    sim = Simulator(size)
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(7, 7), ComponentType.EXIT, atom_type=AtomType.BASIC)
    return sim


# ---------------------------------------------------------------------------
# Shape placement
# ---------------------------------------------------------------------------


def test_connector_tri_placement_shape_and_bonds():
    sim = _make_sim()
    center = Hex(3, 3)
    record = sim.place("connector_tri", center, rotation=0, atom_type=AtomType.BASIC)

    assert len(record.component_ids) == 4
    assert len(record.links) == 3

    expected = _y_cells(center)
    placed_cells = [sim.entrypoints[cid].pos for cid in record.component_ids]
    assert set(placed_cells) == set(expected)
    for cell in expected:
        assert sim.board.base_obj[cell] == ComponentType.CONNECTOR

    # Bonds match Stage 1's pinned Y semantics.
    atoms = {cell: Atom(AtomType.BASIC) for cell in expected}
    for cell, atom in atoms.items():
        sim.board.place_atom(cell, atom)

    sim.next_step()

    center_atom = atoms[center]
    connected = [a for _, a in center_atom.iter_connections()]
    assert len(connected) == 3
    for beam in expected[1:]:
        beam_atom = sim.board.get_atom(beam)
        assert [a for _, a in beam_atom.iter_connections()] == [center_atom]


def test_place_atomicity_on_occupied_cell():
    sim = _make_sim()
    center = Hex(3, 3)
    target = _y_cells(center)[1]
    sim.board.place_atom(target, Atom(AtomType.BASIC))
    baseline = im.active_count()

    with pytest.raises(SimulationRuntimeError):
        sim.place("connector_tri", center, rotation=0, atom_type=AtomType.BASIC)

    assert im.active_count() == baseline
    assert sim.placements == []
    for cell in _y_cells(center):
        assert sim.board.base_obj[cell] == ComponentType.EMPTY


def test_rotation_validation():
    sim = _make_sim()
    with pytest.raises(SimulationRuntimeError, match="rotation"):
        sim.place("connector_tri", Hex(3, 3), rotation=1, atom_type=AtomType.BASIC)
    for i, rotation in enumerate((0, 2, 4)):
        record = sim.place(
            "connector_tri",
            Hex(2 + i * 2, 2),
            rotation=rotation,
            atom_type=AtomType.BASIC,
        )
        assert record.rotation == rotation


def test_overrides_reach_every_cell():
    sim = _make_sim()
    record = sim.place("connector_tri", Hex(3, 3), rotation=0, atom_type=AtomType.BASIC)
    for cid in record.component_ids:
        assert sim.entrypoints[cid].atom_type is AtomType.BASIC


def test_remove_placement():
    sim = _make_sim()
    record = sim.place("connector_tri", Hex(3, 3), rotation=0, atom_type=AtomType.BASIC)
    cells = [sim.entrypoints[cid].pos for cid in record.component_ids]

    sim.remove_placement(record)

    assert record not in sim.placements
    for cell in cells:
        assert sim.board.base_obj[cell] == ComponentType.EMPTY
    for cid in record.component_ids:
        assert sim._lookup(cid) is None
        assert sim.connections.links_of(cid) == set()


def test_unknown_blueprint_raises():
    sim = _make_sim()
    with pytest.raises(SimulationRuntimeError, match="nope"):
        sim.place("nope", Hex(3, 3))


# ---------------------------------------------------------------------------
# Manipulator-spec placement
# ---------------------------------------------------------------------------


def test_arm_placement_stores_spec():
    sim = _make_sim()
    record = sim.place("arm", Hex(3, 3))
    assert len(record.component_ids) == 1
    assert record.links == ()
    (cid,) = record.component_ids
    spec = sim.components[cid].spec
    assert isinstance(spec, ManipulatorSpec)
    assert spec.name == "arm"


def test_gated_presets_raise():
    sim = _make_sim()
    for name in ("arm_piston", "arm_double", "arm_triple", "arm_hex"):
        with pytest.raises(SimulationRuntimeError, match="not implemented"):
            sim.place(name, Hex(3, 3))


def test_length_override_bounds():
    sim = _make_sim()
    with pytest.raises(SimulationRuntimeError, match="length"):
        sim.place("arm", Hex(3, 3), length=7)
    with pytest.raises(SimulationRuntimeError, match="length"):
        sim.place("arm", Hex(3, 3), length=0)
    record = sim.place("arm", Hex(3, 3), length=3)
    (cid,) = record.component_ids
    assert sim.components[cid].hand_length == 3


def test_spec_field_override_rejected():
    sim = _make_sim()
    with pytest.raises(SimulationRuntimeError, match="arm_count"):
        sim.place("arm", Hex(3, 3), arm_count=2)


def test_reset_clears_placements():
    sim = _make_sim()
    sim.place("connector_tri", Hex(3, 3), rotation=0, atom_type=AtomType.BASIC)
    sim.place("arm", Hex(1, 1))
    assert len(sim.placements) == 2
    sim.reset()
    assert sim.placements == []
