"""
Level runtime: build a simulator from a `LevelSpec` and run it to a result.

Level bundles puzzle's starting conditions with its own runtime state,
so levels run independently of one another.

The high-level entry point is `Level.from_file` and `load_solution` + `run`;
the spec can also be constructed in Python:

```python
from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.atoms.atom import AtomType
from opus_magnum_sym.elements.board import Hex
from opus_magnum_sym.elements.components import ComponentType, ShapeCell, ShapeTemplate
from opus_magnum_sym.levels import EntrypointSpec, Level, LevelSpec

# Local two-cell straight entrance and exit shapes.
entrance = ShapeTemplate(
    name="entrance_straight_2",
    comp_type=ComponentType.ENTRANCE,
    cells=(ShapeCell(offset=Hex(0, 0)), ShapeCell(offset=Hex(-1, 1))),
    links=((0, 1),),
)
exit_ = ShapeTemplate(
    name="exit_straight_2",
    comp_type=ComponentType.EXIT,
    cells=(ShapeCell(offset=Hex(0, 0)), ShapeCell(offset=Hex(-1, 1))),
    links=((0, 1),),
)

spec = LevelSpec(
    size=(6, 6),
    shapes=(entrance, exit_),
    entrypoints=(
        EntrypointSpec(ComponentType.ENTRANCE, "entrance_straight_2", Hex(2, 3), AtomType.SALT, rotation=1),
        EntrypointSpec(ComponentType.EXIT, "exit_straight_2", Hex(3, 2), AtomType.SALT, rotation=2),
    ),
    allowed_blueprints=frozenset({"arm"}),
    steps=30,
)

level = Level(spec)
arm = level.place("arm", Hex(3, 3))
(arm_id,) = arm.component_ids
level.assign_step_action(arm_id, 1, StepActionType.GRAB)
for step in (2, 3, 4, 5):
    level.assign_step_action(arm_id, step, StepActionType.ROTATE_CLW)
level.assign_step_action(arm_id, 6, StepActionType.RELEASE)

result = level.run()
print(result.status)            # LevelStatus.COMPLETED
print(result.total_finished)    # 1
print(result.finished_by_exit)  # {0: 1}
```

Entrypoints may be fixed (the level places them, above) or solution-placed
(`entrypoints_fixed 0`); see `levels/spec.py` and `interpreter/level_loader.py`.
"""

from collections import Counter
from pathlib import Path
from typing import cast

from opus_magnum_sym.elements.board import Hex
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
        self._exit_records: list[PlacementRecord] = []

        if spec.entrypoints_fixed:
            for ep in spec.entrypoints:
                record = self.sim.place(ep.shape, cast(Hex, ep.pos), rotation=ep.rotation, atom_type=ep.atom_type)
                self._entrypoint_records.append(record)
                if ep.kind is ComponentType.EXIT:
                    self._exit_records.append(record)

            # Check solution placements only after entrypoints are on the board;
            # entrypoint shapes are *not* part of the allow-list.
            self.sim.allowed_blueprints = set(spec.allowed_blueprints)
        else:
            # Entrypoints are solution-placed:
            # make their shapes placeable alongside regular allow-list.
            entrypoint_shapes = {ep.shape for ep in spec.entrypoints}
            self.sim.allowed_blueprints = set(spec.allowed_blueprints) | entrypoint_shapes

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

        Unfixed entrypoints are re-checked every call:
        missing or duplicate required entrypoint yields `FAILED` without stepping.
        """
        if not self.spec.entrypoints_fixed:
            mismatch = self._unfixed_placement_error()
            if mismatch is not None:
                num_exits = sum(1 for ep in self.spec.entrypoints if ep.kind is ComponentType.EXIT)
                return LevelResult(
                    status=LevelStatus.FAILED,
                    error=mismatch,
                    steps=0,
                    finished={},
                    finished_by_exit=dict.fromkeys(range(num_exits), 0),
                    total_finished=0,
                )

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

    def _unfixed_placement_error(self) -> LevelError | None:
        """
        Return a `LevelError` when solution-placed entrypoints and the spec does not match.
        Each defined entrypoint requires exactly one placement of its shape.
        """
        spec_counts = Counter(ep.shape for ep in self.spec.entrypoints)
        placed_counts = Counter(record.blueprint for record in self.sim.placements if record.blueprint in spec_counts)
        for shape, expected in spec_counts.items():
            actual = placed_counts[shape]
            if actual != expected:
                return LevelError(
                    exception="EntrypointPlacementError",
                    message=f"entrypoint shape {shape!r}: expected {expected} placement(s), found {actual}",
                    step=0,
                )
        return None

    def _exit_cluster_key(self, record: PlacementRecord) -> frozenset[int]:
        """
        Current exit cluster id set for `record`, from the live connection graph.

        Matches `ResultCounter` key, essentially a closure of exit ids.

        Connections only link same-type components, so for exits contains only exits.
        Recomputed at snapshot time so a solution that links
        or splits exit entrypoints is reflected in `finished_by_exit`.
        """
        ids: set[int] = set()
        for comp_id in record.component_ids:
            ids.update(self.sim.connections.group_of(comp_id))
        return frozenset(ids)

    def _exit_records_for_snapshot(self) -> list[PlacementRecord]:
        """
        Exit placements aligned with spec exit entrypoints, resolved at snapshot time.

        Fixed mode reuses records stored at build; unfixed mode matches each
        exit spec to the n-th placement of its shape,
        so copies and solution-placed entrypoints report correctly.
        """
        if self.spec.entrypoints_fixed:
            return list(self._exit_records)

        placements_by_shape: dict[str, list[PlacementRecord]] = {}
        for record in self.sim.placements:
            placements_by_shape.setdefault(record.blueprint, []).append(record)

        shape_used: dict[str, int] = {}
        records: list[PlacementRecord] = []
        for ep in self.spec.entrypoints:
            if ep.kind is not ComponentType.EXIT:
                continue
            index = shape_used.get(ep.shape, 0)
            records.append(placements_by_shape[ep.shape][index])
            shape_used[ep.shape] = index + 1
        return records

    def _snapshot(self, status: LevelStatus, error: LevelError | None) -> LevelResult:
        finished = self.sim.env.results.clusters()
        finished_by_exit = {
            index: finished.get(self._exit_cluster_key(record), 0)
            for index, record in enumerate(self._exit_records_for_snapshot())
        }
        return LevelResult(
            status=status,
            error=error,
            steps=self.sim.step,
            finished=finished,
            finished_by_exit=finished_by_exit,
            total_finished=self.sim.env.results.total_finished(),
        )
