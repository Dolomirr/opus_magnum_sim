"""
Minimal stdout-only logging for simulation and REPL.
"""

import logging


_SOURCE_WIDTH = 11
_POS_WIDTH = 8
_VERB_WIDTH = 10
_SUBJECT_WIDTH = 10


class SimLogger:
    """
    Logger with optional pretty-print formatting.
    """

    _LEVELS = frozenset({"debug", "info", "warning", "error", "critical"})

    def __init__(self, logger: logging.Logger, pretty: bool = False) -> None:
        self._logger = logger
        self._pretty = pretty
        self._seen_placed = False
        self._setup_separator_printed = False

    def __getattr__(self, name: str):
        if name not in self._LEVELS:
            raise AttributeError(name)

        def method(msg: str, *args, **kwargs) -> None:
            self._emit(name, msg, args, kwargs)

        return method

    def _emit(self, level: str, msg: str, args: tuple, kwargs: dict) -> None:
        source = kwargs.pop("source", None)
        source_pos = kwargs.pop("source_pos", None)
        if self._pretty:
            formatted = msg % args if args else msg
            pretty = self._format_pretty(formatted, source, source_pos)
            getattr(self._logger, level)(pretty, **kwargs)
        else:
            getattr(self._logger, level)(msg, *args, **kwargs)

    def _format_pretty(self, msg: str, source: str | None, source_pos) -> str:
        # "<verb> <subject> @ (r, s)"
        if " @ " not in msg:
            return msg
        head, pos = msg.split(" @ ", 1)
        parts = head.split()
        if len(parts) < 2:
            return msg
        verb = parts[0]
        subject = " ".join(parts[1:])

        if verb == "placed":
            self._seen_placed = True
            src = source if source is not None else "simulator"
            src_pos = self._format_pos(source_pos) if source_pos is not None else self._format_pos(pos)
            return (
                f"{src:<{_SOURCE_WIDTH}}  @ {src_pos:<{_POS_WIDTH}}  |  "
                f"{verb:<{_VERB_WIDTH}}  {subject:<{_SUBJECT_WIDTH}}  @ {pos:<{_POS_WIDTH}}"
            )

        prefix = ""
        if self._seen_placed and not self._setup_separator_printed:
            prefix = self._setup_separator()
            self._setup_separator_printed = True

        src = source if source is not None else ""
        src_pos = self._format_pos(source_pos)
        return (
            f"{prefix}"
            f"{src:<{_SOURCE_WIDTH}}  @ {src_pos:<{_POS_WIDTH}}  |  "
            f"{verb:<{_VERB_WIDTH}}  {subject:<{_SUBJECT_WIDTH}}  @ {pos:<{_POS_WIDTH}}"
        )

    def _setup_separator(self) -> str:
        header = (
            f"{'source':<{_SOURCE_WIDTH}}  @ {'at':<{_POS_WIDTH}}  |  "
            f"{'action':<{_VERB_WIDTH}}  {'spec':<{_SUBJECT_WIDTH}}  @ {'at':<{_POS_WIDTH}}"
        )
        line = "-" * len(header)
        return f"\n{header}\n{line}\n"

    @staticmethod
    def _format_pos(pos) -> str:
        if pos is None:
            return ""
        if isinstance(pos, str):
            return pos
        if hasattr(pos, "r") and hasattr(pos, "s"):
            return f"({pos.r}, {pos.s})"
        return str(pos)


logger = SimLogger(logging.getLogger("opus_magnum_sym"), pretty=False)

_FORMATTER = logging.Formatter("%(message)s")


def configure_logging(pretty: bool = True, level: int = logging.INFO) -> None:
    """
    Single console handler.
    Pass `level` to set verbosity.
    """
    logger._pretty = pretty
    logger._seen_placed = False
    logger._setup_separator_printed = False
    logger._logger.setLevel(level)
    if not logger._logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_FORMATTER)
        logger._logger.addHandler(handler)
    logger._logger.propagate = False
