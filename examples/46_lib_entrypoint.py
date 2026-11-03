"""
Unfolded in-python level placed through `Level.place_entrypoint`.

Same level as `examples/45_level_graph.py`, but the solution places its
unfixed entrypoints by *spec index* instead of by shape name:

The entrypoint's shape, atom-type fallback and default rotation come from the
spec; the optional `rotation` overrides the spec's (demonstrated on the exit).
The returned `PlacementRecord` exposes the placed component ids:
`record.component_ids` for every shape, and `record.comp_id` for single-cell
entrypoints.

Level: three single-atom entrances (water, salt, fire) and one three-atom exit.
The exit molecule is salt with water and fire attached to it,
one empty cell between the two beams (bonds 120 degrees apart);
water and fire are linked only through the salt atom.

The solution is just a sketch: it places the entrypoints, a glyph, a connector
group and two manipulators, then schedules a few arm actions.
 It is valid but never assembles the exit molecule, so `total_finished` stays 0 and,
with `target=2`, the result reports `FailureReason.TIMEOUT`.
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
        cells=(ShapeCell(offset=Hex(0, 0), atom_type=AtomType.WATER),),
        links=(),
    )
    entrance_salt = ShapeTemplate(
        name="entrance_salt",
        comp_type=ComponentType.ENTRANCE,
        cells=(ShapeCell(offset=Hex(0, 0), atom_type=AtomType.SALT),),
        links=(),
    )
    entrance_fire = ShapeTemplate(
        name="entrance_fire",
        comp_type=ComponentType.ENTRANCE,
        cells=(ShapeCell(offset=Hex(0, 0), atom_type=AtomType.FIRE),),
        links=(),
    )

    # ========================================
    # Exit shape:
    # salt, water and fire one empty cell apart
    # ========================================
    exit_water_fire_salt = ShapeTemplate(
        name="exit_water_fire_salt",
        comp_type=ComponentType.EXIT,
        cells=(
            ShapeCell(offset=Hex(0, 0), atom_type=AtomType.SALT),
            ShapeCell(offset=Hex(-1, 1), atom_type=AtomType.WATER),
            ShapeCell(offset=Hex(1, 0), atom_type=AtomType.FIRE),
        ),
        links=((0, 1), (0, 2)),  # water-salt and fire-salt only
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
        atom_types=frozenset({AtomType.WATER, AtomType.SALT, AtomType.FIRE}),
        target=2,
    )

    level = Level(spec)
    print("entrypoint_count:", level.entrypoint_count)

    # ========================================
    # Solution:
    # entrypoints first (unfixed mode), placed by spec index.
    # `place_entrypoint` returns the placement record; its `component_ids`
    # (or `comp_id` for single-cell shapes) expose the placed ids.
    # ========================================
    entrance_water = level.place_entrypoint(0, Hex(1, 1))
    entrance_salt  = level.place_entrypoint(1, Hex(1, 4))
    entrance_fire  = level.place_entrypoint(2, Hex(1, 7))
    exit_record    = level.place_entrypoint(3, Hex(6, 4), rotation=1)

    print("entrance ids:", entrance_water.comp_id, entrance_salt.comp_id, entrance_fire.comp_id)
    print("exit ids:", exit_record.component_ids)

    # ========================================
    # Solution:
    # glyph, connector group, manipulators
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
    print(result.status)             # LevelStatus.COMPLETED
    print(result.total_finished)     # 0
    print(result.finished_by_exit)   # {0: 0}
    print(result.solved)             # False (target=2)
    print(result.reason)             # FailureReason.TIMEOUT
    print(result.failed_step)        # 60


if __name__ == "__main__":
    main()
