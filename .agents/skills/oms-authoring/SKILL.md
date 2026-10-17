---
name: oms-authoring
description: Author and style `.oms` Opus Magnum puzzle/solution scripts — DSL commands and tokens, component-ID allocation, arm hand positioning, required house style (leading blank line, context comment, sections, `# id n` tags), and the validate/run/save workflow.
---

# Authoring `.oms` Solution Scripts

## When to use this skill

Use it whenever you create or edit a `.oms` file (usually under `examples/`), or are
asked to script an Opus Magnum puzzle/level, lay out components and step actions, or
fix a `.oms` validation/runtime error.

## How a `.oms` file works

A `.oms` file is a plain-text DSL, loaded line by line by
`SimInterpreter.load_file` (`src/opus_magnum_sym/interpreter/sim_interpreter.py`). Rules:

- Blank lines are ignored.
- A `#` starts a comment; it may be a full line or inline after a command.
- Each command is tokenized with `shlex`, so `key=value` stays atomic and quoting works if needed.
- Commands run top-to-bottom; component IDs follow this order (see "Component IDs").
- Parsing is lenient: a bad line prints `Error parsing line N: ...`, `Unknown command ...`,
  or `Failed to connect ...` and is skipped — it does not abort the load. Watch for these messages.

## Command reference

```text
comp <r> <s> <type> [key=value ...]      # place a component (alias: c)
action <comp_id> <step> <action_type>    # schedule a step action (alias: a)
remove <comp_id>                         # remove a component (alias: rm)
connection <id_a> <id_b>                 # link two components
disconnection <id_a> <id_b>              # unlink two components
```

- `comp`: `r` = row, `s` = column (hex `Hex(r, s)`). `<type>` is a `ComponentType` name, case-insensitive.
- `action`: `<comp_id>` is the component's id, `<step>` the 0-based simulation step,
  `<action_type>` a `StepActionType` name (case-insensitive).

## Component types

| token | class | required kwargs | notes |
|-------|-------|-----------------|-------|
| `arm` | `Manipulator` | — | optional `rotation`, `length`; only component that accepts `action` |
| `entrance` | `Enter` | `atom_type` | spawns an atom each step its cell is empty |
| `exit` | `Exit` | `atom_type` | consumes a matching molecule; required by `validate`/`run` |
| `connector` | `Connector` | `atom_type` | bonds atoms sitting on its glyph + connected glyph partners |
| `disconnector` | `Disconnector` | `atom_type` | breaks bonds between atoms on its glyph + connected partners |

`arm_retr` and `transporter` are enum values but are **not** registered in
`_COMPONENT_MAP`; using them in `comp` raises `Unknown component`.

## Component kwargs

- `atom_type=<name>` — required for `entrance`, `exit`, `connector`, `disconnector`.
  Only `basic` exists today.
- `rotation=<0..5>` — optional initial rotation (default `0`).
- `length=<int>` — arm hand length (default `1`); arm only.

Omitting a required `atom_type` makes the `comp` line fail at parse time (component not placed).

## Step actions

Usable on an arm:

| token | effect |
|-------|--------|
| `none` | remove any action assigned to that step (rarely used in files) |
| `grab` | pick up the whole molecule at the hand (no-op if empty) |
| `release` | drop the held molecule onto its current cells (no-op if blocked) |
| `rotate_clw` | full rotation: arm swings around its base, carrying the held molecule |
| `rotate_cclw` | full rotation, opposite direction |
| `rotate_molecule_clw` | in-place: arm stays, held molecule rotates around the hand |
| `rotate_molecule_cclw` | in-place, opposite direction |

Declared but **not usable** on the basic arm — they raise `ActionAssignmentError` at
execution: `extend`, `retract`, `move_pos`, `move_neg`.

`action` targets only non-entrypoint components (in practice, arms). Assigning an
`action` to an entrance/exit/connector/disconnector id raises a load-time error (the line is skipped).

## Coordinates, board size, adjacency

- The CLI creates a fixed `Simulator((10, 10))`, so valid coordinates are `0..9` for
  both `r` and `s`. Out-of-bounds `comp` lines fail placement.
- Hex cells are adjacent along the six `Direction.H*` offsets. `connection`/`disconnection`
  only work between **adjacent** cells of the **same type** (and only for
  entrance/exit/connector/disconnector).

## Component IDs

- IDs are allocated by `index_manager.allocate()` starting at `0`, in the order `comp` lines appear.
- `remove` frees an id back into the pool, so a later `comp` may reuse it. When you write
  `# id n`, use the id the component actually receives at that point in the file.
- Document every `comp` line with an inline `# id n` comment (house rule below).

## Arm hand position

The hand sits at the arm's cell plus the rotation offset (scaled by `length`):

| rotation | direction | offset (dr, ds) |
|----------|-----------|-----------------|
| 0 | H1 | (−1, +1) |
| 1 | H3 | (0, +1) |
| 2 | H5 | (+1, 0) |
| 3 | H7 | (+1, −1) |
| 4 | H9 | (0, −1) |
| 5 | H11 | (−1, 0) |

Hand cell = `(r + dr*length, s + ds*length)`. Default `rotation=0`, `length=1` → hand at `(r−1, s+1)`.

## House style (required)

Follow these rules for every new `.oms` file:

1. **Leading blank line** — the file starts with one empty line before anything else.
2. **Context comment** — immediately after, a short, dry comment stating the scenario,
   e.g. `# verification of connector/disconnector components`. One or two lines.
3. **Logical sections** — group related lines (components, connections, actions) and
   separate sections with one blank line.
4. **Section comments only when needed** — annotate a section only when it is not
   self-explanatory or is important to the scenario. Do not comment every section or every step.
5. **`# id n` on every component** — each `comp` line ends with an inline `# id n`
   showing the allocated id.
6. **Ascending step order** — within a component, list `action` lines by increasing `step`.

These rules are cosmetic; the parser ignores blank lines and comments. They exist for
human and agent readability.

## Canonical template

See `templates/basic.oms`, reproduced here:

```text

# minimal entrance -> arm -> exit delivery

# Entrance spawns a basic atom at (2,3).
comp 2 3 entrance atom_type=basic # id 0

# Exit consumes the atom once it is released here.
comp 3 2 exit atom_type=basic     # id 1

# Arm at (3,3): rotation 0 -> hand at (2,4); length defaults to 1.
comp 3 3 arm                      # id 2

# Move the atom from the entrance to the exit.
action 2 1 rotate_cclw
action 2 2 grab
action 2 3 rotate_cclw
action 2 4 release
```

## Authoring & verification workflow

```bash
# Validate syntax + entrance/exit presence (does not run the simulation)
just validate examples/my_level.oms

# Run headlessly and print the delivered-molecule count
just run examples/my_level.oms 30
```

## Caveats / known limitations that affect scripts

- Entrances re-spawn the instant their cell is emptied, so a spare atom can remain after an arm grabs.
- Steps run non-entrypoint components first, then entrypoints; simultaneous actions can race.
- `!save` / `!edit` emit a minimal canonical form and drop `connection`/`disconnection`
  links, `# id n` comments, section comments, and the leading blank line. Treat
  hand-written files as the source of truth for style and connections.
- `connection` is the only link keyword; there is no `disconnect` alias (use `disconnection`).
- Only `AtomType.BASIC` exists; bond/type patterns beyond "covers the exit group exactly"
  are not yet verified.
