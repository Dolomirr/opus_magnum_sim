from enum import IntEnum, auto


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
    """
    Action a component performs on one simulation step.

    Actions are scheduled per component through `Level.assign_step_action` or
    `Simulator.assign_step_action`; the component executes its action when the
    simulation reaches that step. `EXTEND`/`RETRACT` apply only to piston arms.

    ```python
    level.assign_step_action(arm_id, 1, StepActionType.GRAB)
    ```
    """

    NONE = 0
    GRAB = auto()
    RELEASE = auto()
    ROTATE_CLW = auto()
    ROTATE_CCLW = auto()
    ROTATE_MOLECULE_CLW = auto()
    ROTATE_MOLECULE_CCLW = auto()
    EXTEND = auto()
    RETRACT = auto()
    MOVE_POS = auto()
    MOVE_NEG = auto()
