from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from fab.registry import RegistryStore, utc_now
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from fab.registry import RegistryStore, utc_now


SERVICE_NAME = "alexandria-ingester"
ARTIFACTS_DIR = "artifacts"


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
        return self.store / "ingest-ledger" / "alexandria.jsonl"


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(repo: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def git_pull(repo: Path) -> None:
    subprocess.run(["git", "-C", str(repo), "pull", "--ff-only"], check=True)


def repo_head(repo: Path) -> str | None:
    return git_output(repo, "rev-parse", "HEAD")


def repo_dirty(repo: Path) -> bool | None:
    output = git_output(repo, "status", "--short")
    if output is None:
        return None
    return bool(output)


def bundle_commit(repo: Path, bundle: Path) -> str | None:
    try:
        relpath = bundle.relative_to(repo)
    except ValueError:
        return None
    return git_output(repo, "log", "-n", "1", "--format=%H", "--", str(relpath))


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
    relpath = bundle_relpath(config.alexandria, bundle)
    return {
        "created_at": utc_now(),
        "service": SERVICE_NAME,
        "alexandria_repo": str(config.alexandria),
        "alexandria_head_commit": repo_head(config.alexandria),
        "alexandria_dirty": repo_dirty(config.alexandria),
        "bundle_relpath": relpath,
        "bundle_path": str(bundle),
        "bundle_commit": bundle_commit(config.alexandria, bundle),
        "manifest_path": str(bundle / "manifest.json"),
        "manifest_sha256": sha256_file(bundle / "manifest.json"),
    }


def ingest_bundle(
    config: IngesterConfig,
    bundle: Path,
    *,
    store: RegistryStore,
) -> dict[str, Any]:
    entry = base_ledger_entry(config, bundle)
    try:
        packet = store.ingest_run_bundle(bundle)
    except Exception as exc:  # noqa: BLE001 - service ledger should capture bundle failures.
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
    alexandria = config.alexandria.resolve()
    store_path = config.store.resolve()
    normalized = IngesterConfig(
        alexandria=alexandria,
        store=store_path,
        ledger=config.ledger.resolve() if config.ledger is not None else None,
        pull=config.pull,
        limit=config.limit,
    )

    if normalized.pull:
        git_pull(normalized.alexandria)

    ledger_entries = read_ledger(normalized.ledger_path)
    already_ingested = ingested_bundle_relpaths(ledger_entries)
    bundles = discover_ready_bundles(normalized.alexandria)
    store = RegistryStore.at(normalized.store)

    results: list[dict[str, Any]] = []
    processed = 0
    for bundle in bundles:
        relpath = bundle_relpath(normalized.alexandria, bundle)
        if relpath in already_ingested:
            results.append({"bundle_relpath": relpath, "status": "skipped"})
            continue
        if normalized.limit is not None and processed >= normalized.limit:
            results.append({"bundle_relpath": relpath, "status": "deferred"})
            continue
        results.append(ingest_bundle(normalized, bundle, store=store))
        processed += 1

    counts = {
        "discovered": len(bundles),
        "ingested": sum(1 for item in results if item["status"] == "ingested"),
        "skipped": sum(1 for item in results if item["status"] == "skipped"),
        "deferred": sum(1 for item in results if item["status"] == "deferred"),
        "errors": sum(1 for item in results if item["status"] == "error"),
    }
    return {
        "service": SERVICE_NAME,
        "alexandria": str(normalized.alexandria),
        "store": str(normalized.store),
        "ledger": str(normalized.ledger_path),
        "alexandria_head_commit": repo_head(normalized.alexandria),
        "alexandria_dirty": repo_dirty(normalized.alexandria),
        "counts": counts,
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
        prog="alexandria-ingester",
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

    if args.poll_interval is None:
        summary = run_once(config)
        print_summary(summary, as_json=args.json)
        if summary["counts"]["errors"] and not args.allow_errors:
            return 1
        return 0

    try:
        while True:
            summary = run_once(config)
            print_summary(summary, as_json=args.json)
            if summary["counts"]["errors"] and not args.allow_errors:
                return 1
            time.sleep(args.poll_interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
