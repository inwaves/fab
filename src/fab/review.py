"""Attention rules: which workstreams need a human to look at them, and why."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from fab.errors import RegistryError
from fab.status import TERMINAL_STATUSES
from fab.util import current_time, format_datetime, parse_datetime

if TYPE_CHECKING:
    from fab.store import RegistryStore

DEFAULT_STALE_DAYS = 7

REVIEW_REASONS = frozenset(
    {
        "no_contract",
        "missing_contract_file",
        "no_state_packet",
        "missing_rationale",
        "blocked",
        "limited",
        "flagged",
        "deviated",
        "review_due",
        "stale",
        "paused",
        "quarantined",
        "invalid_review_due_at",
        "invalid_last_state_update_at",
        "invalid_contract_pointer",
    }
)

# Live-state list fields that raise an attention reason when non-empty.
LIVE_STATE_REASONS = (
    ("blockers", "blocked"),
    ("limitations", "limited"),
    ("flags", "flagged"),
    ("deviations", "deviated"),
)


def ensure_stale_days(stale_days: int) -> None:
    if stale_days < 1:
        raise RegistryError(f"invalid stale days: {stale_days}")


def ensure_review_reason(reason: str | None) -> None:
    if reason is not None and reason not in REVIEW_REASONS:
        valid = ", ".join(sorted(REVIEW_REASONS))
        raise RegistryError(f"invalid review reason: {reason}; valid: {valid}")


def attached_contract_summary(store: RegistryStore, entry: dict[str, Any]) -> dict[str, Any] | None:
    contract = entry.get("contract") or {}
    contract_id = contract.get("id")
    version = contract.get("version")
    if not contract_id or version is None:
        return None

    path = store.contract_version_path(contract_id, version)
    summary = {
        "id": contract_id,
        "version": version,
        "path": str(path),
        "exists": path.is_file(),
    }
    if path.is_file():
        summary["text"] = path.read_text(encoding="utf-8")
    return summary


def review_summary(
    store: RegistryStore,
    entry: dict[str, Any],
    live_state: dict[str, Any],
    packets: list[dict[str, Any]],
    *,
    stale_days: int = DEFAULT_STALE_DAYS,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or current_time()
    reasons = review_reasons(store, entry, live_state, packets, stale_days=stale_days, now=now)
    return {
        "reasons": reasons,
        "stale_days": stale_days,
        "reviewed_at": format_datetime(now),
    }


def review_reasons(
    store: RegistryStore,
    entry: dict[str, Any],
    live_state: dict[str, Any],
    packets: list[dict[str, Any]],
    *,
    stale_days: int,
    now: datetime,
) -> list[str]:
    reasons: list[str] = []
    status = entry.get("status")
    timestamps = entry.get("timestamps", {})

    due_at = timestamps.get("next_review_due_at")
    if due_at:
        try:
            if parse_datetime(due_at) <= now:
                reasons.append("review_due")
        except RegistryError:
            reasons.append("invalid_review_due_at")

    if status == "paused":
        reasons.append("paused")
    if status == "quarantined":
        reasons.append("quarantined")

    if status in TERMINAL_STATUSES:
        return reasons

    reasons.extend(contract_reasons(store, entry))

    if not packets:
        reasons.append("no_state_packet")
    if not live_state.get("rationale"):
        reasons.append("missing_rationale")
    for field, reason in LIVE_STATE_REASONS:
        if live_state.get(field):
            reasons.append(reason)

    last_state_update_at = timestamps.get("last_state_update_at")
    if last_state_update_at:
        try:
            threshold = now - timedelta(days=stale_days)
            if parse_datetime(last_state_update_at) <= threshold:
                reasons.append("stale")
        except RegistryError:
            reasons.append("invalid_last_state_update_at")

    return reasons


def contract_reasons(store: RegistryStore, entry: dict[str, Any]) -> list[str]:
    contract = entry.get("contract") or {}
    contract_id = contract.get("id")
    contract_version = contract.get("version")
    if not contract_id or contract_version is None:
        return ["no_contract"]
    try:
        contract_path = store.contract_version_path(contract_id, contract_version)
    except RegistryError:
        return ["invalid_contract_pointer"]
    if not contract_path.is_file():
        return ["missing_contract_file"]
    return []


def attention_items(
    store: RegistryStore,
    *,
    status: str | None = None,
    program: str | None = None,
    reason: str | None = None,
    stale_days: int = DEFAULT_STALE_DAYS,
    include_clear: bool = False,
) -> list[dict[str, Any]]:
    """Workstreams with attention reasons, plus a slice of live state for context."""
    ensure_review_reason(reason)
    ensure_stale_days(stale_days)

    items = []
    for entry in store.list_workstreams(status=status, program=program):
        live_state = store.get_live_state(entry["id"])
        packets = store.list_packets(entry["id"])
        review = review_summary(store, entry, live_state, packets, stale_days=stale_days)
        if reason and reason not in review["reasons"]:
            continue
        if not include_clear and not review["reasons"]:
            continue
        items.append(
            {
                "workstream": entry,
                "review": review,
                "live_state": {
                    "updated_at": live_state.get("updated_at"),
                    "next_intended_action": live_state.get("next_intended_action"),
                    "rationale": live_state.get("rationale"),
                },
            }
        )
    return items
