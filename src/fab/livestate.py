"""Live state: the mutable per-workstream view built by merging state packets."""

from __future__ import annotations

from typing import Any

from fab.util import append_unique

# Packet list fields and the live-state list they accumulate into.
PACKET_LIST_FIELDS = (
    ("blockers", "blockers"),
    ("limitations", "limitations"),
    ("deviations", "deviations"),
    ("flags", "flags"),
    ("artifacts", "artifacts"),
)

# Packet scalar fields that append a single entry to a live-state list.
PACKET_SCALAR_FIELDS = (
    ("tried", "experiments"),
    ("result", "results"),
    ("failed", "failed_attempts"),
)


def empty_live_state(workstream_id: str, state_id: str) -> dict[str, Any]:
    return {
        "id": state_id,
        "workstream_id": workstream_id,
        "current_hypothesis": None,
        "current_plan": None,
        "experiments": [],
        "results": [],
        "failed_attempts": [],
        "blockers": [],
        "limitations": [],
        "deviations": [],
        "resource_usage": {},
        "next_intended_action": None,
        "rationale": None,
        "flags": [],
        "artifacts": [],
        "updated_at": None,
    }


def merge_packet_into_live_state(live_state: dict[str, Any], packet: dict[str, Any]) -> None:
    """Fold one packet into the live state in place.

    Lists accumulate without duplicates; ``next_action`` and ``rationale``
    replace the current values because they describe the present intent.
    """
    for packet_field, state_field in PACKET_SCALAR_FIELDS:
        if packet.get(packet_field):
            append_unique(live_state.setdefault(state_field, []), [packet[packet_field]])
    for packet_field, state_field in PACKET_LIST_FIELDS:
        if packet.get(packet_field):
            append_unique(live_state.setdefault(state_field, []), packet[packet_field])
    if packet.get("next_action"):
        live_state["next_intended_action"] = packet["next_action"]
    if packet.get("rationale"):
        live_state["rationale"] = packet["rationale"]
    live_state["updated_at"] = packet["created_at"]
