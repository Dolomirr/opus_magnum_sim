import pytest  # noqa: INP001

from opus_magnum_sym.elements.board import Direction, Hex
from opus_magnum_sym.elements.components import (
    ComponentType,
    ManipulatorSpec,
    ShapeCell,
    ShapeTemplate,
    get_blueprint,
    list_blueprints,
    register_blueprint,
)


def _adj_offset(rotation: int) -> Hex:
    return Direction().from_rotation(rotation).apply(Hex(0, 0))


class TestTemplateValidation:
    def test_missing_origin(self):
        cells = (ShapeCell(offset=_adj_offset(0)),)
        with pytest.raises(ValueError, match="origin"):
            ShapeTemplate("x", ComponentType.CONNECTOR, cells, ())

    def test_duplicate_offsets(self):
        cells = (
            ShapeCell(offset=Hex(0, 0)),
            ShapeCell(offset=_adj_offset(0)),
            ShapeCell(offset=_adj_offset(0)),
        )
        with pytest.raises(ValueError, match="distinct"):
            ShapeTemplate("x", ComponentType.CONNECTOR, cells, ())

    def test_non_adjacent_link(self):
        cells = (ShapeCell(offset=Hex(0, 0)), ShapeCell(offset=Hex(2, 2)))
        with pytest.raises(ValueError, match="not adjacent"):
            ShapeTemplate("x", ComponentType.CONNECTOR, cells, ((0, 1),))

    def test_link_index_out_of_range(self):
        cells = (ShapeCell(offset=Hex(0, 0)), ShapeCell(offset=_adj_offset(0)))
        with pytest.raises(ValueError, match="out of range"):
            ShapeTemplate("x", ComponentType.CONNECTOR, cells, ((0, 2),))

    def test_self_link_rejected(self):
        cells = (ShapeCell(offset=Hex(0, 0)),)
        with pytest.raises(ValueError, match="distinct"):
            ShapeTemplate("x", ComponentType.CONNECTOR, cells, ((0, 0),))

    def test_bad_rotation_set(self):
        cells = (ShapeCell(offset=Hex(0, 0)),)
        with pytest.raises(ValueError, match=r"0\.\.5"):
            ShapeTemplate("x", ComponentType.CONNECTOR, cells, (), allowed_rotations=frozenset({6}))

    def test_non_entrypoint_comp_type(self):
        cells = (ShapeCell(offset=Hex(0, 0)),)
        with pytest.raises(ValueError, match="entrypoint"):
            ShapeTemplate("x", ComponentType.ARM, cells, ())

    def test_valid_template_accepted(self):
        cells = (ShapeCell(offset=Hex(0, 0)), ShapeCell(offset=_adj_offset(0)))
        tpl = ShapeTemplate("ok", ComponentType.CONNECTOR, cells, ((0, 1),))
        assert tpl.name == "ok"


class TestSpecValidation:
    def test_bad_arm_count(self):
        with pytest.raises(ValueError, match="arm_count"):
            ManipulatorSpec("x", 4, False, 1, 6)

    def test_inverted_length_bounds(self):
        with pytest.raises(ValueError, match="length"):
            ManipulatorSpec("x", 1, False, 6, 5)

    def test_zero_min_length(self):
        with pytest.raises(ValueError, match="length"):
            ManipulatorSpec("x", 1, False, 0, 6)


class TestRegistry:
    def test_duplicate_name(self):
        with pytest.raises(ValueError, match="already registered"):
            register_blueprint(ManipulatorSpec("arm", 1, False, 1, 6))

    def test_unknown_name(self):
        with pytest.raises(KeyError, match="does_not_exist"):
            get_blueprint("does_not_exist")


class TestBuiltins:
    def test_arm(self):
        spec = get_blueprint("arm")
        assert isinstance(spec, ManipulatorSpec)
        assert spec.arm_count == 1
        assert spec.extendable is False
        assert (spec.min_length, spec.max_length) == (1, 6)
        assert spec.implemented is True

    def test_gated_presets_not_implemented(self):
        for name in ("arm_double", "arm_triple", "arm_hex"):
            spec = get_blueprint(name)
            assert isinstance(spec, ManipulatorSpec)
            assert spec.implemented is False

    def test_arm_piston(self):
        spec = get_blueprint("arm_piston")
        assert isinstance(spec, ManipulatorSpec)
        assert spec.arm_count == 1
        assert spec.extendable is True
        assert (spec.min_length, spec.max_length) == (1, 3)
        assert spec.implemented is True

    def test_all_builtins_listed(self):
        names = {entry["name"] for entry in list_blueprints()}
        expected = {
            "connector_straight_2",
            "connector_tri",
            "connector_tri_odd",
            "entrance_straight_2",
            "exit_straight_2",
            "arm",
            "arm_piston",
            "arm_double",
            "arm_triple",
            "arm_hex",
        }
        assert expected <= names

    @pytest.mark.parametrize("name", ["connector_tri", "connector_tri_odd"])
    def test_y_template_geometry(self, name):
        tpl = get_blueprint(name)
        assert isinstance(tpl, ShapeTemplate)
        assert tpl.comp_type is ComponentType.CONNECTOR
        assert len(tpl.cells) == 4
        assert [cell.offset for cell in tpl.cells].count(Hex(0, 0)) == 1
        beam_offsets = [cell.offset for cell in tpl.cells if cell.offset != Hex(0, 0)]
        assert len(beam_offsets) == 3
        assert len(tpl.links) == 3
        direction = Direction()
        # Beams are mutually non-adjacent.
        for a, b in ((0, 1), (0, 2), (1, 2)):
            assert not direction.are_adjacent(beam_offsets[a], beam_offsets[b])
        # Every link is adjacent.
        for i, j in tpl.links:
            assert direction.are_adjacent(tpl.cells[i].offset, tpl.cells[j].offset)

    def test_y_rotation_constraints(self):
        assert get_blueprint("connector_tri").allowed_rotations == frozenset({0, 2, 4})
        assert get_blueprint("connector_tri_odd").allowed_rotations == frozenset({1, 3, 5})

    def test_straight_view(self):
        tpl = get_blueprint("connector_straight_2")
        assert isinstance(tpl, ShapeTemplate)
        assert tpl.comp_type is ComponentType.CONNECTOR
        assert len(tpl.cells) == 2
        assert tpl.links == ((0, 1),)
        assert tpl.allowed_rotations is None
