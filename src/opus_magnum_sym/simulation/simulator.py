from typing import TYPE_CHECKING

from icecream import ic

import opus_magnum_sym.elements.env.index_manager as im
from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.board import Board, Direction, Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.components.components_index import get_component_type
from opus_magnum_sym.elements.components.connections import ConnectionGraph
from opus_magnum_sym.elements.env import level_counter
from opus_magnum_sym.logging import logger

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
        self.connections = ConnectionGraph()
        self.step = 0

    def _verify_init_state(self):
        # TODO: create more granular verification if needed
        entrypoints = {comp.type for comp in self.entrypoints.values()}
        if not all(
            (
                ComponentType.ENTRANCE in entrypoints,
                ComponentType.EXIT in entrypoints,
            ),
        ):
            msg = "Incorrect initial state of board, ENTER or EXIT is missing."
            raise SimulationRuntimeError(msg, step=self.step)

    def held_cells(self) -> set[Hex]:
        """
        Cells currently occupied by molecules held in an arm's hand.
        """
        cells: set[Hex] = set()
        for comp in self.components.values():
            holding = getattr(comp, "holding", None)
            if holding:
                cells.update(holding)
        return cells

    def next_step(self):
        if self.step == 0:
            self._verify_init_state()

        for comp in self.components.values():
            # Mechanical collision: arm cannot move cells held by another arm.
            # Recomputing per component means later arms see where
            # earlier arms moved this step.
            blocked = self.held_cells() - set(getattr(comp, "holding", None) or ())
            comp.execute_step(self.board, self.step, blocked_cells=blocked)
        held_cells = self.held_cells()
        for comp in self.entrypoints.values():
            if comp.type == ComponentType.ENTRANCE and comp.pos in held_cells:
                continue
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
        comp = get_component_type(comp_type)(idx=new_id, pos=cell, **kwargs)
        if not self.board.place_component_cells(comp.footprint(), comp_type, new_id):
            im.free(new_id)
            msg = f"Cannot place {comp_type.name.lower()} at ({cell.r}, {cell.s})."
            raise SimulationRuntimeError(msg, step=self.step)

        if comp_type in {
            ComponentType.ENTRANCE,
            ComponentType.EXIT,
            ComponentType.CONNECTOR,
            ComponentType.DISCONNECTOR,
        }:
            self.entrypoints[new_id] = comp
        else:
            self.components[new_id] = comp

        logger.info(
            "placed %s @ (%d, %d)",
            comp_type.name.lower(),
            cell.r,
            cell.s,
            source="simulator",
            source_pos=f"({cell.r}, {cell.s})",
        )

    def _lookup(self, idx: int) -> Component | None:
        if idx in self.components:
            return self.components[idx]
        return self.entrypoints.get(idx)

    def _refresh_groups(self) -> None:
        for comp in self.entrypoints.values():
            group = [self._lookup(i) for i in self.connections.group_of(comp.idx)]
            comp.group = [c for c in group if c is not None and c.idx != comp.idx]

    def connect_components(self, id_a: int, id_b: int) -> bool:
        comp_a = self._lookup(id_a)
        comp_b = self._lookup(id_b)
        if comp_a is None or comp_b is None:
            return False
        if id_a == id_b or id_b in self.connections.links_of(id_a):
            return False
        if comp_a.type != comp_b.type or comp_a.type not in {
            ComponentType.ENTRANCE,
            ComponentType.EXIT,
            ComponentType.CONNECTOR,
            ComponentType.DISCONNECTOR,
        }:
            return False
        # Multi-cell entrypoints: switch to any-footprint-cell neighborhood when they appear.
        if not Direction().are_adjacent(comp_a.pos, comp_b.pos):
            return False
        self.connections.add(id_a, id_b)
        self._refresh_groups()
        return True

    def disconnect_components(self, id_a: int, id_b: int) -> bool:
        if id_b not in self.connections.links_of(id_a):
            return False
        self.connections.remove(id_a, id_b)
        self._refresh_groups()
        return True

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
        self.board.remove_component_cells(comp.footprint())
        self.connections.remove_component(comp_id)
        self.im.free(comp_id)
        self._refresh_groups()

    def reset(self) -> None:
        self.board.clear()
        self.components.clear()
        self.entrypoints.clear()
        self.connections = ConnectionGraph()
        self.step = 0
        self.im.reset()
        level_counter.reset()
