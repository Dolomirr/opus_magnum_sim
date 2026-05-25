from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opus_magnum_sym.elements.board import Hex


class ActionType(IntEnum):
    NONE = 0
    ADD_COMPONENT = auto()
    REMOVE_COMPONENT = auto()
    ADD_INSTRUCTION = auto()
    REMOVE_INSTRUCTION = auto()
    REORDER_INSTRUCTION = auto()
    START_SIMULATION = auto()
    RESET = auto()
    FINISH = auto()


class StepActionType(IntEnum):
    NONE = 0
    GRAB = auto()
    RELEASE = auto()
    ROTATE_CLW = auto()
    ROTATE_CCLW = auto()
    EXTEND = auto()
    RETRACT = auto()
    MOVE_POS = auto()
    MOVE_NEG = auto()
