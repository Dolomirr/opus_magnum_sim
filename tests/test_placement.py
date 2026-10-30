"""
Tests for the high-level placement API (`Simulator.place` / `remove_placement`).
"""

import pytest  # noqa: INP001

import opus_magnum_sym.elements.env.index_manager as im
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Direction, Hex
from opus_magnum_sym.elements.components import (
    ComponentType,
    ManipulatorSpec,
    RetractableManipulator,
    ShapeCell,
    ShapeTemplate,
)
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
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.SALT)
    sim.add_component(Hex(7, 7), ComponentType.EXIT, atom_type=AtomType.SALT)
    return sim


# ---------------------------------------------------------------------------
# Shape placement
# ---------------------------------------------------------------------------


def test_connector_tri_placement_shape_and_bonds():
    sim = _make_sim()
    center = Hex(3, 3)
    record = sim.place("connector_tri", center, rotation=0, atom_type=AtomType.SALT)

    assert len(record.component_ids) == 4
    assert len(record.links) == 3

    expected = _y_cells(center)
    placed_cells = [sim.entrypoints[cid].pos for cid in record.component_ids]
    assert set(placed_cells) == set(expected)
    for cell in expected:
        assert sim.board.base_obj[cell] == ComponentType.CONNECTOR

    # Bonds match Stage 1's pinned Y semantics.
    atoms = {cell: Atom(AtomType.SALT) for cell in expected}
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
    sim.board.place_atom(target, Atom(AtomType.SALT))
    baseline = im.active_count()

    with pytest.raises(SimulationRuntimeError):
        sim.place("connector_tri", center, rotation=0, atom_type=AtomType.SALT)

    assert im.active_count() == baseline
    assert sim.placements == []
    for cell in _y_cells(center):
        assert sim.board.base_obj[cell] == ComponentType.EMPTY


def test_place_rollback_on_link_failure():
    sim = _make_sim()
    center = Hex(3, 3)
    baseline = im.active_count()
    before_ids = set(sim.components) | set(sim.entrypoints)

    # A template with duplicate links passes definition-time validation
    # (only adjacency, bounds, and self-links are checked) but fails at
    # wiring time: the second link is already present in the graph.
    beam_offset = Direction().from_rotation(0).apply(Hex(0, 0))
    template = ShapeTemplate(
        "duplicate_link_test",
        ComponentType.CONNECTOR,
        cells=(
            ShapeCell(offset=Hex(0, 0)),
            ShapeCell(offset=beam_offset),
        ),
        links=((0, 1), (0, 1)),
    )

    with pytest.raises(SimulationRuntimeError, match="invalid link"):
        sim.place(template, center, atom_type=AtomType.SALT)

    assert im.active_count() == baseline
    assert set(sim.components) | set(sim.entrypoints) == before_ids
    assert sim.placements == []
    placed_cells = (
        center,
        Hex(center.r + beam_offset.r, center.s + beam_offset.s),
    )
    for cell in placed_cells:
        assert sim.board.base_obj[cell] == ComponentType.EMPTY


def test_rotation_validation():
    sim = _make_sim()
    with pytest.raises(SimulationRuntimeError, match="rotation"):
        sim.place("connector_tri", Hex(3, 3), rotation=1, atom_type=AtomType.SALT)
    for i, rotation in enumerate((0, 2, 4)):
        record = sim.place(
            "connector_tri",
            Hex(2 + i * 2, 2),
            rotation=rotation,
            atom_type=AtomType.SALT,
        )
        assert record.rotation == rotation


