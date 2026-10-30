"""Level definition model tests (Stage 3)."""

from dataclasses import FrozenInstanceError

import pytest
from fixtures.levels import make_level_spec
from fixtures.shapes import entrance_straight_2, exit_straight_2, straight_shape, typed_exit

from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeCell, ShapeTemplate
from opus_magnum_sym.levels import EntrypointSpec


def _entrance(**overrides) -> EntrypointSpec:
    kwargs = dict(
        kind=ComponentType.ENTRANCE,
        shape="entrance_straight_2",
        pos=Hex(2, 3),
        atom_type=AtomType.SALT,
        rotation=1,
    )
    kwargs.update(overrides)
    return EntrypointSpec(**kwargs)


def _exit(**overrides) -> EntrypointSpec:
    kwargs = dict(
        kind=ComponentType.EXIT,
        shape="exit_straight_2",
        pos=Hex(3, 2),
        atom_type=AtomType.SALT,
        rotation=2,
    )
    kwargs.update(overrides)
    return EntrypointSpec(**kwargs)


def test_valid_spec():
    spec = make_level_spec()
    assert spec.size == (6, 6)
    assert spec.steps == 30
    assert spec.allowed_blueprints == frozenset({"arm"})
    assert {ep.shape for ep in spec.entrypoints} == {"entrance_straight_2", "exit_straight_2"}
    # Entrypoint shapes are not required to appear in the allow-list.
    assert "entrance_straight_2" not in spec.allowed_blueprints
    assert "exit_straight_2" not in spec.allowed_blueprints


def test_spec_is_immutable():
    spec = make_level_spec()
    with pytest.raises(FrozenInstanceError):
        spec.steps = 1


# --- EntrypointSpec validation ---


@pytest.mark.parametrize("kind", [ComponentType.ARM, ComponentType.CONNECTOR, ComponentType.EMPTY])
def test_entrypoint_kind_must_be_entrance_or_exit(kind):
    with pytest.raises(ValueError, match="kind"):
        _entrance(kind=kind)


@pytest.mark.parametrize("atom_type", [AtomType.NONE, AtomType.BASIC])
def test_entrypoint_forbidden_atom_types(atom_type):
    with pytest.raises(ValueError, match="atom_type"):
        _entrance(atom_type=atom_type)


@pytest.mark.parametrize("rotation", [-1, 6])
def test_entrypoint_rotation_range(rotation):
    with pytest.raises(ValueError, match="rotation"):
        _entrance(rotation=rotation)


# --- LevelSpec validation ---


@pytest.mark.parametrize("size", [(0, 6), (6, 0), (-1, 6)])
def test_size_must_be_positive(size):
    with pytest.raises(ValueError, match="size"):
        make_level_spec(size=size)


@pytest.mark.parametrize("steps", [0, -3])
def test_steps_must_be_positive(steps):
    with pytest.raises(ValueError, match="steps"):
        make_level_spec(steps=steps)


def test_target_rejects_negative():
    with pytest.raises(ValueError, match="negative"):
        make_level_spec(target=-1)


def test_target_zero_normalized_to_none():
    assert make_level_spec(target=0).target is None


def test_target_rejects_non_int():
    with pytest.raises(ValueError, match="int"):
        make_level_spec(target="1")


def test_shape_names_must_be_unique():
    with pytest.raises(ValueError, match="unique"):
        make_level_spec(shapes=(entrance_straight_2(), entrance_straight_2()))


def test_entrypoint_shape_must_be_local():
    with pytest.raises(ValueError, match="defined in the spec"):
        make_level_spec(entrypoints=(_entrance(shape="not_defined"), _exit()))


def test_entrypoint_shape_comp_type_must_match():
    with pytest.raises(ValueError, match="comp_type"):
        make_level_spec(entrypoints=(_entrance(shape="exit_straight_2"), _exit()))


def test_requires_entrance():
    with pytest.raises(ValueError, match="entrance"):
        make_level_spec(entrypoints=(_exit(),))


def test_requires_exit():
    with pytest.raises(ValueError, match="exit"):
        make_level_spec(entrypoints=(_entrance(),))


def test_allow_unknown_blueprint_rejected():
    with pytest.raises(ValueError, match="unknown"):
        make_level_spec(allowed_blueprints=frozenset({"nope"}))


def test_allow_unimplemented_blueprint_rejected():
    with pytest.raises(ValueError, match="not implemented"):
        make_level_spec(allowed_blueprints=frozenset({"arm_double"}))


def test_allow_list_resolves_local_shape():
    local = straight_shape("local_connector", ComponentType.CONNECTOR)
    spec = make_level_spec(
        shapes=(entrance_straight_2(), exit_straight_2(), local),
        allowed_blueprints=frozenset({"local_connector", "arm"}),
    )
    assert "local_connector" in spec.allowed_blueprints


