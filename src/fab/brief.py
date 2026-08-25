"""The brief: a cross-workstream read model for human review.

Everything here is deterministic aggregation over stored records. The
"contract review" groups repeated claim text, shared limitations and shared
references; it does not infer semantic contradictions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fab.refs import brief_reference_review
from fab.review import DEFAULT_STALE_DAYS, ensure_stale_days, review_summary
from fab.util import current_time, format_datetime

if TYPE_CHECKING:
    from fab.store import RegistryStore

# Judgment action -> next-context bucket.
NEXT_CONTEXT_BUCKETS = {
    "trust-local": "trusted_local",
    "safe-as-context": "safe_as_context",
    "replicate": "needs_replication",
    "needs-replication": "needs_replication",
    "needs-critique": "needs_critique",
    "reject": "do_not_propagate",
    "do-not-propagate": "do_not_propagate",
    "quarantine": "do_not_propagate",
}
NEXT_CONTEXT_ORDER = (
    "trusted_local",
    "safe_as_context",
    "needs_replication",
    "needs_critique",
    "do_not_propagate",
)


def build_brief(
    store: RegistryStore,
    *,
    program: str | None = None,
    contract_id: str | None = None,
    stale_days: int = DEFAULT_STALE_DAYS,
) -> dict[str, Any]:
    ensure_stale_days(stale_days)
    workstreams = store.list_workstreams(program=program)
    if contract_id:
        workstreams = [
            entry
            for entry in workstreams
            if (entry.get("contract") or {}).get("id") == contract_id
        ]

    now = current_time()
    summaries: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    attention: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    for entry in workstreams:
        workstream_id = entry["id"]
        live_state = store.get_live_state(workstream_id)
        packets = store.list_packets(workstream_id)
        workstream_decisions = store.list_decisions(workstream_id)
        review = review_summary(store, entry, live_state, packets, stale_days=stale_days, now=now)
        if review["reasons"]:
            attention.append(
                {
                    "workstream_id": workstream_id,
                    "title": entry.get("title"),
                    "reasons": review["reasons"],
                }
            )
        summaries.append(workstream_summary(entry, live_state, review))
        decisions.extend(workstream_decisions)
        for artifact in live_state.get("artifacts", []):
            artifacts.append(brief_artifact_summary(workstream_id, artifact, workstream_decisions))
            claims.extend(
                brief_claim_summary(workstream_id, artifact, claim, workstream_decisions)
                for claim in artifact.get("claims", [])
            )

    references = brief_reference_review(store, summaries, artifacts)
    return {
        "generated_at": format_datetime(now),
        "filters": {
            "program": program,
            "contract_id": contract_id,
            "stale_days": stale_days,
        },
        "counts": {
            "workstreams": len(workstreams),
            "attention": len(attention),
            "artifacts": len(artifacts),
            "claims": len(claims),
            "decisions": len(decisions),
            "explicit_refs": len(references["explicit_refs"]),
            "used_refs": len(references["used_refs"]),
        },
        "attention": attention,
        "workstreams": summaries,
        "artifacts": artifacts,
        "claims": claims,
        "contract_review": contract_review_from_brief(summaries, artifacts, claims, decisions),
        "next_context": next_context_from_decisions(decisions),
        "references": references,
    }


def workstream_summary(
    entry: dict[str, Any],
    live_state: dict[str, Any],
    review: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": entry["id"],
        "title": entry.get("title"),
        "status": entry.get("status"),
        "program": entry.get("program"),
        "contract": entry.get("contract"),
        "review": review,
        "next_intended_action": live_state.get("next_intended_action"),
        "rationale": live_state.get("rationale"),
        "results": live_state.get("results", []),
        "blockers": live_state.get("blockers", []),
        "limitations": live_state.get("limitations", []),
        "flags": live_state.get("flags", []),
        "deviations": live_state.get("deviations", []),
    }


def brief_artifact_summary(
    workstream_id: str,
    artifact: dict[str, Any],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    artifact_id = artifact["id"]
    return {
        "workstream_id": workstream_id,
        "id": artifact_id,
        "kind": artifact.get("kind"),
        "path": artifact.get("path"),
        "description": artifact.get("description"),
        "produced_by": artifact.get("produced_by"),
        "created_at": artifact.get("created_at"),
        "claims": len(artifact.get("claims", [])),
        "evidence": len(artifact.get("evidence", [])),
        "uncertainty": artifact.get("uncertainty"),
        "status": artifact.get("status"),
        "limitations": artifact.get("limitations", []),
        "used_refs": artifact.get("used_refs", []),
        "review": artifact.get("review", {}),
        "judgments": matching_decisions(
            decisions,
            target_type="artifact",
            candidate_ids=[artifact_id, f"{workstream_id}/{artifact_id}"],
        ),
    }


def brief_claim_summary(
    workstream_id: str,
    artifact: dict[str, Any],
    claim: dict[str, Any],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    artifact_id = artifact["id"]
    claim_id = claim["id"]
    return {
        "workstream_id": workstream_id,
        "artifact_id": artifact_id,
        "id": claim_id,
        "ref": f"{artifact_id}/{claim_id}",
        "text": claim.get("text"),
        "confidence": claim.get("confidence"),
        "evidence": claim.get("evidence", []),
        "caveats": claim.get("caveats", []),
        "judgments": matching_decisions(
            decisions,
            target_type="claim",
            candidate_ids=[
                claim_id,
                f"{artifact_id}/{claim_id}",
                f"{workstream_id}/{artifact_id}/{claim_id}",
            ],
        ),
    }


def matching_decisions(
    decisions: list[dict[str, Any]],
    *,
    target_type: str,
    candidate_ids: list[str],
) -> list[dict[str, Any]]:
    matches = []
    for decision in decisions:
        target = decision.get("target") or {"type": "workstream", "id": decision.get("workstream_id")}
        if target.get("type") == target_type and target.get("id") in candidate_ids:
            matches.append(decision)
    return matches


def next_context_from_decisions(decisions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    context: dict[str, list[dict[str, Any]]] = {bucket: [] for bucket in NEXT_CONTEXT_ORDER}
    for decision in decisions:
        bucket = NEXT_CONTEXT_BUCKETS.get(decision.get("action"))
        if bucket:
            context[bucket].append(
                {
                    "workstream_id": decision.get("workstream_id"),
                    "target": decision.get("target"),
                    "rationale": decision.get("rationale"),
                    "decision_id": decision.get("id"),
                }
            )
    return context


def normalized_comparison_text(value: str | None) -> str:
    text = " ".join(str(value or "").casefold().split())
    return text.strip(" \t\r\n.,;:")


def sorted_unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def artifact_ref_from_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "workstream_id": artifact.get("workstream_id"),
        "artifact_id": artifact.get("id"),
        "path": artifact.get("path"),
        "status": artifact.get("status"),
        "produced_by": artifact.get("produced_by"),
    }


ArtifactLookup = dict[tuple[Any, Any], dict[str, Any]]


def claim_ref_from_summary(claim: dict[str, Any], artifact_lookup: ArtifactLookup) -> dict[str, Any]:
    artifact = artifact_lookup.get((claim.get("workstream_id"), claim.get("artifact_id")), {})
    return {
        "workstream_id": claim.get("workstream_id"),
        "artifact_id": claim.get("artifact_id"),
        "claim_id": claim.get("id"),
        "ref": claim.get("ref"),
        "text": claim.get("text"),
        "confidence": claim.get("confidence"),
        "artifact_status": artifact.get("status"),
        "judgment_actions": [
            decision.get("action")
            for decision in claim.get("judgments", [])
            if decision.get("action")
        ],
    }


def grouped_claims(claims: list[dict[str, Any]], artifact_lookup: ArtifactLookup) -> list[dict[str, Any]]:
    """Group claims whose text matches after whitespace/case/punctuation normalisation."""
    groups: dict[str, dict[str, Any]] = {}
    for claim in claims:
        key = normalized_comparison_text(claim.get("text"))
        if not key:
            continue
        group = groups.setdefault(
            key,
            {
                "key": key,
                "text": claim.get("text"),
                "count": 0,
                "workstreams": [],
                "artifacts": [],
                "judgment_actions": [],
                "artifact_statuses": [],
                "claims": [],
            },
        )
        artifact = artifact_lookup.get((claim.get("workstream_id"), claim.get("artifact_id")), {})
        group["count"] += 1
        group["workstreams"].append(str(claim.get("workstream_id") or ""))
        group["artifacts"].append(
            "/".join(
                str(value)
                for value in [claim.get("workstream_id"), claim.get("artifact_id")]
                if value
            )
        )
        if artifact.get("status"):
            group["artifact_statuses"].append(str(artifact["status"]))
        for decision in claim.get("judgments", []):
            if decision.get("action"):
                group["judgment_actions"].append(str(decision["action"]))
        group["claims"].append(claim_ref_from_summary(claim, artifact_lookup))

    result = [
        {
            **group,
            "workstreams": sorted_unique(group["workstreams"]),
            "artifacts": sorted_unique(group["artifacts"]),
            "judgment_actions": sorted_unique(group["judgment_actions"]),
            "artifact_statuses": sorted_unique(group["artifact_statuses"]),
        }
        for group in groups.values()
    ]
    return sorted(result, key=lambda item: (-item["count"], item["text"] or ""))


def grouped_artifact_strings(
    artifacts: list[dict[str, Any]],
    field: str,
    *,
    key_name: str,
) -> list[dict[str, Any]]:
    """Group a string-list artefact field (limitations, used_refs) by normalised value."""
    groups: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        for value in artifact.get(field, []):
            key = normalized_comparison_text(value)
            if not key:
                continue
            group = groups.setdefault(
                key,
                {
                    key_name: value,
                    "count": 0,
                    "workstreams": [],
                    "artifacts": [],
                },
            )
            group["count"] += 1
            group["workstreams"].append(str(artifact.get("workstream_id") or ""))
            group["artifacts"].append(artifact_ref_from_summary(artifact))

    result = [
        {**group, "workstreams": sorted_unique(group["workstreams"])}
        for group in groups.values()
    ]
    return sorted(result, key=lambda item: (-item["count"], item[key_name] or ""))


def grouped_artifact_statuses(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        status = artifact.get("status") or "unknown"
        group = groups.setdefault(status, {"status": status, "count": 0, "artifacts": []})
        group["count"] += 1
        group["artifacts"].append(artifact_ref_from_summary(artifact))
    return sorted(groups.values(), key=lambda item: (-item["count"], item["status"]))


def contract_review_from_brief(
    workstreams: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    artifact_lookup: ArtifactLookup = {
        (artifact.get("workstream_id"), artifact.get("id")): artifact
        for artifact in artifacts
    }
    claim_groups = grouped_claims(claims, artifact_lookup)
    limitation_groups = grouped_artifact_strings(artifacts, "limitations", key_name="limitation")
    used_ref_groups = grouped_artifact_strings(artifacts, "used_refs", key_name="ref")
    next_context = next_context_from_decisions(decisions)

    repeated_claims = [group for group in claim_groups if group["count"] > 1]
    shared_limitations = [group for group in limitation_groups if group["count"] > 1]
    shared_refs = [group for group in used_ref_groups if group["count"] > 1]
    summary = [
        f"{len(artifacts)} artifacts across {len(workstreams)} workstreams.",
        f"{len(repeated_claims)} repeated claim groups by normalized exact text.",
        f"{len(shared_limitations)} shared limitation groups.",
        f"{len(shared_refs)} shared used-reference groups.",
        (
            "No deterministic contradiction inference yet; tensions require "
            "human judgment or a later reviewer-agent pass."
        ),
    ]
    return {
        "mode": "deterministic",
        "scope": {
            "workstreams": len(workstreams),
            "artifacts": len(artifacts),
            "claims": len(claims),
        },
        "summary": summary,
        "artifact_statuses": grouped_artifact_statuses(artifacts),
        "claim_groups": claim_groups,
        "repeated_claims": repeated_claims,
        "limitation_groups": limitation_groups,
        "shared_limitations": shared_limitations,
        "used_ref_groups": used_ref_groups,
        "shared_used_refs": shared_refs,
        "review_queue": {
            "needs_replication": next_context["needs_replication"],
            "needs_critique": next_context["needs_critique"],
            "do_not_propagate": next_context["do_not_propagate"],
            "safe_as_context": next_context["safe_as_context"],
            "trusted_local": next_context["trusted_local"],
            "unreviewed_artifacts": [
                artifact_ref_from_summary(artifact)
                for artifact in artifacts
                if not artifact.get("judgments")
            ],
            "unreviewed_claims": [
                claim_ref_from_summary(claim, artifact_lookup)
                for claim in claims
                if not claim.get("judgments")
            ],
        },
        "tensions": {
            "explicit": [],
            "note": (
                "This deterministic pass does not infer semantic contradictions. "
                "It only exposes repeated text, shared limitations, shared refs, "
                "and human judgment targets."
            ),
        },
    }
