from __future__ import annotations

import json
import re
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
READ_ONLY_FILE_MODE = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
REVIEW_REASONS = {
    "no_contract",
    "missing_contract_file",
    "no_state_packet",
    "missing_rationale",
    "blocked",
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
TERMINAL_STATUSES = {"stopped", "completed"}
ARTIFACT_PROVENANCE_FIELDS = ("code", "datasets", "models", "prompts", "evals")


class RegistryError(Exception):
    """Raised when a registry operation cannot be completed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_datetime(value: str) -> datetime:
    raw = value.strip()
    if not raw:
        raise RegistryError("empty datetime")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
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
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$")
    highest = 0
    for item in existing:
        match = pattern.match(item)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}_{highest + 1:03d}"


def contract_version_filename(version: int) -> str:
    if version < 1:
        raise RegistryError(f"invalid contract version: {version}")
    return f"v{version:03d}.md"


def ensure_safe_id(kind: str, value: str) -> None:
    if not SAFE_ID_RE.fullmatch(value):
        raise RegistryError(f"invalid {kind}: {value}")


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

    def contract_version_path(self, contract_id: str, version: int) -> Path:
        ensure_safe_id("contract id", contract_id)
        return self.contracts_dir / contract_id / contract_version_filename(version)

    def existing_workstream_ids(self) -> list[str]:
        if not self.workstreams_dir.exists():
            return []
        return sorted(path.stem for path in self.workstreams_dir.glob("*.json"))

    def ensure_ready(self) -> None:
        if not self.workstreams_dir.exists():
            raise RegistryError(f"registry is not initialized: {self.root}")

    def ensure_contract_exists(self, contract_id: str, version: int | None) -> None:
        if version is None:
            raise RegistryError(f"contract version is required for {contract_id}")
        path = self.contract_version_path(contract_id, version)
        if not path.is_file():
            raise RegistryError(f"contract version not found: {path}")

    def lock_contract_version(self, contract_id: str, version: int | None) -> None:
        self.ensure_contract_exists(contract_id, version)
        path = self.contract_version_path(contract_id, version)
        path.chmod(READ_ONLY_FILE_MODE)

    def write_contract_version(self, contract_id: str, version: int, text: str) -> Path:
        self.init()
        path = self.contract_version_path(contract_id, version)
        if path.exists():
            raise RegistryError(f"contract version already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        path.chmod(READ_ONLY_FILE_MODE)
        return path

    def read_contract_version(self, contract_id: str, version: int) -> str:
        self.ensure_contract_exists(contract_id, version)
        return self.contract_version_path(contract_id, version).read_text(encoding="utf-8")

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
        if contract_id:
            self.lock_contract_version(contract_id, contract_version)
        elif contract_version is not None:
            raise RegistryError("contract version cannot be set without contract id")

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
        live_state = self.get_live_state(workstream_id)
        packets = self.list_packets(workstream_id)
        return {
            "workstream": entry,
            "attached_contract": attached_contract_summary(self, entry),
            "review": review_summary(self, entry, live_state, packets),
            "live_state": live_state,
            "recent_packets": packets[-5:],
            "recent_decisions": self.list_decisions(workstream_id)[-5:],
        }

    def review_workstreams(
        self,
        *,
        status: str | None = None,
        program: str | None = None,
        reason: str | None = None,
        stale_days: int = 7,
        include_clear: bool = False,
    ) -> list[dict[str, Any]]:
        self.ensure_ready()
        if reason is not None and reason not in REVIEW_REASONS:
            valid = ", ".join(sorted(REVIEW_REASONS))
            raise RegistryError(f"invalid review reason: {reason}; valid: {valid}")
        if stale_days < 1:
            raise RegistryError(f"invalid stale days: {stale_days}")

        items = []
        for entry in self.list_workstreams(status=status, program=program):
            live_state = self.get_live_state(entry["id"])
            packets = self.list_packets(entry["id"])
            review = review_summary(self, entry, live_state, packets, stale_days=stale_days)
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
        self.lock_contract_version(contract_id, version)
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
        rationale: str | None = None,
        blocker: list[str] | None = None,
        deviation: list[str] | None = None,
        flag: list[str] | None = None,
        artifact: list[str] | None = None,
        artifact_ref: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        entry = self.get_workstream(workstream_id)
        existing_packets = [path.stem for path in (self.packets_dir / workstream_id).glob("*.json")]
        packet_id = compact_id("pkt", existing_packets)
        now = utc_now()
        live_state = self.get_live_state(workstream_id)
        artifacts = normalize_artifact_refs(
            artifact,
            artifact_ref,
            source=source,
            created_at=now,
            existing_ids=artifact_ids(live_state.get("artifacts", [])),
        )
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
            "rationale": rationale,
            "blockers": blocker or [],
            "deviations": deviation or [],
            "flags": flag or [],
            "artifacts": artifacts,
        }
        write_json(self.packet_path(workstream_id, packet_id), packet)

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
        next_review_due_at: str | None = None,
    ) -> dict[str, Any]:
        if next_review_due_at is not None:
            parse_datetime(next_review_due_at)
        entry = self.get_workstream(workstream_id)
        existing_decisions = [path.stem for path in (self.decisions_dir / workstream_id).glob("*.json")]
        decision_id = compact_id("dec", existing_decisions)
        status_before = entry.get("status")
        status_after = status_after_for_action(action, status_before)
        if status_after != status_before:
            entry["status"] = status_after
        if next_review_due_at is not None:
            entry.setdefault("timestamps", {})["next_review_due_at"] = next_review_due_at
        if status_after != status_before or next_review_due_at is not None:
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
            "next_review_due_at": next_review_due_at,
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
        "rationale": None,
        "flags": [],
        "artifacts": [],
        "updated_at": None,
    }


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
    stale_days: int = 7,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    reasons = review_reasons(store, entry, live_state, packets, stale_days=stale_days, now=now)
    return {
        "reasons": reasons,
        "stale_days": stale_days,
        "reviewed_at": now.isoformat().replace("+00:00", "Z"),
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

    contract = entry.get("contract") or {}
    contract_id = contract.get("id")
    contract_version = contract.get("version")
    if not contract_id or contract_version is None:
        reasons.append("no_contract")
    else:
        try:
            contract_path = store.contract_version_path(contract_id, contract_version)
        except RegistryError:
            reasons.append("invalid_contract_pointer")
        else:
            if not contract_path.is_file():
                reasons.append("missing_contract_file")

    if not packets:
        reasons.append("no_state_packet")
    if not live_state.get("rationale"):
        reasons.append("missing_rationale")
    if live_state.get("blockers"):
        reasons.append("blocked")
    if live_state.get("flags"):
        reasons.append("flagged")
    if live_state.get("deviations"):
        reasons.append("deviated")

    last_state_update_at = timestamps.get("last_state_update_at")
    if last_state_update_at:
        try:
            threshold = now - timedelta(days=stale_days)
            if parse_datetime(last_state_update_at) <= threshold:
                reasons.append("stale")
        except RegistryError:
            reasons.append("invalid_last_state_update_at")

    return reasons


def artifact_ids(artifacts: list[Any]) -> list[str]:
    ids = []
    for artifact in artifacts:
        if isinstance(artifact, dict) and artifact.get("id"):
            ids.append(str(artifact["id"]))
    return ids


def normalize_artifact_refs(
    artifact_paths: list[str] | None,
    artifact_refs: list[dict[str, Any]] | None,
    *,
    source: str,
    created_at: str,
    existing_ids: list[str],
) -> list[dict[str, Any]]:
    artifacts = []
    used_ids = list(existing_ids)

    for path in artifact_paths or []:
        if not path:
            continue
        artifact_id = compact_id("art", used_ids)
        normalized = normalize_artifact_ref(
            {"id": artifact_id, "path": path},
            source=source,
            created_at=created_at,
            existing_ids=used_ids,
        )
        used_ids.append(normalized["id"])
        artifacts.append(normalized)

    for artifact_ref in artifact_refs or []:
        artifact_id = artifact_ref.get("id") or compact_id("art", used_ids)
        artifact_ref = {**artifact_ref, "id": artifact_id}
        normalized = normalize_artifact_ref(
            artifact_ref,
            source=source,
            created_at=created_at,
            existing_ids=used_ids,
        )
        used_ids.append(normalized["id"])
        artifacts.append(normalized)

    return artifacts


def normalize_artifact_ref(
    artifact: dict[str, Any],
    *,
    source: str,
    created_at: str,
    existing_ids: list[str],
) -> dict[str, Any]:
    artifact_id = str(artifact.get("id") or "")
    ensure_safe_id("artifact id", artifact_id)
    if artifact_id in existing_ids:
        raise RegistryError(f"artifact already exists: {artifact_id}")

    path = artifact.get("path")
    if not path:
        raise RegistryError("artifact path is required")

    return {
        "id": artifact_id,
        "kind": artifact.get("kind") or "artifact",
        "path": str(path),
        "description": artifact.get("description"),
        "produced_by": artifact.get("produced_by") or source,
        "created_at": artifact.get("created_at") or created_at,
        "provenance": normalize_artifact_provenance(artifact.get("provenance")),
        "review": normalize_artifact_review(artifact.get("review")),
    }


def normalize_artifact_provenance(provenance: Any) -> dict[str, list[str]]:
    if provenance is None:
        provenance = {}
    if not isinstance(provenance, dict):
        raise RegistryError("artifact provenance must be an object")

    normalized = {}
    for field in ARTIFACT_PROVENANCE_FIELDS:
        value = provenance.get(field, [])
        if value is None:
            value = []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise RegistryError(f"artifact provenance {field} must be a list")
        normalized[field] = [str(item) for item in value if item]
    return normalized


def normalize_artifact_review(review: Any) -> dict[str, Any]:
    if review is None:
        review = {}
    if not isinstance(review, dict):
        raise RegistryError("artifact review must be an object")
    return {
        "local_only": bool(review.get("local_only", True)),
        "safe_to_reuse": bool(review.get("safe_to_reuse", False)),
        "notes": review.get("notes"),
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
    if packet.get("rationale"):
        live_state["rationale"] = packet["rationale"]
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
