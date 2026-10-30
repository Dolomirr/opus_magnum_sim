"""Level runtime and result tests (Stage 4)."""

from pathlib import Path

import pytest  # noqa: INP001
from fixtures.levels import make_level_spec
from fixtures.shapes import entrance_straight_2, exit_straight_2

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Direction, Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeCell, ShapeTemplate, get_blueprint
from opus_magnum_sym.levels import EntrypointSpec, Level, LevelSpec, LevelStatus
from opus_magnum_sym.simulation.collision import CollisionCategory
from opus_magnum_sym.simulation.errors import SimulationRuntimeError


def _schedule_delivery(level: Level) -> int:
    """Place an arm and program the canonical delivery (mirrors test_integration)."""
    arm_record = level.place("arm", Hex(3, 3))
    (arm_id,) = arm_record.component_ids
    level.assign_step_action(arm_id, 1, StepActionType.GRAB)
    for step in (2, 3, 4, 5):
        level.assign_step_action(arm_id, step, StepActionType.ROTATE_CLW)
    level.assign_step_action(arm_id, 6, StepActionType.RELEASE)
    return arm_id


def _single_cell_shape(name: str, comp_type: ComponentType) -> ShapeTemplate:
    return ShapeTemplate(
        name=name,
        comp_type=comp_type,
        cells=(ShapeCell(offset=Hex(0, 0)),),
        links=(),
    )


def _collision_spec() -> LevelSpec:
    """Single-cell entrance (0,0) and exit (5,5) on a 7x7 board."""
    return LevelSpec(
        size=(7, 7),
        shapes=(
            _single_cell_shape("entrance_1", ComponentType.ENTRANCE),
            _single_cell_shape("exit_1", ComponentType.EXIT),
        ),
        entrypoints=(
            EntrypointSpec(
                kind=ComponentType.ENTRANCE,
                shape="entrance_1",
                pos=Hex(0, 0),
                atom_type=AtomType.SALT,
            ),
            EntrypointSpec(
                kind=ComponentType.EXIT,
                shape="exit_1",
                pos=Hex(5, 5),
                atom_type=AtomType.SALT,
            ),
        ),
        allowed_blueprints=frozenset({"arm"}),
        steps=10,
        entrypoints_fixed=True,
    )


def test_delivery_result_counts():
    level = Level(make_level_spec())
    _schedule_delivery(level)

    result = level.run()

    assert result.status is LevelStatus.COMPLETED
    assert result.error is None
    assert result.steps == 30  # default limit is the spec's
    assert result.total_finished == 1
    assert result.finished_by_exit == {0: 1}
    # Entrance pair (ids 0,1) then exit pair (ids 2,3): one delivered molecule.
    assert result.finished == {frozenset({2, 3}): 1}


def test_step_limit_override_respected():
    level = Level(make_level_spec())
    _schedule_delivery(level)

    result = level.run(steps=3)

    assert result.status is LevelStatus.COMPLETED
    assert result.steps == 3
    assert result.total_finished == 0  # delivery needs 7 steps


def test_place_non_allowed_blueprint_raises():
    level = Level(make_level_spec())

    with pytest.raises(SimulationRuntimeError, match="not allowed"):
        level.place("connector_tri", Hex(4, 4), atom_type=AtomType.SALT)


def test_collision_yields_error_with_metadata():
    level = Level(_collision_spec())
    arm_record = level.place("arm", Hex(3, 3), length=2)
    (arm_id,) = arm_record.component_ids

    level.sim.board.place_atom(Hex(1, 5), Atom(AtomType.SALT))
    level.sim.board.place_atom(Hex(2, 5), Atom(AtomType.SALT))  # blocker on the sweep arc

    level.assign_step_action(arm_id, 1, StepActionType.GRAB)
    level.assign_step_action(arm_id, 2, StepActionType.ROTATE_CLW)

    result = level.run()

    assert result.status is LevelStatus.ERROR
    assert result.error is not None
    assert result.error.exception == "SimulationCollisionError"
    assert result.error.step == 2
    event = result.error.collision
    assert event is not None
    assert event.category is CollisionCategory.SWEEP_ATOM
    assert event.cell == Hex(2, 5)
    assert event.owner_ids == (arm_id,)
    # No steps are incremented past the failing step.
    assert result.steps == 2


def test_linked_exit_entrypoints_reported_in_finished_by_exit(tmp_path):
    """A solution `connection`-linking two exits lands deliveries under the union cluster key."""
    exit_a = Hex(3, 3)
    exit_b = Direction.H3.apply(exit_a)
    spec = LevelSpec(
        size=(6, 6),
        shapes=(
            _single_cell_shape("entrance_1", ComponentType.ENTRANCE),
            _single_cell_shape("exit_1", ComponentType.EXIT),
        ),
        entrypoints=(
            EntrypointSpec(kind=ComponentType.ENTRANCE, shape="entrance_1", pos=Hex(1, 1), atom_type=AtomType.SALT),
            EntrypointSpec(kind=ComponentType.EXIT, shape="exit_1", pos=exit_a, atom_type=AtomType.SALT),
            EntrypointSpec(kind=ComponentType.EXIT, shape="exit_1", pos=exit_b, atom_type=AtomType.SALT),
        ),
        allowed_blueprints=frozenset(),
        steps=1,
        entrypoints_fixed=True,
    )
    level = Level(spec)
    exit_ids = [record.component_ids[0] for record in level._exit_records]

    solution = tmp_path / "link_exits.oms"
    solution.write_text(f"connection {exit_ids[0]} {exit_ids[1]}\n")
    level.load_solution(solution)

    board = level.sim.board
    board.place_atom(exit_a, Atom(AtomType.SALT))
    board.place_atom(exit_b, Atom(AtomType.SALT))
    board.connect_atoms(exit_a, exit_b)

    result = level.run()

    union = frozenset(exit_ids)
    assert result.finished == {union: 1}
    assert result.finished_by_exit == {0: 1, 1: 1}
    # linked exits share cluster, so they report same completion step
    assert result.finished_steps_by_exit == {0: 0, 1: 0}


