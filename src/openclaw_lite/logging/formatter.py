"""Custom structlog processor that wraps log messages in box-drawn sections."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from openclaw_lite.logging.categories import RESET, LogCategory

# Patterns for sensitive data that must never appear in logs
_SENSITIVE_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9]{20,})", re.IGNORECASE),
    re.compile(r"(Bearer\s+[a-zA-Z0-9._\-]+)", re.IGNORECASE),
    re.compile(r"(api[_-]?key\s*[:=]\s*\S+)", re.IGNORECASE),
    re.compile(r"(password\s*[:=]\s*\S+)", re.IGNORECASE),
]

BOX_WIDTH = 78


def _redact_sensitive(text: str) -> str:
    """Replace sensitive patterns with [REDACTED]."""
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _wrap_lines(text: str, width: int) -> list[str]:
    """Soft-wrap text to fit within box width."""
    lines: list[str] = []
    for raw_line in text.split("\n"):
        while len(raw_line) > width:
            lines.append(raw_line[:width])
            raw_line = raw_line[width:]
        lines.append(raw_line)
    return lines


def box_format(
    category: LogCategory,
    message: str,
    *,
    correlation_id: str = "",
    module: str = "",
    level: str = "INFO",
    extra: dict[str, Any] | None = None,
) -> str:
    """Format a log message inside a category-specific box.

    Returns a multi-line string with box-drawing characters, header,
    and optional metadata.
    """
    style = category.style
    color = style.color
    border = style.border_char
    inner_width = BOX_WIDTH - 4  # account for "┃ " prefix and " ┃" suffix

    now = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
    header_parts = [f"{style.emoji} {style.label}"]
    if correlation_id:
        header_parts.append(f"[{correlation_id[:8]}]")
    header_parts.append(f"{now}")
    if module:
        header_parts.append(f"({module})")
    header_parts.append(f"[{level}]")
    header = " ".join(header_parts)

    # Redact sensitive data
    message = _redact_sensitive(message)

    lines: list[str] = []
    # Top border
    lines.append(f"{color}\u250f{border * (BOX_WIDTH - 2)}\u2513{RESET}")
    # Header line
    padded_header = header.ljust(inner_width)[:inner_width]
    lines.append(f"{color}\u2503{RESET} {padded_header} {color}\u2503{RESET}")
    # Separator
    lines.append(f"{color}\u2520{'─' * (BOX_WIDTH - 2)}\u2528{RESET}")
    # Message lines
    for msg_line in _wrap_lines(message, inner_width):
        padded = msg_line.ljust(inner_width)[:inner_width]
        lines.append(f"{color}\u2503{RESET} {padded} {color}\u2503{RESET}")
    # Extra fields
    if extra:
        lines.append(
            f"{color}\u2520{'─' * (BOX_WIDTH - 2)}\u2528{RESET}"
        )
        for key, value in extra.items():
            kv = f"{key}: {value}"
            kv = _redact_sensitive(kv)
            padded = kv.ljust(inner_width)[:inner_width]
            lines.append(
                f"{color}\u2503{RESET} {padded} {color}\u2503{RESET}"
            )
    # Bottom border
    lines.append(f"{color}\u2517{border * (BOX_WIDTH - 2)}\u251b{RESET}")

    return "\n".join(lines)


def structlog_box_processor(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that formats events using box drawing.

    Expected keys in *event_dict*:

    - ``category`` (:class:`LogCategory`): determines visual style.
    - ``correlation_id`` (str, optional): request-scoped trace ID.
    - ``module`` (str, optional): originating module name.

    If ``category`` is absent the event passes through unmodified.
    """
    category = event_dict.pop("category", None)
    if category is None:
        return event_dict

    correlation_id = event_dict.pop("correlation_id", "")
    module = event_dict.pop("module", "")
    message = event_dict.get("event", "")
    level = method_name.upper()

    # Collect remaining keys as extra
    skip_keys = {"event", "_record", "_from_structlog", "timestamp"}
    extra = {
        k: v for k, v in event_dict.items() if k not in skip_keys
    }

    formatted = box_format(
        category,
        str(message),
        correlation_id=correlation_id,
        module=module,
        level=level,
        extra=extra if extra else None,
    )
    event_dict["event"] = formatted
    return event_dict
