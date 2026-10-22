"""
Continuous geometry for spatial collision detection.

Coordinates are normalized, so hex cell's width (center to center distnace between the two) was 1.0.
Radiuses are fractions of that width, derived from `omsim` pixel ratios.
Separate from renderer's sizes.
Stateless (functinoal goes BRRR).
"""

# TODO: profile how this axes switch afect performance

from math import cos, hypot, pi, sin, sqrt

from opus_magnum_sym.elements.board.hex import Hex

ATOM_RADIUS: float = 29.0 / 82.0
ARM_BASE_RADIUS: float = 20.0 / 82.0

# Collision takes samples from a full rotation step at multiples of this fraction of a step.
# Smaller values catch 'sliding' contacts at large pivot radiuses
# but at the cost of higher amount of pairwise tests.
# TODO: check how it looks without sliding collisions, and wether it makes sens
SWEEP_INCREMENT: float = 0.125

_SQRT_3: float = sqrt(3.0)


def hex_to_xy(cell: Hex) -> tuple[float, float]:
    """
    Center of `cell` in normalized space.
    """
    return (cell.s + 0.5 * cell.r, (_SQRT_3 / 2.0) * cell.r)


def rotate_offset(offset: tuple[float, float], steps: float) -> tuple[float, float]:
    """
    Rotate xy offset by `steps` with 60-degree increments.
    Fractions are allowed.

    Positive steps match `Hex.rotate_around` (arm's clockwise).
    """
    theta = steps * pi / 3.0
    x, y = offset
    c, s = cos(theta), sin(theta)
    return (x * c - y * s, x * s + y * c)


def circles_overlap(
    a: tuple[float, float],
    ar: float,
    b: tuple[float, float],
    br: float,
) -> bool:
    """
    True when the two circles edges intersect (center distance < r1 + r2).
    """
    return hypot(b[0] - a[0], b[1] - a[1]) < ar + br