@pytest.mark.parametrize(
    ("name", "allowed"),
    [
        ("connector_tri", {0, 2, 4}),
        ("connector_tri_odd", {1, 3, 5}),
    ],
)
def test_y_template_accepts_all_and_only_its_rotations(name, allowed):
    for rotation in range(6):
        sim = _make_sim()
        if rotation in allowed:
            record = sim.place(name, Hex(3, 3), rotation=rotation, atom_type=AtomType.SALT)
            assert record.rotation == rotation
            # Every allowed placement covers the full 4-cell Y: origin + 3 beams.
            positions = {sim.entrypoints[cid].pos for cid in record.component_ids}
            assert len(positions) == 4
        else:
            with pytest.raises(SimulationRuntimeError, match="rotation"):
                sim.place(name, Hex(3, 3), rotation=rotation, atom_type=AtomType.SALT)
            assert sim.placements == []


def test_overrides_reach_every_cell():
    sim = _make_sim()
    record = sim.place("connector_tri", Hex(3, 3), rotation=0, atom_type=AtomType.SALT)
    for cid in record.component_ids:
        assert sim.entrypoints[cid].atom_type is AtomType.SALT


def test_remove_placement():
    sim = _make_sim()
    record = sim.place("connector_tri", Hex(3, 3), rotation=0, atom_type=AtomType.SALT)
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


def test_comp_id_returns_sole_id_for_single_component_placement():
    sim = _make_sim()
    record = sim.place("arm", Hex(3, 3))
    assert record.comp_id == record.component_ids[0]


def test_comp_id_rejects_multi_component_placement():
    sim = _make_sim()
    record = sim.place("connector_straight_2", Hex(3, 3), atom_type=AtomType.SALT)
    with pytest.raises(ValueError, match="component_ids"):
        _ = record.comp_id


def test_gated_presets_raise():
    sim = _make_sim()
    for name in ("arm_double", "arm_triple", "arm_hex"):
        with pytest.raises(SimulationRuntimeError, match="not implemented"):
            sim.place(name, Hex(3, 3))


def test_arm_piston_placement_stores_retractable_arm():
    sim = _make_sim()
    record = sim.place("arm_piston", Hex(3, 3))
    assert len(record.component_ids) == 1
    (cid,) = record.component_ids
    comp = sim.components[cid]
    assert comp.type is ComponentType.ARM_RETR
    assert isinstance(comp, RetractableManipulator)
    assert comp.spec.name == "arm_piston"
    assert comp.spec.extendable is True
    assert (comp.spec.min_length, comp.spec.max_length) == (1, 3)


def test_arm_piston_length_override_bounds():
    sim = _make_sim()
    with pytest.raises(SimulationRuntimeError, match="length"):
        sim.place("arm_piston", Hex(3, 3), length=4)
    record = sim.place("arm_piston", Hex(3, 3), length=3)
    (cid,) = record.component_ids
    assert sim.components[cid].hand_length == 3


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
    sim.place("connector_tri", Hex(3, 3), rotation=0, atom_type=AtomType.SALT)
    sim.place("arm", Hex(1, 1))
    assert len(sim.placements) == 2
    sim.reset()
    assert sim.placements == []


# ---------------------------------------------------------------------------
# Rotation / occupancy validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rotation", range(6))
def test_straight_template_rotation_geometry(rotation):
    sim = _make_sim()
    origin = Hex(4, 4)
    record = sim.place("connector_straight_2", origin, rotation=rotation, atom_type=AtomType.SALT)

    dr, ds = Direction().from_rotation(rotation).offset
    beam = Hex(origin.r + dr, origin.s + ds)
    positions = [sim.entrypoints[cid].pos for cid in record.component_ids]
    assert set(positions) == {origin, beam}

    assert len(record.component_ids) == 2
    assert len(record.links) == 1
    (id_a, id_b) = record.links[0]
    assert sim.connections.links_of(id_a) == {id_b}


