"""
Loader for `.oml` level files into a `LevelSpec`.

Mirrors `SimInterpreter`'s shlex-per-line style, but raises `LevelLoadError`
with the offending line number instead of printing and continuing.
"""

import re
import shlex
from pathlib import Path

from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeCell, ShapeTemplate
from opus_magnum_sym.levels.spec import EntrypointSpec, LevelSpec

# One shape cell: `(r,s)` optionally followed by `:atom_type`.
_CELL_RE = re.compile(r"\((-?\d+),(-?\d+)\)(?::([A-Za-z_][A-Za-z0-9_]*))?")


class LevelLoadError(Exception):
    """Raised when a level file cannot be parsed or is invalid."""

    def __init__(self, message: str, line: int | None = None) -> None:
        self.message = message
        self.line = line
        if line is None:
            super().__init__(message)
        else:
            super().__init__(f"line {line}: {message}")


def _parse_cells(value: str) -> tuple[ShapeCell, ...]:
    value = value.strip()
    if not value:
        raise ValueError("cells cannot be empty")
    cells: list[ShapeCell] = []
    cursor = 0
    for match in _CELL_RE.finditer(value):
        if value[cursor : match.start()].strip(", "):
            raise ValueError(f"malformed cells in {value!r}")
        cursor = match.end()
        kwargs: dict[str, object] = {}
        type_name = match.group(3)
        if type_name is not None:
            try:
                kwargs["atom_type"] = getattr(AtomType, type_name.upper())
            except AttributeError:
                raise ValueError(f"unknown atom_type {type_name!r}") from None
        cells.append(
            ShapeCell(offset=Hex(int(match.group(1)), int(match.group(2))), kwargs=kwargs)
        )
    if value[cursor:].strip(", "):
        raise ValueError(f"malformed cells in {value!r}")
    if not cells:
        raise ValueError("cells cannot be empty")
    return tuple(cells)


def _parse_links(value: str) -> tuple[tuple[int, int], ...]:
    value = value.strip()
    if not value:
        return ()
    links = []
    for part in value.split(","):
        a, b = part.split("-")
        links.append((int(a), int(b)))
    return tuple(links)


def _parse_rotations(value: str) -> frozenset[int]:
    return frozenset(int(rotation) for rotation in value.split(","))


