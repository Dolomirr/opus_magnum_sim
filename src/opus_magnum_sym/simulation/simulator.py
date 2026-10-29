from typing import TYPE_CHECKING

from icecream import ic

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Board, Direction, Hex
from opus_magnum_sym.elements.components import (
    BlueprintRegistry,
    ComponentSpec,
    ComponentType,
    ManipulatorSpec,
    ShapeTemplate,
    default_registry,
)
from opus_magnum_sym.elements.components.components_index import get_component_type
from opus_magnum_sym.elements.components.connections import ConnectionGraph
from opus_magnum_sym.elements.env.level_env import LevelEnv, default_env
from opus_magnum_sym.logging import logger
from opus_magnum_sym.simulation.collision import CollisionEvent, detect_collision
from opus_magnum_sym.simulation.errors import SimulationCollisionError, SimulationRuntimeError
from opus_magnum_sym.simulation.movement import Movement
from opus_magnum_sym.simulation.placement import PlacementRecord

if TYPE_CHECKING:
    from opus_magnum_sym.elements.components.base_component import Component


class Simulator:
    def __init__(
        self,
        size: tuple[int, int],
        env: LevelEnv | None = None,
        blueprints: BlueprintRegistry | None = None,
    ) -> None:
        self.board: Board = Board(*size)
        self.env = env if env is not None else default_env
        self.im = self.env.im
        self.blueprints = blueprints if blueprints is not None else default_registry.clone()
        self.components: dict[int, Component] = {}
        self.entrypoints: dict[int, Component] = {}
        self.connections = ConnectionGraph()
        self.step = 0
        self.collision: CollisionEvent | None = None
        self.placements: list[PlacementRecord] = []
        self.allowed_blueprints: set[str] | None = None

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

        movements: list[Movement] = []
        try:
            for comp in self.components.values():
                # Mechanical collision: arm cannot move cells held by another arm.
                # Recomputing per component means later arms see where
                # earlier arms moved this step.
                blocked = self.held_cells() - set(getattr(comp, "holding", None) or ())
                comp.execute_step(
                    self.board,
                    self.step,
                    blocked_cells=blocked,
                    movement_recorder=movements,
                )
        except SimulationCollisionError as err:
            self.collision = err.event
            raise

        # Collision is detected after visual step:
        # components above have already committed their full rotation/holding,
        # so on actual collision the arm stays at its final pose
        # (past event.progress/event.cell) instead of freezing mid-sweep.
        event = detect_collision(
            self.board,
            [*self.components.values(), *self.entrypoints.values()],
            movements,
            self.step,
        )
        if event is not None:
            self.collision = event
            raise SimulationCollisionError(event)

        held_cells = self.held_cells()
        for comp in self.entrypoints.values():
            if comp.type == ComponentType.ENTRANCE and comp.pos in held_cells:
                continue
            comp.execute_step(self.board, self.step)

        self.step += 1

    def add_component(
        self,
        cell: Hex,
        comp_type: ComponentType,
        **kwargs,
    ):
        new_id = self.im.allocate()
        comp = get_component_type(comp_type)(idx=new_id, pos=cell, **kwargs)
        if not self.board.place_component_cells(comp.footprint(), comp_type, new_id):
            self.im.free(new_id)
            msg = f"Cannot place {comp_type.name.lower()} at ({cell.r}, {cell.s})."
            raise SimulationRuntimeError(msg, step=self.step)

        comp.env = self.env

        if comp_type in {
            ComponentType.ENTRANCE,
            ComponentType.EXIT,
            ComponentType.CONNECTOR,
            ComponentType.DISCONNECTOR,
            ComponentType.SALT_TRANSMUTER,
            ComponentType.DUPLICATION_GLYPH,
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
            comp.group = [c for c in group if c is not None and c.idx != comp.idx]  # ty: ignore
            links = [self._lookup(i) for i in self.connections.links_of(comp.idx)]
            comp.links = [c for c in links if c is not None] # ty: ignore

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

    def place(
        self,
        name: str | ShapeTemplate,
        pos: Hex,
        rotation: int = 0,
        **overrides,
    ) -> PlacementRecord:
        if isinstance(name, ShapeTemplate):
            try:
                self.blueprints.register(name)
            except ValueError as exc:
                msg = f"Blueprint {name.name!r} is already registered."
                raise SimulationRuntimeError(msg, step=self.step) from exc
            blueprint = name
            name = name.name
        else:
            try:
                blueprint = self.blueprints.get(name)
            except KeyError as exc:
                msg = f"Unknown blueprint {name!r}."
                raise SimulationRuntimeError(msg, step=self.step) from exc
        if not blueprint.implemented:
            msg = f"Blueprint {name!r} is not implemented and cannot be placed."
            raise SimulationRuntimeError(msg, step=self.step)

        if self.allowed_blueprints is not None and name not in self.allowed_blueprints:
            msg = f"Blueprint {name!r} is not allowed in this level."
            raise SimulationRuntimeError(msg, step=self.step)

        if overrides.get("atom_type") is AtomType.BASIC:
            msg = f"Blueprint {name!r} cannot use atom_type 'basic'."
            raise SimulationRuntimeError(msg, step=self.step)

        if isinstance(blueprint, ManipulatorSpec):
            return self._place_manipulator(blueprint, name, pos, rotation, overrides)
        if isinstance(blueprint, ComponentSpec):
            return self._place_component(blueprint, name, pos, rotation, overrides)
        return self._place_shape(blueprint, name, pos, rotation, overrides)

    def _place_manipulator(
        self,
        blueprint: ManipulatorSpec,
        name: str,
        pos: Hex,
        rotation: int,
        overrides: dict,
    ) -> PlacementRecord:
        spec_fields = {
            "name",
            "arm_count",
            "extendable",
            "min_length",
            "max_length",
            "implemented",
        }
        for key in spec_fields:
            if key in overrides:
                msg = f"{key!r} is defined by blueprint {name!r} and cannot be overridden at placement."
                raise SimulationRuntimeError(msg, step=self.step)

        length = overrides.get("length", 1)
        if not blueprint.min_length <= length <= blueprint.max_length:
            msg = (
                f"length {length} out of bounds for blueprint {name!r}: "
                f"require {blueprint.min_length} <= length <= {blueprint.max_length}"
            )
            raise SimulationRuntimeError(msg, step=self.step)

        comp_type = ComponentType.ARM_RETR if blueprint.extendable else ComponentType.ARM
        before = set(self.components) | set(self.entrypoints)
        self.add_component(pos, comp_type, spec=blueprint, rotation=rotation, **overrides)
        (comp_id,) = (set(self.components) | set(self.entrypoints)) - before

        record = PlacementRecord(
            blueprint=name,
            pos=pos,
            rotation=rotation,
            component_ids=(comp_id,),
            links=(),
        )
        self.placements.append(record)
        return record

    def _place_component(
        self,
        blueprint: ComponentSpec,
        name: str,
        pos: Hex,
        rotation: int,
        overrides: dict,
    ) -> PlacementRecord:
        if overrides:
            msg = f"Blueprint {name!r} does not accept overrides: {sorted(overrides)}."
            raise SimulationRuntimeError(msg, step=self.step)

        before = set(self.components) | set(self.entrypoints)
        self.add_component(pos, blueprint.comp_type, rotation=rotation)
        (comp_id,) = (set(self.components) | set(self.entrypoints)) - before

        record = PlacementRecord(
            blueprint=name,
            pos=pos,
            rotation=rotation,
            component_ids=(comp_id,),
            links=(),
        )
        self.placements.append(record)
        return record

    def _place_shape(
        self,
        blueprint: ShapeTemplate,
        name: str,
        pos: Hex,
        rotation: int,
        overrides: dict,
    ) -> PlacementRecord:
        if blueprint.allowed_rotations is not None and rotation not in blueprint.allowed_rotations:
            msg = f"Blueprint {name!r} does not allow rotation {rotation}."
            raise SimulationRuntimeError(msg, step=self.step)

        cells = [
            Hex(
                pos.r + cell.offset.rotate_around(Hex(0, 0), rotation).r,
                pos.s + cell.offset.rotate_around(Hex(0, 0), rotation).s,
            )
            for cell in blueprint.cells
        ]
        for cell in cells:
            if not self.board.in_bounds(cell) or not self.board.free_to_place(cell):
                msg = f"Cannot place blueprint {name!r}: cell ({cell.r}, {cell.s}) is occupied or out of bounds."
                raise SimulationRuntimeError(msg, step=self.step)

        placed_ids: list[int] = []
        try:
            for cell, template_cell in zip(cells, blueprint.cells, strict=True):
                # Cell kwargs takes priority over placement overrides,
                # so per-cell atom types are never overwritten by blanket placement `atom_type`.
                kwargs = {**overrides, **template_cell.kwargs}
                before = set(self.components) | set(self.entrypoints)
                self.add_component(cell, blueprint.comp_type, **kwargs)
                (comp_id,) = (set(self.components) | set(self.entrypoints)) - before
                placed_ids.append(comp_id)
        except Exception:
            for comp_id in reversed(placed_ids):
                self.remove_component(comp_id)
            raise

        links: list[tuple[int, int]] = []
        for a, b in blueprint.links:
            id_a, id_b = placed_ids[a], placed_ids[b]
            if not self.connect_components(id_a, id_b):
                for comp_id in reversed(placed_ids):
                    self.remove_component(comp_id)
                msg = f"Blueprint {name!r} defines an invalid link between cells {a} and {b}."
                raise SimulationRuntimeError(msg, step=self.step)
            links.append((id_a, id_b))

        record = PlacementRecord(
            blueprint=name,
            pos=pos,
            rotation=rotation,
            component_ids=tuple(placed_ids),
            links=tuple(links),
        )
        self.placements.append(record)
        return record

    def remove_placement(self, record: PlacementRecord) -> None:
        for comp_id in record.component_ids:
            self.remove_component(comp_id)
        self.placements.remove(record)

    def reset(self) -> None:
        self.board.clear()
        self.components.clear()
        self.entrypoints.clear()
        self.connections = ConnectionGraph()
        self.step = 0
        self.collision = None
        self.placements.clear()
        self.env.reset()
