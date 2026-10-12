"""
Minimal stdout-only logging for both simulation and REPL.
"""

import logging

logger = logging.getLogger("opus_magnum_sym")


def conf_logger(level: int = logging.INFO) -> None:
    """
    Set up logger.
    Pass `level` to change verbosity.
    """
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.propagate = False
