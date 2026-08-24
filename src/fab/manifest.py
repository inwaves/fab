"""Remote run bundles: manifest schema validation and bundle layout checks.

A run bundle is a directory containing ``READY``, ``manifest.json`` and an
``artifact/`` directory. :func:`read_run_bundle` validates all three and returns
a :class:`RunBundle`; the store then decides whether the bundle belongs to a
workstream it knows about.

Containment is checked on resolved paths: ``READY``, ``manifest.json``, every
evidence path and the ``artifact/`` directory must resolve to a location inside
the resolved bundle root, so symlinks pointing out of a remotely supplied bundle
are rejected. The checks are point-in-time; a bundle that is being rewritten
while it is ingested is outside this module's guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fab.errors import RegistryError
from fab.util import ensure_safe_id, read_json

REMOTE_RUN_STATUSES = frozenset({"completed", "completed_with_limitations", "failed"})
READY_MARKER = "READY"
MANIFEST_FILENAME = "manifest.json"
ARTIFACT_DIRNAME = "artifact"


@dataclass(frozen=True)
class RunBundle:
    """A run bundle whose layout and manifest have been validated."""

    path: Path
    manifest_path: Path
    artifact_dir: Path
    run: dict[str, Any]


def require_manifest_field(manifest: dict[str, Any], field: str) -> Any:
    if field not in manifest:
        raise RegistryError(f"run manifest missing field: {field}")
    return manifest[field]


def normalize_manifest_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"run manifest {label} must be a non-empty string")
    return value


def normalize_manifest_string_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise RegistryError(f"run manifest {label} must be a list")
    normalized = []
    for item in value:
        if not isinstance(item, str):
            raise RegistryError(f"run manifest {label} entries must be strings")
        if item.strip():
            normalized.append(item)
    return normalized


def normalize_run_contract(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RegistryError("run manifest contract must be an object")
    contract_id = normalize_manifest_string(value.get("id"), label="contract.id")
    ensure_safe_id("contract id", contract_id)
    version = value.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise RegistryError("run manifest contract.version must be a positive integer")
    return {"id": contract_id, "version": version}


def normalize_run_evidence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RegistryError("run manifest evidence must be a list")
    normalized = []
    for item in value:
        if isinstance(item, str):
            item = {"summary": item}
        if not isinstance(item, dict):
            raise RegistryError("run manifest evidence entries must be objects")
        summary = normalize_manifest_string(item.get("summary"), label="evidence.summary")
        evidence: dict[str, Any] = {"summary": summary}
        path = item.get("path")
        if path is not None:
            evidence["path"] = normalize_manifest_string(path, label="evidence.path")
        normalized.append(evidence)
    return normalized


def normalize_run_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise RegistryError("run manifest must be an object")

    workstream_id = normalize_manifest_string(
        require_manifest_field(manifest, "workstream_id"),
        label="workstream_id",
    )
    ensure_safe_id("workstream id", workstream_id)

    status = normalize_manifest_string(
        require_manifest_field(manifest, "status"),
        label="status",
    )
    if status not in REMOTE_RUN_STATUSES:
        valid = ", ".join(sorted(REMOTE_RUN_STATUSES))
        raise RegistryError(f"invalid run manifest status: {status}; valid: {valid}")

    return {
        "workstream_id": workstream_id,
        "contract": normalize_run_contract(require_manifest_field(manifest, "contract")),
        "source": normalize_manifest_string(
            require_manifest_field(manifest, "source"),
            label="source",
        ),
        "summary": normalize_manifest_string(
            require_manifest_field(manifest, "summary"),
            label="summary",
        ),
        "status": status,
        "claims": normalize_manifest_string_list(
            require_manifest_field(manifest, "claims"),
            label="claims",
        ),
        "evidence": normalize_run_evidence(require_manifest_field(manifest, "evidence")),
        "limitations": normalize_manifest_string_list(
            require_manifest_field(manifest, "limitations"),
            label="limitations",
        ),
        "next": normalize_manifest_string_list(
            require_manifest_field(manifest, "next"),
            label="next",
        ),
        "used_refs": normalize_manifest_string_list(
            require_manifest_field(manifest, "used_refs"),
            label="used_refs",
        ),
    }


def is_within(root: Path, candidate: Path) -> bool:
    """True when ``candidate`` resolves (following symlinks) to inside ``root``."""
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def validate_manifest_paths(bundle: Path, evidence: list[dict[str, Any]]) -> None:
    """Every evidence path must be relative, exist, and resolve inside the bundle."""
    for item in evidence:
        raw_path = item.get("path")
        if not raw_path:
            continue
        path = Path(raw_path)
        if path.is_absolute() or ".." in path.parts:
            raise RegistryError(f"run manifest path must be relative to bundle root: {raw_path}")
        if "://" in raw_path:
            raise RegistryError(f"run manifest path must be relative, not a URI: {raw_path}")
        target = bundle / path
        if not target.exists():
            raise RegistryError(f"run manifest path not found: {raw_path}")
        if not is_within(bundle, target):
            raise RegistryError(f"run manifest path resolves outside the bundle: {raw_path}")


def bundle_file(bundle: Path, name: str) -> Path:
    """Return ``bundle/name``, which must be a regular file resolving inside the bundle."""
    path = bundle / name
    if not path.exists():
        raise RegistryError(f"run bundle is missing {name}: {path}")
    if not path.is_file() or not is_within(bundle, path):
        raise RegistryError(f"run bundle {name} must be a regular file inside the bundle: {path}")
    return path


def read_run_bundle(bundle_path: Path | str) -> RunBundle:
    """Validate a bundle directory and return its normalised manifest."""
    bundle = Path(bundle_path)
    if not bundle.is_dir():
        raise RegistryError(f"run bundle is not a directory: {bundle}")
    bundle_file(bundle, READY_MARKER)
    manifest_path = bundle_file(bundle, MANIFEST_FILENAME)
    run = normalize_run_manifest(read_json(manifest_path))

    artifact_dir = bundle / ARTIFACT_DIRNAME
    if not artifact_dir.is_dir():
        raise RegistryError(f"run bundle artifact directory not found: {artifact_dir}")
    if not is_within(bundle, artifact_dir):
        raise RegistryError(
            f"run bundle artifact directory resolves outside the bundle: {artifact_dir}"
        )
    validate_manifest_paths(bundle, run["evidence"])

    return RunBundle(path=bundle, manifest_path=manifest_path, artifact_dir=artifact_dir, run=run)


def run_artifact_ref(bundle: RunBundle) -> dict[str, Any]:
    """Describe the bundle's ``artifact/`` directory as a structured artefact reference."""
    run = bundle.run
    return {
        "path": str(bundle.artifact_dir),
        "description": run["summary"],
        "status": run["status"],
        "claims": run["claims"],
        "evidence": run["evidence"],
        "limitations": run["limitations"],
        "suggested_follow_up": run["next"],
        "used_refs": run["used_refs"],
    }