def test_y_template_rotation_symmetry():
    sim = _make_sim()

    def rel_cells(name: str, rotation: int, origin: Hex) -> set[Hex]:
        record = sim.place(name, origin, rotation=rotation, atom_type=AtomType.SALT)
        return {
            Hex(comp.pos.r - origin.r, comp.pos.s - origin.s)
            for comp in (sim.entrypoints[cid] for cid in record.component_ids)
        } - {Hex(0, 0)}

    # Each template's allowed rotations all yield the same self-consistent beam
    # set: a Y with 120-degree rotational symmetry around its origin. Rotating
    # a Y by two steps maps its beams onto themselves.
    even_sets = [rel_cells("connector_tri", r, Hex(2 + i * 2, 2)) for i, r in enumerate((0, 2, 4))]
    assert even_sets[0] == even_sets[1] == even_sets[2]

    odd_sets = [rel_cells("connector_tri_odd", r, Hex(2 + i * 2, 6)) for i, r in enumerate((1, 3, 5))]
    assert odd_sets[0] == odd_sets[1] == odd_sets[2]

    # Each template refuses the other's rotations (the "impossible" rotations
    # for that parity-pinned variant).
    for r in (0, 2, 4):
        with pytest.raises(SimulationRuntimeError, match="rotation"):
            sim.place("connector_tri_odd", Hex(1, 1), rotation=r, atom_type=AtomType.SALT)
    for r in (1, 3, 5):
        with pytest.raises(SimulationRuntimeError, match="rotation"):
            sim.place("connector_tri", Hex(1, 1), rotation=r, atom_type=AtomType.SALT)


def test_place_rejects_component_occupied_cell():
    sim = _make_sim()
    center = Hex(3, 3)
    target = _y_cells(center)[1]
    sim.add_component(target, ComponentType.ENTRANCE, atom_type=AtomType.SALT)
    baseline = im.active_count()

    with pytest.raises(SimulationRuntimeError):
        sim.place("connector_tri", center, rotation=0, atom_type=AtomType.SALT)

    assert im.active_count() == baseline
    assert sim.placements == []
    for cell in _y_cells(center):
        assert sim.board.base_obj[cell] != ComponentType.CONNECTOR
    assert sim.board.base_obj[target] == ComponentType.ENTRANCE


def test_place_rejects_overlapping_placement():
    sim = _make_sim()
    center = Hex(3, 3)
    first = sim.place("connector_tri", center, rotation=0, atom_type=AtomType.SALT)

    overlap_origin = _y_cells(center)[1]
    with pytest.raises(SimulationRuntimeError):
        sim.place("connector_tri", overlap_origin, rotation=0, atom_type=AtomType.SALT)

    assert len(sim.placements) == 1
    assert sim.placements[0] is first
    assert len(first.component_ids) == 4
    for cid in first.component_ids:
        assert sim._lookup(cid) is not None
    assert len(first.links) == 3
    for id_a, id_b in first.links:
        assert id_b in sim.connections.links_of(id_a)
        assert id_a in sim.connections.links_of(id_b)


def test_place_rejects_out_of_bounds():
    sim = Simulator((6, 6))
    with pytest.raises(SimulationRuntimeError):
        sim.place("connector_straight_2", Hex(0, 0), rotation=0, atom_type=AtomType.SALT)

    assert sim.board.base_obj[Hex(0, 0)] == ComponentType.EMPTY


def test_replace_after_removal():
    sim = _make_sim()
    center = Hex(3, 3)
    baseline = im.active_count()

    first = sim.place("connector_tri", center, rotation=0, atom_type=AtomType.SALT)
    sim.remove_placement(first)
    assert im.active_count() == baseline

    second = sim.place("connector_tri", center, rotation=0, atom_type=AtomType.SALT)
    assert len(second.component_ids) == 4
    assert len(second.links) == 3
    assert {sim.entrypoints[cid].pos for cid in second.component_ids} == set(_y_cells(center))


def test_arm_place_on_occupied_cell_rejected():
    sim = _make_sim()
    sim.add_component(Hex(3, 3), ComponentType.ENTRANCE, atom_type=AtomType.SALT)

    with pytest.raises(SimulationRuntimeError):
        sim.place("arm", Hex(3, 3))

    assert sim.placements == []
