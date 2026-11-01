from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.env.level_env import LevelEnv, default_env
from opus_magnum_sym.logging import logger

if TYPE_CHECKING:
    from opus_magnum_sym.elements.board import Board, Hex
    from opus_magnum_sym.simulation.movement import Movement


class ComponentAssignmentError(Exception):
    def __init__(
        self,
        message,
        component_type: ComponentType,
    ) -> None:
        self.message = message
        super().__init__(self.message)
        self.component_type = component_type


class ComponentType(IntEnum):
    """
    Full objects index: base objects (manipulator bases, entrypoints) and dynamic parts.

    Covers entrypoints:
    - ENTRANCE
    - EXIT

    Manipulators:

    - ARM
    - ARM_RETR

    Glyphs:

    - CONNECTOR
    - DISCONNECTOR
    - SALT_TRANSMUTER
    - DUPLICATION_GLYPH

    Unoccupied cell:

    - EMPTY

    ```python
    ComponentType.ENTRANCE
    ```
    """

    EMPTY = -1
    ENTRANCE = 0
    EXIT = 1
    ARM = 2
    ARM_RETR = 3
    TRANSPORTER = 4
    CONNECTOR = 5
    DISCONNECTOR = 6
    SALT_TRANSMUTER = 7
    DUPLICATION_GLYPH = 8


@dataclass
class Component(ABC):
    """
    Base of every board component: arms, entrypoints, and glyphs.

    Each component owns a sparse program - `step -> StepActionType` mapping
    in `_programm` - assigned through `assign_step_action`.
    `get_step_action` returns action scheduled for given step,
    or `StepActionType.NONE` when none is.

    Program cycling
    ---------------
    When `cycling` is enabled (per level via `LevelSpec.cycling`),
    program loops instead of ending after its last action.
    The loop is shared across all components and built in three steps:

    1. The simulator computes one period for the whole level:
        the longest program *span* (including gaps between actions).
    2. Every program is extended to that length, padded with `NONE` as "tape filler".
    3. Each component repeats its own program every `cycle_period` steps,
       starting from its first action step; steps before it stay `NONE`.

    A program's length counts the gap between its first and last action:

    ```
    [ * _ * ]   -> length 3
    [ * * * ]   -> length 3
    [ * _ _ * ] -> length 4
    ```

    For example seven components with the following programs assinged befere first step
    (`*` = action, `_` = no action):

    ```
    C1 [ * * * * * ]
    C2 [ * _ _ _ * ]
    C3 [ * * ]
    C4 [ _ * * ]
    C5 [ _ _ * * * ]
    C6 [ _ * * * * * ]
    C7 [ _ _ _ _ _ _ * ]
    ```

    The longest span is 5 (C1, C2, C6), so the period is 5.
    C1-C5 are padded to length 5;
    C6 and C7 skip their leading empty steps before looping.
    Full trace, with `|` marking one tape cycle:

    ```
    C1 [ |* * * * *|* * * * *|* * * * *|* * ]
    C2 [ |* _ _ _ *|* _ _ _ *|* _ _ _ *|* _ ]
    C3 [ |* * _ _ _|* * _ _ _|* * _ _ _|* * ]
    C4 [ |_ * * _ _|_ * * _ _|_ * * _ _|_ * ]
    C5 [ |_ _ * * *|_ _ * * *|_ _ * * *|_ _ ]
    C6 [ |_ * * * * *|* * * * *|* * * * *|* ]
    C7 [ |_ _ _ _ _ _ *|_ _ _ _ *|_ _ _ _ * ]
    ```

    Only components with assignable actions (arms) carry programs;
    entrypoints and glyphs have empty programs and therefore never loop.
    """

    idx: int
    pos: Hex
    type: ComponentType = ComponentType.EMPTY
    rotation: int = 0
    env: LevelEnv = field(default=default_env)
    cycling: bool = field(default=False, init=False, repr=False, compare=False)
    """Program cycling, enabled per level"""
    cycle_period: int = field(default=1, init=False, repr=False, compare=False)
    """Shared cycling loop period computed across all components by simulator before each step."""
    _programm: defaultdict[int, StepActionType] = field(
        default_factory=lambda: defaultdict(lambda: StepActionType.NONE),
    )
    _blocked_cells: set[Hex] = field(default_factory=set, init=False, repr=False, compare=False)
    """Cells held by other arms during step; for mechanical collision checks."""

    _movement_recorder: list[Movement] | None = field(default=None, init=False, repr=False, compare=False)
    """Rotations recorded this step, for the post-action slide collision pass."""
    _step: int = field(default=0, init=False, repr=False, compare=False)

    def assign_step_action(self, step: int, action: StepActionType):
        """
        Adds step action to program of current component.
        If action already assigned to provided step will overwrite previous action.
        Assigning NONE removes the action from the step.
        """
        if action == StepActionType.NONE:
            self._programm.pop(step, None)
        else:
            self._programm[step] = action

    def footprint(self) -> list[Hex]:
        """
        Cells taken by this component's base.

        Default: just `pos`.
        Multi-cell components override this, deriving rotated cells from `self.rotation`.
        `pos` (the origin cell) must always be included;
        overrides must be pure functions of `pos` + `rotation`.
        """
        return [self.pos]

    @property
    def programm(self) -> dict[int, StepActionType]:
        """Assigned step actions (step -> action), excluding empty slots."""
        return {step: action for step, action in self._programm.items() if action != StepActionType.NONE}

    def cycle_bounds(self) -> tuple[int, int] | None:
        """
        (first, last) assigned action step, or `None` when the program is empty.
        """
        if not self._programm:
            return None
        return min(self._programm), max(self._programm)

    def get_step_action(self, step) -> StepActionType:
        """
        Provides action assigned to given step.
        If none is assigned returns `StepActionType.NONE`.

        With cycling enabled the program repeats every `cycle_period` steps,
        starting from its first action step; steps before it stay `NONE`.
        """
        if not self.cycling:
            return self._programm.get(step, StepActionType.NONE)
        bounds = self.cycle_bounds()
        if bounds is None or step < bounds[0]:
            return StepActionType.NONE
        first = bounds[0]
        return self._programm.get(first + (step - first) % self.cycle_period, StepActionType.NONE)

    @abstractmethod
    def _execute(self, board: Board, action_type: StepActionType) -> None: ...

    def log_action(self, verb: str, subject: str, pos: Hex) -> None:
        """
        Log a component action with source identity and location.
        """
        logger.info(
            "%s %s @ (%d, %d)",
            verb,
            subject,
            pos.r,
            pos.s,
            source=self.type.name.lower(),
            source_pos=f"({self.pos.r}, {self.pos.s})",
        )

    def execute_step(
        self,
        board: Board,
        step: int,
        blocked_cells: set[Hex] | None = None,
        movement_recorder: list[Movement] | None = None,
    ) -> None:
        self._blocked_cells = (
            blocked_cells
            if blocked_cells is not None
            else set()
        )  # fmt: skip
        self._movement_recorder = movement_recorder
        self._step = step
        self._execute(
            board=board,
            action_type=self.get_step_action(step=step),
        )
