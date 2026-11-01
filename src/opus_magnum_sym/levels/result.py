"""
Structured results of running a level.
"""

from dataclasses import dataclass, field
from enum import Enum, auto

from opus_magnum_sym.simulation.collision import CollisionCategory, CollisionEvent


class LevelStatus(Enum):
    COMPLETED = "completed"
    ERROR = "error"
    FAILED = "failed"


class FailureReason(Enum):
    """
    Why run ended without solving the level.

    Covers hard failures: collisions, entrypoint mismatches, runtime faults
    and soft failure: reaching the step limit without meeting `target`.
    """

    COLLISION_SWEEP_ATOM = auto()
    COLLISION_SWEEP_ARM_BASE = auto()
    COLLISION_SWEEP_MOVING = auto()
    COLLISION_ENDPOINT_OVERLAP = auto()
    ENTRYPOINT_MISSING = auto()
    ENTRYPOINT_DUPLICATE = auto()
    SIMULATION_ERROR = auto()
    UNEXPECTED_ERROR = auto()
    TIMEOUT = auto()


COLLISION_REASON: dict[CollisionCategory, FailureReason] = {
    CollisionCategory.SWEEP_ATOM: FailureReason.COLLISION_SWEEP_ATOM,
    CollisionCategory.SWEEP_ARM_BASE: FailureReason.COLLISION_SWEEP_ARM_BASE,
    CollisionCategory.SWEEP_MOVING: FailureReason.COLLISION_SWEEP_MOVING,
    CollisionCategory.ENDPOINT_OVERLAP: FailureReason.COLLISION_ENDPOINT_OVERLAP,
}


@dataclass
class LevelError:
    """
    Description of exception that ended run early.

    `exception` is the exception class name
    `reason` classifies the failure for programmatic handling
    `step` the step at which it fired (or `None` when unknown)
    `collision` is the collision event, if any
    """

    exception: str
    message: str
    step: int | None
    reason: FailureReason
    collision: CollisionEvent | None = None


@dataclass
class LevelResult:
    """
    Outcome of a `Level.run`.

    `finished` maps exit-cluster id sets to delivered-molecule counts.
    `finished_by_exit` is human-readable-ish view keyed by spec exit-entrypoint index,
        with zeros filled for undelivered exits.
    `finished_steps_by_exit` maps the same exit index to its completion step (0-based),
        or `None` when the exit never reached `target`.
    `target` is the required per-exit delivery count, `None` when disabled.
    `solved` is true when every exit reached `target` (always true when target is disabled).
    `cost` is the summed cost of placed non-entrypoint components.
    `area` is the number of distinct cells covered by the solution.
    """

    status: LevelStatus
    error: LevelError | None
    steps: int
    finished: dict[frozenset[int], int]
    finished_by_exit: dict[int, int]
    total_finished: int
    target: int | None = None
    finished_steps_by_exit: dict[int, int | None] = field(default_factory=dict)
    cost: int = 0
    area: int = 0
    solved: bool = True

    @property
    def reason(self) -> FailureReason | None:
        """
        Classified failure reason, or `None` when the run solved the level.

        A run that exhausted its step limit without meeting `target` reports
        `FailureReason.TIMEOUT` even though its `status` stays `COMPLETED`.
        """
        if self.error is not None:
            return self.error.reason
        if not self.solved:
            return FailureReason.TIMEOUT
        return None

    @property
    def failed_step(self) -> int | None:
        """
        Step at which the run failed, or `None` when it solved the level.

        For a timeout this is the final executed step (the step limit).
        """
        if self.error is not None:
            return self.error.step
        if not self.solved:
            return self.steps
        return None

    @property
    def metrics(self) -> dict[str, int | None]:
        """
        Solution metrics: cost, area, and steps until every exit finished.

        `completion_steps` counts executed steps up to and including the last
        delivery, or is `None` when at least one exit never reached its target.
        """
        delivered = [step for step in self.finished_steps_by_exit.values() if step is not None]
        complete = bool(self.finished_steps_by_exit) and len(delivered) == len(self.finished_steps_by_exit)
        return {
            "cost": self.cost,
            "area": self.area,
            "completion_steps": max(delivered) + 1 if complete else None,
        }
