import time

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.env import level_counter
from opus_magnum_sym.render.renderer import BoardRenderer
from opus_magnum_sym.simulation.simulator import Simulator


def main():
    sim = Simulator((8, 8))
    renderer = BoardRenderer(sim)

    # Connected entrances: linking them makes the spawned atoms pre-bonded.
    sim.add_component(Hex(2, 3), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(2, 4), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.connect_components(0, 1)

    sim.add_component(Hex(5, 5), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 3), ComponentType.ARM)

    sim.assign_step_action(3, 1, StepActionType.GRAB)
    sim.assign_step_action(3, 2, StepActionType.ROTATE_CLW)
    sim.assign_step_action(3, 3, StepActionType.RELEASE)

    sim.next_step()  # spawns a bonded pair at (2,3)-(2,4)
    sim.remove_component(0)  # entrances would respawn once the atoms move
    sim.remove_component(1)

    renderer.draw()
    renderer.tick(60)
    time.sleep(2)

    for _ in range(3):
        sim.next_step()
        renderer.draw()
        renderer.tick(60)
        time.sleep(2)

    # Connected exits: only a molecule covering every exit cell is consumed.
    sim.reset()
    sim.add_component(Hex(2, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(0, 0), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.connect_components(0, 1)

    a = Atom(AtomType.BASIC)
    b = Atom(AtomType.BASIC)
    sim.board.place_atom(Hex(2, 2), a)
    sim.board.place_atom(Hex(3, 2), b)
    sim.board.connect_atoms(Hex(2, 2), Hex(3, 2))

    renderer.draw()
    renderer.tick(60)
    time.sleep(2)

    sim.next_step()
    print("CORRECT_FINISHED =", level_counter.total_finished())

    renderer.draw()
    renderer.tick(60)
    time.sleep(2)


if __name__ == "__main__":
    main()
