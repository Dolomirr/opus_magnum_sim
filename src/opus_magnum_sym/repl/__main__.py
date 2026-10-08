import sys

import pygame

from opus_magnum_sym.interpreter import SimInterpreter
from opus_magnum_sym.render.renderer import BoardRenderer
from opus_magnum_sym.repl import SimREPL
from opus_magnum_sym.simulation.simulator import Simulator


def main() -> None:
    sim = Simulator((10, 10))
    renderer = BoardRenderer(sim)
    interpreter = SimInterpreter(sim)

    if len(sys.argv) > 1:
        interpreter.load_file(sys.argv[1])

    renderer.draw()

    try:
        SimREPL(sim, renderer, interpreter).run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
