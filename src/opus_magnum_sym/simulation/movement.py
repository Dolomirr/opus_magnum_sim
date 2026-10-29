"""
Movement model for spatial collision detection.

"""

from dataclasses import dataclass, field
from enum import Enum, auto

from opus_magnum_sym.elements.atoms.atom import Atom
from opus_magnum_sym.elements.board.geometry import hex_to_xy, rotate_offset
from opus_magnum_sym.elements.board.hex import Hex


class MovementKind(Enum):
    ARM_SWING = auto()
    """whole arm rotates around the base"""
    MOLECULE_PIVOT = auto()
    """molecule rotates in place around the hand"""
    HAND_SLIDE = auto()
    """held molecule slides along the arm axis (extend/retract)"""


@dataclass
class Movement:
    """
    Records one arm action that moves held molecule:

    - arm swinging around its base (`ARM_SWING`)
    - molecule rotating in place around the hand (`MOLECULE_PIVOT`)
    - hand sliding along the arm axis (`HAND_SLIDE`)

    It captures pivot/axis, 60° rotation (or linear slide offset), and every
    held atom with its cell pre-move. Interpolation maps `t` in [0, 1] to the
    atom's xy position along the movement arc/line.
    """

    owner_id: int
    kind: MovementKind
    pivot: Hex
    rotation_steps: int
    atoms: list[tuple[Hex, Atom]]  # (pre-move cell, atom instance)
    slide_delta: Hex = field(default_factory=lambda: Hex(0, 0))  # linear offset for HAND_SLIDE

    def atom_xy(self, cell: Hex, t: float) -> tuple[float, float]:
        """
        Return the xy position of the atom that started at `cell` at progress `t`.

        Delta of hex's pivoting mapped to xy, rotated and added to the pivot's xy *center*.
        `HAND_SLIDE` instead interpolates linearly from `cell` to `cell + slide_delta`.
        """
        if self.kind is MovementKind.HAND_SLIDE:
            start = hex_to_xy(cell)
            end = hex_to_xy(Hex(cell.r + self.slide_delta.r, cell.s + self.slide_delta.s))
            return (
                start[0] + (end[0] - start[0]) * t,
                start[1] + (end[1] - start[1]) * t,
            )
        pivot_xy = hex_to_xy(self.pivot)
        atom_center = hex_to_xy(cell)
        offset = (atom_center[0] - pivot_xy[0], atom_center[1] - pivot_xy[1])
        rotated = rotate_offset(offset, self.rotation_steps * t)  # rotation_steps * 60° * t
        return (pivot_xy[0] + rotated[0], pivot_xy[1] + rotated[1])

    def swept_cells(self) -> set[Hex]:
        """
        Cells every held atom passes through at cell granularity.

        Rotation movements adds to cells counter start cell and each 60° landing cell;
        `HAND_SLIDE` adds start and cells.
        """
        cells: set[Hex] = {cell for cell, _atom in self.atoms}
        if self.kind is MovementKind.HAND_SLIDE:
            for cell, _atom in self.atoms:
                cells.add(Hex(cell.r + self.slide_delta.r, cell.s + self.slide_delta.s))
            return cells

        sign = 1 if self.rotation_steps >= 0 else -1
        for step in range(1, abs(self.rotation_steps) + 1):
            cells.update(cell.rotate_around(self.pivot, sign * step) for cell, _atom in self.atoms)
        return cells

