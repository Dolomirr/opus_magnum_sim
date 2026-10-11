# Opus Magnum Simulation Environment

Python-based simulation and visualization environment for Opus Magnum puzzle solutions.

## Project Structure

```
src/opus_magnum_sym/
├── elements        # Game entities and state
│   ├── actions/    # Movement and manipulation actions
│   ├── board/      # Grid/board representation
│   ├── components/ # Game components
│   ├── env/        # Environment state management
│   └── objects/    # Atoms, molecules.
├── interpreter     # Parses .oms solution/state files
├── render          # Visualization (pygame-based)
├── repl            # Interactive REPL interface
└── simulation      # Core simulation engine
```

## Running the REPL

```bash
uv run src/opus_magnum_sym/repl
```

The REPL accepts commands to load `.oms` files and adding components and program on-by-one.

Each placed component gets an auto-incrementing id (starting at `0`) in placement order. The id is shown at the left of every program bar at the bottom of the window (`#<id> <type>`), and is the value you pass to the `action` command.

### Example: building a program from scratch

```text
# place components: entrance -> id 0, exit -> id 1, arm -> id 2
comp 2 3 entrance object_type=atom
comp 3 2 exit object_type=atom
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

| Command        | Alias         | Description                                                                                  |
|----------------|---------------|----------------------------------------------------------------------------------------------|
| `!load <path>` | `!r`          | Read a `.oms` file and apply its components and actions to the simulation.                   |
| `!save [path]` | `!w`          | Save the current level as `.oms` to `path` (defaults to `solution.oms`).                     |
| `!run [steps]` |               | Run the simulation for `n` steps (default `30`), redrawing on every step.                    |
| `!reset`       | `!clear`      | Clear the board, remove all components, reset ids, the step counter, and `CORRECT_FINISHED`. |
| `!list`        |               | List placed components with their ids and assigned actions.                                  |
| `!help`        |               | Show the available commands.                                                                 |
| `!quit`        | `!q`, `!exit` | Exit the REPL.                                                                               |

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

## File Format

`.oms` files contain Opus Magnum solutions in a custom text format. See `test_flow.oms` for an example.

## Key Components

- **elements/**: Defines atoms, bonds, arms, glyphs, and board state
- **interpreter/sim_interpreter.py**: Parses `.oms` files into executable instructions
- **simulation/simulator.py**: Executes instructions, manages simulation state
- **render/renderer.py**: Visualizes the simulation using pygame-ce

## Development

```bash
# Install dependencies
uv sync
```

