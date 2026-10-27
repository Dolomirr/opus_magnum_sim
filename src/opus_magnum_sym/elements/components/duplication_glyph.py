from typing import TYPE_CHECKING

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board.directions import Direction
from opus_magnum_sym.elements.board.hex import Hex
from opus_magnum_sym.elements.components.base_component import Component, ComponentType

if TYPE_CHECKING:
    from opus_magnum_sym.elements.board import Board

_ELEMENTAL_TYPES = frozenset(
    {
        AtomType.FIRE,
        AtomType.WATER,
        AtomType.AIR,
        AtomType.EARTH,
    }
)


class DuplicationGlyph(Component):
    """
    Two-cell glyph that turns salt into the elemental atom held on its exemplar cell.

    `pos` is the transmuter cell;
    exemplar cell sits one hex in the facing direction.
    Each step the glyph reads the exemplar's atom (without consuming or mutating it)
    and, when salt atom placed on the transmuter, transmutes it
    in place into that exemplar's element.
    Transmuting in place preserves any bonds, so the salt may already be in a molecule.
    """

    def __init__(self, idx: int, pos, rotation: int = 0) -> None:
        super().__init__(
            idx=idx,
            type=ComponentType.DUPLICATION_GLYPH,
            pos=pos,
            rotation=rotation,
        )

    @property
    def transmuter_pos(self) -> Hex:
        return self.pos

    @property
    def exemplar_pos(self) -> Hex:
        return Direction().from_rotation(self.rotation).apply(self.pos)

    def footprint(self) -> list[Hex]:
        return [self.transmuter_pos, self.exemplar_pos]

    def _execute(self, board: Board, action_type: StepActionType) -> None:
        exemplar = board.get_atom(self.exemplar_pos)
        if exemplar is None or exemplar.type not in _ELEMENTAL_TYPES:
            return

        salt = board.get_atom(self.transmuter_pos)
        if salt is None or salt.type is not AtomType.SALT:
            return

        salt.type = exemplar.type
        self.log_action("transmuted", f"salt into {exemplar.type.name.lower()}", self.transmuter_pos)
