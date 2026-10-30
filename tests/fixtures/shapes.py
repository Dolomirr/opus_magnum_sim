"""
Shared factories for building shape templates in tests.
"""

from opus_magnum_sym.elements.atoms.atom import AtomType
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


def branched_entrance() -> ShapeTemplate:
    """
    Branched entrance: center plus two beams (rotations 1 and 2).

    The two beams are adjacent to each other but are *not* linked, so a correct
    spawn bonds center->beam_a and center->beam_b only (no beam_a<->beam_b bond).
    """
    return ShapeTemplate(
        name="branched_entrance",
        comp_type=ComponentType.ENTRANCE,
        cells=(ShapeCell(offset=Hex(0, 0)), _beam(1), _beam(2)),
        links=((0, 1), (0, 2)),
    )


def typed_exit() -> ShapeTemplate:
    """
    Typed exit: salt center bonded to a water beam (rotation 1) and a fire beam (rotation 2).

    Each cell carries its own `atom_type`; the two beams are adjacent
    to each other but only linked to the center.
    """
    origin = Hex(0, 0)
    return ShapeTemplate(
        name="typed_exit",
        comp_type=ComponentType.EXIT,
        cells=(
            ShapeCell(offset=origin, atom_type=AtomType.SALT),
            ShapeCell(offset=_beam(1).offset, atom_type=AtomType.WATER),
            ShapeCell(offset=_beam(2).offset, atom_type=AtomType.FIRE),
        ),
        links=((0, 1), (0, 2)),
    )
