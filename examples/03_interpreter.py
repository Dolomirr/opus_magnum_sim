"""
DEPRECATED - low-level `SimInterpreter` + `BoardRenderer` loop.
See `examples/30_load_solution.py`.
"""

import time
from pathlib import Path

from opus_magnum_sym.interpreter.sim_interpreter import SimInterpreter
from opus_magnum_sym.render.renderer import BoardRenderer
from opus_magnum_sym.simulation.simulator import Simulator

EXAMPLES_DIR = Path(__file__).resolve().parent


def main():
    sim = Simulator((10, 10))
    renderer = BoardRenderer(sim)

    inter = SimInterpreter(sim)
    inter.load_file(EXAMPLES_DIR / "10_basic_flow.oms")

    for _ in range(12):
        sim.next_step()
        renderer.draw()
        renderer.tick(60)
        time.sleep(5)


if __name__ == "__main__":
    main()
