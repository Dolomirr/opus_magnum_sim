from typing import TYPE_CHECKING

from icecream import ic

import opus_magnum_sym.elements.env.index_manager as im
from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.board import Board, Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.components.components_index import get_component_type
from opus_magnum_sym.elements.env import level_counter

if TYPE_CHECKING:
    from opus_magnum_sym.elements.components.base_component import Component


# TODO: sprinkle Errors across simulation
class SimulationRuntimeError(Exception):
    def __init__(
        self,
        message,
        step: int,
    ) -> None:
        self.message = message
        super().__init__(self.message)


class Simulator:
    def __init__(self, size: tuple[int, int]) -> None:
        self.board: Board = Board(*size)
        self.im = im
        self.components: dict[int, Component] = {}
        self.entrypoints: dict[int, Component] = {}
        self.step = 0

    def _verify_init_state(self):
        # TODO: create more granular verification if needed
        ic(self.entrypoints.values())
        entrypoints = {comp.type for comp in self.entrypoints.values()}
        if not all(
            (
                ComponentType.ENTRANCE in entrypoints,
                ComponentType.EXIT in entrypoints,
            ),
        ):
            msg = "Incorrect initial state of board, ENTER or EXIT is missing."
            raise SimulationRuntimeError(msg, step=self.step)

    def next_step(self):
        if self.step == 0:
            self._verify_init_state()

        for comp in self.components.values():
            comp.execute_step(self.board, self.step)

            # TODO: ! that may cause race conditions
        for comp in self.entrypoints.values():
            comp.execute_step(self.board, self.step)

        self.step += 1

    # TODO: do something with kwargs
    # TODO: rework id logic (again)
    def add_component(
        self,
        cell: Hex,
        comp_type: ComponentType,
        **kwargs,
    ):
        new_id = im.allocate()
        self.board.place_componet(cell, comp_type, new_id)

        # TODO: make that normal
        if comp_type in {ComponentType.ENTRANCE, ComponentType.EXIT}:
            self.entrypoints[new_id] = get_component_type(comp_type)(idx=new_id, pos=cell, **kwargs)
        else:
            self.components[new_id] = get_component_type(comp_type)(idx=new_id, pos=cell, **kwargs)

    def assign_step_action(
        self,
        comp_id: int,
        step: int,
        action: StepActionType,
    ):
        self.components[comp_id].assign_step_action(step=step, action=action)

    def remove_component(self, comp_id: int) -> None:
        comp = self.components.pop(comp_id, None) or self.entrypoints.pop(comp_id, None)
        if comp is None:
            msg = f"Component with id {comp_id} does not exist."
            raise SimulationRuntimeError(msg, step=self.step)
        self.board.remove_component(comp.pos)
        self.im.free(comp_id)

    def reset(self) -> None:
        self.board.clear()
        self.components.clear()
        self.entrypoints.clear()
        self.step = 0
        self.im.reset()
        level_counter.CORRECT_FINISHED = 0
