"""Normalisation of artefact references, claims, evidence and provenance."""

from __future__ import annotations

from typing import Any

from fab.errors import RegistryError
from fab.util import compact_id, ensure_safe_id, normalize_string_list

ARTIFACT_PROVENANCE_FIELDS = (
    "code",
    "configs",
    "datasets",
    "models",
    "prompts",
    "evals",
    "logs",
    "outputs",
)


def artifact_ids(artifacts: list[Any]) -> list[str]:
    return [
        str(artifact["id"])
        for artifact in artifacts
        if isinstance(artifact, dict) and artifact.get("id")
    ]


def artifact_target_exists(live_state: dict[str, Any], target_id: str) -> bool:
    artifact_id = target_id.split("/")[-1]
    return any(artifact.get("id") == artifact_id for artifact in live_state.get("artifacts", []))


def claim_target_exists(live_state: dict[str, Any], target_id: str) -> bool:
    parts = target_id.split("/")
    artifact_id = parts[-2] if len(parts) >= 2 else None
    claim_id = parts[-1]
    for artifact in live_state.get("artifacts", []):
        if artifact_id and artifact.get("id") != artifact_id:
            continue
        for claim in artifact.get("claims", []):
            if claim.get("id") == claim_id:
                return True
    return False


def normalize_artifact_refs(
    artifact_paths: list[str] | None,
    artifact_refs: list[dict[str, Any]] | None,
    *,
    source: str,
    created_at: str,
    existing_ids: list[str],
) -> list[dict[str, Any]]:
    """Turn plain paths and structured references into normalised artefact records."""
    artifacts = []
    used_ids = list(existing_ids)

    for path in artifact_paths or []:
        if not path:
            continue
        normalized = normalize_artifact_ref(
            {"id": compact_id("art", used_ids), "path": path},
            source=source,
            created_at=created_at,
            existing_ids=used_ids,
        )
        used_ids.append(normalized["id"])
        artifacts.append(normalized)

    for artifact_ref in artifact_refs or []:
        artifact_ref = {**artifact_ref, "id": artifact_ref.get("id") or compact_id("art", used_ids)}
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
        "claims": normalize_artifact_claims(artifact.get("claims")),
        "evidence": normalize_artifact_evidence(artifact.get("evidence")),
        "failed_attempts": normalize_string_list(
            artifact.get("failed_attempts") or artifact.get("failures"),
            label="artifact failed_attempts",
        ),
        "limitations": normalize_string_list(
            artifact.get("limitations"),
            label="artifact limitations",
        ),
        "uncertainty": artifact.get("uncertainty"),
        "status": artifact.get("status"),
        "reproduction": normalize_artifact_reproduction(artifact.get("reproduction")),
        "suggested_follow_up": normalize_string_list(
            artifact.get("suggested_follow_up") or artifact.get("follow_up"),
            label="artifact suggested_follow_up",
        ),
        "provenance": normalize_artifact_provenance(artifact.get("provenance")),
        "used_refs": normalize_string_list(
            artifact.get("used_refs"),
            label="artifact used_refs",
        ),
        "review": normalize_artifact_review(artifact.get("review")),
    }


def normalize_artifact_claims(claims: Any) -> list[dict[str, Any]]:
    if claims is None:
        return []
    if isinstance(claims, str):
        claims = [claims]
    if not isinstance(claims, list):
        raise RegistryError("artifact claims must be a list")

    used_ids: list[str] = []
    normalized = []
    for claim in claims:
        if isinstance(claim, str):
            claim = {"text": claim}
        if not isinstance(claim, dict):
            raise RegistryError("artifact claim must be an object")
        claim_id = str(claim.get("id") or compact_id("claim", used_ids))
        ensure_safe_id("claim id", claim_id)
        if claim_id in used_ids:
            raise RegistryError(f"duplicate claim id: {claim_id}")
        used_ids.append(claim_id)
        text = claim.get("text") or claim.get("claim")
        if not text:
            raise RegistryError(f"artifact claim text is required: {claim_id}")
        normalized.append(
            {
                "id": claim_id,
                "text": str(text),
                "confidence": claim.get("confidence"),
                "evidence": normalize_string_list(
                    claim.get("evidence") or claim.get("evidence_ids"),
                    label=f"claim {claim_id} evidence",
                ),
                "caveats": normalize_string_list(
                    claim.get("caveats"),
                    label=f"claim {claim_id} caveats",
                ),
            }
        )
    return normalized


def normalize_artifact_evidence(evidence: Any) -> list[dict[str, Any]]:
    if evidence is None:
        return []
    if isinstance(evidence, str):
        evidence = [evidence]
    if not isinstance(evidence, list):
        raise RegistryError("artifact evidence must be a list")

    used_ids: list[str] = []
    normalized = []
    for item in evidence:
        if isinstance(item, str):
            item = {"summary": item}
        if not isinstance(item, dict):
            raise RegistryError("artifact evidence must be an object")
        evidence_id = str(item.get("id") or compact_id("ev", used_ids))
        ensure_safe_id("evidence id", evidence_id)
        if evidence_id in used_ids:
            raise RegistryError(f"duplicate evidence id: {evidence_id}")
        used_ids.append(evidence_id)
        summary = item.get("summary") or item.get("description") or item.get("text")
        if not summary:
            raise RegistryError(f"artifact evidence summary is required: {evidence_id}")
        normalized.append(
            {
                "id": evidence_id,
                "kind": item.get("kind") or "evidence",
                "summary": str(summary),
                "path": item.get("path"),
                "refs": normalize_string_list(item.get("refs"), label=f"evidence {evidence_id} refs"),
            }
        )
    return normalized


def normalize_artifact_reproduction(reproduction: Any) -> dict[str, Any]:
    if reproduction is None:
        reproduction = {}
    if isinstance(reproduction, str):
        reproduction = {"notes": reproduction}
    if not isinstance(reproduction, dict):
        raise RegistryError("artifact reproduction must be an object")
    return {
        "commands": normalize_string_list(
            reproduction.get("commands"),
            label="artifact reproduction commands",
        ),
        "environment": normalize_string_list(
            reproduction.get("environment"),
            label="artifact reproduction environment",
        ),
        "notes": reproduction.get("notes"),
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
