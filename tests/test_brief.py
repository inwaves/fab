from __future__ import annotations

import unittest

from fab.brief import (
    NEXT_CONTEXT_ORDER,
    contract_review_from_brief,
    grouped_artifact_statuses,
    grouped_artifact_strings,
    grouped_claims,
    matching_decisions,
    next_context_from_decisions,
    normalized_comparison_text,
    sorted_unique,
)


def artifact(
    workstream_id: str,
    artifact_id: str,
    *,
    status: str | None = None,
    limitations: list[str] | None = None,
    used_refs: list[str] | None = None,
    judgments: list[dict] | None = None,
) -> dict:
    return {
        "workstream_id": workstream_id,
        "id": artifact_id,
        "path": f"runs/{workstream_id}/{artifact_id}.md",
        "status": status,
        "produced_by": "agent",
        "limitations": limitations or [],
        "used_refs": used_refs or [],
        "judgments": judgments or [],
    }


def claim(workstream_id: str, artifact_id: str, claim_id: str, text: str | None, judgments: list[dict] | None = None) -> dict:
    return {
        "workstream_id": workstream_id,
        "artifact_id": artifact_id,
        "id": claim_id,
        "ref": f"{artifact_id}/{claim_id}",
        "text": text,
        "confidence": "medium",
        "judgments": judgments or [],
    }


def decision(action: str, *, workstream_id: str = "ws_001", target: dict | None = None, decision_id: str = "dec_001") -> dict:
    record = {"id": decision_id, "workstream_id": workstream_id, "action": action, "rationale": f"because {action}"}
    if target is not None:
        record["target"] = target
    return record


class TextHelperTest(unittest.TestCase):
    def test_normalized_comparison_text(self) -> None:
        self.assertEqual(normalized_comparison_text("  Cluster   Stability.  "), "cluster stability")
        self.assertEqual(normalized_comparison_text(None), "")
        self.assertEqual(normalized_comparison_text("...;"), "")

    def test_sorted_unique_drops_falsy(self) -> None:
        self.assertEqual(sorted_unique(["b", "", "a", "b"]), ["a", "b"])


class GroupingTest(unittest.TestCase):
    def test_grouped_claims_merges_normalised_text_and_orders_by_count(self) -> None:
        artifacts = [
            artifact("ws_001", "art_001", status="completed"),
            artifact("ws_002", "art_001", status="completed_with_limitations"),
            artifact("ws_003", "art_001"),
        ]
        lookup = {(item["workstream_id"], item["id"]): item for item in artifacts}
        needs_replication = decision("needs-replication", target={"type": "claim", "id": "art_001/c"})
        actionless = {"id": "dec_099", "workstream_id": "ws_002", "target": {"type": "claim", "id": "art_001/c"}}
        claims = [
            claim("ws_003", "art_001", "c", "Unique claim."),
            claim("ws_001", "art_001", "c", "Seeded stability only."),
            claim("ws_002", "art_001", "c", "  seeded STABILITY only ", [needs_replication, actionless]),
            claim("ws_003", "art_001", "empty", ""),
            claim("ws_003", "art_001", "none", None),
        ]

        groups = grouped_claims(claims, lookup)

        self.assertEqual([group["count"] for group in groups], [2, 1])
        top = groups[0]
        self.assertEqual(top["key"], "seeded stability only")
        self.assertEqual(top["text"], "Seeded stability only.")
        self.assertEqual(top["workstreams"], ["ws_001", "ws_002"])
        self.assertEqual(top["artifacts"], ["ws_001/art_001", "ws_002/art_001"])
        self.assertEqual(top["judgment_actions"], ["needs-replication"])
        self.assertEqual(top["artifact_statuses"], ["completed", "completed_with_limitations"])
        self.assertEqual(top["claims"][1]["judgment_actions"], ["needs-replication"])
        self.assertEqual(top["claims"][1]["artifact_status"], "completed_with_limitations")
        self.assertIsNone(groups[1]["claims"][0]["artifact_status"])

    def test_grouped_artifact_strings_skips_blank_values(self) -> None:
        artifacts = [
            artifact("ws_001", "art_001", limitations=["Same limit", "   "]),
            artifact("ws_002", "art_001", limitations=["  same LIMIT. ", "Other"]),
        ]

        groups = grouped_artifact_strings(artifacts, "limitations", key_name="limitation")

        self.assertEqual([(group["limitation"], group["count"]) for group in groups], [("Same limit", 2), ("Other", 1)])
        self.assertEqual(groups[0]["workstreams"], ["ws_001", "ws_002"])
        self.assertEqual(groups[0]["artifacts"][0]["artifact_id"], "art_001")

    def test_grouped_artifact_statuses_defaults_to_unknown(self) -> None:
        artifacts = [
            artifact("ws_001", "art_001"),
            artifact("ws_002", "art_001", status="completed"),
            artifact("ws_003", "art_001", status="completed"),
        ]

        groups = grouped_artifact_statuses(artifacts)

        self.assertEqual([(group["status"], group["count"]) for group in groups], [("completed", 2), ("unknown", 1)])


