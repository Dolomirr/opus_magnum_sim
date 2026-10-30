# Agent Guide: Opus Magnum Simulation Environment

This is a **project-level** companion to the global `AGENTS.md`. It documents the codebase-specific conventions, architecture, and workflows needed to work effectively in this repo. Do not overwrite the global `AGENTS.md` in `~/.config/opencode/`.

## 1. Project at a Glance

- **Goal**: Build a Python simulation of *Opus Magnum* puzzles that can later be wrapped as an RL training environment.
- **Current State**: Core simulation, a textual DSL for puzzle solutions (`.oms` files), a Pygame renderer, and an interactive REPL are functional. Features are being added incrementally; many TODOs remain.
- **Language**: Python >=3.14.2.
- **Package Manager**: `uv` (see `pyproject.toml` and `uv.lock`).
- **Package Name**: `opus_magnum_sym` (source under `src/opus_magnum_sym/`).

## 2. Quick Start

```bash
# Run the interactive REPL (opens pygame window by default)
uv run opus-magnum

# Run the REPL without visualization
uv run opus-magnum repl --headless

# Execute inline DSL commands on REPL startup
uv run opus-magnum repl -c "comp 2 3 entrance atom_type=basic" -c "comp 3 3 arm"

# Run a solution headlessly
uv run opus-magnum run examples/10_basic_flow.oms --steps 30

# Run a solution built entirely from inline commands (no .oms file)
uv run opus-magnum run --steps 30 \
  -c "comp 2 3 entrance atom_type=basic" \
  -c "comp 3 2 exit atom_type=basic" \
  -c "comp 3 3 arm" \
  -c "action 2 1 rotate_cclw" \
  -c "action 2 2 grab" \
  -c "action 2 3 rotate_cclw" \
  -c "action 2 4 release"

# Validate a solution file
uv run opus-magnum validate examples/10_basic_flow.oms

# Run a level (starting conditions) + its solution
uv run opus-magnum run --level examples/26_level_fixed.oml examples/26_level_fixed.oms
```

The REPL accepts DSL commands directly and meta-commands prefixed with `!` (e.g. `!run 30`, `!load examples/10_basic_flow.oms`, `!list`, `!help`; also `!history [n]`, `!edit`/`!e`, and `!viz [on|off]` to toggle visualization). Tab completion (commands, component/action names, ids, file paths), history-based auto-suggestions, and persistent history (`~/.cache/opus_magnum_sym/repl_history`) are wired up in `repl/sim_repl.py` via prompt_toolkit.

### Justfile

A `Justfile` at the repo root wraps the common `uv run` invocations so agents can run a single `just` command instead of composing `uv run` arguments by hand. `just` (with no arguments) prints the recipe list. `just` shell command is approved automatically. Available recipes:

- `just repl` — interactive REPL (pygame window)
- `just repl-headless` — REPL without visualization
- `just run <file> [steps]` — headless run, defaults to 30 steps
- `just validate <file>` — validate a solution file
- `just test` — run the pytest suite
- `just test-file <file>` — run one test file
- `just lint` — `ruff check --fix .`
- `just format` — `ruff format .`
- `just check` — `ty check src`
- `just full` — `check` + `lint` + `test`

## 3. Repo Layout

```
src/opus_magnum_sym/
├── elements/
│   ├── actions/        # Per-step action enum (StepActionType)
│   ├── board/          # Hex grid, coordinates, directions
│   ├── components/     # Components: arms, entrance, exit; blueprints.py (placement templates)
│   ├── env/            # Per-level env state: index manager, result counter, LevelEnv
│   └── atoms/          # Atom type/instances + molecule BFS (molecule.py)
├── interpreter/        # Parses .oms solution files; level_loader.py parses .oml level files
├── levels/             # Level definition model (spec.py), runtime (level.py), result (result.py)
├── render/             # Pygame-based visualization
├── repl/               # Interactive REPL
└── simulation/         # Simulator orchestration; placement.py (PlacementRecord)
tests/                  # pytest tests + conftest.py (reset global state fixture)
examples/               # Numbered .oms/.oml examples + high-level lib-use demos
```

## 4. Coordinate System

The board is a **pointy-top hex grid** using an **"odd-r" horizontal layout** with axial offset coordinates `(r, s)`.

- `r` = row, `s` = column.
- Adjacent directions are encoded in `elements/board/directions.py` as `Direction.H1`, `H3`, `H5`, `H7`, `H9`, `H11`.
- Arm rotations are integers `0..5` and map to those six directions via `Direction().from_rotation(rotation)`.

