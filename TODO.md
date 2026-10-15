# TODOs

> - [ ]: planned / in process
> - [x]: done
> - [?]: possible in future / it depends
> - [-]: continuous process
> - : comment / remark
> - ...: require filling in


## Long Term Targets

- [ ] Correct steps handling.
    - [x] Ensure enter/exit apply change on atom above only within correct step.
    - ...
- [ ] Atom connection.
    - [x] Multi hex components.
        - [ ] Add high-level api for batch adding (pre-define forms, rather than freestyle)
    - [x] Dynamic atoms IDs.
        - [ ] Add generic types of atoms.
    - [ ] Grabbed counter for each atom.
    - [x] Slots for direction, each holding value if connection in that direction exists.
    - [x] Grabbing logic should be moved to atoms (?).
    - [x] Moving molecules.
        - [x] Graph traversal with "bounded" atoms.
        - [x] Rotation around "hand" not only "base".
    - [ ] Actual components to glue/un-glue molecules.
- [ ] Level completion logic.
    - [ ] Per-exit counters (each should be correct).
    - [ ] Conditions to mark level as correct / finished.
- [ ] ! Collision
    - [?] For start molecules and atoms can go throe each other ig, so only multi arm grab problem is to solve.
    - [ ] For Atoms define `held_by`or smth similar
    - [ ] Define `movement_root` to validate conflicts before moving atom (multi arm grab etc.).
    - ...
- [ ] Program Flow.
    - [ ] Programs cycle (optional, or just the simplest, without epicycles)
    - [?] Possibly only level-wise max steps limit @[Level completion logic]
- [ ] Exporting board state on steps via python structure (full serialization).
- [ ] Optimization.
    - [-] Test suit.
    - [x] Headless simulation.
        - [?] Parallel?
    - [?] Numba (most probably).
        - [ ] Prepare for static structures.
            - [ ] Atoms store as limited pre-allocated array (since board is not infinite) with ids.
            - Classify what cannot be handled statically.
            - ...
- [x] Proper logging.
- [?] Interactive simulation control via keyboard (is it really needed?).
  - [ ] Keyboard control.
  - [ ] Interactive adding.
  - [ ] Ctrl+C handling
- [ ] In-between step visualization (optional ig).
    - Ghost-particles, after @[! Collision].

## Short Term (Reminders)

- ...
- Component signature (`.holding` is defined only for arm etc.) (generics?)
- 