def test_two_levels_stay_independent():
    spec = make_level_spec()
    level_a = Level(spec)
    level_b = Level(spec)
    arm_a = _schedule_delivery(level_a)
    arm_b = _schedule_delivery(level_b)

    # Each level allocates ids from 0 independently.
    assert arm_a == arm_b == 4

    result_a = level_a.run()
    assert result_a.total_finished == 1
    # B untouched by A's run.
    assert level_b.sim.step == 0
    assert level_b.sim.env.results.total_finished() == 0

    result_b = level_b.run()
    assert result_b.total_finished == 1

    # Entrypoint shapes are registered per-level, never in the global registry.
    with pytest.raises(KeyError, match="entrance_straight_2"):
        get_blueprint("entrance_straight_2")


# --- unfixed entrypoints (solution-placed) ---

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _unfixed_straight_spec() -> LevelSpec:
    return LevelSpec(
        size=(6, 6),
        shapes=(entrance_straight_2(), exit_straight_2()),
        entrypoints=(
            EntrypointSpec(
                kind=ComponentType.ENTRANCE,
                shape="entrance_straight_2",
                atom_type=AtomType.SALT,
            ),
            EntrypointSpec(
                kind=ComponentType.EXIT,
                shape="exit_straight_2",
                atom_type=AtomType.SALT,
            ),
        ),
        allowed_blueprints=frozenset({"arm"}),
        steps=30,
        entrypoints_fixed=False,
    )


def test_unfixed_happy_path(tmp_path):
    level = Level(_unfixed_straight_spec())
    solution = tmp_path / "unfixed.oms"
    solution.write_text(
        "place entrance_straight_2 2 3 rotation=1 atom_type=salt\n"
        "place exit_straight_2 3 2 rotation=2 atom_type=salt\n"
        "place arm 3 3\n"
        "action 4 1 grab\n"
        "action 4 2 rotate_clw\n"
        "action 4 3 rotate_clw\n"
        "action 4 4 rotate_clw\n"
        "action 4 5 rotate_clw\n"
        "action 4 6 release\n"
    )
    level.load_solution(solution)

    result = level.run()

    assert result.status is LevelStatus.COMPLETED
    assert result.error is None
    assert result.total_finished == 1
    assert result.finished_by_exit == {0: 1}


def test_unfixed_missing_exit_fails(tmp_path):
    level = Level(_unfixed_straight_spec())
    solution = tmp_path / "missing_exit.oms"
    solution.write_text("place entrance_straight_2 2 3 rotation=1 atom_type=salt\n")
    level.load_solution(solution)

    result = level.run()

    assert result.status is LevelStatus.FAILED
    assert result.error is not None
    assert result.error.step == 0
    assert result.steps == 0
    # The simulator is untouched: no step advanced, nothing consumed.
    assert level.sim.step == 0
    assert level.sim.env.results.total_finished() == 0


def test_unfixed_duplicate_exit_fails(tmp_path):
    level = Level(_unfixed_straight_spec())
    solution = tmp_path / "dup_exit.oms"
    solution.write_text(
        "place entrance_straight_2 2 3 rotation=1 atom_type=salt\n"
        "place exit_straight_2 3 2 rotation=2 atom_type=salt\n"
        "place exit_straight_2 4 3 rotation=2 atom_type=salt\n"
    )
    level.load_solution(solution)

    result = level.run()

    assert result.status is LevelStatus.FAILED
    assert result.steps == 0
    assert level.sim.step == 0


def test_unfixed_copies_per_exit_counts(tmp_path):
    spec = LevelSpec(
        size=(6, 6),
        shapes=(
            _single_cell_shape("entrance_1", ComponentType.ENTRANCE),
            _single_cell_shape("exit_1", ComponentType.EXIT),
        ),
        entrypoints=(
            EntrypointSpec(kind=ComponentType.ENTRANCE, shape="entrance_1", atom_type=AtomType.SALT),
            EntrypointSpec(kind=ComponentType.EXIT, shape="exit_1", atom_type=AtomType.SALT),
            EntrypointSpec(kind=ComponentType.EXIT, shape="exit_1", atom_type=AtomType.SALT),
        ),
        allowed_blueprints=frozenset(),
        steps=1,
        entrypoints_fixed=False,
    )
    level = Level(spec)
    exit_a = Hex(3, 3)
    exit_b = Hex(4, 4)
    solution = tmp_path / "copies.oms"
    solution.write_text(
        "place entrance_1 1 1 atom_type=salt\n"
        f"place exit_1 {exit_a.r} {exit_a.s} atom_type=salt\n"
        f"place exit_1 {exit_b.r} {exit_b.s} atom_type=salt\n"
    )
    level.load_solution(solution)

    board = level.sim.board
    board.place_atom(exit_a, Atom(AtomType.SALT))
    board.place_atom(exit_b, Atom(AtomType.SALT))

    result = level.run()

    assert result.status is LevelStatus.COMPLETED
    assert result.total_finished == 2
    assert result.finished_by_exit == {0: 1, 1: 1}


def test_typed_exit_demo_end_to_end():
    level = Level.from_file(FIXTURES_DIR / "typed_delivery.oml")
    level.load_solution(FIXTURES_DIR / "typed_delivery.oms")

    result = level.run()

    assert result.status is LevelStatus.COMPLETED
    assert result.error is None
    assert result.total_finished == 1
    assert result.finished_by_exit == {0: 1}
