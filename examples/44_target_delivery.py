"""
Run the target-threshold level + solution from `examples/44_target_delivery.om[ls]`.

The level requires one delivery per exit (`target 1`), so the run stops on the
step after the delivery instead of the 30-step limit; the result also reports
the solution cost, area, and per-exit completion step.
"""

from pathlib import Path

from opus_magnum_sym.levels import Level

EXAMPLES_DIR = Path(__file__).resolve().parent


def main():
    level = Level.from_file(EXAMPLES_DIR / "44_target_delivery.oml")
    level.load_solution(EXAMPLES_DIR / "44_target_delivery.oms")

    result = level.run()

    print(result.status)                  # LevelStatus.COMPLETED
    print(result.steps)                   # 7: delivery on step 6, then stop
    print(result.solved)                  # True
    print(result.finished_steps_by_exit)  # {0: 6}
    print(result.metrics)                 # {'cost': 10, 'area': 7, 'completion_steps': 7}


if __name__ == "__main__":
    main()
