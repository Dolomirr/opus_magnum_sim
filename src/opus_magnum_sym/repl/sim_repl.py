import os
import shlex
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import CompleteEvent, Completer, Completion, PathCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.components import ComponentType
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

        history_path = Path.home() / ".cache" / "opus_magnum_sym" / "repl_history"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        self.session = PromptSession(
            history=FileHistory(str(history_path)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=ReplCompleter(self),
        )

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
            "history": self._history,
            "h": self._history,
            "edit": self._edit,
            "e": self._edit,
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

    def _history(self, args: list[str]) -> None:
        n = 20
        if args:
            try:
                n = int(args[0])
            except ValueError:
                print(f"Invalid count: {args[0]}")
                return

        entries = self.session.history.get_strings()
        for line in entries[-n:] if n > 0 else entries:
            print(line)

    def _reset(self, args: list[str]) -> None:
        self.sim.reset()
        print("Board cleared")

    def _save(self, args: list[str]) -> None:
        path = Path(args[0]) if args else Path("solution.oms")
        path.write_text(self._serialize())
        print(f"Saved to {path}")

    def _serialize(self) -> str:
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
                    "  !history [n]      show last n commands (default 20)",
                    "  !edit             edit current solution in $EDITOR and reload",
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


class ReplCompleter(Completer):
    def __init__(self, repl: SimREPL) -> None:
        self.repl = repl
        self.path_completer = PathCompleter()

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        stripped = document.text_before_cursor.lstrip()
        if not stripped:
            return

        if stripped[0] in "!:":
            yield from self._complete_meta(stripped[0], stripped[1:], complete_event)
        else:
            yield from self._complete_dsl(stripped)

    def _complete_meta(self, prefix: str, body: str, complete_event: CompleteEvent) -> Iterable[Completion]:
        tokens, word = self._parse(body)
        if not tokens:
            lw = word.lower()
            for name in sorted(self.repl.meta):
                if name.startswith(lw):
                    yield Completion(prefix + name, start_position=-(len(word) + 1))
            return

        if tokens[0].lower() in {"load", "r", "save", "w"} and len(tokens) == 1:
            yield from self.path_completer.get_completions(Document(word, len(word)), complete_event)

    def _complete_dsl(self, text: str) -> Iterable[Completion]:
        tokens, word = self._parse(text)
        lw = word.lower()
        if not tokens:
            for name in sorted(self.repl.interpreter.dispatch):
                if name.startswith(lw):
                    yield Completion(name, start_position=-len(word))
            return

        cmd, arg_index = tokens[0].lower(), len(tokens) - 1
        candidates: Iterable[str] = ()
        if cmd in {"comp", "c"} and arg_index == 2:
            candidates = [t.name.lower() for t in ComponentType if t != ComponentType.EMPTY]
        elif cmd in {"action", "a"}:
            if arg_index == 0:
                candidates = self._component_ids()
            elif arg_index == 2:
                candidates = [a.name.lower() for a in StepActionType]
        elif cmd in {"remove", "rm"} and arg_index == 0:
            candidates = self._component_ids()

        for cand in candidates:
            if cand.startswith(lw):
                yield Completion(cand, start_position=-len(word))

    def _component_ids(self) -> list[str]:
        components = {**self.repl.sim.entrypoints, **self.repl.sim.components}
        return [str(idx) for idx in sorted(components)]

    @staticmethod
    def _parse(text: str) -> tuple[list[str], str]:
        """Split into completed tokens and the current (possibly empty) partial word."""
        if not text or text[-1] in " \t":
            return text.split(), ""
        tokens = text.split()
        return tokens[:-1], tokens[-1]