class DecisionProjectionTest(unittest.TestCase):
    def test_next_context_buckets_every_mapped_action_and_ignores_others(self) -> None:
        actions = [
            "trust-local",
            "safe-as-context",
            "replicate",
            "needs-replication",
            "needs-critique",
            "reject",
            "do-not-propagate",
            "quarantine",
            "escalate",
            "continue",
        ]
        decisions = [decision(action, decision_id=f"dec_{index:03d}") for index, action in enumerate(actions, start=1)]

        context = next_context_from_decisions(decisions)

        self.assertEqual(tuple(context), NEXT_CONTEXT_ORDER)
        self.assertEqual({bucket: len(items) for bucket, items in context.items()}, {
            "trusted_local": 1,
            "safe_as_context": 1,
            "needs_replication": 2,
            "needs_critique": 1,
            "do_not_propagate": 3,
        })
        self.assertEqual(context["trusted_local"][0]["decision_id"], "dec_001")
        self.assertIsNone(context["trusted_local"][0]["target"])

    def test_matching_decisions_defaults_legacy_records_to_workstream_target(self) -> None:
        legacy = decision("continue")
        artifact_judgment = decision("needs-critique", target={"type": "artifact", "id": "ws_001/art_001"})

        self.assertEqual(
            matching_decisions([legacy, artifact_judgment], target_type="workstream", candidate_ids=["ws_001"]),
            [legacy],
        )
        self.assertEqual(
            matching_decisions([legacy, artifact_judgment], target_type="artifact", candidate_ids=["art_001", "ws_001/art_001"]),
            [artifact_judgment],
        )
        self.assertEqual(matching_decisions([legacy], target_type="claim", candidate_ids=["x"]), [])

    def test_contract_review_lists_unreviewed_targets_and_shared_groups(self) -> None:
        judged = decision("needs-critique", target={"type": "artifact", "id": "art_001"})
        artifacts = [
            artifact("ws_001", "art_001", status="completed", limitations=["Missing labels"], used_refs=["alexandria://a.md"], judgments=[judged]),
            artifact("ws_002", "art_001", status="completed", limitations=["missing labels"], used_refs=["alexandria://a.md"]),
        ]
        claim_judgment = decision("safe-as-context", target={"type": "claim", "id": "art_001/c"}, workstream_id="ws_001")
        claims = [
            claim("ws_001", "art_001", "c", "Same claim", [claim_judgment]),
            claim("ws_002", "art_001", "c", "same claim"),
        ]
        workstreams = [{"id": "ws_001"}, {"id": "ws_002"}]

        review = contract_review_from_brief(workstreams, artifacts, claims, [judged, claim_judgment])

        self.assertEqual(review["mode"], "deterministic")
        self.assertEqual(review["scope"], {"workstreams": 2, "artifacts": 2, "claims": 2})
        self.assertEqual(review["summary"][0], "2 artifacts across 2 workstreams.")
        self.assertEqual(len(review["repeated_claims"]), 1)
        self.assertEqual(len(review["shared_limitations"]), 1)
        self.assertEqual(review["shared_used_refs"][0]["ref"], "alexandria://a.md")
        self.assertEqual(
            [item["workstream_id"] for item in review["review_queue"]["unreviewed_artifacts"]],
            ["ws_002"],
        )
        self.assertEqual(
            [item["workstream_id"] for item in review["review_queue"]["unreviewed_claims"]],
            ["ws_002"],
        )
        self.assertEqual(len(review["review_queue"]["needs_critique"]), 1)
        self.assertEqual(len(review["review_queue"]["safe_as_context"]), 1)
        self.assertEqual(review["artifact_statuses"], [{
            "status": "completed",
            "count": 2,
            "artifacts": [
                {"workstream_id": "ws_001", "artifact_id": "art_001", "path": "runs/ws_001/art_001.md", "status": "completed", "produced_by": "agent"},
                {"workstream_id": "ws_002", "artifact_id": "art_001", "path": "runs/ws_002/art_001.md", "status": "completed", "produced_by": "agent"},
            ],
        }])
        self.assertEqual(review["tensions"]["explicit"], [])


if __name__ == "__main__":
    unittest.main()
