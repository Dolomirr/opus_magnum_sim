from math import cos, pi, sin


def hex_vertices(
    center_x: float,
    center_y: float,
    radius: float,
) -> list[tuple[float, float]]:
    vertices: list[tuple[float, float]] = []

    for i in range(6):
        angle = pi / 180 * (60 * i - 30)
        x = center_x + radius * cos(angle)
        y = center_y + radius * sin(angle)
        vertices.append((x, y))

    return vertices