def test_entrypoint_cell_out_of_bounds():
    with pytest.raises(ValueError, match="out of bounds"):
        make_level_spec(entrypoints=(_entrance(pos=Hex(0, 0), rotation=0), _exit()))


def test_entrypoint_cells_non_overlapping():
    with pytest.raises(ValueError, match="overlaps"):
        make_level_spec(entrypoints=(_entrance(), _exit(pos=Hex(2, 3), rotation=1)))


# --- fixed / unfixed modes ---


def test_fixed_mode_requires_position():
    with pytest.raises(ValueError, match="requires a position"):
        make_level_spec(entrypoints=(_entrance(pos=None), _exit()))


def test_unfixed_mode_rejects_position():
    with pytest.raises(ValueError, match="must not specify a position"):
        make_level_spec(entrypoints_fixed=False, entrypoints=(_entrance(), _exit(pos=None)))


def test_unfixed_mode_allows_positionless_entrypoints():
    spec = make_level_spec(
        entrypoints_fixed=False,
        entrypoints=(_entrance(pos=None), _exit(pos=None)),
    )
    assert all(ep.pos is None for ep in spec.entrypoints)


# --- atom_type fallback requirement ---


def test_atom_type_required_for_untyped_shape():
    with pytest.raises(ValueError, match="requires atom_type"):
        make_level_spec(entrypoints=(_entrance(atom_type=None), _exit()))


def test_atom_type_optional_when_all_cells_typed():
    spec = make_level_spec(
        shapes=(entrance_straight_2(), typed_exit()),
        entrypoints=(
            _entrance(pos=Hex(1, 1), rotation=0),
            _exit(shape="typed_exit", pos=Hex(4, 4), rotation=0, atom_type=None),
        ),
    )
    assert spec.entrypoints[1].atom_type is None


# --- declared atom_types ---


def test_atom_types_reject_forbidden_values():
    with pytest.raises(ValueError, match="atom_types"):
        make_level_spec(atom_types=frozenset({AtomType.SALT, AtomType.BASIC}))


def test_atom_types_must_include_entrypoint_types():
    with pytest.raises(ValueError, match="not declared in atom_types"):
        make_level_spec(
            shapes=(entrance_straight_2(), typed_exit()),
            entrypoints=(
                _entrance(pos=Hex(1, 1), rotation=0),
                _exit(shape="typed_exit", pos=Hex(4, 4), rotation=0, atom_type=None),
            ),
            atom_types=frozenset({AtomType.SALT}),
        )


def test_atom_types_accepts_declared_superset():
    spec = make_level_spec(
        shapes=(entrance_straight_2(), typed_exit()),
        entrypoints=(
            _entrance(pos=Hex(1, 1), rotation=0),
            _exit(shape="typed_exit", pos=Hex(4, 4), rotation=0, atom_type=None),
        ),
        atom_types=frozenset({AtomType.SALT, AtomType.WATER, AtomType.FIRE}),
    )
    assert spec.atom_types == frozenset({AtomType.SALT, AtomType.WATER, AtomType.FIRE})


# --- duplicate entrypoints (copies) ---


def test_duplicate_entrypoints_same_shape_legal():
    spec = make_level_spec(
        entrypoints=(
            _entrance(pos=Hex(1, 1), rotation=0),
            _exit(pos=Hex(3, 3), rotation=0),
            _exit(pos=Hex(4, 4), rotation=0),
        ),
    )
    assert [ep.shape for ep in spec.entrypoints].count("exit_straight_2") == 2


# --- typed-cell kwargs validation ---


def test_shape_rejects_unknown_typed_cell_key():
    bad = ShapeTemplate(
        name="bad_exit",
        comp_type=ComponentType.EXIT,
        cells=(ShapeCell(offset=Hex(0, 0), kwargs={"bogus": 1}),),
        links=(),
    )
    with pytest.raises(ValueError, match="unknown typed-cell parameter"):
        make_level_spec(shapes=(entrance_straight_2(), exit_straight_2(), bad))


def test_shape_rejects_non_atom_type_typed_cell():
    bad = ShapeTemplate(
        name="bad_exit",
        comp_type=ComponentType.EXIT,
        cells=(ShapeCell(offset=Hex(0, 0), kwargs={"atom_type": "salt"}),),
        links=(),
    )
    with pytest.raises(ValueError, match="invalid atom_type"):
        make_level_spec(shapes=(entrance_straight_2(), exit_straight_2(), bad))


def test_shape_rejects_forbidden_typed_cell():
    bad = ShapeTemplate(
        name="bad_exit",
        comp_type=ComponentType.EXIT,
        cells=(ShapeCell(offset=Hex(0, 0), kwargs={"atom_type": AtomType.BASIC}),),
        links=(),
    )
    with pytest.raises(ValueError, match="invalid atom_type"):
        make_level_spec(shapes=(entrance_straight_2(), exit_straight_2(), bad))
