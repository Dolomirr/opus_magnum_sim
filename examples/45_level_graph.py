"""
Unfolded in-python level: every shape, entrypoint and placement provided explicitly.

`LevelSpec` holds the shapes, entrypoints and allow-list;
`Level.place` instantiates them on the board.

Level: three single-atom entrances (water, salt, fire) and one three-atom exit.
The exit molecule is salt with water and fire attached to it,
one empty cell between the two beams (bonds 120 degrees apart);
water and fire are linked only through the salt atom.

The solution is just sketch:
it places the entrypoints, a glyph, a connector group and two manipulators,
then schedules few arm actions.

It is valid but never assembles the exit molecule, so `total_finished` stays 0.
"""

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import BPN, ComponentType, ShapeCell, ShapeTemplate
from opus_magnum_sym.levels import Level, LevelSpec, mkentr, mkexit


def main():
    # ========================================
    # Entrance shapes:
    # one cell, one atom type each
    # ========================================
    entrance_water = ShapeTemplate(
        name="entrance_water",
        comp_type=ComponentType.ENTRANCE,
        cells=(
            ShapeCell(
                offset=Hex(0, 0),
                atom_type=AtomType.WATER,
            ),
        ),
        links=(),
    )
    entrance_salt = ShapeTemplate(
        name="entrance_salt",
        comp_type=ComponentType.ENTRANCE,
        cells=(
            ShapeCell(
                offset=Hex(0, 0),
                atom_type=AtomType.SALT,
            ),
        ),
        links=(),
    )
    entrance_fire = ShapeTemplate(
        name="entrance_fire",
        comp_type=ComponentType.ENTRANCE,
        cells=(
            ShapeCell(
                offset=Hex(0, 0),
                atom_type=AtomType.FIRE,
            ),
        ),
        links=(),
    )

    # ========================================
    # Exit shape:
    # salt, water and fire one empty cell apart
    #
    # Offsets: rotation 0 = (-1, 1), rotation 2 = (1, 0);
    # water -> fire is distance 2,
    # cell between them is rotation 1 = (0, 1).
    # ========================================
    exit_water_fire_salt = ShapeTemplate(
        name="exit_water_fire_salt",
        comp_type=ComponentType.EXIT,
        cells=(
            ShapeCell(
                offset=Hex(0, 0),
                atom_type=AtomType.SALT,
            ),
            ShapeCell(
                offset=Hex(-1, 1),
                atom_type=AtomType.WATER,
            ),
            ShapeCell(
                offset=Hex(1, 0),
                atom_type=AtomType.FIRE,
            ),
        ),
        links=((0, 1), (0, 2)),         # water-salt and fire-salt only
    )

    spec = LevelSpec(
        size=(9, 9),
        shapes=(
            entrance_water,
            entrance_salt,
            entrance_fire,
            exit_water_fire_salt,
        ),
        entrypoints=(
            mkentr("entrance_water"),
            mkentr("entrance_salt"),
            mkentr("entrance_fire"),
            mkexit("exit_water_fire_salt"),
        ),
        allowed_blueprints=frozenset(
            {
                BPN.ARM,
                BPN.ARM_PISTON,
                BPN.CONNECTOR_STRAIGHT_2,
                BPN.CONNECTOR_TRI,
                BPN.CONNECTOR_TRI_ODD,
                BPN.SALT_TRANSMUTER,
            }
        ),
        steps=60,
        atom_types=frozenset(
            {
                AtomType.WATER,
                AtomType.SALT,
                AtomType.FIRE,
            }
        ),
        target=2,
    )

    level = Level(spec)

    # ========================================
    # Solution:
    # entrypoints first (unfixed mode)
    # ========================================
    level.place("entrance_water", Hex(1, 1))
    level.place("entrance_salt", Hex(1, 4))
    level.place("entrance_fire", Hex(1, 7))
    level.place("exit_water_fire_salt", Hex(6, 4))

    # ========================================
    # Solution:
    # glyph, connector group, manipulators
    #
    # Glyphs have no assignable actions,
    # so their placement result is discarded.
    # ========================================
    level.place("salt_transmuter", Hex(4, 2))
    level.place("connector_tri", Hex(4, 6), atom_type=AtomType.SALT)

    arm_id = level.place("arm", Hex(4, 4)).comp_id
    level.place("arm_piston", Hex(2, 6), rotation=0)

    # ========================================
    # Solution:
    # few arm actions (nothing is delivered)
    # ========================================
    level.assign_step_action(arm_id, 1, StepActionType.GRAB)
    level.assign_step_action(arm_id, 2, StepActionType.ROTATE_CLW)
    level.assign_step_action(arm_id, 3, StepActionType.ROTATE_CLW)
    level.assign_step_action(arm_id, 4, StepActionType.RELEASE)

    result = level.run()
    print(result.status)                # LevelStatus.COMPLETED
    print(result.total_finished)        # 0
    print(result.finished_by_exit)      # {0: 0}
    print(result.solved)                # False (target=2)


if __name__ == "__main__":
    main()
