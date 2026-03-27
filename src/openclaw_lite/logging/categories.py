"""Log category definitions with visual formatting styles."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class CategoryStyle:
    """Visual formatting configuration for a log category."""
    emoji: str
    label: str
    border_char: str
    color: str  # ANSI color code


class LogCategory(Enum):
    """Log categories with distinct visual styles."""

    REASONING = CategoryStyle(
        emoji="\U0001f9e0",  # brain
        label="REASONING",
        border_char="\u2501",  # ━
        color="\033[36m",     # cyan
    )
    TOOL_CALL = CategoryStyle(
        emoji="\U0001f527",  # wrench
        label="TOOL CALL",
        border_char="\u2500",  # ─
        color="\033[33m",     # yellow
    )
    TASK_UPDATE = CategoryStyle(
        emoji="\u2705",       # check mark
        label="TASK UPDATE",
        border_char="\u2500",  # ─
        color="\033[32m",     # green
    )
    FINAL_ANSWER = CategoryStyle(
        emoji="\U0001f4ac",  # speech balloon
        label="FINAL ANSWER",
        border_char="\u2501",  # ━
        color="\033[35m",     # magenta
    )
    MEMORY = CategoryStyle(
        emoji="\U0001f4be",  # floppy disk
        label="MEMORY",
        border_char="\u2500",  # ─
        color="\033[34m",     # blue
    )
    SYSTEM = CategoryStyle(
        emoji="\u2699\ufe0f",  # gear
        label="SYSTEM",
        border_char="\u2500",  # ─
        color="\033[37m",     # white
    )

    @property
    def style(self) -> CategoryStyle:
        return self.value


RESET = "\033[0m"
