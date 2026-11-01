"""
Solution-placed-entrypoints delivery through the high-level `Level` API.

Builds `LevelSpec` in python with `entrypoints_fixed=False` and typed shapes;
the solution places the entrypoint shapes (and the arm) anywhere on the board.

Atom types live on the shape's cells, so neither the `mkentr`/`mkexit`
definitions nor the `place` calls carry `atom_type` fallback.

Library equivalent of `examples/41_unfixed_delivery.om[ls]`.
"""

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import BPN, ComponentType, ShapeCell, ShapeTemplate
from opus_magnum_sym.levels import Level, LevelSpec, mkentr, mkexit


def straight_typed(name: str, comp_type: ComponentType, atom_type: AtomType) -> ShapeTemplate:
    """
    Straight two-cell shape whose cells are both typed with `atom_type`.
    """
    return ShapeTemplate(
        name=name,
        comp_type=comp_type,
        cells=(
            ShapeCell(offset=Hex(0, 0), atom_type=atom_type),
            ShapeCell(offset=Hex(-1, 1), atom_type=atom_type),
        ),
        links=((0, 1),),
    )


def main():
    spec = LevelSpec(
        size=(6, 6),
        shapes=(
            straight_typed("entrance_straight_2", ComponentType.ENTRANCE, AtomType.SALT),
            straight_typed("exit_straight_2", ComponentType.EXIT, AtomType.SALT),
        ),
        entrypoints=(
            mkentr("entrance_straight_2"),
            mkexit("exit_straight_2"),
        ),
        allowed_blueprints=frozenset({BPN.ARM}),
        steps=30,
        entrypoints_fixed=False,
    )

    level = Level(spec)

    # Solution places the entrypoint shapes (and the arm) itself.
    level.place("entrance_straight_2", Hex(2, 3), rotation=1)
    level.place("exit_straight_2", Hex(3, 2), rotation=2)
    arm_id = level.place("arm", Hex(3, 3)).comp_id

    # Grab the molecule, swing it four steps onto the exit, then release.
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
