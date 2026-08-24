"""Workstream lifecycle: statuses, allowed transitions, and judgment actions."""

from __future__ import annotations

from typing import Any

from fab.artifacts import artifact_target_exists, claim_target_exists
from fab.errors import RegistryError

VALID_STATUSES = frozenset(
    {
        "planned",
        "running",
        "paused",
        "stopped",
        "completed",
        "quarantined",
    }
)
TERMINAL_STATUSES = frozenset({"stopped", "completed"})

# Allowed lifecycle moves. Terminal statuses have no exits; a human can still
# correct a mistake with ``RegistryStore.set_status(..., force=True)``.
STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "planned": frozenset({"running", "paused", "stopped", "quarantined"}),
    "running": frozenset({"paused", "stopped", "completed", "quarantined"}),
    "paused": frozenset({"running", "stopped", "completed", "quarantined"}),
    "quarantined": frozenset({"running", "paused", "stopped"}),
    "stopped": frozenset(),
    "completed": frozenset(),
}

VALID_DECISION_TARGET_TYPES = frozenset({"workstream", "artifact", "claim"})

# Judgment actions that move a workstream's lifecycle status.
STATUS_FOR_ACTION = {
    "continue": "running",
    "pause": "paused",
    "stop": "stopped",
    "complete": "completed",
    "quarantine": "quarantined",
}

# Judgment actions that only record a verdict about the target.
VERDICT_ACTIONS = frozenset(
    {
        "merge",
        "split",
        "replicate",
        "escalate",
        "promote",
        "trust-local",
        "reject",
        "needs-replication",
        "needs-critique",
        "do-not-propagate",
        "safe-as-context",
    }
)

VALID_DECISION_ACTIONS = frozenset(STATUS_FOR_ACTION) | VERDICT_ACTIONS


def ensure_status(status: Any) -> None:
    if status not in VALID_STATUSES:
        raise RegistryError(f"invalid status: {status}")


def ensure_decision_action(action: str) -> None:
    if action not in VALID_DECISION_ACTIONS:
        valid = ", ".join(sorted(VALID_DECISION_ACTIONS))
        raise RegistryError(f"invalid judgment action: {action}; valid: {valid}")


def status_after_for_action(action: str, status_before: str | None) -> str | None:
    return STATUS_FOR_ACTION.get(action, status_before)


def ensure_status_transition(status_before: str | None, status_after: str | None) -> None:
    """Raise unless ``status_before -> status_after`` is an allowed lifecycle move.

    Staying in the same status is always allowed so repeated judgments are
    idempotent.
    """
    if status_before == status_after:
        return
    if status_before not in STATUS_TRANSITIONS:
        raise RegistryError(f"invalid status: {status_before}")
    allowed = STATUS_TRANSITIONS[status_before]
    if status_after in allowed:
        return
    if allowed:
        detail = f"allowed: {', '.join(sorted(allowed))}"
    else:
        detail = f"{status_before} is terminal"
    raise RegistryError(
        f"invalid status transition: {status_before} -> {status_after}; {detail}"
    )


def normalize_decision_target(
    live_state: dict[str, Any],
    workstream_id: str,
    target_type: str,
    target_id: str | None,
) -> dict[str, str]:
    if target_type not in VALID_DECISION_TARGET_TYPES:
        valid = ", ".join(sorted(VALID_DECISION_TARGET_TYPES))
        raise RegistryError(f"invalid judgment target type: {target_type}; valid: {valid}")
    if target_type == "workstream":
        if target_id and target_id != workstream_id:
            raise RegistryError(f"workstream judgment target must be {workstream_id}")
        return {"type": "workstream", "id": target_id or workstream_id}
    if not target_id:
        raise RegistryError(f"target id is required for {target_type} judgment")
    if target_type == "artifact" and not artifact_target_exists(live_state, target_id):
        raise RegistryError(f"artifact target not found: {target_id}")
    if target_type == "claim" and not claim_target_exists(live_state, target_id):
        raise RegistryError(f"claim target not found: {target_id}")
    return {"type": target_type, "id": target_id}
