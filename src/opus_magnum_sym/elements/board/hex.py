from typing import NamedTuple


class Hex(NamedTuple):
    r: int
    s: int

    def rotate_around(self, pivot: Hex, steps: int) -> Hex:
        """
        Rotate this cell `steps` 60° steps around `pivot` (positive = arm's CLW).
        """
        steps %= 6
        x, z = self.s - pivot.s, self.r - pivot.r
        y = -x - z
        for _ in range(steps):
            x, y, z = -z, -x, -y
        return Hex(pivot.r + z, pivot.s + x)
