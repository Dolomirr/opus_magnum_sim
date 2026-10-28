"""
Level definition model: immutable, validated starting conditions.
Pure python data.

`LevelSpec` describes a level:
- board size
- shape templates available for entrypoints
- the entrypoint placements themselves
- blueprint allow-list defining solution placements
- step limit

This data layer is fully independant  from `Simulator`
"""

from dataclasses import dataclass

from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board.hex import Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeTemplate, default_registry

_FORBIDDEN_ATOM_TYPES = frozenset({AtomType.NONE, AtomType.BASIC})


@dataclass(frozen=True)
class EntrypointSpec:
    """
    Placement of one entrypoint: named shape plus its origin cell, rotation and atom type.
    """

    kind: ComponentType
    shape: str
    pos: Hex
    atom_type: AtomType
    rotation: int = 0

    def __post_init__(self) -> None:
        if self.kind not in (ComponentType.ENTRANCE, ComponentType.EXIT):
            raise ValueError(f"EntrypointSpec kind must be ENTRANCE or EXIT, got {self.kind.name}")
        if self.atom_type in _FORBIDDEN_ATOM_TYPES:
            raise ValueError(f"EntrypointSpec atom_type must not be {self.atom_type.name.lower()!r}")
        if self.rotation not in range(6):
            raise ValueError(f"EntrypointSpec rotation must be within 0..5, got {self.rotation}")


@dataclass(frozen=True)
class LevelSpec:
    """
    Immutable, validated description of a level's starting conditions.

    `shapes` holds the shape templates that entrypoints resolve against;
    `allowed_blueprints` defines solution placements
    It can allow either local shape (entrypoints) or built-in from global default registry (components/glyphs).
    """

    size: tuple[int, int]
    shapes: tuple[ShapeTemplate, ...]
    entrypoints: tuple[EntrypointSpec, ...]
    allowed_blueprints: frozenset[str]
    steps: int

    def __post_init__(self) -> None:
        rows, cols = self.size
        if rows <= 0 or cols <= 0:
            raise ValueError(f"LevelSpec size must be positive, got {self.size!r}")
        if self.steps <= 0:
            raise ValueError(f"LevelSpec steps must be positive, got {self.steps}")

        shape_names = [shape.name for shape in self.shapes]
        if len(set(shape_names)) != len(shape_names):
            raise ValueError("LevelSpec shape names must be unique")
        shapes_by_name = {shape.name: shape for shape in self.shapes}

        if not any(ep.kind == ComponentType.ENTRANCE for ep in self.entrypoints):
            raise ValueError("LevelSpec requires at least one entrance")
        if not any(ep.kind == ComponentType.EXIT for ep in self.entrypoints):
            raise ValueError("LevelSpec requires at least one exit")

        for ep in self.entrypoints:
            shape = shapes_by_name.get(ep.shape)
            if shape is None:
                raise ValueError(f"entrypoint shape {ep.shape!r} must be defined in the spec")
            if shape.comp_type != ep.kind:
                raise ValueError(
                    f"entrypoint shape {ep.shape!r} comp_type {shape.comp_type.name} does not match kind {ep.kind.name}"
                )

        for name in self.allowed_blueprints:
            blueprint = shapes_by_name.get(name)
            if blueprint is None:
                try:
                    blueprint = default_registry.get(name)
                except KeyError as exc:
                    raise ValueError(f"allowed blueprint {name!r} is unknown") from exc
            if not blueprint.implemented:
                raise ValueError(f"allowed blueprint {name!r} is not implemented")

        occupied: set[Hex] = set()
        for ep in self.entrypoints:
            for cell in _entrypoint_cells(ep, shapes_by_name[ep.shape]):
                if not (0 <= cell.r < rows and 0 <= cell.s < cols):
                    raise ValueError(f"entrypoint {ep.shape!r} cell ({cell.r}, {cell.s}) is out of bounds")
                if cell in occupied:
                    raise ValueError(f"entrypoint {ep.shape!r} cell ({cell.r}, {cell.s}) overlaps another entrypoint")
                occupied.add(cell)


def _entrypoint_cells(ep: EntrypointSpec, shape: ShapeTemplate) -> tuple[Hex, ...]:
    """
    Absolute cells occupied by `ep`, from shape's offsets rotated around the origin.

    Mirrors the simulator's `_place_shape` cell computation using pure `Hex` math.
    """
    return tuple(
        Hex(
            ep.pos.r + cell.offset.rotate_around(Hex(0, 0), ep.rotation).r,
            ep.pos.s + cell.offset.rotate_around(Hex(0, 0), ep.rotation).s,
        )
        for cell in shape.cells
    )
