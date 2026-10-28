"""Level runtime and result tests (Stage 4)."""

import pytest  # noqa: INP001
from fixtures.levels import make_level_spec

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Hex
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
