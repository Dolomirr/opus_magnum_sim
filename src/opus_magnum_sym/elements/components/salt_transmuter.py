from typing import TYPE_CHECKING

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
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


class SaltTransmuter(Component):
    """
    Single-cell transmuter that turns an elemental atom (fire, water, air, earth)
    sitting on its cell into salt. Non-elemental atoms are left untouched.

    The atom is mutated in place so it works for atoms bonded into a molecule
    without disturbing the molecule's bonds.
    """

    def __init__(self, idx: int, pos, rotation: int = 0) -> None:
        super().__init__(
            idx=idx,
            type=ComponentType.SALT_TRANSMUTER,
            pos=pos,
            rotation=rotation,
        )

    def _execute(self, board: Board, action_type: StepActionType) -> None:
        atom = board.get_atom(self.pos)
        if atom is None or atom.type not in _ELEMENTAL_TYPES:
            return
        atom.type = AtomType.SALT
        self.log_action("transmuted", "elemental atom into salt", self.pos)
