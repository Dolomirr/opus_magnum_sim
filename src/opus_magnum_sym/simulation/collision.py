"""
Collision events for spatial collision detection.

Arm rotations are recorded as continuous arcs in 2D rather than checked only at start/end
cells. After all arms move, a separate collision pass samples every moved atom along its arc
(on fixed sub-steps) and tests for overlap with stationary atoms, arm bases, and atoms carried
by other arms. Any physical overlap stops the run and reports the step, category, and cell.

Overlap includes atoms or arm bases touching during movement, two moving atoms crossing paths
simultaneously, and an arm rotating or releasing a molecule onto an already-occupied cell.
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


def detect_collision(
    board: Board,
    components: Iterable[Component],
    movements: list[Movement],
    step: int,
) -> CollisionEvent | None:
    """
    Slide recorded movements and return first collision if any is detected.

    Samples `t` at `SWEEP_INCREMENT` *fractions* of rotation,
    testing every moving atom against static colliders (board atoms, arm bases, stationary held atoms)
    and then against the atoms of every other movement at the same `t`.

    The first collision is one with the lowest `t`,
    then the lowest component id in the collision candidates,
    then static collision before moving-vs-moving one.
    """
    if not movements:
        return None

    statics = _collect_static_colliders(board, components, movements)
    steps = round(1.0 / SWEEP_INCREMENT)

    for i in range(1, steps + 1):
        t = i / steps
        candidates = _collisions_at(movements, statics, t)
        if candidates:
            candidate = min(candidates, key=lambda c: (c.min_owner, c.moving_vs_moving))
            return CollisionEvent(
                category=candidate.category,
                step=step,
                cell=candidate.cell,
                owner_ids=candidate.owner_ids,
                progress=t,
            )
    return None


def _collect_static_colliders(
    board: Board,
    components: Iterable[Component],
    movements: list[Movement],
) -> list[_StaticCollider]:
    moving_atoms = {atom for movement in movements for _, atom in movement.atoms}

    board_colliders = [
        _StaticCollider(hex_to_xy(cell), ATOM_RADIUS, StaticKind.ATOM, None, cell) for cell in board.atoms
    ]

    component_colliders: list[_StaticCollider] = []
    for comp in components:
        if comp.type in (ComponentType.ARM, ComponentType.ARM_RETR):
            component_colliders.extend(
                _StaticCollider(hex_to_xy(cell), ARM_BASE_RADIUS, StaticKind.ARM_BASE, comp.idx, cell)
                for cell in comp.footprint()
            )
        holding = getattr(comp, "holding", None)
        if holding:
            component_colliders.extend(
                _StaticCollider(hex_to_xy(cell), ATOM_RADIUS, StaticKind.HELD_ATOM, comp.idx, cell)
                for cell, atom in holding.items()
                if atom not in moving_atoms
            )

    return [*board_colliders, *component_colliders]


def _collisions_at(
    movements: list[Movement],
    statics: list[_StaticCollider],
    t: float,
) -> list[_Candidate]:
    ordered = sorted(movements, key=lambda m: m.owner_id)
    positions = {m.owner_id: [m.atom_xy(cell, t) for cell, _ in m.atoms] for m in ordered}
    candidates: list[_Candidate] = []

    # Bro :cry:
    for i, movement in enumerate(ordered):
        for xy in positions[movement.owner_id]:
            for static in statics:
                if not circles_overlap(xy, ATOM_RADIUS, static.center, static.radius):
                    continue
                category = (
                    CollisionCategory.SWEEP_ARM_BASE
                    if static.kind is StaticKind.ARM_BASE
                    else CollisionCategory.SWEEP_ATOM
                )
                if static.owner_id is None or static.owner_id == movement.owner_id:
                    owners = (movement.owner_id,)
                else:
                    owners = tuple(sorted((movement.owner_id, static.owner_id)))
                candidates.append(_Candidate(min(owners), False, category, owners, static.cell))

            for other in ordered[i + 1 :]:
                for oxy in positions[other.owner_id]:
                    if not circles_overlap(xy, ATOM_RADIUS, oxy, ATOM_RADIUS):
                        continue
                    owners = tuple(sorted((movement.owner_id, other.owner_id)))
                    midpoint = ((xy[0] + oxy[0]) / 2.0, (xy[1] + oxy[1]) / 2.0)
                    cell = xy_to_hex(*midpoint)
                    candidates.append(
                        _Candidate(
                            min(owners),
                            True,
                            CollisionCategory.SWEEP_MOVING,
                            owners,
                            cell,
                        )
                    )
    return candidates
