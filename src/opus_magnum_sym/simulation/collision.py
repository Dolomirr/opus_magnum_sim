"""
Collision events for spatial collision detection.
"""

from dataclasses import dataclass
from enum import Enum, auto

from opus_magnum_sym.elements.board.hex import Hex


class CollisionCategory(Enum):
    """
    Physical collision outcome categories.
    """

    SWEEP_ATOM = auto()
    SWEEP_ARM_BASE = auto()
    SWEEP_MOVING = auto()
    ENDPOINT_OVERLAP = auto()


@dataclass(frozen=True)
class CollisionEvent:
    category: CollisionCategory
    step: int
    cell: Hex
    owner_ids: tuple[int, ...]
    progress: float