When placing components or reading the board, always use `Hex(r, s)`.

## 5. Key Domain Model

### Board (`elements/board/board.py`)

- Backed by `numpy` arrays plus an atom registry.
- Layers:
  - `base_obj` — static components (arm bases, entrance, exit).
  - `atoms` — dict mapping `Hex` cell → `Atom` instance (dynamic objects).
  - `components_ids` — maps each occupied cell to the component ID.
- Atom access goes through `place_atom` / `get_atom` / `remove_atom`; `move_atom(src, dst)` relocates an atom as a single validated operation (on failure the board is untouched).
- Component placement goes through `place_component_cells(cells, type, id)`, which validates all cells before writing and leaves the board untouched on any failure; `place_componet` (single cell) is a thin delegate. Removal mirrors it via `remove_component_cells(cells)`.
- `get_molecule(cell)` returns `{Hex: Atom}` for every atom connected to the atom at `cell` (empty if the cell is empty) without mutating the board; `pop_molecule` removes and returns the same set.
- `Board.get_state()` returns a stacked `(2, rows, cols)` ndarray of `base_obj` + an atom-type layer derived from `atoms`.
- `Board.clone()` provides a deep copy (atoms included).

### Components (`elements/components/`)

- `Component` is an abstract dataclass; every concrete component has:
  - `idx`: unique ID allocated by the component's `LevelEnv` index manager.
  - `pos`: `Hex` location on the board.
  - `type`: `ComponentType`.
  - `rotation`: `0..5`.
  - `_programm`: a dict mapping simulation step → `StepActionType`.
  - `footprint()`: cells occupied by the component's base (default `[pos]`; multi-cell components override it as a pure function of `pos` + `rotation`).
- `ComponentType` values: `ENTRANCE`, `EXIT`, `ARM`, `ARM_RETR`, `TRANSPORTER`, `CONNECTOR`, `DISCONNECTOR`, `SALT_TRANSMUTER`, `DUPLICATION_GLYPH`.
- Concrete classes:
  - `Manipulator` (`ARM`) — rotates, grabs/releases atoms at its hand position.
  - `RetractableManipulator` (`ARM_RETR`) — piston arm; hand slides along the rotation axis (`EXTEND`/`RETRACT`).
  - `Enter` (`ENTRANCE`) — spawns an `Atom` of its configured `AtomType` (per-cell, so each typed cell of a shape spawns its own type) if the cell is empty, then bonds it to its *directly-linked* entrance partners only.
  - `Exit` (`EXIT`) — accepts a full molecule via exact-cover + bond-pattern matching (see "Connected entrances/exits" below) and records a finished molecule in its env's `ResultCounter`.

### Atoms (`elements/atoms/atom.py`)

- `AtomType`: `NONE`, `BASIC`, `FIRE`, `WATER`, `EARTH`, `AIR`, `SALT`, `METAL`. `NONE` and `BASIC` are non-game placeholders rejected by the high-level placement API (`sim.place`) and by level entrypoints.
- `Atom`: an instance placed on the board via `board.place_atom`. It carries `connections` — a list of 6 slots (`Atom | None`), one per neighbor direction, indexed by rotation index `0..5` matching `Direction().from_rotation(rotation)`; the opposite of slot `i` is slot `(i + 3) % 6`. `connect` / `disconnect` / `connection_at` maintain these slots reciprocally, and `rotate_connections(steps)` rotates every slot in place.
- Bonds are created manually (low-level, by cell) via `Board.connect_atoms` / `Board.disconnect_atoms`. `molecule.py::collect_molecule(root)` runs a BFS to return all atoms connected to `root`.
- `Atom.connect` / `Atom.disconnect` are the low-level slot primitives with no positional validation; all bonding/removal from `src/` must route through `Board.connect_atoms` / `Board.disconnect_atoms`, which reject non-adjacent cells.
- The manipulator grabs, rotates, and releases whole molecules (every atom bonded to the atom at its hand), not single atoms. A held atom records its holder arm ids in `Atom.held_by` (a set, so several arms may hold the same molecule); an arm refuses to move or release a molecule into a cell occupied by a board atom or by another arm's held molecule, and refuses to move a molecule that is also held by another arm.

### Actions (`elements/actions/actions.py`)

Per-step actions (`StepActionType`):

