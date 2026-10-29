"""
Run the solution-placed-entrypoints level + solution from `examples/41_unfixed_delivery.om[ls]`.

Thin wrapper over the `.oml`/`.oms` pair: load both files, run, print the result.
"""

from pathlib import Path

from opus_magnum_sym.levels import Level

EXAMPLES_DIR = Path(__file__).resolve().parent


def main():
    level = Level.from_file(EXAMPLES_DIR / "41_unfixed_delivery.oml")
    level.load_solution(EXAMPLES_DIR / "41_unfixed_delivery.oms")

    result = level.run()

    print(result.status)           # LevelStatus.COMPLETED
    print(result.total_finished)   # 1
    print(result.finished_by_exit) # {0: 1}


if __name__ == "__main__":
    main()
