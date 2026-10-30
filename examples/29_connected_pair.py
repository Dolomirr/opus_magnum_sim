"""
Bonded-pair delivery through the high-level `Level` API.

Defines linked two-cell entrance and exit shapes, so entrance spawns
pre-bonded molecule and exit only consumes matching one.

Library equivalent of `examples/11_bonded_pair.oms`.
"""

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeCell, ShapeTemplate
from opus_magnum_sym.levels import EntrypointSpec, Level, LevelSpec


def main():
    # Straight two-cell shape: origin cell plus one linked beam cell.
    def straight(name: str, comp_type: ComponentType) -> ShapeTemplate:
        return ShapeTemplate(
            name=name,
            comp_type=comp_type,
            cells=(ShapeCell(offset=Hex(0, 0)), ShapeCell(offset=Hex(-1, 1))),
            links=((0, 1),),
        )

    spec = LevelSpec(
        size=(6, 6),
        shapes=(
            straight("entrance_straight_2", ComponentType.ENTRANCE),
            straight("exit_straight_2", ComponentType.EXIT),
        ),
        entrypoints=(
            EntrypointSpec(
                ComponentType.ENTRANCE,
                "entrance_straight_2",
                Hex(2, 3),
                AtomType.SALT,
                rotation=1,
            ),
            EntrypointSpec(
                ComponentType.EXIT,
                "exit_straight_2",
                Hex(3, 2),
                AtomType.SALT,
                rotation=2,
            ),
        ),
        allowed_blueprints=frozenset({"arm"}),
        steps=30,
        entrypoints_fixed=True,
    )

    level = Level(spec)
    arm_id = level.place("arm", Hex(3, 3)).comp_id

    # Grab bonded pair, swing it four steps onto the exit, release.
    level.assign_step_action(arm_id, 1, StepActionType.GRAB)
    for step in (2, 3, 4, 5):
        level.assign_step_action(arm_id, step, StepActionType.ROTATE_CLW)
    level.assign_step_action(arm_id, 6, StepActionType.RELEASE)

    result = level.run()
    print(result.status)  # LevelStatus.COMPLETED
    print(result.total_finished)  # 1
    print(result.finished_by_exit)  # {0: 1}


if __name__ == "__main__":
    main()
