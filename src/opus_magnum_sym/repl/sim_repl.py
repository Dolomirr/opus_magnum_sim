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
        line = line.strip()
        if not line or line.startswith("#"):
            return

        if line[0] in "!:":
            self._meta(line[1:])
        else:
            self.interpreter.evaluate_line(line)

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

    def _save(self, args: list[str]): ...

    def _help(self, args: list[str]) -> None:
        print(
            "\n".join(
                [
                    "DSL commands:",
                    "  comp <x> <y> <type> [key=value ...]",
                    "  action <comp_id> <step> <action_type>",
                    "Meta commands:",
                    "  !run [steps]   run simulation",
                    "  !load <path>   load level file",
                    "  !list          list placed components",
                    "  !help          show this message",
                    "  !save          save level to file",
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
