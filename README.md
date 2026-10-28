# Opus Magnum Simulation Environment

Python-based simulation and visualization environment for Opus Magnum puzzle solutions.

## Project Structure

```
src/opus_magnum_sym/
├── elements        # Game entities and state
│   ├── actions/    # Movement and manipulation actions
│   ├── board/      # Grid/board representation
│   ├── components/ # Game components
│   ├── env/        # Per-level environment state (ids, result counters)
│   └── atoms/      # Atoms (with bonding slots).
├── interpreter     # Parses .oms solution files and .oml level files
├── levels          # Level definition model, runtime, and results
├── render          # Visualization (pygame-based)
├── repl            # Interactive REPL interface
└── simulation      # Core simulation engine
```

## Running the REPL

```bash
uv run src/opus_magnum_sym/repl
```

The REPL accepts commands to load `.oms` files and adding components and program on-by-one. It provides persistent command history (stored in `~/.cache/opus_magnum_sym/repl_history`), history-based auto-suggestions, and Tab completion for commands, component/action names, component ids, and file paths.

Each placed component gets an auto-incrementing id (starting at `0`) in placement order. The id is shown at the left of every program bar at the bottom of the window (`#<id> <type>`), and is the value you pass to the `action` command.

### Example: building a program from scratch

```text
# place components: entrance -> id 0, exit -> id 1, arm -> id 2
comp 2 3 entrance atom_type=basic
comp 3 2 exit atom_type=basic
comp 3 3 arm

# program for the arm (id 2) step by step
action 2 1 rotate_cclw
action 2 2 grab
action 2 3 rotate_cclw
action 2 4 release

# run the simulation
!run 30
```

Program bars update as soon as an `action` is entered; the cell for the current step is highlighted while running. Use `!list` to print component ids and assigned actions at any time.

### DSL commands

Everything that does not start with `!` (or `:`) is treated as DSL input.

| Command                               | Alias | Description                                                 |
|---------------------------------------|-------|-------------------------------------------------------------|
| `comp <x> <y> <type> [key=value ...]` | `c`   | Place a component on the board.                             |
| `action <id> <step> <type>`           | `a`   | Assign action to component at a step. `none` type to clear. |
| `remove <id>`                         | `rm`  | Remove a component from the board.                          |

### Meta commands

Lines starting with `!` (or `:`) are REPL commands; any other line is treated as DSL input.
Arguments are space-separated.

| Command        | Alias         | Description                                                                                             |
|----------------|---------------|---------------------------------------------------------------------------------------------------------|
| `!load <path>` | `!r`          | Read a `.oms` file and apply its components and actions to the simulation.                              |
| `!save [path]` | `!w`          | Save the current level as `.oms` to `path` (defaults to `solution.oms`).                                |
| `!run [steps]` |               | Run the simulation for `n` steps (default `30`), redrawing on every step.                               |
| `!reset`       | `!clear`      | Clear the board, remove all components, reset ids, step counter, and per-cluster finished counters.     |
| `!list`        |               | List placed components with their ids and assigned actions.                                             |
| `!history [n]` |               | Show the last `n` entered commands (default `20`); history persists across sessions.                    |
| `!edit`        | `!e`          | Open the current solution in `$EDITOR` (default `vi`); on exit the board is reset and file is reloaded. |
| `!help`        |               | Show the available commands.                                                                            |
| `!quit`        | `!q`, `!exit` | Exit the REPL.                                                                                          |

Reading from and saving to a file:

```text
# read a saved solution from disk
!load test_flow.oms

# run it for 30 steps
!run 30

# save the current level back to a file
!save level.oms
```

`!load` merges the file contents into the running simulation; it does not reset the board first, so load into a fresh REPL session if you want a clean state.

### Collision Handling

When simulation executes a step, arm rotations are recorded as continuous arcs in two dimensional space rather than checking only start and end cells. 
After all arms move, separate collision pass samples every moved atom along its arc (on fixed sub-steps) and tests for overlap with stationary atoms, arm bases, and atoms carried by other arms. 
Any physical overlap immediately stops the simulation run and reports circumstances under which collision occurred (step, type, cell).

