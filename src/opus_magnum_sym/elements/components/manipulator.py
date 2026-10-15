from typing import TYPE_CHECKING

from icecream import ic

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.actions.base_action import ActionAssignmentError
from opus_magnum_sym.elements.atoms.atom import Atom
from opus_magnum_sym.elements.board.directions import Direction
from opus_magnum_sym.elements.components.base_component import Component, ComponentType

if TYPE_CHECKING:
    from opus_magnum_sym.elements.board import Board, Hex


class Manipulator(Component):
    def __init__(self, idx: int, pos: Hex, rotation: int = 0, length: int = 1) -> None:
        super().__init__(
            idx=idx,
            type=ComponentType.ARM,
            pos=pos,
            rotation=rotation,
        )
        self.hand_length: int = length  # TODO: check correct length
        # absolute cells of the currently held molecule
        self.holding: dict[Hex, Atom] | None = None

    @property
    def get_hand_pos(self) -> Hex:
        return (
            Direction().from_rotation(self.rotation)
            .apply(self.pos, self.hand_length)
        )  # fmt: skip

    def _rotate(self, rotation: int = 1) -> None:
        self.rotation = (self.rotation + rotation) % 6
        if self.holding:
            self.holding = {
                pos.rotate_around(self.pos, rotation): atom
                for pos, atom in self.holding.items()
            }
            for atom in self.holding.values():
                atom.rotate_connections(rotation)

    def _rotate_molecule(self, rotation: int = 1) -> None:
        if not self.holding:
            return
        self.holding = {pos.rotate_around(self.get_hand_pos, rotation): atom for pos, atom in self.holding.items()}
        for atom in self.holding.values():
            atom.rotate_connections(rotation)

    def _extend(self) -> None:
        msg = "Assigned EXTEND action to component that does not support this action."
        raise ActionAssignmentError(msg, self.type, self.idx)

    def _retract(self) -> None:
        msg = "Assigned RETRACT action to component that does not support this action."
        raise ActionAssignmentError(msg, self.type, self.idx)

    def _grab(self, board: Board) -> None:
        if self.holding is None:
            hand = self.get_hand_pos
            grabbed = board.pop_molecule(hand)
            if grabbed:
                self.holding = grabbed
                self.log_action("grabbed", f"{len(grabbed)} atom(s)", hand)

    def _release(self, board: Board) -> None:
        if self.holding is None:
            return
        if not all(
            board.in_bounds(pos) and pos not in board.atoms for pos in self.holding
        ):
            return
        hand = self.get_hand_pos
        for pos, atom in self.holding.items():
            board.place_atom(pos, atom)
        self.log_action("released", f"{len(self.holding)} atom(s)", hand)
        self.holding = None

    def _execute(self, board: Board, action_type: StepActionType) -> None:
        match action_type:
            case StepActionType.NONE:
                pass
            case StepActionType.ROTATE_CLW:
                self._rotate(1)
            case StepActionType.ROTATE_CCLW:
                self._rotate(-1)
            case StepActionType.ROTATE_MOLECULE_CLW:
                self._rotate_molecule(1)
            case StepActionType.ROTATE_MOLECULE_CCLW:
                self._rotate_molecule(-1)
            case StepActionType.EXTEND:
                self._extend()
            case StepActionType.RETRACT:
                self._retract()
            case StepActionType.GRAB:
                self._grab(board)
            case StepActionType.RELEASE:
                self._release(board)
                # TODO: add movement action
            case _:
                msg = f"Invalid action assigned to component of type manipulator: {action_type} {self.idx}"
                raise ActionAssignmentError(msg, self.type, self.idx)
