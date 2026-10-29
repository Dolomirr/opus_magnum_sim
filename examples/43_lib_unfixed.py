"""
Solution-placed-entrypoints delivery through the high-level `Level` API.

Builds `LevelSpec` in Python with `entrypoints_fixed=False`;
solution places entrypoint shapes (as well as arm) anywhere on the board.

Library equivalent of `examples/41_unfixed_delivery.om[ls]`.`
"""

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeCell, ShapeTemplate
from opus_magnum_sym.levels import EntrypointSpec, Level, LevelSpec


def straight(name: str, comp_type: ComponentType) -> ShapeTemplate:
    """
    Straight two-cell shape: origin cell + one linked beam cell.
    """
    return ShapeTemplate(
        name=name,
        comp_type=comp_type,
        cells=(ShapeCell(offset=Hex(0, 0)), ShapeCell(offset=Hex(-1, 1))),
        links=((0, 1),),
    )


def main():
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
                atom_type=AtomType.SALT,
            ),
            EntrypointSpec(
                ComponentType.EXIT,
                "exit_straight_2",
                atom_type=AtomType.SALT,
            ),
        ),
        allowed_blueprints=frozenset({"arm"}),
        steps=30,
        entrypoints_fixed=False,
    )

    level = Level(spec)

    # Solution places entrypoints shapes anywhere on the board.
    level.place("entrance_straight_2", Hex(2, 3), rotation=1, atom_type=AtomType.SALT)
    level.place("exit_straight_2", Hex(3, 2), rotation=2, atom_type=AtomType.SALT)
    (arm_id,) = level.place("arm", Hex(3, 3)).component_ids

    # Grab the molecule, moves it four steps onto the exit, then release.
    level.assign_step_action(arm_id, 1, StepActionType.GRAB)
    for step in (2, 3, 4, 5):
        level.assign_step_action(arm_id, step, StepActionType.ROTATE_CLW)
    level.assign_step_action(arm_id, 6, StepActionType.RELEASE)

    result = level.run()
    print(result.status)               # LevelStatus.COMPLETED
    print(result.total_finished)       # 1
    print(result.finished_by_exit)     # {0: 1}


if __name__ == "__main__":
    main()
