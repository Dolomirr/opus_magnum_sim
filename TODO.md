# TODOs

- [ ] Correct steps handling.
    - [ ] Ensure enter/exit apply change on atom above only within correct step.
        - How to handle removal on movement?
- [ ] Atom connection.
    - [ ] Multi hex components.
    - [ ] Dynamic atoms IDs.
        - Should it be handled via "build-in" atoms, while combinations separately?
        - Only generic types as enums.
    - [ ] Grabbed counter for each atom.
    - [ ] Slots for direction, each holding value if connection in that direction exists.
    - [ ] Grabbing logic should be moved to atoms (?).
    - [ ] Moving molecules.
        - Correct rotations (cutout matrices with molecules and dot products?)
        - [ ] Graph traversal with "bounded" atoms.
    - [ ] Actual components to glue/un-glue molecules.
- [ ] ! Collision
    - For start molecules and atoms can go throe each other ig, so only multi arm grab problem is to solve.
    - [ ] For Atoms define "holded_by" or smth similar
    - [ ] Define "movement root" to validate conflicts before moving atom (multi arm grab etc).
- [ ] Programs cycle (optional, or just the simplest, without epicycles)
- [ ] Exporting board state on steps via python structure.
- [ ] Optimization.
    - [ ] Prepare test suit.
    - [ ] Headless simulation.
        - [ ] Parallel?
    - [ ] Prepare for static structures.
        - [ ] Atoms store as limited pre-allocated array (since board is not infinite) with ids.
        - Classify what cannot be handled statically.
- [ ] Proper logging.
- [ ] Interactive simulation control via keyboard (is it really needed?).


