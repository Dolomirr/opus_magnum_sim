"""
Structured results of running a level.
"""

from dataclasses import dataclass, field
from enum import Enum

from opus_magnum_sym.simulation.collision import CollisionEvent


class LevelStatus(Enum):
    COMPLETED = "completed"
    ERROR = "error"
    FAILED = "failed"


@dataclass
class LevelError:
    """
    Description of exception that ended run early.

    `exception` is the exception class name
    `step` the step at which it fired (or `None` when unknown)
    `collision` is the collision event, if any
    """

    exception: str
    message: str
    step: int | None
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