class LevelLoader:
    """
    Accumulates level commands and builds a validated `LevelSpec`.
    """

    def __init__(self) -> None:
        self._size: tuple[int, int] | None = None
        self._steps: int | None = None
        self._allowed: list[str] = []
        self._shapes: dict[str, ShapeTemplate] = {}
        self._entrypoints: list[EntrypointSpec] = []
        self._entrypoints_fixed = True
        self._atom_types: frozenset[AtomType] = frozenset()
        self._dispatch = {
            "size": self._handle_size,
            "steps": self._handle_steps,
            "allow": self._handle_allow,
            "shape": self._handle_shape,
            "entrance": self._handle_entrance,
            "exit": self._handle_exit,
            "atom_types": self._handle_atom_types,
            "entrypoints_fixed": self._handle_entrypoints_fixed,
        }

    def load_file(self, path: str | Path) -> LevelSpec:
        with Path(path).open("r") as f:
            return self.load(f.read())

    def load(self, text: str) -> LevelSpec:
        for line_num, line in enumerate(text.splitlines(), 1):
            self._evaluate_line(line, line_num)
        return self._build()

    def _evaluate_line(self, line: str, line_num: int) -> None:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            return
        tokens = shlex.split(line, comments=True)
        if not tokens:
            return
        command = tokens[0].lower()
        handler = self._dispatch.get(command)
        if handler is None:
            raise LevelLoadError(f"unknown command {command!r}", line_num)
        try:
            handler(tokens[1:])
        except LevelLoadError:
            raise
        except (ValueError, AttributeError, IndexError) as exc:
            raise LevelLoadError(str(exc), line_num) from exc

    def _handle_size(self, args: list[str]) -> None:
        if len(args) != 2:
            raise ValueError("size expects <rows> <cols>")
        self._size = (int(args[0]), int(args[1]))

    def _handle_steps(self, args: list[str]) -> None:
        if len(args) != 1:
            raise ValueError("steps expects <n>")
        self._steps = int(args[0])

    def _handle_allow(self, args: list[str]) -> None:
        if not args:
            raise ValueError("allow expects at least one blueprint name")
        self._allowed.extend(args)

    def _handle_atom_types(self, args: list[str]) -> None:
        if not args:
            raise ValueError("atom_types expects at least one atom type")
        atom_types = set()
        for name in args:
            try:
                atom_types.add(getattr(AtomType, name.upper()))
            except AttributeError:
                raise ValueError(f"unknown atom_type {name!r}") from None
        self._atom_types = frozenset(atom_types)

    def _handle_entrypoints_fixed(self, args: list[str]) -> None:
        if len(args) != 1 or args[0] not in ("0", "1"):
            raise ValueError("entrypoints_fixed expects 0 or 1")
        self._entrypoints_fixed = args[0] == "1"

    def _handle_shape(self, args: list[str]) -> None:
        if len(args) < 4:
            raise ValueError("shape expects <name> <kind> cells=... links=... [rotations=...]")
        name = args[0]
        try:
            comp_type = getattr(ComponentType, args[1].upper())
        except AttributeError:
            raise ValueError(f"unknown shape kind {args[1]!r}") from None
        if name in self._shapes:
            raise ValueError(f"duplicate shape name {name!r}")

        cells = None
        links = None
        rotations = None
        for arg in args[2:]:
            key, value = arg.split("=", 1)
            if key == "cells":
                cells = _parse_cells(value)
            elif key == "links":
                links = _parse_links(value)
            elif key == "rotations":
                rotations = _parse_rotations(value)
            else:
                raise ValueError(f"unknown shape parameter {key!r}")

        if cells is None or links is None:
            raise ValueError("shape requires cells=... and links=...")

        self._shapes[name] = ShapeTemplate(
            name=name,
            comp_type=comp_type,
            cells=cells,
            links=links,
            allowed_rotations=rotations,
        )

    def _handle_entrance(self, args: list[str]) -> None:
        self._add_entrypoint(ComponentType.ENTRANCE, args)

    def _handle_exit(self, args: list[str]) -> None:
        self._add_entrypoint(ComponentType.EXIT, args)

    def _add_entrypoint(self, kind: ComponentType, args: list[str]) -> None:
        if not args:
            raise ValueError(
                f"{kind.name.lower()} expects <shape> [<r> <s>] [rotation=k] [atom_type=<type>]"
            )
        shape = args[0]
        remaining = args[1:]

        pos: Hex | None = None
        rotation = 0
        atom_type: AtomType | None = None
        # Positioned form: the two tokens after <shape> are integers r, s.
        if (
            len(remaining) >= 2
            and remaining[0].lstrip("-").isdigit()
            and remaining[1].lstrip("-").isdigit()
        ):
            pos = Hex(int(remaining[0]), int(remaining[1]))
            options = remaining[2:]
        else:
            options = remaining

        for arg in options:
            key, value = arg.split("=", 1)
            if key == "rotation":
                rotation = int(value)
            elif key == "atom_type":
                try:
                    atom_type = getattr(AtomType, value.upper())
                except AttributeError:
                    raise ValueError(f"unknown atom_type {value!r}") from None
            else:
                raise ValueError(f"unknown entrypoint parameter {key!r}")
        self._entrypoints.append(
            EntrypointSpec(
                kind=kind,
                shape=shape,
                pos=pos,
                atom_type=atom_type,
                rotation=rotation,
            )
        )

    def _build(self) -> LevelSpec:
        if self._size is None:
            raise LevelLoadError("missing 'size' command")
        if self._steps is None:
            raise LevelLoadError("missing 'steps' command")
        try:
            return LevelSpec(
                size=self._size,
                shapes=tuple(self._shapes.values()),
                entrypoints=tuple(self._entrypoints),
                allowed_blueprints=frozenset(self._allowed),
                steps=self._steps,
                entrypoints_fixed=self._entrypoints_fixed,
                atom_types=self._atom_types,
            )
        except ValueError as exc:
            raise LevelLoadError(str(exc)) from exc
