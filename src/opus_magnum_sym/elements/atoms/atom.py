from collections.abc import Iterator
from enum import IntEnum, auto


class AtomType(IntEnum):
    NONE = 0
    BASIC = auto()


class Atom:
    """
    Single atom instance placed on the board.

    Slots are indexed by rotation index 0..5 matching
    `Direction().from_rotation(rotation)`; the neighbor opposite to slot i
    is reached via slot (i + 3) % 6.
    """

    __slots__ = (
        "connections",
        "type",
    )

    def __init__(self, type: AtomType = AtomType.BASIC) -> None:
        self.type = type
        self.connections: list[Atom | None] = [None] * 6

    def iter_connections(self) -> Iterator[tuple[int, Atom]]:
        """
        Yield (rotation, atom) for each nonempty connection slot.
        """
        for rotation, atom in enumerate(self.connections):
            if atom is not None:
                yield rotation, atom

    def connection_at(self, rotation: int) -> Atom | None:
        """
        Atom connected in the direction of given rotation index, if any.
        """
        return self.connections[rotation % 6]

    def connect(self, rotation: int, other: Atom) -> None:
        """
        Connect `other` at given rotation index, mirroring its opposite slot.
        No-op when either side already has a connection.

        Performs no positional validation;
        this is low-level primitive.
        Board-level callers should prefer `Board.connect_atoms`.
        """
        rotation %= 6
        opposite = (rotation + 3) % 6
        if (
            self.connections[rotation] is not None
            or other.connections[opposite] is not None
        ):
            return
        self.connections[rotation] = other
        other.connections[opposite] = self

    def disconnect(self, rotation: int) -> None:
        """
        Remove the connection at given rotation index from both atoms.
        """
        rotation %= 6
        other = self.connections[rotation]
        self.connections[rotation] = None
        if other is not None:
            other.connections[(rotation + 3) % 6] = None

    def rotate_connections(self, steps: int) -> None:
        """
        Rotate connection slots by `steps`.
        Every atom of a molecule must be rotated by the same `steps`;
        reciprocity is preserved because opposite slots shift together.
        """
        steps %= 6
        self.connections = self.connections[-steps:] + self.connections[:-steps]
