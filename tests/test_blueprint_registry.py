"""Per-instance blueprint registry tests (Stage 2)."""

import pytest  # noqa: INP001
from fixtures.shapes import entrance_straight_2, exit_straight_2, straight_shape

from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import (
    BlueprintRegistry,
    ComponentType,
    get_blueprint,
    list_blueprints,
)
from opus_magnum_sym.interpreter.sim_interpreter import SimInterpreter
from opus_magnum_sym.simulation.simulator import SimulationRuntimeError, Simulator


def test_removed_poc_names_not_global():
    names = {entry["name"] for entry in list_blueprints()}
    assert "entrance_straight_2" not in names
    assert "exit_straight_2" not in names


def test_place_removed_name_fails_without_registration():
    sim = Simulator((6, 6))
    with pytest.raises(SimulationRuntimeError, match="Unknown blueprint"):
        sim.place("entrance_straight_2", Hex(2, 3), atom_type=AtomType.SALT)


def test_place_by_template_object():
    sim = Simulator((6, 6))
    record = sim.place(entrance_straight_2(), Hex(2, 3), rotation=1, atom_type=AtomType.SALT)

    assert record.blueprint == "entrance_straight_2"
    assert len(record.component_ids) == 2

    # Registered locally as a side effect, so the name now resolves.
    again = sim.place("entrance_straight_2", Hex(4, 4), atom_type=AtomType.SALT)
    assert again.blueprint == "entrance_straight_2"


def test_place_by_object_duplicate_name_rejected():
    sim = Simulator((6, 6))
    sim.place(entrance_straight_2(), Hex(2, 3), atom_type=AtomType.SALT)

    with pytest.raises(ValueError, match="already registered"):
        sim.place(entrance_straight_2(), Hex(5, 5), atom_type=AtomType.SALT)


def test_registry_isolation_two_simulators():
    sim_a = Simulator((6, 6))
    sim_b = Simulator((6, 6))
    sim_a.blueprints.register(straight_shape("shared_name", ComponentType.ENTRANCE))
    sim_b.blueprints.register(straight_shape("shared_name", ComponentType.EXIT))

    rec_a = sim_a.place("shared_name", Hex(2, 3), atom_type=AtomType.SALT)
    rec_b = sim_b.place("shared_name", Hex(2, 3), atom_type=AtomType.SALT)

    assert sim_a.entrypoints[rec_a.component_ids[0]].type is ComponentType.ENTRANCE
    assert sim_b.entrypoints[rec_b.component_ids[0]].type is ComponentType.EXIT


def test_clone_does_not_leak_into_global():
    sim = Simulator((6, 6))
    sim.blueprints.register(straight_shape("only_local", ComponentType.ENTRANCE))

    assert "only_local" in {entry["name"] for entry in sim.blueprints.list()}
    with pytest.raises(KeyError, match="only_local"):
        get_blueprint("only_local")


def test_registry_clone_is_independent():
    reg = BlueprintRegistry()
    reg.register(straight_shape("x", ComponentType.CONNECTOR))
    clone = reg.clone()
    clone.register(straight_shape("y", ComponentType.CONNECTOR))

    assert "y" in {entry["name"] for entry in clone.list()}
    with pytest.raises(KeyError, match="y"):
        reg.get("y")


def test_registry_duplicate_rejected_direct():
    reg = BlueprintRegistry()
    reg.register(straight_shape("x", ComponentType.CONNECTOR))
    with pytest.raises(ValueError, match="already registered"):
        reg.register(straight_shape("x", ComponentType.CONNECTOR))


def test_default_registry_unchanged_by_simulators():
    # The module-level default registry is not affected by any simulator's local
    # registrations; this is the guarantee `default_registry.clone()` provides.
    names_before = {entry["name"] for entry in list_blueprints()}
    sim = Simulator((6, 6))
    sim.blueprints.register(exit_straight_2())
    assert {entry["name"] for entry in list_blueprints()} == names_before


def test_dsl_place_level_local_shape():
    sim = Simulator((6, 6))
    sim.blueprints.register(entrance_straight_2())
    interp = SimInterpreter(sim)

    interp.evaluate_line("place entrance_straight_2 2 3 rotation=1 atom_type=salt")

    assert len(sim.placements) == 1
    assert sim.placements[0].blueprint == "entrance_straight_2"
    assert len(sim.placements[0].component_ids) == 2
