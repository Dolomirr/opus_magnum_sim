"""Level solution metrics: target, completion steps, cost, area (Step 10)."""

from fixtures.levels import make_level_spec

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import Atom, AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.levels import Level, LevelStatus
from opus_magnum_sym.levels.cost import component_cost

DELIVERY_STEP = 6
SECOND_DELIVERY_STEP = 15


def _schedule_delivery(level: Level) -> int:
    """Place an arm and program the canonical delivery (mirrors test_level)."""
    (arm_id,) = level.place("arm", Hex(3, 3)).component_ids
    level.assign_step_action(arm_id, 1, StepActionType.GRAB)
    for step in (2, 3, 4, 5):
        level.assign_step_action(arm_id, step, StepActionType.ROTATE_CLW)
    level.assign_step_action(arm_id, 6, StepActionType.RELEASE)
    return arm_id


def _schedule_second_delivery(level: Level, arm_id: int) -> None:
    """Swing the arm back after the first release and deliver the respawned molecule."""
    level.assign_step_action(arm_id, 8, StepActionType.ROTATE_CLW)
    level.assign_step_action(arm_id, 9, StepActionType.ROTATE_CLW)
    level.assign_step_action(arm_id, 10, StepActionType.GRAB)
    for step in (11, 12, 13, 14):
        level.assign_step_action(arm_id, step, StepActionType.ROTATE_CLW)
    level.assign_step_action(arm_id, 15, StepActionType.RELEASE)


def test_target_stops_at_delivery_step():
    level = Level(make_level_spec(target=1))
    _schedule_delivery(level)

    result = level.run()

    assert result.status is LevelStatus.COMPLETED
    assert result.solved is True
    assert result.steps == DELIVERY_STEP + 1
    assert result.total_finished == 1
    assert result.finished_steps_by_exit == {0: DELIVERY_STEP}
    assert result.metrics == {"cost": 10, "area": 7, "completion_steps": DELIVERY_STEP + 1}


def test_target_requires_each_delivery():
    level = Level(make_level_spec(target=2))
    arm_id = _schedule_delivery(level)
    _schedule_second_delivery(level, arm_id)

    result = level.run()

    assert result.solved is True
    assert result.steps == SECOND_DELIVERY_STEP + 1
    assert result.total_finished == 2
    # Completion is the target-th delivery, not the first one.
    assert result.finished_steps_by_exit == {0: SECOND_DELIVERY_STEP}


def test_unsolved_target_reports_none_and_runs_to_limit():
    level = Level(make_level_spec(target=2))
    _schedule_delivery(level)

    result = level.run()

    assert result.status is LevelStatus.COMPLETED
    assert result.solved is False
    assert result.steps == 30
    assert result.finished_by_exit == {0: 1}
    assert result.finished_steps_by_exit == {0: None}
    assert result.metrics["completion_steps"] is None


def test_target_none_and_zero_run_to_limit():
    for target in (None, 0):
        level = Level(make_level_spec(target=target))
        _schedule_delivery(level)

        result = level.run()

        assert result.target is None
        assert result.solved is True
        assert result.steps == 30
        assert result.total_finished == 1
        assert result.finished_steps_by_exit == {0: DELIVERY_STEP}


def test_cost_sums_placed_components_and_ignores_entrypoints():
    level = Level(
        make_level_spec(
            allowed_blueprints=frozenset({"arm", "connector_straight_2", "glyph_duplication"}),
        )
    )
    level.place("arm", Hex(3, 3))
    level.place("glyph_duplication", Hex(1, 0))
    level.place("connector_straight_2", Hex(0, 4), rotation=2, atom_type=AtomType.SALT)

    result = level.run(steps=1)

    # arm 10 + duplication glyph 20 + straight-2 connector 10; entrypoints are free.
    assert result.cost == 40


def test_component_cost_lookup():
    assert component_cost("arm") == 10
    assert component_cost("arm_piston") == 20
    assert component_cost("connector_straight_2") == 10
    assert component_cost("connector_tri") == 20
    assert component_cost("connector_tri_odd") == 20
    assert component_cost("salt_transmuter") == 10
    assert component_cost("glyph_duplication") == 20
    # Entrypoint shapes are per-level and not in the built-in table.
    assert component_cost("entrance_straight_2") == 0


def test_compound_connector_costs_once_not_per_cell():
    level = Level(make_level_spec(allowed_blueprints=frozenset({"connector_tri"})))
    level.place("connector_tri", Hex(4, 4), atom_type=AtomType.SALT)

    result = level.run(steps=1)

    # A Y-shaped connector is one component with its own cost, not 4 cells each.
    assert result.cost == 20


def test_area_counts_component_atom_and_sweep_cells():
    level = Level(make_level_spec(target=1))
    _schedule_delivery(level)

    result = level.run()

    entrance_cells = {Hex(2, 3), Hex(2, 4)}
    swept = set(entrance_cells)
    for rotation in (1, 2, 3, 4):
        swept |= {cell.rotate_around(Hex(3, 3), rotation) for cell in entrance_cells}
    expected = swept | {Hex(3, 3)}  # plus the arm base footprint

    assert len(expected) == 7
    assert result.area == len(expected)
    assert level.sim.env.area.cells <= expected


def test_area_counts_board_atom_stops():
    level = Level(make_level_spec())
    level.sim.board.place_atom(Hex(0, 5), Atom(AtomType.SALT))

    result = level.run(steps=1)

    # Entrypoint cells, the arm-free board atom, and nothing else.
    assert result.area == 5
