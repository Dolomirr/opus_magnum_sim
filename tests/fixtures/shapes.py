"""
Shared factories for building shape templates in tests.
"""

from opus_magnum_sym.elements.board import Direction, Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeCell, ShapeTemplate


def _beam(rotation: int) -> ShapeCell:
    return ShapeCell(offset=Direction().from_rotation(rotation).apply(Hex(0, 0)))


def straight_shape(name: str, comp_type: ComponentType) -> ShapeTemplate:
    """Two-cell straight shape: origin plus one beam at rotation 0."""
    return ShapeTemplate(
        name=name,
        comp_type=comp_type,
        cells=(ShapeCell(offset=Hex(0, 0)), _beam(0)),
        links=((0, 1),),
    )


def entrance_straight_2() -> ShapeTemplate:
    return straight_shape("entrance_straight_2", ComponentType.ENTRANCE)


def exit_straight_2() -> ShapeTemplate:
    return straight_shape("exit_straight_2", ComponentType.EXIT)
