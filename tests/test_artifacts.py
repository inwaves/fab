from __future__ import annotations

import unittest

from fab.artifacts import (
    ARTIFACT_PROVENANCE_FIELDS,
    artifact_ids,
    artifact_target_exists,
    claim_target_exists,
    normalize_artifact_claims,
    normalize_artifact_evidence,
    normalize_artifact_provenance,
    normalize_artifact_ref,
    normalize_artifact_refs,
    normalize_artifact_reproduction,
    normalize_artifact_review,
)
from fab.errors import RegistryError


class ClaimNormalisationTest(unittest.TestCase):
    def test_strings_and_aliases_are_accepted(self) -> None:
        self.assertEqual(
            normalize_artifact_claims("just text"),
            [{"id": "claim_001", "text": "just text", "confidence": None, "evidence": [], "caveats": []}],
        )
        claims = normalize_artifact_claims(
            ["first", {"claim": "alias text", "evidence_ids": "ev_1", "confidence": "low"}]
        )
        self.assertEqual([claim["id"] for claim in claims], ["claim_001", "claim_002"])
        self.assertEqual(claims[1]["text"], "alias text")
        self.assertEqual(claims[1]["evidence"], ["ev_1"])
        self.assertEqual(claims[1]["confidence"], "low")
        self.assertEqual(normalize_artifact_claims(None), [])

    def test_rejections(self) -> None:
        cases = [
            ({"text": "x"}, "artifact claims must be a list"),
            ([42], "artifact claim must be an object"),
            ([{"id": "dup", "text": "a"}, {"id": "dup", "text": "b"}], "duplicate claim id: dup"),
            ([{"id": "c1"}], "artifact claim text is required: c1"),
            ([{"id": "../c", "text": "x"}], "invalid claim id"),
        ]
        for value, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(RegistryError, message):
                    normalize_artifact_claims(value)


class EvidenceNormalisationTest(unittest.TestCase):
    def test_strings_and_aliases_are_accepted(self) -> None:
        self.assertEqual(
            normalize_artifact_evidence("summary only"),
            [{"id": "ev_001", "kind": "evidence", "summary": "summary only", "path": None, "refs": []}],
        )
        evidence = normalize_artifact_evidence(
            [{"description": "d"}, {"text": "t", "kind": "plot", "path": "p.png", "refs": "r://1"}]
        )
        self.assertEqual([item["summary"] for item in evidence], ["d", "t"])
        self.assertEqual(evidence[1]["kind"], "plot")
        self.assertEqual(evidence[1]["refs"], ["r://1"])
        self.assertEqual(normalize_artifact_evidence(None), [])

    def test_rejections(self) -> None:
        cases = [
            ({"summary": "x"}, "artifact evidence must be a list"),
            ([42], "artifact evidence must be an object"),
            ([{"id": "dup", "summary": "a"}, {"id": "dup", "summary": "b"}], "duplicate evidence id: dup"),
            ([{"id": "e1"}], "artifact evidence summary is required: e1"),
            ([{"id": "e 1", "summary": "x"}], "invalid evidence id"),
        ]
        for value, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(RegistryError, message):
                    normalize_artifact_evidence(value)


class ArtifactBlockNormalisationTest(unittest.TestCase):
    def test_reproduction_accepts_notes_string_and_rejects_lists(self) -> None:
        self.assertEqual(
            normalize_artifact_reproduction("notes only"),
            {"commands": [], "environment": [], "notes": "notes only"},
        )
        self.assertEqual(normalize_artifact_reproduction(None), {"commands": [], "environment": [], "notes": None})
        self.assertEqual(
            normalize_artifact_reproduction({"commands": "one", "environment": ["a", ""]}),
            {"commands": ["one"], "environment": ["a"], "notes": None},
        )
        with self.assertRaisesRegex(RegistryError, "artifact reproduction must be an object"):
            normalize_artifact_reproduction(["cmd"])

    def test_provenance_fills_every_field_and_drops_unknown_ones(self) -> None:
        normalized = normalize_artifact_provenance({"code": "one", "datasets": None, "unknown": ["x"]})

        self.assertEqual(tuple(normalized), ARTIFACT_PROVENANCE_FIELDS)
        self.assertEqual(normalized["code"], ["one"])
        self.assertEqual(normalized["datasets"], [])
        self.assertEqual(normalize_artifact_provenance(None)["outputs"], [])
        with self.assertRaisesRegex(RegistryError, "artifact provenance must be an object"):
            normalize_artifact_provenance("code")
        with self.assertRaisesRegex(RegistryError, "artifact provenance code must be a list"):
            normalize_artifact_provenance({"code": {"a": 1}})

    def test_review_defaults_to_local_only(self) -> None:
        self.assertEqual(
            normalize_artifact_review(None),
            {"local_only": True, "safe_to_reuse": False, "notes": None},
        )
        self.assertEqual(
            normalize_artifact_review({"local_only": 0, "safe_to_reuse": 1, "notes": "n"}),
            {"local_only": False, "safe_to_reuse": True, "notes": "n"},
        )
        with self.assertRaisesRegex(RegistryError, "artifact review must be an object"):
            normalize_artifact_review("yes")


