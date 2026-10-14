from typing import TYPE_CHECKING

from icecream import ic

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.components.base_component import Component
from opus_magnum_sym.elements.env import level_counter

if TYPE_CHECKING:
    from opus_magnum_sym.elements.board import Board, Hex


class Enter(Component):
    def __init__(
        self,
        idx: int,
        pos: Hex,
        atom_type: AtomType,
        rotation: int = 0,
    ) -> None:
        super().__init__(
            idx=idx,
            type=ComponentType.ENTRANCE,
            pos=pos,
            rotation=rotation,
        )
        self.atom_type = atom_type
        self.group: list[Component] = []

    def _execute(self, board: Board, action_type: StepActionType) -> None:
        # action_type is stale here since spawning new atoms depends on state of board
        if board.get_atom(self.pos) is None:
            board.place_atom(self.pos, Atom(self.atom_type))
            self.log_action("spawned", self.atom_type.name.lower(), self.pos)

        # TODO: [@collision] currently if cell up-to-pair is occupied by foreign molecule silently fails.

        # Bond this entrance's atom to its connected entrance partners.
        # Execute sequentially, so last spawner in a group completes every bond;
        # `connect_atoms` automatically no-ops on already bonded pairs and rejects non-adjacent cells defensively.
        for partner in self.group:
            if isinstance(partner, Enter) and board.get_atom(partner.pos) is not None:
                board.connect_atoms(self.pos, partner.pos)


class Exit(Component):
    def __init__(
        self,
        idx: int,
        pos: Hex,
        atom_type: AtomType,
        rotation: int = 0,
    ) -> None:
        super().__init__(
            idx=idx,
            type=ComponentType.EXIT,
            pos=pos,
            rotation=rotation,
        )
        self.atom_type = atom_type
        self.group: list[Component] = []

    def _execute(self, board: Board, action_type: StepActionType) -> None:
        # Single molecule must sit precisely on the cells of this exit and its connected exit partners.
        # The first member to run pops the whole molecule.
        # Others see an empty cell and return, so `CORRECT_FINISHED` increments once per delivered molecule.

        # TODO: what if molecule will be moved in between? (is it even possible?)
        # TODO: real type/bond-pattern  verification.
        exits = [self, *(c for c in self.group if isinstance(c, Exit))]
        for comp in exits:
            atom = board.get_atom(comp.pos)
            if atom is None or atom.type != comp.atom_type:
                return
        cells = [comp.pos for comp in exits]
        molecule = board.get_molecule(self.pos)
        if set(molecule) != set(cells):
            return
        board.pop_molecule(self.pos)
        level_counter.CORRECT_FINISHED += 1
        self.log_action("consumed", self.atom_type.name.lower(), self.pos)
