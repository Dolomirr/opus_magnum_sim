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
from typing import cast

from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board.hex import Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeTemplate, default_registry

_FORBIDDEN_ATOM_TYPES = frozenset({AtomType.NONE, AtomType.BASIC})


@dataclass(frozen=True)
class EntrypointSpec:
    """
    Placement of one entrypoint: named shape plus its origin cell, rotation and atom type.

    `pos` is `None` when the level leaves placement to the solution
    (`entrypoints_fixed` is false); `atom_type` is `None` when every cell of the
    shape carries its own typed `atom_type` and no fallback is needed.
    """

    kind: ComponentType
    shape: str
    pos: Hex | None = None
    atom_type: AtomType | None = None
    rotation: int = 0

    def __post_init__(self) -> None:
        if self.kind not in (ComponentType.ENTRANCE, ComponentType.EXIT):
            raise ValueError(f"EntrypointSpec kind must be ENTRANCE or EXIT, got {self.kind.name}")
        if self.atom_type is not None and self.atom_type in _FORBIDDEN_ATOM_TYPES:
            raise ValueError(f"EntrypointSpec atom_type must not be {self.atom_type.name.lower()!r}")
        if self.rotation not in range(6):
            raise ValueError(f"EntrypointSpec rotation must be within 0..5, got {self.rotation}")


def entrance(shape: str, pos: Hex | None = None, rotation: int = 0) -> EntrypointSpec:
    """
    Define an entrance entrypoint from a locally defined shape.

    `pos` is `None` for solution-placed entrypoint (`entrypoints_fixed` false).
    Atom types are carried by the shape's typed cells,
    so no `atom_type` placeholder is required here.
    """
    return EntrypointSpec(kind=ComponentType.ENTRANCE, shape=shape, pos=pos, rotation=rotation)


def exit(shape: str, pos: Hex | None = None, rotation: int = 0) -> EntrypointSpec:
    """
    Define an exit entrypoint from a locally defined shape.

    `pos` is `None` for solution-placed entrypoint (`entrypoints_fixed` false).
    Atom types are carried by the shape's typed cells,
    so no `atom_type` placeholder is required here.
    """
    return EntrypointSpec(kind=ComponentType.EXIT, shape=shape, pos=pos, rotation=rotation)


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
    entrypoints_fixed: bool = True
    atom_types: frozenset[AtomType] = frozenset()

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

        if any(atom_type in _FORBIDDEN_ATOM_TYPES for atom_type in self.atom_types):
            raise ValueError("LevelSpec atom_types must not include none or basic")

        self._validate_typed_cells()

        for ep in self.entrypoints:
            shape = shapes_by_name.get(ep.shape)
            if shape is None:
                raise ValueError(f"entrypoint shape {ep.shape!r} must be defined in the spec")
            if shape.comp_type != ep.kind:
                raise ValueError(
                    f"entrypoint shape {ep.shape!r} comp_type {shape.comp_type.name} does not match kind {ep.kind.name}"
                )
            if self.entrypoints_fixed and ep.pos is None:
                raise ValueError(f"entrypoint {ep.shape!r} requires a position in fixed mode")
            if not self.entrypoints_fixed and ep.pos is not None:
                raise ValueError(f"entrypoint {ep.shape!r} must not specify a position in unfixed mode")
            if any("atom_type" not in cell.kwargs for cell in shape.cells) and ep.atom_type is None:
                raise ValueError(f"entrypoint {ep.shape!r} requires atom_type because its shape has untyped cells")
            self._validate_declared_atom_types(ep, shape)

        for name in self.allowed_blueprints:
            blueprint = shapes_by_name.get(name)
            if blueprint is None:
                try:
                    blueprint = default_registry.get(name)
                except KeyError as exc:
                    raise ValueError(f"allowed blueprint {name!r} is unknown") from exc
            if not blueprint.implemented:
                raise ValueError(f"allowed blueprint {name!r} is not implemented")

        if self.entrypoints_fixed:
            occupied: set[Hex] = set()
            for ep in self.entrypoints:
                for cell in _entrypoint_cells(ep, shapes_by_name[ep.shape]):
                    if not (0 <= cell.r < rows and 0 <= cell.s < cols):
                        raise ValueError(f"entrypoint {ep.shape!r} cell ({cell.r}, {cell.s}) is out of bounds")
                    if cell in occupied:
                        raise ValueError(
                            f"entrypoint {ep.shape!r} cell ({cell.r}, {cell.s}) overlaps another entrypoint"
                        )
                    occupied.add(cell)

    def _validate_typed_cells(self) -> None:
        """
        Reject unknown typed-cell kwargs and non-`AtomType`/forbidden typed values.

        `ShapeTemplate` does not validate `ShapeCell.kwargs`, so the level spec
        is the layer that enforces typed-cell correctness.
        """
        # ladders goes brrr
        for shape in self.shapes:
            for cell in shape.cells:
                for key, value in cell.kwargs.items():
                    if key == "atom_type":
                        if not isinstance(value, AtomType) or value in _FORBIDDEN_ATOM_TYPES:
                            raise ValueError(
                                f"shape {shape.name!r} cell {cell.offset!r} has invalid atom_type {value!r}"
                            )
                    else:
                        raise ValueError(
                            f"shape {shape.name!r} cell {cell.offset!r} has unknown typed-cell parameter {key!r}"
                        )

    def _validate_declared_atom_types(self, ep: EntrypointSpec, shape: ShapeTemplate) -> None:
        """
        Reject an entrypoint whose atom types (fallback plus typed cells) are not
        all members of `self.atom_types`, when a declaration was provided.
        """
        if not self.atom_types:
            return
        entrypoint_types: set[AtomType] = set()
        if ep.atom_type is not None:
            entrypoint_types.add(ep.atom_type)
        for cell in shape.cells:
            atom_type = cell.kwargs.get("atom_type")
            if isinstance(atom_type, AtomType):
                entrypoint_types.add(atom_type)
        for atom_type in entrypoint_types:
            if atom_type not in self.atom_types:
                raise ValueError(
                    f"entrypoint {ep.shape!r} atom_type {atom_type.name.lower()!r} is not declared in atom_types"
                )


def _entrypoint_cells(ep: EntrypointSpec, shape: ShapeTemplate) -> tuple[Hex, ...]:
    """
    Absolute cells occupied by `ep`, from shape's offsets rotated around its origin.

    Mirrors simulator's `_place_shape` cell computation using pure `Hex` math.
    Only valid in fixed mode, where `ep.pos` is guaranteed.
    """
    pos = cast(Hex, ep.pos)
    return tuple(
        Hex(
            pos.r + cell.offset.rotate_around(Hex(0, 0), ep.rotation).r,
            pos.s + cell.offset.rotate_around(Hex(0, 0), ep.rotation).s,
        )
        for cell in shape.cells
    )
