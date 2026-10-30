# Opus Magnum Simulation Environment

Python simulation and visualization of *Opus Magnum* puzzle solutions, 
built to serve as simulated environment.

## Quick Start

```bash
# Install dependencies
uv sync

# Interactive REPL (pygame window); Ctrl-D to exit
uv run opus-magnum

# Run solution headlessly for N steps
uv run opus-magnum run examples/10_basic_flow.oms --steps 30

# Run level (with starting conditions) + its solution
uv run opus-magnum run --level examples/26_level_fixed.oml examples/26_level_fixed.oms
```

## File Formats

Two plain-text DSLs, both with `#` comments:

- `.oml` - level: board size, step limit, entrypoint shapes (optionally with
  placements for fixed mode), and allow-list of place-able blueprints.
- `.oms` - solution: component/blueprint placements and per-step arm actions.

Runnable example pairs are under `examples/`.

## Library Usage

The intended entry point is a `Level`, which owns a simulator, component ids, result counters, and a blueprint registry, 
so levels run independently of one another:

```python
from opus_magnum_sym.levels import Level

level = Level.from_file("examples/26_level_fixed.oml")
level.load_solution("examples/26_level_fixed.oms")
result = level.run()

result.status            # LevelStatus.COMPLETED | ERROR | FAILED
result.total_finished    # int
result.finished_by_exit  # {exit_index: count}
```

Levels can also be defined in Python from `LevelSpec` / `EntrypointSpec`;
see the module docstring of `levels/level.py`.

## Development

```bash
uv sync      # install dependencies
just lint    # ruff
just check   # ty check
just test    # pytest suite
```
