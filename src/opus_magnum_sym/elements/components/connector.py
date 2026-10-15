from collections.abc import Iterator
from itertools import combinations
from typing import TYPE_CHECKING

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board.directions import Direction
from opus_magnum_sym.elements.components.base_component import Component, ComponentType

if TYPE_CHECKING:
    from opus_magnum_sym.elements.board import Board, Hex


def _adjacent_pairs(cells: list[Hex]) -> Iterator[tuple[Hex, Hex]]:
    for a, b in combinations(cells, 2):
        if Direction().are_adjacent(a, b):
            yield a, b


def _atom_matches(board: Board, cell: Hex, atom_type: AtomType) -> bool:
    atom = board.get_atom(cell)
    return atom is not None and atom.type == atom_type


class Connector(Component):
    """
    Bonds atoms sitting on this glyph and its connected glyph partners.
    """

    def __init__(
        self,
        idx: int,
        pos: Hex,
        atom_type: AtomType,
        rotation: int = 0,
    ) -> None:
        super().__init__(
            idx=idx,
            type=ComponentType.CONNECTOR,
            pos=pos,
            rotation=rotation,
        )
        self.atom_type = atom_type
        self.group: list[Component] = []

    def _execute(self, board: Board, action_type: StepActionType) -> None:
        # operate independently (unlike exits) on whatever group subset are above them
        cells = [self.pos, *(c.pos for c in self.group)]
        for a, b in _adjacent_pairs(cells):
            if _atom_matches(board, a, self.atom_type) and _atom_matches(
                board, b, self.atom_type
            ):
                board.connect_atoms(a, b)


class Disconnector(Component):
    """
    Breaks bonds between atoms sitting on this glyph and its connected glyph partners.
    """

    def __init__(
        self,
        idx: int,
        pos: Hex,
        atom_type: AtomType,
        rotation: int = 0,
    ) -> None:
        super().__init__(
            idx=idx,
            type=ComponentType.DISCONNECTOR,
            pos=pos,
            rotation=rotation,
        )
        self.atom_type = atom_type
        self.group: list[Component] = []

    def _execute(self, board: Board, action_type: StepActionType) -> None:
        cells = [self.pos, *(c.pos for c in self.group)]
        for a, b in _adjacent_pairs(cells):
            if _atom_matches(board, a, self.atom_type) and _atom_matches(
                board, b, self.atom_type
            ):
                board.disconnect_atoms(a, b)
