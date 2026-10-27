"""
Behavior-pinning tests for linked groups (connectors, entrances, exits).

Lock the existing group/link execution semantics for exactly the multi-cell
configurations that the Stage 4 blueprint templates will generate. These tests
use only the current low-level API (`add_component`, `connect_components`,
`next_step`).
"""

import pytest  # noqa: INP001

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.atoms.molecule import collect_molecule
from opus_magnum_sym.elements.board import Direction, Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.env import level_counter
from opus_magnum_sym.simulation.simulator import Simulator


def _offset_by(center: Hex, rotation: int) -> Hex:
    dr, ds = Direction().from_rotation(rotation).offset
    return Hex(center.r + dr, center.s + ds)


def _add(sim: Simulator, cell: Hex, comp_type: ComponentType, **kwargs) -> int:
    """Add a component and return its allocated id (ids are sequential)."""
    before = set(sim.components) | set(sim.entrypoints)
    sim.add_component(cell, comp_type, **kwargs)
    after = set(sim.components) | set(sim.entrypoints)
    (new_id,) = after - before
    return new_id


# ---------------------------------------------------------------------------
# 1. Straight 2-connector bonds
# ---------------------------------------------------------------------------


def test_straight_connectors_bond_matching_atoms():
    sim = Simulator((8, 8))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)
    # Two adjacent connectors linked, atoms already on both cells.
    center = Hex(3, 3)
    beam = _offset_by(center, 0)
    conn_a = _add(sim, center, ComponentType.CONNECTOR, atom_type=AtomType.BASIC)
    conn_b = _add(sim, beam, ComponentType.CONNECTOR, atom_type=AtomType.BASIC)
    assert sim.connect_components(conn_a, conn_b) is True

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(center, a)
    sim.board.place_atom(beam, b)

    sim.next_step()

    assert collect_molecule(sim.board.get_atom(center)) == {a, b}


def test_straight_connectors_ignore_mismatched_atom():
    sim = Simulator((8, 8))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)
    center = Hex(3, 3)
    beam = _offset_by(center, 0)
    conn_a = _add(sim, center, ComponentType.CONNECTOR, atom_type=AtomType.BASIC)
    conn_b = _add(sim, beam, ComponentType.CONNECTOR, atom_type=AtomType.BASIC)
    assert sim.connect_components(conn_a, conn_b) is True

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.NONE)
    sim.board.place_atom(center, a)
    sim.board.place_atom(beam, b)

    sim.next_step()

    assert sim.board.get_atom(center) is a
    assert sim.board.get_atom(beam) is b
    assert list(a.iter_connections()) == []


# ---------------------------------------------------------------------------
# 2. Y-connector bonds through center only
# ---------------------------------------------------------------------------


def _y_connector_sim(rotations=(0, 2, 4), center=Hex(3, 3)) -> tuple[Simulator, list[Hex], int]:  # noqa: B008
    """Center connector + beams; returns (sim, cells, center_id)."""
    sim = Simulator((8, 8))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)
    center_id = _add(sim, center, ComponentType.CONNECTOR, atom_type=AtomType.BASIC)
    beam_ids = [_add(sim, _offset_by(center, r), ComponentType.CONNECTOR, atom_type=AtomType.BASIC) for r in rotations]
    for bid in beam_ids:
        assert sim.connect_components(center_id, bid) is True
    cells = [center, *(_offset_by(center, r) for r in rotations)]
    return sim, cells, center_id


def test_y_connector_bonds_center_to_each_beam_only():
    sim, cells, _ = _y_connector_sim()

    atoms = {cell: Atom(AtomType.BASIC) for cell in cells}
    for cell, atom in atoms.items():
        sim.board.place_atom(cell, atom)

    sim.next_step()

    center_atom = atoms[cells[0]]
    # Exactly the three center<->beam bonds.
    connected = [a for _, a in center_atom.iter_connections()]
    assert len(connected) == 3
    assert all(connected.count(sim.board.get_atom(cell)) == 1 for cell in cells[1:])
    # No beam<->beam bonds: each beam connects only to the center atom.
    for beam_cell in cells[1:]:
        beam_atom = sim.board.get_atom(beam_cell)
        assert [a for _, a in beam_atom.iter_connections()] == [center_atom]


# ---------------------------------------------------------------------------
# 3. Linked entrances spawn a bonded molecule
# ---------------------------------------------------------------------------


