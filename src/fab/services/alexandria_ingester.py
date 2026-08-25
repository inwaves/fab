"""Ingest completed Alexandria run bundles into a Fab store.

Scans ``<alexandria>/artifacts/<program>/<workstream>/<run>/READY`` markers,
ingests each bundle once, and records every attempt in a JSONL ledger so the
service can be re-run or polled without double-ingesting. Failed bundles are
recorded as errors and retried on the next scan.

Run as ``fab-alexandria-ingester`` or ``python -m fab.services.alexandria_ingester``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fab.provenance import git_commit_for_path, git_dirty, git_head, sha256_file
from fab.store import RegistryStore
from fab.util import utc_now

SERVICE_NAME = "alexandria-ingester"
ARTIFACTS_DIR = "artifacts"
LEDGER_RELPATH = Path("ingest-ledger") / "alexandria.jsonl"


@dataclass(frozen=True)
class IngesterConfig:
    alexandria: Path
    store: Path
    ledger: Path | None = None
    pull: bool = False
    limit: int | None = None

    @property
    def ledger_path(self) -> Path:
        if self.ledger is not None:
            return self.ledger
        return self.store / LEDGER_RELPATH

    def resolved(self) -> IngesterConfig:
        """The same configuration with every path made absolute."""
        return IngesterConfig(
            alexandria=self.alexandria.resolve(),
            store=self.store.resolve(),
            ledger=self.ledger.resolve() if self.ledger is not None else None,
            pull=self.pull,
            limit=self.limit,
        )


def git_pull(repo: Path) -> None:
    subprocess.run(["git", "-C", str(repo), "pull", "--ff-only"], check=True)


def bundle_relpath(repo: Path, bundle: Path) -> str:
    return bundle.relative_to(repo).as_posix()


def discover_ready_bundles(alexandria: Path) -> list[Path]:
    artifacts_root = alexandria / ARTIFACTS_DIR
    if not artifacts_root.is_dir():
        return []
    bundles = [ready.parent for ready in artifacts_root.glob("*/*/*/READY")]
    return sorted(bundles, key=lambda path: bundle_relpath(alexandria, path))


def read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in ledger {path}:{line_number}: {exc}") from exc
        if not isinstance(entry, dict):
            raise ValueError(f"invalid ledger entry in {path}:{line_number}: expected object")
        entries.append(entry)
    return entries


def append_ledger(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def ingested_bundle_relpaths(entries: list[dict[str, Any]]) -> set[str]:
    return {
        str(entry["bundle_relpath"])
        for entry in entries
        if entry.get("service") == SERVICE_NAME
        and entry.get("status") == "ingested"
        and entry.get("bundle_relpath")
    }


def base_ledger_entry(config: IngesterConfig, bundle: Path) -> dict[str, Any]:
    """The fields that identify a bundle attempt; nothing here touches the bundle contents."""
    return {
        "created_at": utc_now(),
        "service": SERVICE_NAME,
        "alexandria_repo": str(config.alexandria),
        "bundle_relpath": bundle_relpath(config.alexandria, bundle),
        "bundle_path": str(bundle),
    }


def repo_provenance(alexandria: Path) -> dict[str, Any]:
    """Head commit and dirty state of the Alexandria checkout; never raises."""
    return {
        "alexandria_head_commit": git_head(alexandria),
        "alexandria_dirty": git_dirty(alexandria),
    }


def bundle_provenance(config: IngesterConfig, bundle: Path) -> dict[str, Any]:
    """Git and manifest provenance for one bundle; may raise on an unreadable bundle."""
    manifest_path = bundle / "manifest.json"
    return {
        "bundle_commit": git_commit_for_path(config.alexandria, bundle),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
    }


def ingest_bundle(
    config: IngesterConfig,
    bundle: Path,
    *,
    store: RegistryStore,
    repo: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ingest one bundle and ledger the outcome, whether provenance or ingest failed."""
    entry = base_ledger_entry(config, bundle)
    entry.update(repo if repo is not None else repo_provenance(config.alexandria))
    try:
        entry.update(bundle_provenance(config, bundle))
        packet = store.ingest_run_bundle(bundle)
    except Exception as exc:  # noqa: BLE001 - the ledger must record every bundle failure.
        error_entry = {
            **entry,
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        append_ledger(config.ledger_path, error_entry)
        return {
            "bundle_relpath": entry["bundle_relpath"],
            "status": "error",
            "error": error_entry["error"],
            "error_type": error_entry["error_type"],
        }

    success_entry = {
        **entry,
        "status": "ingested",
        "packet_id": packet["id"],
        "workstream_id": packet["workstream_id"],
        "source": packet["source"],
    }
    append_ledger(config.ledger_path, success_entry)
    return {
        "bundle_relpath": entry["bundle_relpath"],
        "status": "ingested",
        "packet_id": packet["id"],
        "workstream_id": packet["workstream_id"],
        "source": packet["source"],
    }


def run_once(config: IngesterConfig) -> dict[str, Any]:
    config = config.resolved()
    if config.pull:
        git_pull(config.alexandria)

    already_ingested = ingested_bundle_relpaths(read_ledger(config.ledger_path))
    bundles = discover_ready_bundles(config.alexandria)
    store = RegistryStore.at(config.store)
    repo = repo_provenance(config.alexandria)

    results: list[dict[str, Any]] = []
    processed = 0
    for bundle in bundles:
        relpath = bundle_relpath(config.alexandria, bundle)
        if relpath in already_ingested:
            results.append({"bundle_relpath": relpath, "status": "skipped"})
            continue
        if config.limit is not None and processed >= config.limit:
            results.append({"bundle_relpath": relpath, "status": "deferred"})
            continue
        results.append(ingest_bundle(config, bundle, store=store, repo=repo))
        processed += 1

    counts = {
        status: sum(1 for item in results if item["status"] == status)
        for status in ("ingested", "skipped", "deferred", "error")
    }
    return {
        "service": SERVICE_NAME,
        "alexandria": str(config.alexandria),
        "store": str(config.store),
        "ledger": str(config.ledger_path),
        **repo,
        "counts": {
            "discovered": len(bundles),
            "ingested": counts["ingested"],
            "skipped": counts["skipped"],
            "deferred": counts["deferred"],
            "errors": counts["error"],
        },
        "bundles": results,
    }


def print_summary(summary: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return

    counts = summary["counts"]
    print(
        f"{summary['service']}: discovered={counts['discovered']} "
        f"ingested={counts['ingested']} skipped={counts['skipped']} "
        f"deferred={counts['deferred']} errors={counts['errors']}"
    )
    for item in summary["bundles"]:
        detail = item.get("packet_id") or item.get("error") or ""
        suffix = f" {detail}" if detail else ""
        print(f"- {item['status']}\t{item['bundle_relpath']}{suffix}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fab-alexandria-ingester",
        description="Ingest completed Alexandria run bundles into a Fab store.",
    )
    parser.add_argument("--alexandria", required=True, type=Path)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--pull", action="store_true", help="run git pull --ff-only before each scan")
    parser.add_argument("--limit", type=int, help="maximum number of new bundles to ingest per scan")
    parser.add_argument("--poll-interval", type=float, help="run continuously with this delay in seconds")
    parser.add_argument("--allow-errors", action="store_true", help="exit zero even when bundle ingest errors occur")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.poll_interval is not None and args.poll_interval <= 0:
        parser.error("--poll-interval must be positive")

    config = IngesterConfig(
        alexandria=args.alexandria,
        store=args.store,
        ledger=args.ledger,
        pull=args.pull,
        limit=args.limit,
    )

    try:
        while True:
            summary = run_once(config)
            print_summary(summary, as_json=args.json)
            if summary["counts"]["errors"] and not args.allow_errors:
                return 1
            if args.poll_interval is None:
                return 0
            time.sleep(args.poll_interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
