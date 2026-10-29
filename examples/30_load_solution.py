"""
Run a level and its solution loaded from `.oml` / `.oms` files.

The simplest high-level entry point: `Level.from_file` + `load_solution` + `run`.
"""

from pathlib import Path

from opus_magnum_sym.levels import Level

EXAMPLES_DIR = Path(__file__).resolve().parent


def main():
    level = Level.from_file(EXAMPLES_DIR / "26_level_fixed.oml")
    level.load_solution(EXAMPLES_DIR / "26_level_fixed.oms")

    result = level.run()

    print(result.status)  # LevelStatus.COMPLETED
    print(result.total_finished)  # 1
    print(result.finished_by_exit)  # {0: 1}


if __name__ == "__main__":
    main()
