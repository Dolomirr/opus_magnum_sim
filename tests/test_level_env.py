"""
Stage 1: per-instance environment state.

Two simulators with explicit envs must not share component ids or finished
counters, and must not touch the module-level default env.
"""

import opus_magnum_sym.elements.env.index_manager as im
from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.elements.env import level_counter
from opus_magnum_sym.elements.env.level_env import LevelEnv, default_env
from opus_magnum_sym.simulation.simulator import Simulator


def _flow_sim(env: LevelEnv) -> Simulator:
    sim = Simulator((6, 6), env=env)
    sim.add_component(Hex(2, 3), ComponentType.ENTRANCE, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 2), ComponentType.EXIT, atom_type=AtomType.BASIC)
    sim.add_component(Hex(3, 3), ComponentType.ARM)
    return sim


def _arm_id(sim: Simulator) -> int:
    return next(cid for cid, comp in sim.components.items() if comp.type == ComponentType.ARM)


def _schedule_delivery(sim: Simulator) -> None:
    arm_id = _arm_id(sim)
    sim.assign_step_action(arm_id, 1, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(arm_id, 2, StepActionType.GRAB)
    sim.assign_step_action(arm_id, 3, StepActionType.ROTATE_CCLW)
    sim.assign_step_action(arm_id, 4, StepActionType.RELEASE)


def test_explicit_envs_share_no_ids():
    env_a = LevelEnv()
    env_b = LevelEnv()
    sim_a = _flow_sim(env_a)
    sim_b = _flow_sim(env_b)

    assert sim_a.env is env_a
    assert sim_b.env is env_b
    assert sim_a.im is env_a.im
    assert sim_b.im is env_b.im

    # Both start allocating from id 0 independently.
    assert set(sim_a.components) | set(sim_a.entrypoints) == {0, 1, 2}
    assert set(sim_b.components) | set(sim_b.entrypoints) == {0, 1, 2}
    assert env_a.im.total_allocated() == 3
    assert env_b.im.total_allocated() == 3


def test_explicit_envs_share_no_counters():
    env_a = LevelEnv()
    env_b = LevelEnv()
    sim_a = _flow_sim(env_a)
    sim_b = _flow_sim(env_b)
    _schedule_delivery(sim_a)

    for _ in range(5):
        sim_a.next_step()
        sim_b.next_step()

    assert env_a.results.total_finished() == 1
    assert env_b.results.total_finished() == 0


def test_interleaved_delivery_stays_independent():
    env_a = LevelEnv()
    env_b = LevelEnv()
    sim_a = _flow_sim(env_a)
    sim_b = _flow_sim(env_b)
    _schedule_delivery(sim_a)
    _schedule_delivery(sim_b)

    for _ in range(5):
        sim_a.next_step()
        sim_b.next_step()

    assert env_a.results.total_finished() == 1
    assert env_b.results.total_finished() == 1
    assert env_a.im.total_allocated() == 3
    assert env_b.im.total_allocated() == 3


def test_explicit_envs_leave_module_default_untouched():
    env = LevelEnv()
    sim = _flow_sim(env)
    _schedule_delivery(sim)
    for _ in range(5):
        sim.next_step()

    assert env.results.total_finished() == 1
    # The module-level default env never saw the injected env's activity.
    assert im.total_allocated() == 0
    assert level_counter.total_finished() == 0


def test_default_simulator_uses_module_default_env():
    # A no-env simulator shares the module-level default env.
    default_sim = Simulator((6, 6))
    assert default_sim.env is default_env
    assert default_sim.env.im is im.default_index_manager
    assert default_sim.env.results is level_counter.default_result_counter
