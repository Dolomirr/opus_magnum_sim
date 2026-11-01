"""Program cycling tests: per-level optional looping of component programs."""

from fixtures.levels import make_level_spec

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.levels import Level


def _cycling_level(**overrides) -> Level:
    return Level(make_level_spec(cycling=True, **overrides))


def test_cycling_defaults_off():
    spec = make_level_spec()
    assert spec.cycling is False
    assert Level(spec).sim.cycling is False


def test_cycle_period_is_longest_program_span():
    level = _cycling_level()
    a = level.place("arm", Hex(0, 0)).component_ids[0]
    b = level.place("arm", Hex(0, 1)).component_ids[0]
    c = level.place("arm", Hex(0, 2)).component_ids[0]
    # spans: a=2, b=5, c=1 -> shared period 5 (longest span, not longest endpoint)
    level.assign_step_action(a, 1, StepActionType.ROTATE_CLW)
    level.assign_step_action(a, 2, StepActionType.ROTATE_CLW)
    for step in (1, 2, 3, 4, 5):
        level.assign_step_action(b, step, StepActionType.ROTATE_CLW)
    level.assign_step_action(c, 7, StepActionType.ROTATE_CLW)

    level.sim._refresh_cycle_period()

    assert {cid: level.sim.components[cid].cycle_period for cid in (a, b, c)} == {a: 5, b: 5, c: 5}


def test_cycling_loops_action_lookup():
    level = _cycling_level()
    arm = level.place("arm", Hex(0, 0)).component_ids[0]
    # program at steps 2,3 -> span 2
    level.assign_step_action(arm, 2, StepActionType.ROTATE_CLW)
    level.assign_step_action(arm, 3, StepActionType.ROTATE_CLW)

    level.sim._refresh_cycle_period()
    comp = level.sim.components[arm]

    assert comp.cycle_period == 2
    assert comp.get_step_action(0) is StepActionType.NONE  # before first action
    assert comp.get_step_action(1) is StepActionType.NONE
    assert comp.get_step_action(2) is StepActionType.ROTATE_CLW
    assert comp.get_step_action(3) is StepActionType.ROTATE_CLW
    assert comp.get_step_action(4) is StepActionType.ROTATE_CLW  # wraps to 2
    assert comp.get_step_action(5) is StepActionType.ROTATE_CLW  # wraps to 3


def test_cycling_offset_beyond_period():
    level = _cycling_level()
    long_arm = level.place("arm", Hex(0, 0)).component_ids[0]
    late_arm = level.place("arm", Hex(0, 1)).component_ids[0]
    # long arm sets period 5; late arm acts once at step 7 (past the period)
    for step in (1, 2, 3, 4, 5):
        level.assign_step_action(long_arm, step, StepActionType.ROTATE_CLW)
    level.assign_step_action(late_arm, 7, StepActionType.ROTATE_CLW)

    level.sim._refresh_cycle_period()
    comp = level.sim.components[late_arm]

    assert comp.cycle_period == 5
    assert comp.get_step_action(6) is StepActionType.NONE
    assert comp.get_step_action(7) is StepActionType.ROTATE_CLW
    assert comp.get_step_action(8) is StepActionType.NONE
    assert comp.get_step_action(12) is StepActionType.ROTATE_CLW  # 7 + 5


def test_cycling_preserves_gaps():
    level = _cycling_level()
    arm = level.place("arm", Hex(0, 0)).component_ids[0]
    # [A _ A] -> span 3, gap at step 2 stays empty on every loop
    level.assign_step_action(arm, 1, StepActionType.ROTATE_CLW)
    level.assign_step_action(arm, 3, StepActionType.ROTATE_CLW)

    level.sim._refresh_cycle_period()
    comp = level.sim.components[arm]

    assert comp.cycle_period == 3
    assert comp.get_step_action(1) is StepActionType.ROTATE_CLW
    assert comp.get_step_action(2) is StepActionType.NONE
    assert comp.get_step_action(3) is StepActionType.ROTATE_CLW
    assert comp.get_step_action(4) is StepActionType.ROTATE_CLW
    assert comp.get_step_action(5) is StepActionType.NONE  # gap preserved


def test_cycling_disabled_does_not_loop():
    level = Level(make_level_spec())
    arm = level.place("arm", Hex(0, 0)).component_ids[0]
    level.assign_step_action(arm, 1, StepActionType.ROTATE_CLW)

    comp = level.sim.components[arm]
    assert comp.get_step_action(1) is StepActionType.ROTATE_CLW
    assert comp.get_step_action(2) is StepActionType.NONE  # program ends


def test_cycling_arm_repeats_rotation():
    level = _cycling_level()
    arm = level.place("arm", Hex(0, 0)).component_ids[0]
    level.assign_step_action(arm, 1, StepActionType.ROTATE_CLW)

    level.run(steps=5)

    # step 0 is NONE, steps 1..4 rotate every step
    assert level.sim.components[arm].rotation == 4


def test_cycling_toggled_after_placement():
    level = Level(make_level_spec())  # cycling off at build time
    arm = level.place("arm", Hex(0, 0)).component_ids[0]
    level.assign_step_action(arm, 1, StepActionType.ROTATE_CLW)

    level.sim.cycling = True  # toggled after the arm was placed

    level.run(steps=4)

    # program loops: steps 1..3 rotate
    assert level.sim.components[arm].rotation == 3
