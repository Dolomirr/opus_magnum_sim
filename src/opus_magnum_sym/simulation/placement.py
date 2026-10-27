from dataclasses import dataclass

from opus_magnum_sym.elements.board.hex import Hex


@dataclass
class PlacementRecord:
    """
    Result of a single `Simulator.place` call.

    `component_ids` are in template cell order (single element for variant blueprints).
    `links` holds absolute component-id pairs of connected single-cell components;
    empty for variant blueprints.
    """

    blueprint: str
    pos: Hex
    rotation: int
    component_ids: tuple[int, ...]
    links: tuple[tuple[int, int], ...]