def _y_entrance_sim(center=Hex(3, 3)) -> tuple[Simulator, list[Hex]]:  # noqa: B008
    sim = Simulator((8, 8))
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)
    center_id = _add(sim, center, ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    beam_ids = [_add(sim, _offset_by(center, r), ComponentType.ENTRANCE, atom_type=AtomType.BASIC) for r in (0, 2, 4)]
    for bid in beam_ids:
        assert sim.connect_components(center_id, bid) is True
    cells = [center, *(_offset_by(center, r) for r in (0, 2, 4))]
    return sim, cells


def test_linked_entrances_spawn_bonded_molecule():
    sim, cells = _y_entrance_sim()

    sim.next_step()

    center_atom = sim.board.get_atom(cells[0])
    assert center_atom is not None
    spawned = {sim.board.get_atom(cell) for cell in cells}
    assert len(spawned) == 4
    assert None not in spawned
    assert len(list(center_atom.iter_connections())) == 3

    # Second step: no duplicates, bonds intact.
    sim.next_step()

    assert len(sim.board.atoms) == 4
    assert len(list(center_atom.iter_connections())) == 3


# ---------------------------------------------------------------------------
# 4. Multi-exit exact cover
# ---------------------------------------------------------------------------


def _y_exit_sim(center=Hex(3, 3)) -> tuple[Simulator, list[Hex]]:  # noqa: B008
    sim = Simulator((8, 8))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    center_id = _add(sim, center, ComponentType.EXIT, atom_type=AtomType.BASIC)
    beam_ids = [_add(sim, _offset_by(center, r), ComponentType.EXIT, atom_type=AtomType.BASIC) for r in (0, 2, 4)]
    for bid in beam_ids:
        assert sim.connect_components(center_id, bid) is True
    cells = [center, *(_offset_by(center, r) for r in (0, 2, 4))]
    return sim, cells


def _place_bonded_y(sim: Simulator, cells: list[Hex]) -> dict[Hex, Atom]:
    atoms = {cell: Atom(AtomType.BASIC) for cell in cells}
    for cell, atom in atoms.items():
        sim.board.place_atom(cell, atom)
    for beam_cell in cells[1:]:
        sim.board.connect_atoms(cells[0], beam_cell)
    return atoms


def test_multi_exit_consumes_exact_cover():
    sim, cells = _y_exit_sim()
    _place_bonded_y(sim, cells)

    sim.next_step()

    assert all(sim.board.get_atom(cell) is None for cell in cells)
    assert level_counter.total_finished() == 1


def test_multi_exit_rejects_subset():
    sim, cells = _y_exit_sim()
    # Cover only the center and one beam, bonded.
    subset = cells[:2]
    atoms = {cell: Atom(AtomType.BASIC) for cell in subset}
    for cell, atom in atoms.items():
        sim.board.place_atom(cell, atom)
    sim.board.connect_atoms(subset[0], subset[1])

    sim.next_step()

    assert all(sim.board.get_atom(cell) is not None for cell in subset)
    assert all(sim.board.get_atom(cell) is None for cell in cells[2:])
    assert level_counter.total_finished() == 0


def test_multi_exit_rejects_extra_bonded_atom():
    sim, cells = _y_exit_sim()
    _place_bonded_y(sim, cells)
    # Extra bonded atom elsewhere, attached to the center, making the molecule
    # cover the exit cells plus one more atom.
    extra = Atom(AtomType.BASIC)
    neighbor = _adjacent_free_neighbor(sim, cells)
    sim.board.place_atom(neighbor, extra)
    sim.board.connect_atoms(cells[0], neighbor)

    sim.next_step()

    assert all(sim.board.get_atom(cell) is not None for cell in cells)
    assert sim.board.get_atom(neighbor) is extra
    assert level_counter.total_finished() == 0


def _adjacent_free_neighbor(sim: Simulator, cells: list[Hex]) -> Hex:
    center = cells[0]
    for r in range(6):
        cand = _offset_by(center, r)
        if cand not in cells and sim.board.get_atom(cand) is None:
            return cand
    raise AssertionError("no free neighbor")


# ---------------------------------------------------------------------------
# 5. Disconnector symmetry
# ---------------------------------------------------------------------------


def test_linked_disconnectors_break_bond():
    sim = Simulator((8, 8))
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)
    center = Hex(3, 3)
    beam = _offset_by(center, 0)
    dis_a = _add(sim, center, ComponentType.DISCONNECTOR, atom_type=AtomType.BASIC)
    dis_b = _add(sim, beam, ComponentType.DISCONNECTOR, atom_type=AtomType.BASIC)
    assert sim.connect_components(dis_a, dis_b) is True

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(center, a)
    sim.board.place_atom(beam, b)
    sim.board.connect_atoms(center, beam)

    sim.next_step()

    assert list(a.iter_connections()) == []
    assert list(b.iter_connections()) == []
