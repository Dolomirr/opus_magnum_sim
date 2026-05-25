from math import sqrt


class HexLayout:
    SQRT_3: float = sqrt(3)

    def __init__(self, hex_size: float):
        self.hex_size: float = hex_size

    def hex_to_pixel(
        self,
        r: int,
        s: int,
    ) -> tuple[float, float]:
        x = self.hex_size * self.SQRT_3 * (s + 0.5 * (r & 1))
        y = self.hex_size * 1.5 * r

        return x, y
