"""
Opus Magnum puzzle simulation.

`opus_magnum_sym` runs Opus Magnum puzzles headlessly.

A puzzle is described by `LevelSpec`:

- board size
- local shape templates
- entrypoints
- allowed blueprints
- step limit

Level is executed via `Level`, which owns its own simulator,
so levels never share component ids, result counters, or registered blueprint.

Puzzles can be built in Python or loaded from the project's text formats:
`.oml` for the level and `.oms` for the solution:

```python
from opus_magnum_sym import Level

level = Level.from_file("level.oml")
level.load_solution("solution.oms")
result = level.run()
print(result.status, result.total_finished, result.metrics)
```

Minimal in-Python level (unfixed mode: solution places the entrypoints):

```python
from opus_magnum_sym import (
    AtomType, ComponentType, Hex, Level,
    LevelSpec, ShapeCell, ShapeTemplate,
    StepActionType, mkentr, mkexit,
)

#   ShapeCell/ShapeTemplate  ->  reusable board pattern (geometry + typed cells)
#   shapes=(...)             ->  local shape definitions, not placed yet
#   mkentr()/mkexit()        ->  entrypoint specs referencing a shape by name
#   allowed_blueprints=...   ->  built-in blueprints the solution may place
#   Level(spec)              ->  runnable level; unfixed mode places nothing yet
#   level.place(...)         ->  place a shape/blueprint; returns PlacementRecord
#   PlacementRecord.comp_id  ->  id of a single-component placement (manipulator)
#   assign_step_action(...)  ->  per-step program for a component id

def straight(name, kind):
    # Reusable two-cell shape: origin Hex(0, 0) plus one beam cell Hex(-1, 1).
    return ShapeTemplate(
        name=name,
        comp_type=kind,
        cells=(
            ShapeCell(offset=Hex(0, 0), atom_type=AtomType.SALT),
            ShapeCell(offset=Hex(-1, 1), atom_type=AtomType.SALT),
        ),
        links=((0, 1),),  # bond between cells 0 and 1
    )

spec = LevelSpec(
    size=(6, 6),
    shapes=(  # local shape definitions, referenced by name below
        straight("entrance_straight_2", ComponentType.ENTRANCE),
        straight("exit_straight_2", ComponentType.EXIT),
    ),
    entrypoints=(  # no position = the solution must place these shapes
        mkentr("entrance_straight_2"),
        mkexit("exit_straight_2"),
    ),
    allowed_blueprints=frozenset({"arm", "connector_straight_2"}),  # built-ins
    steps=30,
    entrypoints_fixed=False,
)

level = Level(spec)

# Place entrypoint shapes first, then regular blueprints.
level.place("entrance_straight_2", Hex(2, 3), rotation=1)
level.place("exit_straight_2", Hex(3, 2), rotation=2)
level.place("connector_straight_2", Hex(1, 1), atom_type=AtomType.SALT)

# comp_id is the manipulator id used for assign_step_action; multi-cell shapes
# (glyphs, connectors, entrypoints) have no actions and need no id here.
arm_id = level.place("arm", Hex(3, 3)).comp_id

# Program the arm: grab on step 1, swing four steps, release on step 6.
level.assign_step_action(arm_id, 1, StepActionType.GRAB)
for step in (2, 3, 4, 5):
    level.assign_step_action(arm_id, step, StepActionType.ROTATE_CLW)
level.assign_step_action(arm_id, 6, StepActionType.RELEASE)

result = level.run()
print(result.status)          # LevelStatus.COMPLETED
print(result.total_finished)  # 1
```

Both entrypoint modes are supported.
The example above is the *unfixed* mode (`entrypoints_fixed=False`, default),
where the solution place the entrypoint shapes, defined without a position,
then call `level.place(...)` (and for exit likewise) before running.
The run fails with `LevelStatus.FAILED` if any entrypoint shape is missing or duplicated.

Provde `entrypoints_fixed=True` `LevelSpec` to position (with optoinal rotation)
entrypoints in level definition: `mkentr(..., Hex(...), rotation=1)` / `mkexit(..., Hex(...))`.
In this casae the solution only places regular blueprints.
"""

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import BPN, ComponentType, ShapeCell, ShapeTemplate
from opus_magnum_sym.levels import Level, LevelSpec, mkentr, mkexit
from opus_magnum_sym.simulation.placement import PlacementRecord

__all__ = [
    "BPN",
    "AtomType",
    "ComponentType",
    "Hex",
    "Level",
    "LevelSpec",
    "PlacementRecord",
    "ShapeCell",
    "ShapeTemplate",
    "StepActionType",
    "mkentr",
    "mkexit",
]
