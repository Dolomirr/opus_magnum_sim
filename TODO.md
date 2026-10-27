# TODOs

> - [ ]: planned / in process
> - [x]: done
> - [ ] (?): possible in future / it depends
> - [ ] (-): continuous process
> - : comment / remark
> - ...: require filling in


## Long Term Targets

- [ ] Correct steps handling.
    - [x] Ensure enter/exit apply change on atom above only within correct step.
    - ...
- [ ] Composed multi hex components (predefined shapes, rather than freestyle).
    - [ ] Pre-defined entrances and exits placement [Level completion logic]
        - [ ] Way of describing such shapes (and possibly "finding root"?)
    - [ ] Fixed shapes of components.
        - [ ] Various shape connectors.
        - [x] Snowflake manipulators
        - [ ] Destructors.
- [x] Atom connection.
    - [x] Generic multi hex components.
    - [x] Dynamic atoms IDs.
        - [x] Add generic types of atoms.
    - [x] Grabbed counter for each atom.
    - [x] Slots for direction, each holding value if connection in that direction exists.
    - [x] Grabbing logic should be moved to atoms (?).
    - [x] Moving molecules.
        - [x] Graph traversal with "bounded" atoms.
        - [x] Rotation around "hand" not only "base".
    - [x] Actual components to glue/un-glue molecules.
- [ ] Level completion logic
    - [x] Per-exit counters (each should be correct).
    - [ ] Move things like `index_manager` and `result_counter` to Simulator or separate Level to isolate envs.
    - [ ] Actual validation of level.
    - [ ] Stale level detection (then no steps limit is given)
    - [ ] Entrances and exists verification, connected to [Composed multi hex components]
    - [ ] Conditions to mark level as correct / finished.
    - [ ] Results counters.
        - [ ] Steps.
        - [ ] Const per-component.
        - [ ] (?) Used space.
- [x] ! Collision
    - [x] ~For start molecules and atoms can go throe each other ig, so only multi arm grab problem is to solve.~
    - [x] ~For Atoms define `held_by`or smth similar~
    - [x] Define `movement_root` to validate conflicts before moving atom (multi arm grab etc.).
    - [x] ~Spatial collision seem to not error-out in REPL?~
    - [x] Make mechanical collision to error-out sim.
- [ ] Program Flow.
    - [ ] Programs cycle (optional, or just the simplest, without epicycles)
    - [ ] (?) Possibly only level-wise max steps limit [Level completion logic]
- [ ] Exporting board state on steps via python structure (full serialization).
- [ ] Optimization.
    - [x] Headless simulation.
        - [x] ~Parallel?~
        - [x] Keep-alive on python-object level daemon.
    - [ ] (?) Numba (most probably) - Need to consider warm-ups and optimization control.
    - [ ] (?) C+- - Ah shiiit here we go again...
    - [ ] (?) Nim - Can be nice, but not transparent.
    - [ ] Prepare for static structures.
        - [ ] Atoms store as limited pre-allocated array (since board is not infinite) with ids.
        - Classify what cannot be handled statically.
        - ...
    - [ ] (?) Consider bitmap collision overlap checking, instead of full sub-step pass.
- [x] Proper logging.
- [ ] Ensure determinism.
    - Currently two hard-coded phases + dict iteration cause simultaneous actions to race
    - [ ] Define resolution order
- [ ] ~(?) Interactive simulation control via keyboard (is it really needed?).~
  - [ ] (?) Keyboard control.
  - [ ] (?) Interactive adding.
  - [x] Ctrl+C handling
- [ ] ! Library usage [Level completion logic]
- [ ] In-between step visualization (optional ig).
    - Ghost-particles, after [Collision].

## Short Term (Reminders)

- ...
- Component signature (`.holding` is defined only for arm etc.) (generics?)
- REPL's `!save` seem to lose connections?

- Make level separate entity, with separate counters and per-level defined entrances (instead of just `straight_2`)

