"""Small helpers shared across the registry: time, JSON I/O, identifiers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fab.errors import RegistryError

SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
DATE_ONLY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def current_time() -> datetime:
    """Return the current UTC time truncated to whole seconds."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def format_datetime(value: datetime) -> str:
    """Render an aware datetime as a compact UTC ISO-8601 string (``...Z``)."""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_now() -> str:
    return format_datetime(current_time())


def parse_datetime(value: str) -> datetime:
    """Parse a date or ISO-8601 datetime; naive values are treated as UTC."""
    raw = value.strip()
    if not raw:
        raise RegistryError("empty datetime")
    if DATE_ONLY_RE.fullmatch(raw):
        return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise RegistryError(f"invalid datetime: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compact_id(prefix: str, existing: list[str]) -> str:
    """Return ``<prefix>_NNN`` one past the highest existing number."""
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$")
    highest = 0
    for item in existing:
        match = pattern.match(item)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}_{highest + 1:03d}"


def ensure_safe_id(kind: str, value: Any) -> None:
    """Reject identifiers that could escape their directory when used as a path segment."""
    if not isinstance(value, str) or not SAFE_ID_RE.fullmatch(value):
        raise RegistryError(f"invalid {kind}: {value}")


def normalize_string_list(value: Any, *, label: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise RegistryError(f"{label} must be a list")
    return [str(item) for item in value if item]


def append_unique(values: list[Any], new_values: list[Any]) -> None:
    for value in new_values:
        if value and value not in values:
            values.append(value)
