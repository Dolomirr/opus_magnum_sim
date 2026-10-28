"""
Level runtime: build a simulator from a `LevelSpec` and run it to a result.
"""

from pathlib import Path

from opus_magnum_sym.elements.components import ComponentType, default_registry
from opus_magnum_sym.elements.env.level_env import LevelEnv
from opus_magnum_sym.interpreter.sim_interpreter import SimInterpreter
from opus_magnum_sym.levels.result import LevelError, LevelResult, LevelStatus
from opus_magnum_sym.levels.spec import LevelSpec
from opus_magnum_sym.simulation.errors import SimulationCollisionError, SimulationRuntimeError
from opus_magnum_sym.simulation.placement import PlacementRecord
from opus_magnum_sym.simulation.simulator import Simulator


class Level:
    """
    A level built from its `LevelSpec`, runnable independently of any other level.

    Owns dedicated simulator so that ids, counters, and shape did not leak between them.
    """

    def __init__(self, spec: LevelSpec) -> None:
        self.spec = spec
        self.sim = Simulator(spec.size, env=LevelEnv(), blueprints=default_registry.clone())

        for shape in spec.shapes:
            self.sim.blueprints.register(shape)

        self._entrypoint_records: list[PlacementRecord] = []
        self._exit_cluster_keys: dict[int, frozenset[int]] = {}
        exit_index = 0
        for ep in spec.entrypoints:
            record = self.sim.place(ep.shape, ep.pos, rotation=ep.rotation, atom_type=ep.atom_type)
            self._entrypoint_records.append(record)
            if ep.kind is ComponentType.EXIT:
                self._exit_cluster_keys[exit_index] = frozenset(record.component_ids)
                exit_index += 1

        # Gate solution placements only after entrypoints are on the board;
        # entrypoint shapes are *not* part of the allow-list.
        self.sim.allowed_blueprints = set(spec.allowed_blueprints)

    # AAA.
    @classmethod
    def from_file(cls, path: str | Path) -> Level:
        """
        Build a level from a `.oml` file.
        """
        from opus_magnum_sym.interpreter.level_loader import LevelLoader  # noqa: PLC0415

        return cls(LevelLoader().load_file(path))

    # solution building

    def place(self, name, pos, rotation: int = 0, **overrides) -> PlacementRecord:
        return self.sim.place(name, pos, rotation=rotation, **overrides)

    def assign_step_action(self, comp_id: int, step: int, action) -> None:
        self.sim.assign_step_action(comp_id, step, action)

    def remove_placement(self, record: PlacementRecord) -> None:
        self.sim.remove_placement(record)

    def load_solution(self, path: str | Path) -> None:
        SimInterpreter(self.sim).load_file(path)

    # running

    def run(self, steps: int | None = None) -> LevelResult:
        """
        Advance the simulation up to the spec limit (or `steps` override).

        Returns `LevelResult`; never raises runtime failures to caller.
        Reaching the limit without an error is `COMPLETED` regardless of delivered counts.
        """
        limit = self.spec.steps if steps is None else steps

        status = LevelStatus.COMPLETED
        error: LevelError | None = None
        try:
            for _ in range(limit):
                self.sim.next_step()
        except SimulationCollisionError as err:
            status = LevelStatus.ERROR
            error = LevelError(
                exception=type(err).__name__,
                message=str(err),
                step=err.step,
                collision=err.event,
            )
        except SimulationRuntimeError as err:
            status = LevelStatus.ERROR
            error = LevelError(
                exception=type(err).__name__,
                message=str(err),
                step=err.step,
            )
        except Exception as err:
            status = LevelStatus.ERROR
            error = LevelError(
                exception=type(err).__name__,
                message=str(err),
                step=self.sim.step,
            )

        return self._snapshot(status, error)

    def _snapshot(self, status: LevelStatus, error: LevelError | None) -> LevelResult:
        finished = self.sim.env.results.clusters()
        finished_by_exit = {index: finished.get(key, 0) for index, key in self._exit_cluster_keys.items()}
        return LevelResult(
            status=status,
            error=error,
            steps=self.sim.step,
            finished=finished,
            finished_by_exit=finished_by_exit,
            total_finished=self.sim.env.results.total_finished(),
        )
