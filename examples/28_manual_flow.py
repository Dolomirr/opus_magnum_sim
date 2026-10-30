"""
Manual delivery through the high-level `Level` API.

Builds a `LevelSpec` in Python, places an arm, schedules per-step actions, then runs.
Library equivalent of `examples/10_basic_flow.oms`.
"""

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeCell, ShapeTemplate
from opus_magnum_sym.levels import EntrypointSpec, Level, LevelSpec


def main():
    # Single-cell entrance and exit shapes.
    entrance = ShapeTemplate(
        name="entrance_single",
        comp_type=ComponentType.ENTRANCE,
        cells=(ShapeCell(offset=Hex(0, 0)),),
        links=(),
    )
    exit_ = ShapeTemplate(
        name="exit_single",
        comp_type=ComponentType.EXIT,
        cells=(ShapeCell(offset=Hex(0, 0)),),
        links=(),
    )

    spec = LevelSpec(
        size=(6, 6),
        shapes=(entrance, exit_),
        entrypoints=(
            EntrypointSpec(
                ComponentType.ENTRANCE,
                "entrance_single",
                Hex(2, 3),
                AtomType.SALT,
            ),
            EntrypointSpec(
                ComponentType.EXIT,
                "exit_single",
                Hex(3, 2),
                AtomType.SALT,
            ),
        ),
        allowed_blueprints=frozenset({"arm"}),
        steps=30,
    )

    level = Level(spec)
    arm_id = level.place("arm", Hex(3, 3)).comp_id

    # Swing onto the entrance, grab the atom, swing onto the exit, release.
    level.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)
    level.assign_step_action(arm_id, 2, StepActionType.GRAB)
    level.assign_step_action(arm_id, 3, StepActionType.ROTATE_CCLW)
    level.assign_step_action(arm_id, 4, StepActionType.RELEASE)

    result = level.run()
    print(result.status)           # LevelStatus.COMPLETED
    print(result.total_finished)   # 1
    print(result.finished_by_exit) # {0: 1}


if __name__ == "__main__":
    main()
