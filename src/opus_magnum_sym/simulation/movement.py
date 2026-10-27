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


@dataclass
class Movement:
    """
    Records one arm action that rotates held molecule:

    - arm swinging around its base (`ARM_SWING`)
    - molecule rotating in place around the hand (`MOLECULE_PIVOT`)

    It captures this pivot, 60° rotation, and every held atom with its cell pre-move.
    Interpolation maps `t` in [0, 1] to atom's xy position along movement arc.
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
