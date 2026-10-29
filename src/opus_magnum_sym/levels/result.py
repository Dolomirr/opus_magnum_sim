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
    `metrics` is reserved for future eval parameters.
    """

    status: LevelStatus
    error: LevelError | None
    steps: int
    finished: dict[frozenset[int], int]
    finished_by_exit: dict[int, int]
    total_finished: int
    # TODO: add them
    metrics: dict = field(default_factory=dict)
