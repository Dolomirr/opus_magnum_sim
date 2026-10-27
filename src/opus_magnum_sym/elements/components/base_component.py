from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING

from opus_magnum_sym.elements.actions.actions import StepActionType
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
    """Full objects index, includes both base objects (manipulator bases, entrance) and dynamic parts as atoms"""

    EMPTY = -1
    ENTRANCE = 0
    EXIT = 1
    ARM = 2
    ARM_RETR = 3
    TRANSPORTER = 4
    CONNECTOR = 5
    DISCONNECTOR = 6
    SALT_TRANSMUTER = 7


@dataclass
class Component(ABC):
    idx: int
    pos: Hex
    type: ComponentType = ComponentType.EMPTY
    rotation: int = 0
    _programm: defaultdict[int, StepActionType] = field(
        default_factory=lambda: defaultdict(lambda: StepActionType.NONE),
    )
    # Cells held by other arms during step; for mechanical collision checks.
    _blocked_cells: set[Hex] = field(default_factory=set, init=False, repr=False, compare=False)
    # Rotations recorded this step, for the post-action slide collision pass.
    _movement_recorder: list[Movement] | None = field(default=None, init=False, repr=False, compare=False)
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

    def get_step_action(self, step) -> StepActionType:
        """
        Provides action assigned to given step.
        If none is assigned returns `StepActionType.NONE`
        """
        return self._programm.get(step, StepActionType.NONE)

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
