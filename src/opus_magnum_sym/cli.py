import argparse
import sys
from collections.abc import Sequence

import pygame

from opus_magnum_sym.elements.components.base_component import ComponentType
from opus_magnum_sym.elements.env import level_counter
from opus_magnum_sym.interpreter import SimInterpreter
from opus_magnum_sym.logging import configure_logging
from opus_magnum_sym.render.factory import create_renderer
from opus_magnum_sym.repl import SimREPL
from opus_magnum_sym.simulation.simulator import LevelFinished, Simulator


def start_repl(file: str | None = None, headless: bool = False, commands: list[str] | None = None) -> None:
    configure_logging()
    sim = Simulator((10, 10))
    renderer = create_renderer(sim, headless=headless)
    interpreter = SimInterpreter(sim)

    if file is not None:
        interpreter.load_file(file)

    for command in commands or []:
        interpreter.evaluate_line(command)

    renderer.draw()

    try:
        SimREPL(sim, renderer, interpreter).run()
    finally:
        pygame.quit()


def _run_headless(file: str | None, steps: int, commands: list[str] | None = None) -> None:
    configure_logging()
    sim = Simulator((10, 10))
    interpreter = SimInterpreter(sim)

    if file is not None:
        interpreter.load_file(file)

    for command in commands or []:
        interpreter.evaluate_line(command)

    try:
        for _ in range(steps):
            sim.next_step()
    except LevelFinished as exc:
        print(exc.message)
        return

    print(f"Ran {steps} steps. Correct finished: {level_counter.total_finished()}")


def _validate(file: str) -> None:
    configure_logging()
    sim = Simulator((10, 10))
    interpreter = SimInterpreter(sim)

    try:
        interpreter.load_file(file)
    except Exception as e:
        print(f"Validation failed: {e}")
        sys.exit(1)

    components = {**sim.entrypoints, **sim.components}

    has_entrance = any(c.type == ComponentType.ENTRANCE for c in components.values())
    has_exit = any(c.type == ComponentType.EXIT for c in components.values())

    if not has_entrance:
        print("Validation failed: no entrance component found")
        sys.exit(1)
    if not has_exit:
        print("Validation failed: no exit component found")
        sys.exit(1)

    print(f"Validation passed: {len(components)} components loaded successfully")


def main(argv: Sequence[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(prog="opus-magnum", description="Opus Magnum puzzle simulator.")
    subparsers = parser.add_subparsers(dest="subcommand")

    repl_parser = subparsers.add_parser("repl", help="interactive REPL session")
    repl_parser.add_argument("file", nargs="?", help="solution file to load on start")
    repl_parser.add_argument(
        "--headless",
        "-H",
        action="store_true",
        help="run without pygame visualization",
    )
    repl_parser.add_argument(
        "--command",
        "-c",
        action="append",
        default=[],
        help="inline DSL command to execute on startup (can be repeated)",
    )

    validate_parser = subparsers.add_parser("validate", help="validate a solution file")
    validate_parser.add_argument("file")

    run_parser = subparsers.add_parser("run", help="run a solution headlessly")
    run_parser.add_argument("file", nargs="?", help="solution file to load before running inline commands")
    run_parser.add_argument("--steps", type=int, default=30)
    run_parser.add_argument(
        "--command",
        "-c",
        action="append",
        default=[],
        help="inline DSL command to execute before running (can be repeated)",
    )

    if not argv or (argv[0] not in subparsers.choices and not argv[0].startswith("-")):
        argv.insert(0, "repl")

    args = parser.parse_args(argv)

    match args.subcommand:
        case "validate":
            _validate(args.file)
        case "run":
            if not args.file and not args.command:
                parser.error("'run' requires either a file or at least one -c/--command")
            _run_headless(args.file, args.steps, commands=args.command)
        case _:
            start_repl(args.file, headless=args.headless, commands=args.command)


if __name__ == "__main__":
    main()
