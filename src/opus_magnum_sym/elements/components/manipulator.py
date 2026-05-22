from typing import TYPE_CHECKING

from icecream import ic

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.actions.base_action import ActionAssignmentError
from opus_magnum_sym.elements.board.directions import Direction
from opus_magnum_sym.elements.components.base_component import Component, ComponentType
from opus_magnum_sym.elements.objects.base_object import ObjectType

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
        self.holding: ObjectType = ObjectType.NONE

    @property
    def get_hand_pos(self) -> Hex:
        return (
            Direction().from_rotation(self.rotation)
            .apply(self.pos, self.hand_length)
        )  # fmt: skip

    def _rotate(self, rotation: int = 1) -> None:
        self.rotation = (self.rotation + rotation) % 6

    def _extend(self) -> None:
        msg = "Assigned EXTEND action to component that does not support this action."
        raise ActionAssignmentError(msg, self.type, self.idx)

    def _retract(self) -> None:
        msg = "Assigned RETRACT action to component that does not support this action."
        raise ActionAssignmentError(msg, self.type, self.idx)

    # TODO: for now just blindly removing/placing from/on board
    def _grab(self, board: Board) -> None:
        pos = self.get_hand_pos
        obj = board.get_object(pos)
        if obj != ObjectType.NONE:
            self.holding = obj
            board.remove_object(pos)

    def _release(self, board: Board) -> None:
        pos = self.get_hand_pos
        if self.holding != ObjectType.NONE:
            board.place_object(pos, self.holding)
            self.holding = ObjectType.NONE

    def _execute(self, board: Board, action_type: StepActionType) -> None:
        match action_type:
            case StepActionType.NONE:
                pass
            case StepActionType.ROTATE_CLW:
                self._rotate(1)
            case StepActionType.ROTATE_CCLW:
                self._rotate(-1)
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
