"""
Shared level-spec fixture reused by Stages 4-5.
"""

from fixtures.shapes import entrance_straight_2, exit_straight_2
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.levels import EntrypointSpec, LevelSpec


def make_level_spec(**overrides) -> LevelSpec:
    """
    A minimal valid level spec: straight-2 entrance and exit on a 6x6 board.

    Matches the canonical delivery geometry used by `tests/test_integration.py`.
    """
    kwargs = {
        "size": (6, 6),
        "shapes": (entrance_straight_2(), exit_straight_2()),
        "entrypoints": (
            EntrypointSpec(
                kind=ComponentType.ENTRANCE,
                shape="entrance_straight_2",
                pos=Hex(2, 3),
                atom_type=AtomType.SALT,
                rotation=1,
            ),
            EntrypointSpec(
                kind=ComponentType.EXIT,
                shape="exit_straight_2",
                pos=Hex(3, 2),
                atom_type=AtomType.SALT,
                rotation=2,
            ),
        ),
        "allowed_blueprints": frozenset({"arm"}),
        "steps": 30,
    }
    kwargs.update(overrides)
    return LevelSpec(**kwargs)
