"""
Minimal stdout-only logging for simulation and REPL.
"""

import logging


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
        if self._pretty:
            formatted = msg % args if args else msg
            pretty = self._format_pretty(formatted)
            getattr(self._logger, level)(pretty, **kwargs)
        else:
            getattr(self._logger, level)(msg, *args, **kwargs)

    def _format_pretty(self, msg: str) -> str:
        # "<verb> <subject> @ (r, s)"
        if " @ " not in msg:
            return msg
        head, pos = msg.split(" @ ", 1)
        parts = head.split()
        if len(parts) < 2:
            return msg
        verb = parts[0]
        subject = " ".join(parts[1:])

        prefix = ""
        if verb == "placed":
            self._seen_placed = True
        elif self._seen_placed and not self._setup_separator_printed:
            prefix = "\n" + "-" * 30 + "\n"
            self._setup_separator_printed = True

        return f"{prefix}{verb:>10}  {subject:<10}  @ {pos}"


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
