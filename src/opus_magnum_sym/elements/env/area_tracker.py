from collections.abc import Iterable
from typing import TYPE_CHECKING

from opus_magnum_sym.elements.board.hex import Hex

if TYPE_CHECKING:
    from opus_magnum_sym.simulation.movement import Movement


class AreaTracker:
    """
    Per-instance set of distinct board cells covered by a solution.

    Coverage is the union of component footprints, atom resting positions,
    and cells swept during arm movements, deduplicated by cell.
    """

    def __init__(self) -> None:
        self._cells: set[Hex] = set()

    def add_component_cells(self, cells: Iterable[Hex]) -> None:
        """
        Add component footprint cells.
        """
        self._cells.update(cells)

    def record_atom_stops(self, board_atom_cells: Iterable[Hex], held_cells: Iterable[Hex]) -> None:
        """
        Add cells where atoms rest on board or in arm's hand.
        """
        self._cells.update(board_atom_cells)
        self._cells.update(held_cells)

    def record_sweep(self, movements: Iterable[Movement]) -> None:
        """
        Add cells swept by atoms of every recorded movement.
        """
        for movement in movements:
            self._cells.update(movement.swept_cells())

    @property
    def count(self) -> int:
        """
        Number of distinct covered cells.
        """
        return len(self._cells)

    def reset(self) -> None:
        """
        Clear every covered cell.
        """
        self._cells.clear()


# Module-level default instance.
# Preserved to keep existing callers working.
default_area_tracker = AreaTracker()
