import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from opus_magnum_sym.render.null_renderer import NullRenderer
from opus_magnum_sym.render.renderer import BoardRenderer
from opus_magnum_sym.simulation.errors import SimulationCollisionError

if TYPE_CHECKING:
    from opus_magnum_sym.repl.sim_repl import SimREPL


class MetaInterpreter:
    def __init__(self, repl: SimREPL) -> None:
        self.repl = repl
        self.commands = {
            "run": self._run,
            "step": self._step,
            "s": self._step,
            "load": self._load,
            "r": self._load,
            "list": self._list,
            "help": self._help,
            "quit": self._quit,
            "q": self._quit,
            "exit": self._quit,
            "save": self._save,
            "w": self._save,
            "reset": self._reset,
            "clear": self._reset,
            "c": self._reset,
            "history": self._history,
            "h": self._history,
            "edit": self._edit,
            "e": self._edit,
            "viz": self._viz,
        }
        self.path_commands = frozenset({"load", "r", "save", "w"})

    def evaluate(self, line: str) -> None:
        tokens = shlex.split(line)
        if not tokens:
            return

        handler = self.commands.get(tokens[0].lower())
        if handler is None:
            print(f"Unknown meta command: {tokens[0]}")
            return
        handler(tokens[1:])

    def command_names(self) -> list[str]:
        return sorted(self.commands)

    def _run(self, args: list[str]) -> None:
        self._advance(args, default_steps=30)

    def _step(self, args: list[str]) -> None:
        self._advance(args, default_steps=1)

    def _advance(self, args: list[str], default_steps: int) -> None:
        steps, pause = default_steps, None

        positional: list[str] = []
        for arg in args:
            key, sep, value = arg.partition("=")
            if not sep:
                positional.append(arg)
                continue
            try:
                if key.lower() in {"steps", "main", "n"}:
                    steps = int(value)
                elif key.lower() in {"pause", "delay"}:
                    pause = float(value)
                else:
                    print(f"Unknown argument: {key}")
                    return
            except ValueError:
                print(f"Invalid value for {key}: {value}")
                return

        if positional:
            try:
                steps = int(positional[0])
            except ValueError:
                print(f"Invalid step count: {positional[0]}")
                return

        # preventing 0-fps pause
        fps = 5 if pause is None else (0 if pause <= 0 else 1 / pause)

        try:
            for _ in range(steps):
                if not self.repl.renderer.process_events():
                    self.repl.running = False
                    return
                self.repl.sim.next_step()
                self.repl.renderer.draw()
                self.repl.renderer.tick(fps)
        except KeyboardInterrupt:
            print("Simulation interrupted. Use !clear to reset or !run to continue.")
        except SimulationCollisionError as e:
            event = e.event
            owners = ", ".join(str(i) for i in event.owner_ids)
            print(
                f"Collision ({event.category.name}) at step {event.step} "
                f"near ({event.cell.r}, {event.cell.s}) involving component(s) {owners}"
            )
            self.repl.renderer.draw()
        except Exception as e:
            print(f"Simulation error: {e}")

    def _load(self, args: list[str]) -> None:
        if not args:
            print("Usage: !load <path>")
            return

        path = Path(args[0])
        if not path.exists():
            print(f"File not found: {path}")
            return
        self.repl.interpreter.load_file(path)

    def _list(self, args: list[str]) -> None:
        components = {**self.repl.sim.entrypoints, **self.repl.sim.components}
        for comp_id, comp in sorted(components.items()):
            print(f"{comp_id}: {comp.type.name} at {comp.pos}")
            if comp.programm:
                actions = ", ".join(f"{step}:{action.name.lower()}" for step, action in sorted(comp.programm.items()))
                print(f"    actions: {actions}")
        for record in self.repl.sim.placements:
            ids = ", ".join(str(i) for i in record.component_ids)
            print(
                f"placement {record.blueprint} at {record.pos} "
                f"rotation={record.rotation} ids=[{ids}]"
            )

    def _history(self, args: list[str]) -> None:
        n = 20
        if args:
            try:
                n = int(args[0])
            except ValueError:
                print(f"Invalid count: {args[0]}")
                return

        entries = self.repl.session.history.get_strings()
        for line in entries[-n:] if n > 0 else entries:
            print(line)

    def _reset(self, args: list[str]) -> None:
        self.repl.sim.reset()
        print("Board cleared")

    def _save(self, args: list[str]) -> None:
        path = Path(args[0]) if args else Path("solution.oms")
        path.write_text(self._serialize())
        print(f"Saved to {path}")

    def _serialize(self) -> str:
        components = sorted(
            {**self.repl.sim.entrypoints, **self.repl.sim.components}.values(),
            key=lambda comp: comp.idx,
        )

        lines: list[str] = []
        for comp in components:
            parts = [f"comp {comp.pos.r} {comp.pos.s} {comp.type.name.lower()}"]
            if hasattr(comp, "atom_type"):
                parts.append(f"atom_type={comp.atom_type.name.lower()}")
            if getattr(comp, "rotation", 0):
                parts.append(f"rotation={comp.rotation}")
            if getattr(comp, "hand_length", 1) != 1:
                parts.append(f"length={comp.hand_length}")
            lines.append(" ".join(parts))

        lines.append("")

        for comp in components:
            for step, action in sorted(comp.programm.items()):
                lines.append(f"action {comp.idx} {step} {action.name.lower()}")

        return "\n".join(lines) + "\n"

    def _edit(self, args: list[str]) -> None:
        fd, tmp = tempfile.mkstemp(prefix="oms_edit_", suffix=".oms")
        path = Path(tmp)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(self._serialize())

            editor = shlex.split(os.environ.get("EDITOR", "vi"))
            try:
                result = subprocess.run([*editor, str(path)], check=False)  # noqa: S603
            except OSError as e:
                print(f"Failed to start editor: {e}")
                return
            if result.returncode != 0:
                print("Editor exited with an error; board left unchanged.")
                return

            self._reset([])
            self._load([str(path)])
        finally:
            path.unlink(missing_ok=True)

    def _viz(self, args: list[str]) -> None:
        if not args:
            state = "on" if isinstance(self.repl.renderer, BoardRenderer) else "off"
            print(f"Visualization is currently {state}")
            return

        cmd = args[0].lower()
        if cmd == "off":
            if isinstance(self.repl.renderer, NullRenderer):
                print("Visualization is already off")
                return
            pygame.quit()
            self.repl.renderer = NullRenderer()
            print("Visualization disabled")
        elif cmd == "on":
            if isinstance(self.repl.renderer, BoardRenderer):
                print("Visualization is already on")
                return
            try:
                self.repl.renderer = BoardRenderer(self.repl.sim)
                self.repl.renderer.draw()
                print("Visualization enabled")
            except Exception as e:
                print(f"Failed to enable visualization: {e}")
                self.repl.renderer = NullRenderer()
        else:
            print("Usage: !viz [on|off]")

    def _help(self, args: list[str]) -> None:
        print(
            "\n".join(
                [
                    "DSL commands:",
                    "  comp <x> <y> <type> [key=value ...]",
                    "  place <blueprint> <x> <y> [rotation=R] [key=value ...]",
                    "  action <comp_id> <step> <action_type>  (use 'none' to clear)",
                    "  remove <comp_id>                       (alias: rm)",
                    "Meta commands:",
                    "  !run [steps] [pause=<sec>]   run simulation (default 30 steps)",
                    "  !step [steps] [pause=<sec>]  advance steps (default 1; alias: !s)",
                    "  !load <path>      load level file",
                    "  !list             list placed components",
                    "  !reset / !clear   clear board and reset counters",
                    "  !history [n]      show last n commands (default 20)",
                    "  !edit             edit current solution in $EDITOR and reload",
                    "  !viz [on|off]     enable/disable visualization",
                    "  !help             show this message",
                    "  !save [path]      save level to file",
                ],
            ),
        )

    def _quit(self, args: list[str]) -> None:
        self.repl.running = False
