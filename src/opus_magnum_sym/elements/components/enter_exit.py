from itertools import combinations
from typing import TYPE_CHECKING

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board.directions import Direction
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.components.base_component import Component

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
        self.links: list[Component] = []

    def _execute(self, board: Board, action_type: StepActionType) -> None:
        # action_type is stale here since spawning new atoms depends on state of board
        if board.get_atom(self.pos) is None:
            board.place_atom(self.pos, Atom(self.atom_type))
            self.log_action("spawned", self.atom_type.name.lower(), self.pos)

        # TODO: [@collision] currently if cell up-to-pair is occupied by foreign molecule silently fails.

        # Bond this entrance's atom to its directly-linked entrance partners only,
        # so branched shape bonds along its links instead of the whole group.
        # Execute sequentially, so the last spawner in a group completes every bond;
        # `connect_atoms` automatically no-ops on already bonded pairs and rejects non-adjacent cells defensively.
        for partner in self.links:
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
        self.links: list[Component] = []

    def _execute(self, board: Board, action_type: StepActionType) -> None:
        # Single molecule must sit precisely on the cells of this exit and its connected exit partners.
        # The first member to run pops the whole molecule.
        # Others see an empty cell and return, so the cluster counter increments once per delivered molecule.

        # TODO: what if molecule will be moved in between? (is it even possible?)
        exits = [self, *(c for c in self.group if isinstance(c, Exit))]
        atoms: dict[Hex, Atom] = {}
        for comp in exits:
            atom = board.get_atom(comp.pos)
            if atom is None or atom.type != comp.atom_type:
                return
            atoms[comp.pos] = atom
        cells = [comp.pos for comp in exits]
        molecule = board.get_molecule(self.pos)
        if set(molecule) != set(cells):
            return

        # Bond-pattern verification: a bond between two covered cells must exist
        # if two exit components are directly linked (no missing, no extra bonds).
        linked = {frozenset((a.idx, b.idx)) for a in exits for b in a.links if isinstance(b, Exit)}
        direction = Direction()
        for a, b in combinations(exits, 2):
            rotation = direction.rotation_between(a.pos, b.pos)
            bonded = rotation is not None and atoms[a.pos].connection_at(rotation) is atoms[b.pos]
            if bonded != (frozenset((a.idx, b.idx)) in linked):
                return

        board.pop_molecule(self.pos)
        self.env.results.record_finished((comp.idx for comp in exits), step=self._step)
        self.log_action("consumed", self.atom_type.name.lower(), self.pos)
