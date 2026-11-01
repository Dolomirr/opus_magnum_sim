# Examples

Numbered `.oms`/`.oml` files and Python scripts, grouped by API generation.

Run a Python example with `uv run python examples/<file>.py`;
run a level and its solution with:

```sh
$ uv run opus-magnum run --level examples/<level>.oml examples/<solution>.oms
```

## Deprecated (01-26)

`01_manual_loop.py`, `02_connected.py`, `03_interpreter.py` and `.oms`
solutions `10`-`25` build boards with low-level `comp` / `connection`
primitives and run `Simulator` / `SimInterpreter` directly.

Most directly indicate `# DEPRECATED - uses low-level ... primitives` 
(a few, e.g. `15`, `17`, `18`, mix both styles and are deprecated as well).
They are kept as references for the low-level API, rendering, and collision/glyph primitives,
not as actual usage examples.

`26_level_fixed.om[ls]` is partially deprecated:
the pair runs, but it uses untyped `atom_type=basic` fallback.

`27_level_typed.*` is the same delivery built with typed cells.

## Current (40-45)

Level + solution pairs:

- `40_fixed_delivery.om[ls]`    - fixed entrypoints.
- `41_unfixed_delivery.om[ls]`  - solution-placed entrypoints.
- `44_target_delivery.om[ls]`   - `target` threshold and early termination.

Python (`Level` API):

- `28_manual_flow.py`, `29_connected_pair.py`  - build the spec in Python, place, run.
- `30_load_solution.py`                        - file-based entrypoint: `Level.from_file` + `load_solution` + `run`.
- `40_`, `41_`, `44_` `.py` wrappers           - run the matching `.om[ls]` pair.
- `42_lib_fixed.py`, `43_lib_unfixed.py`       - library equivalents of the fixed and solution-placed delivery pairs.
- `45_level_graph.py`                          - fully unfolded level and solution, no helpers.
