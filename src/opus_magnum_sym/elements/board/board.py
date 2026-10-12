# pyright: reportUnusedFunction = false
import copy
from typing import TYPE_CHECKING, Self

import numpy as np

from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.components.base_component import ComponentType

if TYPE_CHECKING:
    from opus_magnum_sym.elements.board.hex import Hex


# TODO switch to either bool return or error raising
class Board:
    r"""
    Board is poity-top hexagonal plane ("odd-r" horizontal layout) with axial offset coordinates (r, s).

       row(r)
    col(s)─┼─►    0       1      2
           ▼  ┌───────────────────────┐
              │       │       │       │
           0  │  0,0  │  0,1  │  0,2  │
              │       │       │       │
              │───────┼───────┼───────│
              │       │       │       │
           1  │  1,0  │  1,1  │  1,2  │
              │       │       │       │
              │───────┼───────┼───────│
              │       │       │       │
           2  │  2,0  │  2,1  │  2,2  │
              │       │       │       │
              └───────────────────────┘

           / \     / \     / \
         /     \ /     \ /     \
        |  0,0  |  0,1  |  0,2  |
        |       |       |       |
         \     / \     / \     / \
           \ /     \ /     \ /     \
            |  1,0  |  1,1  |  1,2  |
            |       |       |       |
           / \     / \     / \     /
         /     \ /     \ /     \ /
        |  2,0  |  2,1  |  2,2  |
        |       |       |       |
         \     / \     / \     /
           \ /     \ /     \ /
    """

    rows: int
    cols: int

    base_obj: np.ndarray[tuple[int, int], np.dtype[np.int32]]
    """Semi-static elements on board (manipulator bases, etc.)"""
    # transport: np.ndarray[tuple[int, int], np.dtype[np.int32]]
    """Direction of transporters, -1 == no transport line, can be remotely coincided vector filed"""
    atoms: dict[Hex, Atom]
    """Dynamic atom instances keyed by board cell"""
    components_ids: np.ndarray[tuple[int, int], np.dtype[np.int32]]

    def __init__(
        self,
        rows: int,
        cols: int,
    ):
        self.rows = rows
        self.cols = cols

        self.base_obj = np.full((rows, cols), ComponentType.EMPTY, dtype=np.int32)
        # self.transport = np.full((rows, cols), Direction.NONE.id, dtype=np.int32)
        self.atoms = {}
        self.components_ids = np.full((rows, cols), -1, dtype=np.int32)

    def in_bounds(self, cell: Hex) -> bool:
        """Checks if some cell is in bounds of board"""
        return 0 <= cell.r < self.rows and 0 <= cell.s < self.cols

    # TODO: split in several layers, think about transportation
    def free_to_place(self, cell: Hex) -> bool:
        return (
            self.base_obj[cell] == ComponentType.EMPTY
            and cell not in self.atoms
        )  # fmt:skip

    # TODO: treat as internal methods, add top-level env.add_component
    def place_componet(
        self,
        cell: Hex,
        comp_type: ComponentType,
        comp_id=-1,
    ) -> bool:
        if not self.in_bounds(cell) or not self.free_to_place(cell):
            return False
        self.base_obj[cell] = comp_type
        self.components_ids[cell] = comp_id
        return True

    # TODO: remove by id
    def remove_component(self, hex_cell: Hex) -> bool:
        if not self.in_bounds(hex_cell):
            return False
        self.base_obj[hex_cell] = ComponentType.EMPTY
        self.components_ids[hex_cell] = -1
        return True

    # TODO: plan transporter placing logic
    def place_transporter(self) -> None: ...
    def remove_transporter(self) -> None: ...

    def place_atom(
        self,
        hex_cell: Hex,
        atom: Atom,
    ) -> bool:
        if not self.in_bounds(hex_cell) or hex_cell in self.atoms:
            return False
        self.atoms[hex_cell] = atom
        return True

    def get_atom(self, hex_cell: Hex) -> Atom | None:
        return self.atoms.get(hex_cell)

    def remove_atom(self, hex_cell: Hex) -> Atom | None:
        """Removes atom from cell, returning the removed instance if present."""
        if not self.in_bounds(hex_cell):
            return None
        return self.atoms.pop(hex_cell, None)

    def move_atom(self, src: Hex, dst: Hex) -> bool:
        """
        Relocates atom from src to dst as a single validated operation.
        On any failure the board is left untouched.
        """
        atom = self.atoms.get(src)
        if atom is None or not self.in_bounds(dst) or dst in self.atoms:
            return False
        self.atoms[dst] = atom
        del self.atoms[src]
        return True

    def step_transporter(self, component, direction) -> None: ...  # pyright: ignore[reportUnusedParameter]

    def get_state(self) -> np.ndarray[tuple[int, int, int], np.dtype[np.int32]]:
        objects = np.full((self.rows, self.cols), AtomType.NONE, dtype=np.int32)
        for (r, s), atom in self.atoms.items():
            objects[r, s] = atom.type
        return np.stack(
            (
                self.base_obj,
                # self.transport,
                objects,
            ),
            axis=0,
        )

    def clear(self) -> None:
        """
        Reset all board layers without changing dimensions.
        """
        self.base_obj[:] = ComponentType.EMPTY
        self.atoms.clear()
        self.components_ids[:] = -1

    def clone(self) -> Self:
        new = self.__class__(self.rows, self.cols)  # typing.Self support
        new.base_obj = self.base_obj.copy()
        # new.transport = self.transport.copy()
        new.atoms = copy.deepcopy(self.atoms)
        new.components_ids = self.components_ids.copy()
        return new
