"""Level file loader tests (Stage 5)."""

from pathlib import Path

import pytest
from fixtures.levels import make_level_spec

from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.interpreter.level_loader import LevelLoader, LevelLoadError
from opus_magnum_sym.levels import Level, LevelStatus

FIXTURES_DIR = Path(__file__).parent / "fixtures"

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
    level = Level.from_file(FIXTURES_DIR / "fixed_delivery.oml")
    level.load_solution(FIXTURES_DIR / "fixed_delivery.oms")

    result = level.run()

    assert result.status is LevelStatus.COMPLETED
    assert result.error is None
    assert result.total_finished == 1
    assert result.finished_by_exit == {0: 1}


# --- new Stage 2 directives ---


def test_atom_types_directive_round_trip():
    spec = LevelLoader().load("size 6 6\nsteps 30\natom_types salt water fire\n" + LEVEL_TEXT)
    assert spec.atom_types == frozenset({AtomType.SALT, AtomType.WATER, AtomType.FIRE})


def test_entrypoints_fixed_defaults_to_true():
    spec = LevelLoader().load(LEVEL_TEXT)
    assert spec.entrypoints_fixed is True


def test_entrypoints_fixed_zero_round_trip():
    text = (
        "size 6 6\nsteps 30\nentrypoints_fixed 0\n"
        "shape entrance_straight_2 entrance cells=(0,0),(-1,1) links=0-1\n"
        "shape exit_straight_2 exit cells=(0,0),(-1,1) links=0-1\n"
        "entrance entrance_straight_2 atom_type=salt\n"
        "exit exit_straight_2 atom_type=salt\n"
        "allow arm\n"
    )
    spec = LevelLoader().load(text)
    assert spec.entrypoints_fixed is False
    assert all(ep.pos is None for ep in spec.entrypoints)


def test_entrypoints_fixed_rejects_bad_value():
    with pytest.raises(LevelLoadError, match="entrypoints_fixed"):
        LevelLoader().load("size 6 6\nsteps 30\nentrypoints_fixed 2\n")


def test_typed_cell_parsing():
    text = (
        "size 6 6\nsteps 30\n"
        "shape typed_exit exit cells=(0,0):salt,(-1,1):water,(1,0):fire links=0-1,0-2\n"
        "shape entrance_straight_2 entrance cells=(0,0),(-1,1) links=0-1\n"
        "entrance entrance_straight_2 1 1 atom_type=salt\n"
        "exit typed_exit 4 4 atom_type=salt\n"
        "allow arm\n"
    )
    spec = LevelLoader().load(text)
    typed = next(shape for shape in spec.shapes if shape.name == "typed_exit")
    assert typed.cells[0].kwargs["atom_type"] is AtomType.SALT
    assert typed.cells[1].kwargs["atom_type"] is AtomType.WATER
    assert typed.cells[2].kwargs["atom_type"] is AtomType.FIRE


def test_typed_cell_unknown_type_rejected():
    with pytest.raises(LevelLoadError, match="unknown atom_type"):
        LevelLoader().load("size 6 6\nsteps 30\nshape s exit cells=(0,0):bogus links=\n")


def test_malformed_cells_rejected():
    with pytest.raises(LevelLoadError, match="malformed cells"):
        LevelLoader().load("size 6 6\nsteps 30\nshape s exit cells=(0,0),garbage links=\n")


def test_fixed_mode_missing_position_error():
    text = (
        "size 6 6\nsteps 30\n"
        "shape e entrance cells=(0,0) links=\n"
        "shape x exit cells=(0,0) links=\n"
        "entrance e atom_type=salt\n"
        "exit x 1 1 atom_type=salt\n"
    )
    with pytest.raises(LevelLoadError, match="requires a position"):
        LevelLoader().load(text)


def test_unfixed_mode_position_error():
    text = (
        "size 6 6\nsteps 30\nentrypoints_fixed 0\n"
        "shape e entrance cells=(0,0) links=\n"
        "shape x exit cells=(0,0) links=\n"
        "entrance e 1 1 atom_type=salt\n"
        "exit x atom_type=salt\n"
    )
    with pytest.raises(LevelLoadError, match="must not specify a position"):
        LevelLoader().load(text)


def test_untyped_shape_requires_atom_type():
    text = (
        "size 6 6\nsteps 30\nentrypoints_fixed 0\n"
        "shape e entrance cells=(0,0) links=\n"
        "shape x exit cells=(0,0) links=\n"
        "entrance e atom_type=salt\n"
        "exit x\n"
    )
    with pytest.raises(LevelLoadError, match="requires atom_type"):
        LevelLoader().load(text)


def test_fully_typed_shape_omits_atom_type():
    text = (
        "size 6 6\nsteps 30\nentrypoints_fixed 0\n"
        "shape e entrance cells=(0,0) links=\n"
        "shape x exit cells=(0,0):salt links=\n"
        "entrance e atom_type=salt\n"
        "exit x\n"
    )
    spec = LevelLoader().load(text)
    exit_ep = next(ep for ep in spec.entrypoints if ep.kind.name == "EXIT")
    assert exit_ep.atom_type is None
