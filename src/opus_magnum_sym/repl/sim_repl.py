from collections.abc import Iterable
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import (
    CompleteEvent,
    Completer,
    Completion,
    PathCompleter,
)
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory

from opus_magnum_sym.elements.actions.actions import StepActionType
from opus_magnum_sym.elements.components import ComponentType
from opus_magnum_sym.interpreter import SimInterpreter
from opus_magnum_sym.render.null_renderer import NullRenderer
from opus_magnum_sym.render.renderer import BoardRenderer
from opus_magnum_sym.repl.meta import MetaInterpreter
from opus_magnum_sym.simulation.simulator import Simulator


class SimREPL:
    def __init__(
        self,
        sim: Simulator,
        renderer: BoardRenderer | NullRenderer,
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

        self.meta = MetaInterpreter(self)
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
        self.meta.evaluate(line)

    def _refresh(self) -> None:
        if not self.renderer.process_events():
            self.running = False
            return
        self.renderer.draw()


class ReplCompleter(Completer):
    def __init__(self, repl: SimREPL) -> None:
        self.repl = repl
        self.path_completer = PathCompleter()

    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]:
        stripped = document.text_before_cursor.lstrip()
        if not stripped:
            return

        if stripped[0] in "!:":
            yield from self._complete_meta(stripped[0], stripped[1:], complete_event)
        else:
            yield from self._complete_dsl(stripped)

    def _complete_meta(
        self,
        prefix: str,
        body: str,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]:
        tokens, word = self._parse(body)
        if not tokens:
            lw = word.lower()
            for name in self.repl.meta.command_names():
                if name.startswith(lw):
                    yield Completion(prefix + name, start_position=-(len(word) + 1))
            return

        if tokens[0].lower() in self.repl.meta.path_commands and len(tokens) == 1:
            yield from self.path_completer.get_completions(
                Document(word, len(word)),
                complete_event,
            )

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
        elif cmd == "target" and arg_index >= 1:
            candidates = self._exit_ids()

        for cand in candidates:
            if cand.startswith(lw):
                yield Completion(cand, start_position=-len(word))

    def _component_ids(self) -> list[str]:
        components = {**self.repl.sim.entrypoints, **self.repl.sim.components}
        return [str(idx) for idx in sorted(components)]

    def _exit_ids(self) -> list[str]:
        return [str(idx) for idx, comp in sorted(self.repl.sim.entrypoints.items()) if comp.type == ComponentType.EXIT]

    @staticmethod
    def _parse(text: str) -> tuple[list[str], str]:
        """
        Split into completed tokens and current partial word.
        """
        if not text or text[-1] in " \t":
            return text.split(), ""
        tokens = text.split()
        return tokens[:-1], tokens[-1]
