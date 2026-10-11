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

Program bars update as soon as an `action` is entered; the cell for the current step is highlighted while running. Use `!list` to print component ids at any time.

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

