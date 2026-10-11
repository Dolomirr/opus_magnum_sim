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

