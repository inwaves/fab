from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_STATUSES = {
    "planned",
    "running",
    "paused",
    "stopped",
    "completed",
    "quarantined",
}

RELATIONSHIP_LIST_FIELDS = {"children", "related", "blocks", "blocked_by"}


class RegistryError(Exception):
    """Raised when a registry operation cannot be completed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$")
    highest = 0
    for item in existing:
        match = pattern.match(item)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}_{highest + 1:03d}"


@dataclass(frozen=True)
class RegistryStore:
    root: Path

    @classmethod
    def at(cls, root: Path | str) -> "RegistryStore":
        return cls(Path(root))

    @property
    def workstreams_dir(self) -> Path:
        return self.root / "workstreams"

    @property
    def live_state_dir(self) -> Path:
        return self.root / "live-state"

    @property
    def packets_dir(self) -> Path:
        return self.root / "state-packets"

    @property
    def decisions_dir(self) -> Path:
        return self.root / "decisions"

    @property
    def contracts_dir(self) -> Path:
        return self.root / "contracts"

    def init(self) -> None:
        for path in [
            self.workstreams_dir,
            self.live_state_dir,
            self.packets_dir,
            self.decisions_dir,
            self.contracts_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def workstream_path(self, workstream_id: str) -> Path:
        return self.workstreams_dir / f"{workstream_id}.json"

    def live_state_path(self, workstream_id: str) -> Path:
        return self.live_state_dir / f"{workstream_id}.json"

    def packet_path(self, workstream_id: str, packet_id: str) -> Path:
        return self.packets_dir / workstream_id / f"{packet_id}.json"

    def decision_path(self, workstream_id: str, decision_id: str) -> Path:
        return self.decisions_dir / workstream_id / f"{decision_id}.json"

    def existing_workstream_ids(self) -> list[str]:
        if not self.workstreams_dir.exists():
            return []
        return sorted(path.stem for path in self.workstreams_dir.glob("*.json"))

    def ensure_ready(self) -> None:
        if not self.workstreams_dir.exists():
            raise RegistryError(f"registry is not initialized: {self.root}")

    def create_workstream(
        self,
        *,
        title: str,
        program: str,
        owner: str | None = None,
        workstream_id: str | None = None,
        status: str = "planned",
        contract_id: str | None = None,
        contract_version: int | None = None,
        artifact_root: str | None = None,
        next_review_due_at: str | None = None,
    ) -> dict[str, Any]:
        self.init()
        if status not in VALID_STATUSES:
            raise RegistryError(f"invalid status: {status}")

        existing = self.existing_workstream_ids()
        workstream_id = workstream_id or compact_id("ws", existing)
        if workstream_id in existing:
            raise RegistryError(f"workstream already exists: {workstream_id}")

        now = utc_now()
        entry = {
            "id": workstream_id,
            "title": title,
            "program": program,
            "human_owner": owner,
            "status": status,
            "contract": {
                "id": contract_id,
                "version": contract_version,
            },
            "live_state": {
                "id": f"state_{workstream_id}",
                "updated_at": None,
            },
            "links": {
                "artifact_root": artifact_root,
                "decision_log": str(Path("decisions") / workstream_id),
                "run_index": None,
            },
            "relationships": {
                "parent": None,
                "children": [],
                "related": [],
                "blocks": [],
                "blocked_by": [],
            },
            "visibility": {
                "reusable_by_other_workstreams": False,
                "requires_review_before_sharing": True,
            },
            "timestamps": {
                "created_at": now,
                "updated_at": now,
                "last_state_update_at": None,
                "next_review_due_at": next_review_due_at,
            },
            "metadata": {},
        }
        live_state = empty_live_state(workstream_id, entry["live_state"]["id"])
        write_json(self.workstream_path(workstream_id), entry)
        write_json(self.live_state_path(workstream_id), live_state)
        return entry

    def get_workstream(self, workstream_id: str) -> dict[str, Any]:
        self.ensure_ready()
        return read_json(self.workstream_path(workstream_id))

    def save_workstream(self, entry: dict[str, Any]) -> dict[str, Any]:
        entry.setdefault("timestamps", {})["updated_at"] = utc_now()
        write_json(self.workstream_path(entry["id"]), entry)
        return entry

    def list_workstreams(
        self,
        *,
        status: str | None = None,
        program: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_ready()
        items = [read_json(path) for path in sorted(self.workstreams_dir.glob("*.json"))]
        if status:
            items = [item for item in items if item.get("status") == status]
        if program:
            items = [item for item in items if item.get("program") == program]
        return items

    def get_live_state(self, workstream_id: str) -> dict[str, Any]:
        self.ensure_ready()
        return read_json(self.live_state_path(workstream_id))

    def show(self, workstream_id: str) -> dict[str, Any]:
        entry = self.get_workstream(workstream_id)
        return {
            "workstream": entry,
            "live_state": self.get_live_state(workstream_id),
            "recent_packets": self.list_packets(workstream_id)[-5:],
            "recent_decisions": self.list_decisions(workstream_id)[-5:],
        }

    def set_status(self, workstream_id: str, status: str) -> dict[str, Any]:
        if status not in VALID_STATUSES:
            raise RegistryError(f"invalid status: {status}")
        entry = self.get_workstream(workstream_id)
        entry["status"] = status
        return self.save_workstream(entry)

    def attach_contract(
        self,
        workstream_id: str,
        *,
        contract_id: str,
        version: int | None = None,
    ) -> dict[str, Any]:
        entry = self.get_workstream(workstream_id)
        entry["contract"] = {"id": contract_id, "version": version}
        return self.save_workstream(entry)

    def link_workstreams(
        self,
        workstream_id: str,
        target_id: str,
        *,
        relationship: str = "related",
    ) -> dict[str, Any]:
        if workstream_id == target_id:
            raise RegistryError("cannot link a workstream to itself")
        entry = self.get_workstream(workstream_id)
        self.get_workstream(target_id)

        relationships = entry.setdefault("relationships", {})
        if relationship == "parent":
            relationships["parent"] = target_id
        elif relationship in RELATIONSHIP_LIST_FIELDS:
            values = relationships.setdefault(relationship, [])
            if target_id not in values:
                values.append(target_id)
        else:
            valid = ", ".join(sorted(RELATIONSHIP_LIST_FIELDS | {"parent"}))
            raise RegistryError(f"invalid relationship: {relationship}; valid: {valid}")
        return self.save_workstream(entry)

    def add_state_packet(
        self,
        workstream_id: str,
        *,
        source: str,
        changed: str | None = None,
        tried: str | None = None,
        failed: str | None = None,
        result: str | None = None,
        next_action: str | None = None,
        continue_reason: str | None = None,
        blocker: list[str] | None = None,
        deviation: list[str] | None = None,
        flag: list[str] | None = None,
        artifact: list[str] | None = None,
    ) -> dict[str, Any]:
        entry = self.get_workstream(workstream_id)
        existing_packets = [path.stem for path in (self.packets_dir / workstream_id).glob("*.json")]
        packet_id = compact_id("pkt", existing_packets)
        now = utc_now()
        packet = {
            "id": packet_id,
            "workstream_id": workstream_id,
            "created_at": now,
            "source": source,
            "changed": changed,
            "tried": tried,
            "failed": failed,
            "result": result,
            "next_action": next_action,
            "reason_for_continuing": continue_reason,
            "blockers": blocker or [],
            "deviations": deviation or [],
            "flags": flag or [],
            "artifacts": artifact or [],
        }
        write_json(self.packet_path(workstream_id, packet_id), packet)

        live_state = self.get_live_state(workstream_id)
        merge_packet_into_live_state(live_state, packet)
        write_json(self.live_state_path(workstream_id), live_state)

        entry["live_state"]["updated_at"] = now
        entry["timestamps"]["last_state_update_at"] = now
        self.save_workstream(entry)
        return packet

    def list_packets(self, workstream_id: str) -> list[dict[str, Any]]:
        packet_dir = self.packets_dir / workstream_id
        if not packet_dir.exists():
            return []
        return [read_json(path) for path in sorted(packet_dir.glob("*.json"))]

    def add_decision(
        self,
        workstream_id: str,
        *,
        action: str,
        rationale: str,
        actor: str | None = None,
    ) -> dict[str, Any]:
        entry = self.get_workstream(workstream_id)
        existing_decisions = [path.stem for path in (self.decisions_dir / workstream_id).glob("*.json")]
        decision_id = compact_id("dec", existing_decisions)
        status_before = entry.get("status")
        status_after = status_after_for_action(action, status_before)
        if status_after != status_before:
            entry["status"] = status_after
            self.save_workstream(entry)

        decision = {
            "id": decision_id,
            "workstream_id": workstream_id,
            "created_at": utc_now(),
            "actor": actor,
            "action": action,
            "rationale": rationale,
            "status_before": status_before,
            "status_after": status_after,
        }
        write_json(self.decision_path(workstream_id, decision_id), decision)
        return decision

    def list_decisions(self, workstream_id: str) -> list[dict[str, Any]]:
        decision_dir = self.decisions_dir / workstream_id
        if not decision_dir.exists():
            return []
        return [read_json(path) for path in sorted(decision_dir.glob("*.json"))]


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
        "deviations": [],
        "resource_usage": {},
        "next_intended_action": None,
        "reason_for_continuing": None,
        "flags": [],
        "artifacts": [],
        "updated_at": None,
    }


def append_unique(values: list[Any], new_values: list[Any]) -> None:
    for value in new_values:
        if value and value not in values:
            values.append(value)


def merge_packet_into_live_state(live_state: dict[str, Any], packet: dict[str, Any]) -> None:
    if packet.get("tried"):
        append_unique(live_state.setdefault("experiments", []), [packet["tried"]])
    if packet.get("result"):
        append_unique(live_state.setdefault("results", []), [packet["result"]])
    if packet.get("failed"):
        append_unique(live_state.setdefault("failed_attempts", []), [packet["failed"]])
    if packet.get("blockers"):
        append_unique(live_state.setdefault("blockers", []), packet["blockers"])
    if packet.get("deviations"):
        append_unique(live_state.setdefault("deviations", []), packet["deviations"])
    if packet.get("flags"):
        append_unique(live_state.setdefault("flags", []), packet["flags"])
    if packet.get("artifacts"):
        append_unique(live_state.setdefault("artifacts", []), packet["artifacts"])
    if packet.get("next_action"):
        live_state["next_intended_action"] = packet["next_action"]
    if packet.get("reason_for_continuing"):
        live_state["reason_for_continuing"] = packet["reason_for_continuing"]
    live_state["updated_at"] = packet["created_at"]


def status_after_for_action(action: str, status_before: str | None) -> str | None:
    if action == "continue":
        return "running"
    if action == "pause":
        return "paused"
    if action == "stop":
        return "stopped"
    if action == "complete":
        return "completed"
    if action == "quarantine":
        return "quarantined"
    return status_before