class ArtifactRefTest(unittest.TestCase):
    def test_defaults_and_aliases(self) -> None:
        artifact = normalize_artifact_ref(
            {
                "id": "art_009",
                "path": "runs/x.md",
                "failures": ["unseeded run"],
                "follow_up": "label neighbours",
                "produced_by": "other-agent",
                "created_at": "2026-01-01T00:00:00Z",
            },
            source="agent-a",
            created_at="now",
            existing_ids=[],
        )

        self.assertEqual(artifact["kind"], "artifact")
        self.assertEqual(artifact["produced_by"], "other-agent")
        self.assertEqual(artifact["created_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(artifact["failed_attempts"], ["unseeded run"])
        self.assertEqual(artifact["suggested_follow_up"], ["label neighbours"])
        self.assertIsNone(artifact["status"])
        self.assertTrue(artifact["review"]["local_only"])

    def test_rejections(self) -> None:
        with self.assertRaisesRegex(RegistryError, "artifact path is required"):
            normalize_artifact_ref({"id": "art_001"}, source="a", created_at="t", existing_ids=[])
        with self.assertRaisesRegex(RegistryError, "artifact already exists: art_001"):
            normalize_artifact_ref(
                {"id": "art_001", "path": "p"}, source="a", created_at="t", existing_ids=["art_001"]
            )
        with self.assertRaisesRegex(RegistryError, "invalid artifact id: a/b"):
            normalize_artifact_ref({"id": "a/b", "path": "p"}, source="a", created_at="t", existing_ids=[])

    def test_refs_number_plain_paths_before_structured_ones(self) -> None:
        artifacts = normalize_artifact_refs(
            ["a.md", "", "b.md"],
            [{"path": "c.md"}, {"id": "custom", "path": "d.md", "kind": "plot"}],
            source="agent",
            created_at="now",
            existing_ids=["art_002"],
        )

        self.assertEqual([item["id"] for item in artifacts], ["art_003", "art_004", "art_005", "custom"])
        self.assertEqual([item["path"] for item in artifacts], ["a.md", "b.md", "c.md", "d.md"])
        self.assertEqual(artifacts[-1]["kind"], "plot")
        self.assertEqual(normalize_artifact_refs(None, None, source="s", created_at="t", existing_ids=[]), [])


class TargetLookupTest(unittest.TestCase):
    live_state = {
        "artifacts": [
            {"id": "art_001", "claims": [{"id": "claim_a"}]},
            {"id": "art_002", "claims": []},
        ]
    }

    def test_artifact_targets(self) -> None:
        self.assertTrue(artifact_target_exists(self.live_state, "art_001"))
        self.assertTrue(artifact_target_exists(self.live_state, "ws_001/art_002"))
        self.assertFalse(artifact_target_exists(self.live_state, "art_009"))
        self.assertFalse(artifact_target_exists({}, "art_001"))

    def test_claim_targets(self) -> None:
        self.assertTrue(claim_target_exists(self.live_state, "claim_a"))
        self.assertTrue(claim_target_exists(self.live_state, "art_001/claim_a"))
        self.assertTrue(claim_target_exists(self.live_state, "ws_001/art_001/claim_a"))
        self.assertFalse(claim_target_exists(self.live_state, "art_002/claim_a"))
        self.assertFalse(claim_target_exists(self.live_state, "claim_zzz"))

    def test_artifact_ids_ignores_malformed_entries(self) -> None:
        self.assertEqual(artifact_ids([{"id": "x"}, {"no": 1}, "str", {"id": ""}, {"id": 7}]), ["x", "7"])


if __name__ == "__main__":
    unittest.main()