Physical overlap includes atoms or arm bases touching during movement, two moving atoms crossing paths at the same time, and arm rotating or releasing molecule onto already occupied cell.

## File Format

`.oms` files contain Opus Magnum solutions in a custom text format. See `test_flow.oms` for an example.

## Library Usage: Levels

A *level* bundles a puzzle's starting conditions and its own runtime state (component ids, result counters, blueprint registry), so levels run independently of one another. The public API lives in `opus_magnum_sym.levels`.

### Define a level in Python

```python
from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeCell, ShapeTemplate
from opus_magnum_sym.levels import EntrypointSpec, Level, LevelSpec, LevelStatus

# Local two-cell straight entrance and exit shapes.
entrance = ShapeTemplate(
    name="entrance_straight_2",
    comp_type=ComponentType.ENTRANCE,
    cells=(ShapeCell(offset=Hex(0, 0)), ShapeCell(offset=Hex(-1, 1))),
    links=((0, 1),),
)
exit_ = ShapeTemplate(
    name="exit_straight_2",
    comp_type=ComponentType.EXIT,
    cells=(ShapeCell(offset=Hex(0, 0)), ShapeCell(offset=Hex(-1, 1))),
    links=((0, 1),),
)

spec = LevelSpec(
    size=(6, 6),
    shapes=(entrance, exit_),
    entrypoints=(
        EntrypointSpec(ComponentType.ENTRANCE, "entrance_straight_2", Hex(2, 3), AtomType.SALT, rotation=1),
        EntrypointSpec(ComponentType.EXIT, "exit_straight_2", Hex(3, 2), AtomType.SALT, rotation=2),
    ),
    allowed_blueprints=frozenset({"arm"}),
    steps=30,
)

level = Level(spec)
arm = level.place("arm", Hex(3, 3))
(arm_id,) = arm.component_ids
level.assign_step_action(arm_id, 1, StepActionType.GRAB)
for step in (2, 3, 4, 5):
    level.assign_step_action(arm_id, step, StepActionType.ROTATE_CLW)
level.assign_step_action(arm_id, 6, StepActionType.RELEASE)

result = level.run()
print(result.status)           # LevelStatus.COMPLETED
print(result.total_finished)   # 1
print(result.finished_by_exit) # {0: 1}
```

### Load a level and solution from files

The same starting conditions are loadable from a `.oml` file (via `Level.from_file`), and the solution from a `.oms` file (`Level.load_solution`):

```python
level = Level.from_file("examples/place_delivery.oml")
level.load_solution("examples/place_delivery.oms")
result = level.run()
```

A `.oml` level file defines `size`, `steps`, an `allow` list, local `shape` definitions, and `entrance`/`exit` placements:

```text
size 6 6
steps 30
shape entrance_straight_2 entrance cells=(0,0),(-1,1) links=0-1
shape exit_straight_2 exit cells=(0,0),(-1,1) links=0-1
entrance entrance_straight_2 2 3 rotation=1 atom_type=salt
exit exit_straight_2 3 2 rotation=2 atom_type=salt
allow arm
```

### Run a level from the CLI

```bash
uv run opus-magnum run --level examples/place_delivery.oml examples/place_delivery.oms
```

The `LevelResult` (`levels/result.py`) reports `status` (`COMPLETED`/`ERROR`), the steps executed, per-exit finished counts (`finished` / `finished_by_exit`), `total_finished`, and an optional `error` with exception metadata (and collision event, when the run collided).

## Key Components

- **elements/**: Defines atoms, bonds, arms, glyphs, and board state
- **interpreter/sim_interpreter.py**: Parses `.oms` files into executable instructions
- **interpreter/level_loader.py**: Parses `.oml` level files into a `LevelSpec`
- **levels/**: Level definition model (`LevelSpec`), runtime (`Level`), and results (`LevelResult`)
- **simulation/simulator.py**: Executes instructions, manages simulation state
- **render/renderer.py**: Visualizes the simulation using pygame-ce

## Development

```bash
# Install dependencies
uv sync
```

