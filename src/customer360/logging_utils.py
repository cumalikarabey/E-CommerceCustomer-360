from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import TextIO


ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_COLORS = {
    "grey": "\033[90m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
}


def _supports_color(stream: TextIO) -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    return hasattr(stream, "isatty") and stream.isatty()


def colorize(text: str, color: str, enabled: bool, bold: bool = False) -> str:
    if not enabled:
        return text
    prefix = ANSI_COLORS.get(color, "")
    if bold:
        prefix = ANSI_BOLD + prefix
    return f"{prefix}{text}{ANSI_RESET}"


class Customer360Formatter(logging.Formatter):
    LEVEL_COLORS = {
        "DEBUG": "grey",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red",
    }

    def __init__(self, use_color: bool) -> None:
        super().__init__(fmt="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        original_level = record.levelname
        level_color = self.LEVEL_COLORS.get(original_level, "blue")
        record.levelname = colorize(original_level, level_color, self.use_color, bold=True)
        try:
            return super().format(record)
        finally:
            record.levelname = original_level


def configure_logging(verbose: bool = True, use_color: bool | None = None) -> logging.Logger:
    logger = logging.getLogger("customer360")
    logger.handlers.clear()
    logger.propagate = False

    handler = logging.StreamHandler(stream=sys.stdout)
    color_enabled = _supports_color(handler.stream) if use_color is None else use_color
    handler.setFormatter(Customer360Formatter(use_color=color_enabled))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO if verbose else logging.WARNING)
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("customer360")


def logger_uses_color(logger: logging.Logger) -> bool:
    for handler in logger.handlers:
        formatter = handler.formatter
        if hasattr(formatter, "use_color"):
            return bool(getattr(formatter, "use_color"))
    return False


@dataclass
class StepLogger:
    logger: logging.Logger
    total_steps: int
    use_color: bool = False
    current_step: int = 0

    def next(self, title: str) -> None:
        self.current_step += 1
        step_prefix = f"[STEP {self.current_step}/{self.total_steps}]"
        step_prefix = colorize(step_prefix, "cyan", self.use_color, bold=True)
        self.logger.info("%s %s", step_prefix, title)

