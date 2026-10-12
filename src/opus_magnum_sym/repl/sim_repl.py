import shlex
from pathlib import Path

from prompt_toolkit import PromptSession

from opus_magnum_sym.interpreter import SimInterpreter
from opus_magnum_sym.render.renderer import BoardRenderer
from opus_magnum_sym.simulation.simulator import Simulator


class SimREPL:
    def __init__(
        self,
        sim: Simulator,
        renderer: BoardRenderer,
        interpreter: SimInterpreter,
    ) -> None:
        self.sim = sim
        self.renderer = renderer
        self.interpreter = interpreter
        self.session = PromptSession()

        self.meta = {
            "run": self._run,
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
        }
        self.running = True

    def run(self) -> None:
        while self.running:
            try:
                line = self.session.prompt("oms> ")
            except EOFError, KeyboardInterrupt:
                break
            self.evaluate(line)

    def evaluate(self, line: str) -> None:
        # splitting strings containing multi lines commands
        entries = [entry.strip() for entry in line.splitlines()]
        entries = [entry for entry in entries if entry and not entry.startswith("#")]
        if not entries:
            return

        for entry in entries:
            if entry[0] in "!:":
                self._meta(entry[1:])
            else:
                self.interpreter.evaluate_line(entry)

        self._refresh()

    def _meta(self, line: str) -> None:
        tokens = shlex.split(line)
        if not tokens:
            return

        handler = self.meta.get(tokens[0].lower())
        if handler is None:
            print(f"Unknown meta command: {tokens[0]}")
            return
        handler(tokens[1:])

    def _run(self, args: list[str]) -> None:
        try:
            steps = int(args[0]) if args else 30
        except ValueError:
            print(f"Invalid step count: {args[0]}")
            return

        try:
            for _ in range(steps):
                if not self.renderer.process_events():
                    self.running = False
                    return
                self.sim.next_step()
                self.renderer.draw()
                self.renderer.tick(5)
        except KeyboardInterrupt:
            print("Simulation interrupted. Use !clear to reset or !run to continue.")
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
        self.interpreter.load_file(path)

    def _list(self, args: list[str]) -> None:
        components = {**self.sim.entrypoints, **self.sim.components}
        for comp_id, comp in sorted(components.items()):
            print(f"{comp_id}: {comp.type.name} at {comp.pos}")
            if comp.programm:
                actions = ", ".join(f"{step}:{action.name.lower()}" for step, action in sorted(comp.programm.items()))
                print(f"    actions: {actions}")

    def _reset(self, args: list[str]) -> None:
        self.sim.reset()
        print("Board cleared")

    def _save(self, args: list[str]) -> None:
        path = Path(args[0]) if args else Path("solution.oms")

        components = sorted(
            {**self.sim.entrypoints, **self.sim.components}.values(),
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

        path.write_text("\n".join(lines) + "\n")
        print(f"Saved to {path}")

    def _help(self, args: list[str]) -> None:
        print(
            "\n".join(
                [
                    "DSL commands:",
                    "  comp <x> <y> <type> [key=value ...]",
                    "  action <comp_id> <step> <action_type>  (use 'none' to clear)",
                    "  remove <comp_id>                       (alias: rm)",
                    "Meta commands:",
                    "  !run [steps]      run simulation",
                    "  !load <path>      load level file",
                    "  !list             list placed components",
                    "  !reset / !clear   clear board and reset counters",
                    "  !help             show this message",
                    "  !save [path]      save level to file",
                ],
            ),
        )

    def _quit(self, args: list[str]) -> None:
        self.running = False

    def _refresh(self) -> None:
        if not self.renderer.process_events():
            self.running = False
            return
        self.renderer.draw()
