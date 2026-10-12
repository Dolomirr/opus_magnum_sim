import argparse
import sys
from collections.abc import Sequence

import pygame

from opus_magnum_sym.interpreter import SimInterpreter
from opus_magnum_sym.render.renderer import BoardRenderer
from opus_magnum_sym.repl import SimREPL
from opus_magnum_sym.simulation.simulator import Simulator


def start_repl(file: str | None = None) -> None:
    sim = Simulator((10, 10))
    renderer = BoardRenderer(sim)
    interpreter = SimInterpreter(sim)

    if file is not None:
        interpreter.load_file(file)

    renderer.draw()

    try:
        SimREPL(sim, renderer, interpreter).run()
    finally:
        pygame.quit()


# TODO: not forget cli
def main(argv: Sequence[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(prog="opus-magnum", description="Opus Magnum puzzle simulator.")
    subparsers = parser.add_subparsers(dest="command")

    repl_parser = subparsers.add_parser("repl", help="interactive REPL with visualization (default)")
    repl_parser.add_argument("file", nargs="?", help="solution file to load on start")

    validate_parser = subparsers.add_parser("validate", help="validate a solution file (not implemented yet)")
    validate_parser.add_argument("file")

    run_parser = subparsers.add_parser("run", help="run a solution headlessly (not implemented yet)")
    run_parser.add_argument("file")
    run_parser.add_argument("--steps", type=int, default=30)

    if not argv or (argv[0] not in subparsers.choices and not argv[0].startswith("-")):
        argv.insert(0, "repl")

    args = parser.parse_args(argv)

    match args.command:
        case "validate" | "run":
            parser.error(f"'{args.command}' is not implemented yet")
        case _:
            start_repl(args.file)


if __name__ == "__main__":
    main()
