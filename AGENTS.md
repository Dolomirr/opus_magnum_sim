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
uv run opus-magnum run examples/test_flow.oms --steps 30

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
uv run opus-magnum validate examples/test_flow.oms
```

The REPL accepts DSL commands directly and meta-commands prefixed with `!` (e.g. `!run 30`, `!load examples/test_flow.oms`, `!list`, `!help`; also `!history [n]`, `!edit`/`!e`, and `!viz [on|off]` to toggle visualization). Tab completion (commands, component/action names, ids, file paths), history-based auto-suggestions, and persistent history (`~/.cache/opus_magnum_sym/repl_history`) are wired up in `repl/sim_repl.py` via prompt_toolkit.

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
│   ├── components/     # Components: arms, entrance, exit
│   ├── env/            # Global-ish helpers: index manager, level counter
│   └── atoms/          # Atom type/instances + molecule BFS (molecule.py)
├── interpreter/        # Parses .oms solution files
├── render/             # Pygame-based visualization
├── repl/               # Interactive REPL
└── simulation/         # Simulator orchestration
tests/                  # pytest tests + conftest.py (reset global state fixture)
examples/               # Example .oms solutions + ad-hoc integration scripts
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
  - `idx`: unique ID from the global index manager.
  - `pos`: `Hex` location on the board.
  - `type`: `ComponentType`.
  - `rotation`: `0..5`.
  - `_programm`: a dict mapping simulation step → `StepActionType`.
  - `footprint()`: cells occupied by the component's base (default `[pos]`; multi-cell components override it as a pure function of `pos` + `rotation`).
- `ComponentType` values: `ENTRANCE`, `EXIT`, `ARM`, `ARM_RETR`, `TRANSPORTER`.
- Concrete classes:
  - `Manipulator` (`ARM`) — rotates, grabs/releases atoms at its hand position.
  - `Enter` (`ENTRANCE`) — spawns an `Atom` of its configured `AtomType` if the cell is empty, then bonds it to any connected entrance partners.
  - `Exit` (`EXIT`) — accepts a full molecule via group exact-cover matching (see "Connected entrances/exits" below) and increments `level_counter.CORRECT_FINISHED`.

### Atoms (`elements/atoms/atom.py`)

- `AtomType`: `NONE` and `BASIC` (the only atom kind so far).
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
- Component IDs are allocated globally via `elements/env/index_manager.py`. In tests, reset it with `im.reset()`.

### Connected entrances/exits (`elements/components/connections.py`)

- `ConnectionGraph` is a pure-id undirected link graph (`add`, `remove`, `remove_component`, `links_of`, `group_of`); `group_of` returns the transitive closure including the node itself.
- `Simulator.connect_components(id_a, id_b)` links two components, returning `False` (no state change) unless both ids exist, differ, are not already linked, share the same type, and that type is `ENTRANCE` or `EXIT`, and the two cells are adjacent. `disconnect_components` removes an existing link.
- On any link change the simulator refreshes each entrypoint's `group` list (its transitive neighbours). Linked entrances bond their spawned atoms together; linked exits accept a molecule only when it covers every group cell exactly (set equality), consuming the whole molecule and incrementing `CORRECT_FINISHED` once.

### Interpreter (`interpreter/sim_interpreter.py`)

Parses `.oms` text files. Commands:

```text
# Place a component
comp <x> <y> <COMPONENT_TYPE> [key=value ...]

# Schedule a step action on a component
action <comp_id> <step> <STEP_ACTION_TYPE>

# Link two components (adjacent, same type, ENTRANCE or EXIT only)
connection <comp_id_a> <comp_id_b>

# Unlink two components
disconnection <comp_id_a> <comp_id_b>
```

Example (`examples/test_flow.oms`):

```text
comp 2 3 entrance atom_type=basic
comp 3 2 exit atom_type=basic
comp 3 3 arm

action 2 1 rotate_cclw
action 2 2 grab
action 2 3 rotate_cclw
action 2 4 release
```

Keyword arguments supported by `_handle_comp`:

- `atom_type=<AtomType name>` — e.g. `atom_type=basic`
- `rotation=<int>` — initial rotation
- `length=<int>` — arm length

## 6. Rendering

`render/renderer.py` uses `pygame-ce`. `BoardRenderer` draws the grid, components, objects, and manipulator hands. It is typically driven from the REPL or from ad-hoc scripts like `examples/_test_flow.py`.

## 7. Testing & Linting Conventions

- Tests live in `tests/` and use `pytest`.
- `tests/conftest.py` provides an autouse `clean_state` fixture that resets the global `index_manager` and `level_counter` before every test. Because these keep module-level state, any test that allocates component IDs or runs the simulator relies on it.
- Coverage is behavior-focused (architecture regression guards): `test_atom.py` (connection slots), `test_board.py` (atom placement/movement, `move_atom` atomicity), `test_manipulator.py` (arm grab/release, movement recording, ENDPOINT_OVERLAP payloads), `test_simulator.py` (entrance spawn, exit consume, arm moving an atom to the exit, sweep collisions), `test_geometry.py` (hex↔xy mapping, offset rotation, circle overlap), `test_movement.py` (`Movement.atom_xy` interpolation), `test_collision.py` (`detect_collision` unit tests).
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
- Use `level_counter.CORRECT_FINISHED` or custom reward logic.

## 9. Known Limitations / TODOs

- Connector / disconnector / transporter components themselves are not implemented; the link graph and `connection` DSL command exist only as the structure they will plug into.
- `EXTEND`, `RETRACT`, `MOVE_POS`, `MOVE_NEG` are declared but largely unimplemented.
- Only a single atom kind (`AtomType.BASIC`) exists. Atoms have per-direction connection slots and manual bonding, but alchemical glyphs, multiple bond types, and bond rendering are not modeled.
- The simulator runs components in two hard-coded phases; simultaneous actions can race.
- Mechanical molecule collision is structural: an arm can't move/release into a cell held by another arm (cell-level), and can't move a molecule that is also held by another arm (`Atom.held_by` is a set of holder ids — a shared molecule is blocked from moving rather than torn into two places). Note: the current whole-molecule grab (`Board.pop_molecule`) removes the entire connected molecule, so a second arm can't grab an already-held molecule — the shared-holder state is currently unreachable, and the shared-move guard only triggers once grab is changed to allow multiple holders.
- `level_counter.CORRECT_FINISHED` is a module-level counter — not suitable for parallel environments without refactoring. It counts delivered molecules (not atoms), so a lone exit no longer tears apart a multi-atom molecule touching it.
- `Board.place_componet` retains a typo in the source; preserve existing naming unless refactoring.

## 10. Files to Read First

For any new task, start with these:

1. `README.md` — high-level description.
2. `examples/test_flow.oms` — concrete DSL example.
3. `src/opus_magnum_sym/simulation/simulator.py` — simulation orchestration.
4. `src/opus_magnum_sym/elements/components/manipulator.py` — how arms act.
5. `src/opus_magnum_sym/interpreter/sim_interpreter.py` — DSL parsing.
6. `src/opus_magnum_sym/elements/board/board.py` — board state representation.

## 11. Skills

- `.agents/skills/oms-authoring/SKILL.md` — how to author and style `.oms` solution/level scripts (DSL syntax, component IDs, arm hand positioning, house style). Load it before writing or editing a `.oms` file.
