"""
Fixed-entrypoints delivery through the high-level `Level` API.

Builds `LevelSpec` in python with typed shapes and both entrypoints placed on
the board; the solution then places the arm and schedules its actions.

Atom types live on the shape's cells, so `mkentr`/`mkexit` define fixed
entrypoint from a position without `atom_type` fallback.

Library equivalent of `examples/40_fixed_delivery.om[ls]`.
"""

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeCell, ShapeTemplate
from opus_magnum_sym.levels import Level, LevelSpec, mkentr, mkexit


def straight_typed(name: str, comp_type: ComponentType, atom_type: AtomType) -> ShapeTemplate:
    """
    Straight two-cell shape whose cells are both typed with `atom_type`.
    """
    return ShapeTemplate(
        name=name,
        comp_type=comp_type,
        cells=(
            ShapeCell(offset=Hex(0, 0), kwargs={"atom_type": atom_type}),
            ShapeCell(offset=Hex(-1, 1), kwargs={"atom_type": atom_type}),
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
            mkentr("entrance_straight_2", Hex(2, 3), rotation=1),
            mkexit("exit_straight_2", Hex(3, 2), rotation=2),
        ),
        allowed_blueprints=frozenset({"arm"}),
        steps=30,
    )

    level = Level(spec)
    (arm_id,) = level.place("arm", Hex(3, 3)).component_ids

    # Grab the molecule, swing it four steps onto the exit, then release.
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
