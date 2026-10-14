# TODOs

## Long Term Targets

- [ ] Correct steps handling.
    - [ ] Ensure enter/exit apply change on atom above only within correct step.
        - How to handle removal on movement?
- [ ] Atom connection.
    - [ ] Multi hex components.
    - [x] Dynamic atoms IDs.
        - [ ] Add generic types of atoms.
        - [ ] Per-exit counters (each should be correct).
    - [ ] Grabbed counter for each atom.
    - [x] Slots for direction, each holding value if connection in that direction exists.
    - [x] Grabbing logic should be moved to atoms (?).
    - [x] Moving molecules.
        - [x] Graph traversal with "bounded" atoms.
        - [ ] Rotation around "hand" not only "base".
    - [ ] Actual components to glue/un-glue molecules.
- [ ] ! Collision
    - For start molecules and atoms can go throe each other ig, so only multi arm grab problem is to solve.
    - [ ] For Atoms define "holded_by" or smth similar
    - [ ] Define "movement root" to validate conflicts before moving atom (multi arm grab etc.).
    - ...
- [ ] Program Flow.
    - [ ] Programs cycle (optional, or just the simplest, without epicycles)
- [ ] Exporting board state on steps via python structure.
- [ ] Optimization.
    - [ ] Prepare test suit.
    - [x] Headless simulation.
        - [ ] Parallel?
    - [ ] Numba (most probably).
        - [ ] Prepare for static structures.
            - [ ] Atoms store as limited pre-allocated array (since board is not infinite) with ids.
            - Classify what cannot be handled statically.
            - ...
- [x] Proper logging.
- [ ] Interactive simulation control via keyboard (is it really needed?).
  - [ ] Keyboard control.
  - [ ] Interactive adding.
  - [ ] Ctrl+C handling

## Short Term (Reminders)

- ...
- Component signature (.holding is defined only for arm etc.)
- Make/Just-file
- Visualization for connections
- Move demos/scratches from root
- Rotating alongside head (not base).

