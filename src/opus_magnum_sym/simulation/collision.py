"""
Collision events for spatial collision detection.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from opus_magnum_sym.elements.board.geometry import (
    ARM_BASE_RADIUS,
    ATOM_RADIUS,
    SWEEP_INCREMENT,
    circles_overlap,
    hex_to_xy,
    xy_to_hex,
)
from opus_magnum_sym.elements.board.hex import Hex
from opus_magnum_sym.elements.components.base_component import ComponentType
from opus_magnum_sym.simulation.movement import Movement

if TYPE_CHECKING:
    from opus_magnum_sym.elements.board import Board
    from opus_magnum_sym.elements.components.base_component import Component


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


class StaticKind(Enum):
    """Static collider classes, mapped to a reporting category."""

    ATOM = auto()
    ARM_BASE = auto()
    HELD_ATOM = auto()


@dataclass(frozen=True)
class _StaticCollider:
    center: tuple[float, float]
    radius: float
    kind: StaticKind
    owner_id: int | None
    cell: Hex


@dataclass(frozen=True)
class _Candidate:
    min_owner: int
    moving_vs_moving: bool
    category: CollisionCategory
    owner_ids: tuple[int, ...]
    cell: Hex

