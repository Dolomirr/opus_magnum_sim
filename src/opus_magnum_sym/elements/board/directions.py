from icecream import ic

from opus_magnum_sym.elements.board.hex import Hex


# VERY un-python way of doing that
class Direction:
    r"""
    Static class defining hexagonal direction corresponding to standard grid.
    Neared neigbouts of each hexagons defined nearest neigbour on grid + right upper and right down cells.

     -------┌───────┬───────┐  |   -------┌───────┬───────┐
    |       │       │       │  |  |       │       │       │
    |       │ -1,0  │ -1,1  │  |  |       │  H11  │   H1  │
    |       │       │       │  |  |       │       │       │
    ┌───────┼───────┼───────│  |  ┌───────┼───────┼───────│
    │       │       │       │  |  │       │       │       │
    │  0,-1 │  0,0  │  0,1  │  |  │   H9  │  NONE │   H3  │
    │       │       │       │  |  │       │       │       │
    └───────┼───────┼───────│  |  └───────┼───────┼───────│
    |       │       │       │  |  |       │       │       │
    |       │  1,0  │  1,1  │  |  |       │   H7  │   H5  │
    |       │       │       │  |  |       │       │       │
     -------└───────┴───────┘  |   -------└───────┴───────┘
                               |  Directions:
           / \     / \         |         / \     / \
         /     \ /     \       |       /     \ /     \
        | -1,0  | -1,1  |      |      |  H11  |  H1   |
        |       |       |      |      |       |       |
       / \     / \     / \     |     / \     / \     / \
     /     \ /     \ /     \   |   /     \ /     \ /     \
    |  0,-1 |  0,0  |  0,1  |  |  |  H9   |  NONE |   H3  |
    |       |       |       |  |  |       |       |       |
     \     / \     / \     /   |   \     / \     / \     /
       \ /     \ /     \ /     |     \ /     \ /     \ /
        |  1,0  |  1,1  |      |      |  H7   |  H5   |
        |       |       |      |      |       |       |
         \     / \     /       |       \     / \     /
           \ /     \ /         |         \ /     \ /

    Usage:
    ======
    ```
    grid = np.zeros((10, 10), dtype=int)
    origin = Hex(10, 10)

    offset = Direction.H3.offset              # offset of length 1 on the right
    offset_2 = Direction.H11.offset_at(2)  # offset of length 2 on upper left

    neigbour = Direction.H3.apply(origin)  # get coordinate of hex on the left of origin
    far = Direction.H11.apply(origin, length=3) # get coordinate of hex on the upper left of origin
    ```
    """

    class _Dir:
        """Direction object for each possible individual firection from central hexagon."""

        id: int
        name: str
        _offset: tuple[int, int]
        __slots__ = (
            "_offset",
            "id",
            "name",
        )

        def __init__(
            self,
            iden: int,
            name: str,
            offset: tuple[int, int],
        ) -> None:
            self.id = iden
            self.name = name
            self._offset = offset

        @property
        def offset(self) -> tuple[int, int]:
            """Base offset of length 1."""
            return self._offset

        def offset_at(self, length: int) -> tuple[int, int]:
            """Offset scaled by length."""
            if length == 0:
                return (0, 0)
            dr, ds = self._offset
            return (dr * length, ds * length)

        def apply(self, curr_hex: Hex, length: int = 1) -> Hex:
            """Apply direction to coordinate."""
            dr, ds = self.offset_at(length)
            return Hex(curr_hex.r + dr, curr_hex.s + ds)

        def __repr__(self) -> str:
            return f"Direction.{self.name}"

    NONE: _Dir = _Dir(0, "NONE", (0, 0))
    H1: _Dir = _Dir(1, "H1", (-1, 1))
    H3: _Dir = _Dir(3, "H3", (0, 1))
    H5: _Dir = _Dir(5, "H5", (1, 1))
    H7: _Dir = _Dir(7, "H7", (1, 0))
    H9: _Dir = _Dir(9, "H9", (0, -1))
    H11: _Dir = _Dir(11, "H11", (-1, 0))

    BY_ID: dict[int, _Dir] = {d.id: d for d in (NONE, H1, H3, H5, H7, H9, H11)}  # noqa: RUF012

    def from_rotation(self, rotation: int = 0) -> _Dir:
        rotations = (
            self.H1,
            self.H3,
            self.H5,
            self.H7,
            self.H9,
            self.H11,
        )
        return ic(rotations[rotation % 6])  # additional check to prevent overflow
