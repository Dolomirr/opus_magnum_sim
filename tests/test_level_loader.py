"""Level file loader tests (Stage 5)."""

from pathlib import Path

import pytest
from fixtures.levels import make_level_spec

from opus_magnum_sym.interpreter.level_loader import LevelLoader, LevelLoadError
from opus_magnum_sym.levels import Level, LevelStatus

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

# Text form of `make_level_spec()`; order matches the fixture's shapes/entrypoints.
LEVEL_TEXT = "\n".join(
    [
        "size 6 6",
        "steps 30",
        "shape entrance_straight_2 entrance cells=(0,0),(-1,1) links=0-1",
        "shape exit_straight_2 exit cells=(0,0),(-1,1) links=0-1",
        "entrance entrance_straight_2 2 3 rotation=1 atom_type=salt",
        "exit exit_straight_2 3 2 rotation=2 atom_type=salt",
        "allow arm",
    ]
)


def test_round_trip_spec_equality():
    loaded = LevelLoader().load(LEVEL_TEXT)
    assert loaded == make_level_spec()


def test_unknown_command_reports_line():
    with pytest.raises(LevelLoadError, match="line 3"):
        LevelLoader().load("size 6 6\nsteps 30\nbogus command\n")


def test_malformed_line_reports_line():
    with pytest.raises(LevelLoadError, match="line 2"):
        LevelLoader().load("size 6 6\nsteps many\n")


def test_unknown_shape_kind_rejected():
    with pytest.raises(LevelLoadError, match="unknown shape kind"):
        LevelLoader().load("size 6 6\nsteps 30\nshape s bogus cells=(0,0) links=\n")


def test_non_shape_kind_rejected():
    with pytest.raises(LevelLoadError, match="entrypoint kind"):
        LevelLoader().load("size 6 6\nsteps 30\nshape s arm cells=(0,0) links=\n")


def test_missing_cells_rejected():
    with pytest.raises(LevelLoadError, match="requires cells"):
        LevelLoader().load("size 6 6\nsteps 30\nshape s entrance links=0-1 rotations=1\n")


def test_duplicate_shape_name_rejected():
    with pytest.raises(LevelLoadError, match="duplicate shape"):
        LevelLoader().load("size 6 6\nsteps 30\nshape s entrance cells=(0,0) links=\nshape s exit cells=(0,0) links=\n")


def test_unknown_atom_type_rejected():
    with pytest.raises(LevelLoadError, match="unknown atom_type"):
        LevelLoader().load(
            "size 6 6\nsteps 30\n"
            "shape e entrance cells=(0,0) links=\n"
            "shape x exit cells=(0,0) links=\n"
            "entrance e 1 1 atom_type=bogus\n"
        )


def test_demo_pair_end_to_end():
    level = Level.from_file(EXAMPLES_DIR / "place_delivery.oml")
    level.load_solution(EXAMPLES_DIR / "place_delivery.oms")

    result = level.run()

    assert result.status is LevelStatus.COMPLETED
    assert result.error is None
    assert result.total_finished == 1
    assert result.finished_by_exit == {0: 1}
