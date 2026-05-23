from icecream import ic

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.objects.base_object import ObjectType
from opus_magnum_sym.simulation.simulator import Simulator


def main():
    sim = Simulator((10, 10))

    sim.add_component(Hex(2, 3), ComponentType.ENTRANCE, object_type=ObjectType.ATOM)
    sim.add_component(Hex(3, 2), ComponentType.EXIT, object_type=ObjectType.ATOM)
    sim.add_component(Hex(3, 3), ComponentType.ARM)

    # ic(sim.board.base_obj, sim.board.objects)
    # ic(sim.components, sim.entrypoints)

    sim.assign_step_action(2, 1, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(2, 2, StepActionType.GRAB)
    sim.assign_step_action(2, 3, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(2, 4, StepActionType.RELEASE)
    sim.assign_step_action(2, 5, StepActionType.ROTATE_CLW)

    sim.assign_step_action(2, 6, StepActionType.GRAB)
    sim.assign_step_action(2, 7, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(2, 8, StepActionType.RELEASE)
    sim.assign_step_action(2, 9, StepActionType.ROTATE_CLW)

    for _ in range(12):
        ic(sim.step)
        sim.next_step()
        ic(sim.board.base_obj, sim.board.objects)


if __name__ == "__main__":
    main()
