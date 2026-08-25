"""File-backed registry store.

Layout under ``root``::

    workstreams/<ws>.json              slow-changing registry entry
    live-state/<ws>.json               mutable state merged from packets
    state-packets/<ws>/pkt_NNN.json    append-only agent packets
    decisions/<ws>/dec_NNN.json        append-only human judgments
    contracts/<contract>/vNNN.md       immutable contract versions
    sources.json                       external source adapters

Every identifier that becomes a path segment is validated by the path builder
that uses it, so no caller can escape the store directory.
"""

from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fab.artifacts import artifact_ids, normalize_artifact_refs
from fab.brief import build_brief
from fab.errors import RegistryError
from fab.livestate import empty_live_state, merge_packet_into_live_state
from fab.manifest import read_run_bundle, run_artifact_ref
from fab.refs import ReferenceResolver, brief_reference_review, reference_check
from fab.review import (
    DEFAULT_STALE_DAYS,
    attached_contract_summary,
    attention_items,
    review_summary,
)
from fab.status import (
    ensure_decision_action,
    ensure_status,
    ensure_status_transition,
    normalize_decision_target,
    status_after_for_action,
)
from fab.util import compact_id, ensure_safe_id, parse_datetime, read_json, utc_now, write_json

RELATIONSHIP_LIST_FIELDS = frozenset({"children", "related", "blocks", "blocked_by"})
RELATIONSHIP_CHOICES = ("parent", "children", "related", "blocks", "blocked_by")
READ_ONLY_FILE_MODE = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
RECENT_LIMIT = 5


def contract_version_filename(version: int) -> str:
    if version < 1:
        raise RegistryError(f"invalid contract version: {version}")
    return f"v{version:03d}.md"


