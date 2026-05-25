from dataclasses import dataclass
from enum import IntEnum, auto


class EventType(IntEnum):
    NONE = 0

    OBJECT_PLACED = auto()
    OBJECT_REMOVED = auto()

    COMPONENT_PLACED = auto()
    COMPONENT_REMOVED = auto()

    ARM_ROTATED = auto()
    ARM_EXTENDED = auto()

    SIMULATION_STARTED = auto()
    SIMULATION_RESET = auto()


@dataclass
class RenderEvent:
    type: EventType
    r: int
    s: int
    value: int
