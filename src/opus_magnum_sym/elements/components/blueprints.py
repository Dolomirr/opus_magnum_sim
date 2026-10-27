"""
High-level placement blueprints: shape templates and manipulator specs.

Definition layer on top of existing single-hex primitives.
Placed `ShapeTemplate` exists at runtime as N primitive components
connected through `ConnectionGraph`.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from opus_magnum_sym.elements.board.directions import Direction
from opus_magnum_sym.elements.board.hex import Hex
from opus_magnum_sym.elements.components.base_component import ComponentType

_SHAPE_COMPONENT_TYPES = frozenset(
    {
        ComponentType.ENTRANCE,
        ComponentType.EXIT,
        ComponentType.CONNECTOR,
        ComponentType.DISCONNECTOR,
    }
)


@dataclass(frozen=True)
class ShapeCell:
    """
    Single-hex cell in a`ShapeTemplate`.
    """

    offset: Hex
    kwargs: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ShapeTemplate:
    """
    Multi-cell group of single-hex components with pre-wired links.
    """

    name: str
    comp_type: ComponentType
    cells: tuple[ShapeCell, ...]
    links: tuple[tuple[int, int], ...]
    implemented: bool = True
    allowed_rotations: frozenset[int] | None = None

    def __post_init__(self) -> None:
        if self.comp_type not in _SHAPE_COMPONENT_TYPES:
            raise ValueError(f"ShapeTemplate comp_type must be an entrypoint kind, got {self.comp_type}")

        offsets = [cell.offset for cell in self.cells]
        if offsets.count(Hex(0, 0)) != 1:
            raise ValueError("ShapeTemplate must have exactly one origin cell at Hex(0, 0)")
        if len(set(offsets)) != len(offsets):
            raise ValueError("ShapeTemplate cell offsets must be distinct")
        if self.allowed_rotations is not None and any(r not in range(6) for r in self.allowed_rotations):
            raise ValueError("allowed_rotations entries must be within 0..5")

        direction = Direction()
        for a, b in self.links:
            if a == b:
                raise ValueError(f"link pair must reference distinct cells, got ({a}, {b})")
            if not (0 <= a < len(self.cells) and 0 <= b < len(self.cells)):
                raise ValueError(f"link index {a} or {b} out of range")
            if not direction.are_adjacent(self.cells[a].offset, self.cells[b].offset):
                raise ValueError(
                    f"link ({a}, {b}) cells are not adjacent: " +
                    f"{self.cells[a].offset} and {self.cells[b].offset}"
                )  # fmt: skip


@dataclass(frozen=True)
class ManipulatorSpec:
    """
    Capability descriptor for arm variant.
    """

    name: str
    arm_count: int
    extendable: bool
    min_length: int
    max_length: int
    implemented: bool = True

    def __post_init__(self) -> None:
        if self.arm_count not in {1, 2, 3, 6}:
            raise ValueError(f"arm_count must be one of {{1, 2, 3, 6}}, got {self.arm_count}")
        if not 1 <= self.min_length <= self.max_length:
            raise ValueError(
                f"invalid length bounds {self.min_length}..{self.max_length}; require 1 <= min_length <= max_length"
            )


_blueprints: dict[str, ShapeTemplate | ManipulatorSpec] = {}


def register_blueprint(blueprint: ShapeTemplate | ManipulatorSpec) -> None:
    """
    Register blueprint.
    Raises ``ValueError`` on duplicated name.
    """
    if blueprint.name in _blueprints:
        raise ValueError(f"blueprint already registered: {blueprint.name!r}")
    _blueprints[blueprint.name] = blueprint


def get_blueprint(name: str) -> ShapeTemplate | ManipulatorSpec:
    """
    Return the blueprint registered under gven name.
    """
    try:
        return _blueprints[name]
    except KeyError as exc:
        raise KeyError(f"unknown blueprint: {name!r}") from exc


def list_blueprints() -> list[dict]:
    """
    Return one entry per registered blueprint: name and implemented flag.
    """
    return [{"name": name, "implemented": blueprint.implemented} for name, blueprint in _blueprints.items()]


def _beam(rotation: int, **kwargs) -> ShapeCell:
    return ShapeCell(offset=Direction().from_rotation(rotation).apply(Hex(0, 0)), kwargs=kwargs)


def _y_template(
    name: str,
    comp_type: ComponentType,
    allowed_rotations: frozenset[int],
    implemented: bool = True,
) -> ShapeTemplate:
    beams = tuple(_beam(r) for r in (0, 2, 4))
    cells = (ShapeCell(offset=Hex(0, 0)), *beams)
    links = tuple((0, i) for i in range(1, len(cells)))
    return ShapeTemplate(
        name=name,
        comp_type=comp_type,
        cells=cells,
        links=links,
        implemented=implemented,
        allowed_rotations=allowed_rotations,
    )


def _straight_template(name: str, comp_type: ComponentType) -> ShapeTemplate:
    cells = (ShapeCell(offset=Hex(0, 0)), _beam(0))
    return ShapeTemplate(
        name=name,
        comp_type=comp_type,
        cells=cells,
        links=((0, 1),),
        implemented=True,
        allowed_rotations=None,
    )


for _tpl in (
    _straight_template("connector_straight_2", ComponentType.CONNECTOR),
    _y_template("connector_tri", ComponentType.CONNECTOR, frozenset({0, 2, 4})),
    _y_template("connector_tri_odd", ComponentType.CONNECTOR, frozenset({1, 3, 5})),
    _straight_template("entrance_straight_2", ComponentType.ENTRANCE),
    _straight_template("exit_straight_2", ComponentType.EXIT),
):
    register_blueprint(_tpl)

for _spec in (
    ManipulatorSpec("arm", 1, False, 1, 6, implemented=True),
    ManipulatorSpec("arm_piston", 1, True, 1, 3, implemented=True),
    ManipulatorSpec("arm_double", 2, False, 1, 6, implemented=False),
    ManipulatorSpec("arm_triple", 3, False, 1, 6, implemented=False),
    ManipulatorSpec("arm_hex", 6, False, 1, 6, implemented=False),
):
    register_blueprint(_spec)