@dataclass(frozen=True)
class RegistryStore:
    root: Path

    @classmethod
    def at(cls, root: Path | str) -> RegistryStore:
        return cls(Path(root))

    # ------------------------------------------------------------------ layout

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

    @property
    def sources_path(self) -> Path:
        return self.root / "sources.json"

    def content_dirs(self) -> tuple[Path, ...]:
        return (
            self.workstreams_dir,
            self.live_state_dir,
            self.packets_dir,
            self.decisions_dir,
            self.contracts_dir,
        )

    def init(self) -> None:
        for path in self.content_dirs():
            path.mkdir(parents=True, exist_ok=True)

    def ensure_ready(self) -> None:
        if not self.workstreams_dir.exists():
            raise RegistryError(f"registry is not initialized: {self.root}")

    def is_empty(self) -> bool:
        """True when no workstream, state, packet, decision or contract file exists.

        Source configuration is deliberately ignored: configuring sources before
        seeding a store is legitimate.
        """
        for directory in self.content_dirs():
            if directory.exists() and any(path.is_file() for path in directory.rglob("*")):
                return False
        return True

    # ------------------------------------------------------- per-entity paths

    def workstream_path(self, workstream_id: str) -> Path:
        ensure_safe_id("workstream id", workstream_id)
        return self.workstreams_dir / f"{workstream_id}.json"

    def live_state_path(self, workstream_id: str) -> Path:
        ensure_safe_id("workstream id", workstream_id)
        return self.live_state_dir / f"{workstream_id}.json"

    def workstream_packets_dir(self, workstream_id: str) -> Path:
        ensure_safe_id("workstream id", workstream_id)
        return self.packets_dir / workstream_id

    def packet_path(self, workstream_id: str, packet_id: str) -> Path:
        ensure_safe_id("packet id", packet_id)
        return self.workstream_packets_dir(workstream_id) / f"{packet_id}.json"

    def workstream_decisions_dir(self, workstream_id: str) -> Path:
        ensure_safe_id("workstream id", workstream_id)
        return self.decisions_dir / workstream_id

    def decision_path(self, workstream_id: str, decision_id: str) -> Path:
        ensure_safe_id("decision id", decision_id)
        return self.workstream_decisions_dir(workstream_id) / f"{decision_id}.json"

    def contract_version_path(self, contract_id: str, version: int) -> Path:
        ensure_safe_id("contract id", contract_id)
        return self.contracts_dir / contract_id / contract_version_filename(version)

    # ---------------------------------------------------------------- sources

    def read_sources(self) -> dict[str, Any]:
        if not self.sources_path.exists():
            return {"sources": {}}
        data = read_json(self.sources_path)
        sources = data.get("sources")
        if not isinstance(sources, dict):
            raise RegistryError("sources registry must contain a sources object")
        return {"sources": sources}

    def write_sources(self, data: dict[str, Any]) -> None:
        write_json(self.sources_path, data)

    def add_source(self, name: str, path: str | Path, *, uri_prefix: str) -> dict[str, Any]:
        self.init()
        ensure_safe_id("source name", name)
        if not uri_prefix:
            raise RegistryError("source uri prefix is required")
        data = self.read_sources()
        source = {
            "name": name,
            "path": str(Path(path).expanduser()),
            "uri_prefix": uri_prefix,
        }
        data["sources"][name] = source
        self.write_sources(data)
        return source

    def list_sources(self) -> list[dict[str, Any]]:
        self.ensure_ready()
        sources = self.read_sources()["sources"]
        return [sources[name] for name in sorted(sources)]

    def resolver(self) -> ReferenceResolver:
        """A reference resolver over the currently configured sources.

        Build one resolver per batch of lookups; the convenience methods below
        each build their own and suit one-off calls.
        """
        return ReferenceResolver.for_store(self)

    def resolve_reference(self, uri: str) -> dict[str, Any]:
        return self.resolver().resolve(uri)

    def contract_reference_entries(
        self,
        contract_id: str,
        version: int,
        text: str,
    ) -> list[dict[str, Any]]:
        return self.resolver().contract_entries(contract_id, version, text)

    def used_reference_entries(self, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.resolver().used_entries(artifacts)

    def reference_review(
        self,
        workstreams: list[dict[str, Any]],
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return brief_reference_review(self, workstreams, artifacts)

    # -------------------------------------------------------------- contracts

    def ensure_contract_exists(self, contract_id: str, version: int | None) -> Path:
        if version is None:
            raise RegistryError(f"contract version is required for {contract_id}")
        path = self.contract_version_path(contract_id, version)
        if not path.is_file():
            raise RegistryError(f"contract version not found: {path}")
        return path

    def lock_contract_version(self, contract_id: str, version: int | None) -> None:
        """Mark an existing contract version read-only once a workstream depends on it."""
        self.ensure_contract_exists(contract_id, version).chmod(READ_ONLY_FILE_MODE)

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
        return self.ensure_contract_exists(contract_id, version).read_text(encoding="utf-8")

    # ------------------------------------------------------------ workstreams

    def existing_workstream_ids(self) -> list[str]:
        if not self.workstreams_dir.exists():
            return []
        return sorted(path.stem for path in self.workstreams_dir.glob("*.json"))

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
        ensure_status(status)
        if contract_id:
            self.ensure_contract_exists(contract_id, contract_version)
        elif contract_version is not None:
            raise RegistryError("contract version cannot be set without contract id")
        if next_review_due_at is not None:
            parse_datetime(next_review_due_at)

        existing = self.existing_workstream_ids()
        workstream_id = workstream_id or compact_id("ws", existing)
        ensure_safe_id("workstream id", workstream_id)
        if workstream_id in existing:
            raise RegistryError(f"workstream already exists: {workstream_id}")

        # All validation is done; only now take on side effects.
        if contract_id:
            self.lock_contract_version(contract_id, contract_version)

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
        write_json(self.workstream_path(workstream_id), entry)
        write_json(
            self.live_state_path(workstream_id),
            empty_live_state(workstream_id, entry["live_state"]["id"]),
        )
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

    def set_status(self, workstream_id: str, status: str, *, force: bool = False) -> dict[str, Any]:
        """Move a workstream to ``status``.

        Transitions follow :data:`fab.status.STATUS_TRANSITIONS` unless ``force``
        is set, which exists so a human can correct a mistaken terminal status.
        """
        ensure_status(status)
        entry = self.get_workstream(workstream_id)
        if not force:
            ensure_status_transition(entry.get("status"), status)
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
        self.lock_contract_version(contract_id, version)
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
            valid = ", ".join(RELATIONSHIP_CHOICES)
            raise RegistryError(f"invalid relationship: {relationship}; valid: {valid}")
        return self.save_workstream(entry)

    # ---------------------------------------------------- live state / packets

    def get_live_state(self, workstream_id: str) -> dict[str, Any]:
        self.ensure_ready()
        return read_json(self.live_state_path(workstream_id))

    def list_packets(self, workstream_id: str) -> list[dict[str, Any]]:
        packet_dir = self.workstream_packets_dir(workstream_id)
        if not packet_dir.exists():
            return []
        return [read_json(path) for path in sorted(packet_dir.glob("*.json"))]

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
        limitation: list[str] | None = None,
        ingest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append a packet, merge it into live state, and stamp the workstream.

        ``ingest`` carries provenance for packets produced from a remote run
        bundle and is stored on the packet as written; it is not merged into
        live state.
        """
        entry = self.get_workstream(workstream_id)
        live_state = self.get_live_state(workstream_id)
        existing_packets = [
            path.stem for path in self.workstream_packets_dir(workstream_id).glob("*.json")
        ]
        packet_id = compact_id("pkt", existing_packets)
        now = utc_now()
        artifacts = normalize_artifact_refs(
            artifact,
            artifact_ref,
            source=source,
            created_at=now,
            existing_ids=artifact_ids(live_state.get("artifacts", [])),
        )
        packet: dict[str, Any] = {
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
            "limitations": limitation or [],
            "artifacts": artifacts,
        }
        if ingest is not None:
            packet["ingest"] = ingest
        write_json(self.packet_path(workstream_id, packet_id), packet)

        merge_packet_into_live_state(live_state, packet)
        write_json(self.live_state_path(workstream_id), live_state)

        entry["live_state"]["updated_at"] = now
        entry["timestamps"]["last_state_update_at"] = now
        self.save_workstream(entry)
        return packet

    def ingest_run_bundle(self, bundle_path: Path | str) -> dict[str, Any]:
        """Ingest a completed remote run bundle as one state packet."""
        bundle = read_run_bundle(bundle_path)
        run = bundle.run
        entry = self.get_workstream(run["workstream_id"])
        expected_contract = entry.get("contract") or {}
        if expected_contract != run["contract"]:
            raise RegistryError(
                "run manifest contract does not match workstream contract: "
                f"{run['contract']} != {expected_contract}"
            )

        failed = run["status"] == "failed"
        return self.add_state_packet(
            run["workstream_id"],
            source=run["source"],
            changed=f"ingested run bundle: {bundle.path}",
            failed=run["summary"] if failed else None,
            result=None if failed else run["summary"],
            next_action="; ".join(run["next"]) or None,
            rationale=run["summary"],
            limitation=run["limitations"],
            artifact_ref=[run_artifact_ref(bundle)],
            ingest={
                "bundle_path": str(bundle.path),
                "manifest_path": str(bundle.manifest_path),
                "status": run["status"],
            },
        )

    # -------------------------------------------------------------- decisions

    def list_decisions(self, workstream_id: str) -> list[dict[str, Any]]:
        decision_dir = self.workstream_decisions_dir(workstream_id)
        if not decision_dir.exists():
            return []
        return [read_json(path) for path in sorted(decision_dir.glob("*.json"))]

    def add_decision(
        self,
        workstream_id: str,
        *,
        action: str,
        rationale: str,
        actor: str | None = None,
        next_review_due_at: str | None = None,
        target_type: str = "workstream",
        target_id: str | None = None,
    ) -> dict[str, Any]:
        """Record a human judgment; workstream-targeted lifecycle actions move status."""
        ensure_decision_action(action)
        if next_review_due_at is not None:
            parse_datetime(next_review_due_at)
        entry = self.get_workstream(workstream_id)
        live_state = self.get_live_state(workstream_id)
        target = normalize_decision_target(live_state, workstream_id, target_type, target_id)

        status_before = entry.get("status")
        status_after = status_before
        if target["type"] == "workstream":
            status_after = status_after_for_action(action, status_before)
            ensure_status_transition(status_before, status_after)

        existing_decisions = [
            path.stem for path in self.workstream_decisions_dir(workstream_id).glob("*.json")
        ]
        decision_id = compact_id("dec", existing_decisions)

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
            "target": target,
            "rationale": rationale,
            "status_before": status_before,
            "status_after": status_after,
            "next_review_due_at": next_review_due_at,
        }
        write_json(self.decision_path(workstream_id, decision_id), decision)
        return decision

    # ------------------------------------------------------------ read models

    def show(self, workstream_id: str) -> dict[str, Any]:
        entry = self.get_workstream(workstream_id)
        live_state = self.get_live_state(workstream_id)
        packets = self.list_packets(workstream_id)
        return {
            "workstream": entry,
            "attached_contract": attached_contract_summary(self, entry),
            "review": review_summary(self, entry, live_state, packets),
            "live_state": live_state,
            "recent_packets": packets[-RECENT_LIMIT:],
            "recent_decisions": self.list_decisions(workstream_id)[-RECENT_LIMIT:],
        }

    def review_workstreams(
        self,
        *,
        status: str | None = None,
        program: str | None = None,
        reason: str | None = None,
        stale_days: int = DEFAULT_STALE_DAYS,
        include_clear: bool = False,
    ) -> list[dict[str, Any]]:
        self.ensure_ready()
        return attention_items(
            self,
            status=status,
            program=program,
            reason=reason,
            stale_days=stale_days,
            include_clear=include_clear,
        )

    def brief(
        self,
        *,
        program: str | None = None,
        contract_id: str | None = None,
        stale_days: int = DEFAULT_STALE_DAYS,
    ) -> dict[str, Any]:
        self.ensure_ready()
        return build_brief(self, program=program, contract_id=contract_id, stale_days=stale_days)

    def check_references(
        self,
        *,
        contract_id: str | None = None,
        version: int | None = None,
        workstream_id: str | None = None,
    ) -> dict[str, Any]:
        self.ensure_ready()
        return reference_check(
            self,
            contract_id=contract_id,
            version=version,
            workstream_id=workstream_id,
        )