- `NONE`, `GRAB`, `RELEASE`
- `ROTATE_CLW`, `ROTATE_CCLW` (full rotation: arm moves around the base, carrying any held molecule)
- `ROTATE_MOLECULE_CLW`, `ROTATE_MOLECULE_CCLW` (in-place rotation: arm stays put, held molecule rotates around the hand)
- `EXTEND`, `RETRACT` (declared but not supported by the basic arm)
- `MOVE_POS`, `MOVE_NEG` (declared but not implemented)

### Simulation Loop (`simulation/simulator.py`)

```python
sim = Simulator((rows, cols))
sim.add_component(Hex(r, s), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
sim.add_component(Hex(r, s), ComponentType.EXIT, atom_type=AtomType.BASIC)
sim.add_component(Hex(r, s), ComponentType.ARM)
sim.assign_step_action(comp_id, step, StepActionType.ROTATE_CCLW)
sim.next_step()  # advances one simulation step
```

- On `step == 0` the simulator verifies that both an entrance and an exit exist.
- Each step calls `execute_step` on every non-entrypoint component, then on entrypoints. **Order may cause race conditions** — be careful when extending logic.
- Component IDs are allocated per-environment via `elements/env/index_manager.py` (an `IndexManager` owned by the simulator's `LevelEnv`). In tests, reset the module default with `im.reset()`.

### Connected entrances/exits (`elements/components/connections.py`)

- `ConnectionGraph` is a pure-id undirected link graph (`add`, `remove`, `remove_component`, `links_of`, `group_of`); `group_of` returns the transitive closure including the node itself.
- `Simulator.connect_components(id_a, id_b)` links two components, returning `False` (no state change) unless both ids exist, differ, are not already linked, share the same type, and that type is `ENTRANCE` or `EXIT`, and the two cells are adjacent. `disconnect_components` removes an existing link.
- On any link change the simulator refreshes each entrypoint's `group` list (transitive neighbours) **and** its `links` list (direct partners, resolved from `connections.links_of`). Components expose both, but game logic uses the direct links:
  - **Entrance bonding**: `Enter._execute` bonds its spawned atom only to its `links` partners (never to transitively-reached-but-unlinked neighbours), so a branched shape bonds exactly along its link set. Execution is sequential, so the last spawner in a group completes every bond; `Board.connect_atoms` no-ops on already-bonded pairs and rejects non-adjacent cells.
  - **Exit verification**: `Exit._execute` first checks exact cell cover (set equality with the exit's `group`) and per-cell `atom.type` against each component's own `atom_type`, then verifies the **bond pattern** — for every ordered pair of covered cells, a bond must exist iff the two exit components are directly linked. No missing bonds, no extra bonds; the rotation for each pair is derived from the hex offset via `Direction().rotation_between`. A molecule whose bonds mismatch the link set is rejected (not consumed).
- Manually `connection`-linked entrypoints are direct links in the same `ConnectionGraph`, so they participate naturally in both entrance bonding and exit verification.

### Blueprints & placement (`elements/components/blueprints.py`, `simulation/placement.py`)

- A high-level placement layer on top of the single-hex primitives. Callers place a named, registered **blueprint** with `sim.place(name, pos, rotation=0, **overrides)`; the result is a `PlacementRecord`.
- Two blueprint flavors, discriminated with `isinstance`:
  - `ShapeTemplate` — a multi-cell group of linkable entrypoint components (`ENTRANCE`, `EXIT`, `CONNECTOR`, `DISCONNECTOR`). At runtime it exists as N ordinary components wired through the existing `ConnectionGraph`. Carries `cells` (offset + per-cell kwargs), `links` (index pairs), and optional `allowed_rotations`. A `ShapeCell`'s `kwargs` may carry `atom_type` (a *typed cell*); at placement `_place_shape` merges per-cell kwargs **over** placement overrides (`{**overrides, **template_cell.kwargs}`), so a typed cell's type is never clobbered by a blanket `atom_type` override. Untyped cells fall back to the override (the entrypoint's `atom_type`).
  - `ManipulatorSpec` — a capability descriptor for an arm variant (`arm_count`, `extendable`, `min_length`/`max_length`). Variants are data, not enum values or subclasses.
- Registry functions: `register_blueprint`, `get_blueprint`, `list_blueprints` (returns name + `implemented` flag). `implemented=False` blueprints are registerable but not placeable (place raises `SimulationRuntimeError`).
- The global `default_registry` holds the built-ins (arm specs, connector shapes, `salt_transmuter`, `glyph_duplication`). Each `Simulator` clones it at construction (`default_registry.clone()`), so per-simulator registrations never leak into the global registry or other simulators. The straight-2 entrance/exit PoC shapes (`entrance_straight_2` / `exit_straight_2`) are **not** registered globally; define them per-level.
- `Simulator.placements` records every placement; `Simulator.remove_placement(record)` removes the member components (which purges their links) and the record. `reset()` clears placements.

### Level concept (`levels/`)

A **level** bundles a puzzle's starting conditions and its own runtime state, so levels run independently of one another. Public names (from `levels/__init__.py`): `EntrypointSpec`, `LevelSpec`, `Level`, `LevelResult`, `LevelError`, `LevelStatus`.

- `LevelSpec` (frozen dataclass, `levels/spec.py`) — immutable, validated starting conditions: board `size`, local `ShapeTemplate`s, a tuple of `EntrypointSpec`, an `allowed_blueprints` frozenset, a `steps` limit, plus `entrypoints_fixed: bool = False` (default: solution places the entrypoints; `True` places them from the spec) and `atom_types: frozenset[AtomType] = frozenset()` (declared atom types, empty = unconstrained). Validation enforces: unique shape names; every entrypoint resolves to a *local* shape with matching `comp_type`; every allow-list name resolves locally or in the global default registry and is `implemented`; at least one entrance and one exit; positive size and steps; typed-cell kwargs are only `atom_type` with a non-`NONE`/`BASIC` `AtomType` value; declared `atom_types` excludes `NONE`/`BASIC` and (when non-empty) must include every entrypoint's fallback and per-cell types; in fixed mode every entrypoint has `pos` and its cells (computed from shape offsets + rotation, pure `Hex`/`Direction` math) are in bounds and pairwise non-overlapping; in unfixed mode every entrypoint has `pos=None`. An entrypoint's `atom_type` is required iff its shape has at least one untyped cell. It never touches a `Simulator`.
- `EntrypointSpec` (frozen dataclass) — one entrance or exit: `kind` (`ENTRANCE`/`EXIT`), `shape` name, `pos` (`Hex | None`, `None` in unfixed mode), `rotation` (0..5), `atom_type` (`AtomType | None`, fallback for untyped cells). `atom_type` may not be `NONE`/`BASIC` when set (mirrors the `place` guard). Multiple entrypoints may share a `shape` name to require copies.
- `Level` (`levels/level.py`) — built from a `LevelSpec`; owns a `Simulator` with a fresh `LevelEnv` and a cloned blueprint registry; registers the spec's shapes, sets `allowed_blueprints`, and (fixed mode) places each entrypoint with one `sim.place(...)` call. In unfixed mode nothing is placed up front and the allow-list is `spec.allowed_blueprints` union the entrypoint shape names, so solutions place entrypoints through the normal `place` path. Solution-building delegates: `place`, `assign_step_action`, `remove_placement`, `load_solution(path)`. `run(steps=None)` advances up to the spec limit (or the override) and returns a `LevelResult` instead of raising. `Level.from_file(path)` builds from a `.oml` file.
- `LevelResult` / `LevelError` / `LevelStatus` (`levels/result.py`) — `status` is `COMPLETED`, `ERROR`, or `FAILED`; `error` carries the exception class name, message, `step`, and optional `CollisionEvent`; `finished` maps exit-cluster id sets to counts, `finished_by_exit` maps spec exit-entrypoint index to counts (zeros filled), `total_finished` sums them; `metrics` is reserved (empty) for future eval parameters.

**Fixed vs unfixed entrypoints**: with `entrypoints_fixed 1` (default) the level places entrypoints at build time; with `entrypoints_fixed 0` the solution must place each defined entrypoint exactly once. Matching is per shape name: placements-of-shape must equal specs-of-shape (extra or missing → `FAILED`). `Level.run` re-checks the count on every call (not just the first) and, on mismatch, returns `LevelResult(status=FAILED, error=LevelError(...), steps=0)` without stepping. `FAILED` is distinct from `ERROR` (a simulation fault).

**Snapshot-time results**: `finished_by_exit` is computed in `_snapshot`, not cached at build time — each exit's cluster key is read from the live `ConnectionGraph` (`connections.group_of`), so a solution that `connection`-links exit entrypoints into one cluster reports correctly. Fixed mode reuses the build-time records; unfixed mode maps each exit spec to the n-th placement of its shape.

**Invariants**: a level's component ids, result counters, and blueprint registry never leak across levels. `AtomType.BASIC`/`NONE` are non-game placeholders rejected from level entrypoints and from `sim.place`, but remain available to the low-level `add_component` path.

### Interpreter (`interpreter/sim_interpreter.py`)

Parses `.oms` text files. Commands:

```text
# Place a component
comp <x> <y> <COMPONENT_TYPE> [key=value ...]

# Place a registered blueprint (shape template or manipulator spec)
place <blueprint_name> <x> <y> [rotation=<int>] [key=value ...]

# Schedule a step action on a component
action <comp_id> <step> <STEP_ACTION_TYPE>

# Link two components (adjacent, same type, ENTRANCE or EXIT only)
connection <comp_id_a> <comp_id_b>

# Unlink two components
disconnection <comp_id_a> <comp_id_b>
```

Example (`examples/10_basic_flow.oms`):

```text
comp 2 3 entrance atom_type=basic
comp 3 2 exit atom_type=basic
comp 3 3 arm

action 2 1 rotate_cclw
action 2 2 grab
action 2 3 rotate_cclw
action 2 4 release
```

Example files carry a short header description; an example that uses the low-level
`comp`/`connection` primitives instead of `place <blueprint>` is marked in that header with
`# DEPRECATED - uses low-level `comp` primitives.` Files built on `place`/`.oml` carry no marker.

Keyword arguments supported by `_handle_comp`:

- `atom_type=<AtomType name>` — e.g. `atom_type=basic`
- `rotation=<int>` — initial rotation
- `length=<int>` — arm length

### Level files (`.oml`, `interpreter/level_loader.py`)

The same starting conditions are loadable from text, alongside the `.oms` solution format. `LevelLoader` reuses the shlex-per-line style but is strict: errors raise `LevelLoadError` with the offending line number (unlike `SimInterpreter`, which prints and continues).

```text
size <rows> <cols>
steps <n>
allow <name> [name ...]
atom_types <type> [type ...]
entrypoints_fixed 0|1
shape <name> <kind> cells=(r,s)[:type],(r,s)[:type],... links=i-j,i-j [rotations=0,1,...]
entrance <shape> [<r> <s>] [rotation=k] [atom_type=<type>]
exit <shape> [<r> <s>] [rotation=k] [atom_type=<type>]
```

`kind` is a `ComponentType` name (`entrance`, `exit`, `connector`, ...); `atom_type` is an `AtomType` name (never `none`/`basic`). Shape `cells` take an optional colon suffix per cell to declare a typed cell, e.g. `cells=(0,0):salt,(-1,1):water,(1,0):fire`; cells without a suffix are untyped and fall back to the entrypoint's `atom_type`. `atom_types` declares the level's used types (optional; empty = unconstrained). `entrypoints_fixed 0` switches to solution-placed entrypoints: `entrance`/`exit` then take no `r s` position, and `atom_type` may be omitted when every cell of the shape is typed. Reference demos: `examples/26_level_fixed.oml` (fixed) and `examples/27_level_typed.oml` (typed, unfixed) + their `.oms` solutions, run end-to-end via `Level.from_file` + `load_solution` + `run`.

## 6. Rendering

`render/renderer.py` uses `pygame-ce`. `BoardRenderer` draws the grid, components, objects, and manipulator hands. It is typically driven from the REPL.

## 7. Testing & Linting Conventions

- Tests live in `tests/` and use `pytest`.
- `tests/conftest.py` provides an autouse `clean_state` fixture that resets the global `index_manager` and `level_counter` before every test. Because these keep module-level state, any test that allocates component IDs or runs the simulator relies on it.
- Coverage is behavior-focused (architecture regression guards): `test_atom.py` (connection slots), `test_board.py` (atom placement/movement, `move_atom` atomicity), `test_manipulator.py` (arm grab/release, movement recording, ENDPOINT_OVERLAP payloads), `test_simulator.py` (entrance spawn, exit consume, arm moving an atom to the exit, sweep collisions), `test_geometry.py` (hex↔xy mapping, offset rotation, circle overlap), `test_movement.py` (`Movement.atom_xy` interpolation), `test_collision.py` (`detect_collision` unit tests), `test_level_env.py` (per-env id/counter isolation), `test_blueprint_registry.py` (registry isolation/clone), `test_level_spec.py` (spec validation branches), `test_level.py` (level run/result/independence), `test_level_loader.py` (`.oml` parsing and demo end-to-end). Shared builders live in `tests/fixtures/` (`shapes.py`, `levels.py`).
- Logging goes through `opus_magnum_sym.logging`. `configure_logging(pretty=True)` (REPL default) emits aligned columns with one separator between setup and runtime; `configure_logging(pretty=False)` emits raw stdlib messages. Do not use `icecream` in source.
- Ruff is heavily configured in `pyproject.toml`. Most docstring rules and unused-import rules are intentionally ignored; do not fight the existing lint list unless asked.

## 8. Common Agent Tasks

### Add a new component type

1. Add the enum value to `ComponentType` in `elements/components/base_component.py`.
2. Create the concrete class inheriting from `Component`.
3. Register it in `_COMPONENT_MAP` in `elements/components/components_index.py`.
4. Update `Simulator.add_component` if special handling is needed (e.g. entrypoints).
5. Add renderer support in `render/renderer.py` if it needs visual representation.

### Add a new per-step action

1. Add the action to `StepActionType` in `elements/actions/actions.py`.
2. Handle it in the relevant component's `_execute` method.

### Add an RL-style environment wrapper

- Use `Simulator` as the underlying engine.
- Expose `board.get_state()` as observations.
- Map actions to `assign_step_action` calls and step with `next_step()`.
- Use `sim.env.results.total_finished()` or wrap a `Level` and inspect its `LevelResult`.

### Define and run a level

1. Build a `LevelSpec` (or `Level.from_file("level.oml")`) with local shapes, entrypoints, allow-list, and step limit.
2. Construct a `Level(spec)` — it owns a fresh env and a cloned blueprint registry, and places the entrypoints.
3. Build the solution through `level.place(...)` / `level.assign_step_action(...)`, or `level.load_solution("solution.oms")`.
4. `result = level.run()` returns a `LevelResult`; inspect `result.status`, `result.total_finished`, `result.finished_by_exit`, and `result.error`.

A complete end-to-end Python example lives in the `levels/level.py` module docstring.

## 9. Known Limitations / TODOs

- The transporter component (`TRANSPORTER`) has no concrete class and is not implemented.
- `EXTEND`/`RETRACT` are implemented only for the piston arm (`arm_piston`, `RetractableManipulator`); the basic arm rejects them. `MOVE_POS`/`MOVE_NEG` remain declared but unimplemented.
- Multi-arm specs (`arm_double`, `arm_triple`, `arm_hex`) are data-only (`implemented=False`): constructing a `Manipulator` with `arm_count != 1` raises `ComponentAssignmentError`. Single-arm `arm` and `arm_piston` are placeable.
- Atoms carry per-direction connection slots and manual bonding, but alchemical glyph effects, multiple bond types, and bond rendering are not modeled. `AtomType.NONE`/`BASIC` are non-game placeholders rejected by the high-level placement API and level entrypoints.
- The simulator runs components in two hard-coded phases; simultaneous actions can race.
- Mechanical molecule collision is structural: an arm can't move/release into a cell held by another arm (cell-level), and can't move a molecule that is also held by another arm (`Atom.held_by` is a set of holder ids — a shared molecule is blocked from moving rather than torn into two places). Note: the current whole-molecule grab (`Board.pop_molecule`) removes the entire connected molecule, so a second arm can't grab an already-held molecule — the shared-holder state is currently unreachable, and the shared-move guard only triggers once grab is changed to allow multiple holders.
- `Board.place_componet` retains a typo in the source; preserve existing naming unless refactoring.

## 10. Files to Read First

For any new task, start with these:

1. `README.md` — high-level description.
2. `examples/10_basic_flow.oms` — concrete DSL example.
3. `src/opus_magnum_sym/simulation/simulator.py` — simulation orchestration.
4. `src/opus_magnum_sym/elements/components/manipulator.py` — how arms act.
5. `src/opus_magnum_sym/interpreter/sim_interpreter.py` — DSL parsing.
6. `src/opus_magnum_sym/elements/board/board.py` — board state representation.

## 11. Files to Ignore

Unless explicitly requested do not touch or read these:

1. `TODO.md` — user-only issues tracker.

## 12. Skills

- `.agents/skills/oms-authoring/SKILL.md` — how to author and style `.oms` solution/level scripts (DSL syntax, component IDs, arm hand positioning, house style). Load it before writing or editing a `.oms` file.
