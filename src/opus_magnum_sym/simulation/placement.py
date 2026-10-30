from dataclasses import dataclass

from opus_magnum_sym.elements.board.hex import Hex


@dataclass
class PlacementRecord:
    """

    ```python
    comp = PlacementRecord(
        blueprint: str,
        pos: Hex,
        rotation: int,
        component_ids: tuple[int, ...],
        links: tuple[tuple[int, int], ...]
    ) -> PlacementRecord
    ```

    Not ment to be instanced manually.
    Result of a single `Level.place` / `Simulator.place` call.

    Use `comp_id` to get placed Manupulator id in order to assign action.

    Manipulators are single-component placements, `assign_step_action` expects.
    Multi-cell shapes (connectors, glyphs, entrypoint shapes) create one component
    per cell and have no assignable actions, so their ids are only needed
    to inspect internal state (cell positions, types, link graph);
    generally there is no need to read their ids after placement.

    """

    blueprint: str
    pos: Hex
    rotation: int
    component_ids: tuple[int, ...]
    links: tuple[tuple[int, int], ...]

    @property
    def comp_id(self) -> int:
        """
        The sole component id of a single-component placement (a manipulator variant).

        ```python
        arm_id = level.place("arm", Hex(3, 3)).comp_id
        ```

        Raises `ValueError` for multi-cell shapes, which create several components
        and have no assignable actions; use `component_ids` when their ids are
        needed to inspect internal state.
        """
        if len(self.component_ids) != 1:
            raise ValueError(
                f"placement {self.blueprint!r} created {len(self.component_ids)} components, "
                "so it has no single comp_id; use component_ids"
            )
        return self.component_ids[0]
