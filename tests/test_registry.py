from __future__ import annotations

import json
import stat
import tempfile
import unittest
from pathlib import Path

from fab.registry import RegistryError, RegistryStore


def write_run_bundle(bundle: Path, manifest: dict, *, ready: bool = True) -> None:
    artifact = bundle / "artifact"
    (artifact / "code").mkdir(parents=True, exist_ok=True)
    (artifact / "results").mkdir(parents=True, exist_ok=True)
    (artifact / "logs").mkdir(parents=True, exist_ok=True)
    (artifact / "report.md").write_text("# Report\n", encoding="utf-8")
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if ready:
        (bundle / "READY").touch()


class RegistryStoreTest(unittest.TestCase):
    def test_create_workstream_separates_entry_and_live_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            entry = store.create_workstream(
                title="A3 false-positive reduction",
                program="safety-finetuning",
                owner="human",
            )

            self.assertEqual(entry["id"], "ws_001")
            self.assertEqual(entry["status"], "planned")
            self.assertIsNone(entry["live_state"]["updated_at"])

            live_state = store.get_live_state("ws_001")
            self.assertEqual(live_state["workstream_id"], "ws_001")
            self.assertIsNone(live_state["rationale"])

    def test_packet_updates_live_state_without_rewriting_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.write_contract_version(
                "contract_001",
                1,
                "# Contract: A3 false-positive reduction\n\n## Research Question\nTest.\n",
            )
            store.create_workstream(
                title="A3 false-positive reduction",
                program="safety-finetuning",
                contract_id="contract_001",
                contract_version=1,
            )

            packet = store.add_state_packet(
                "ws_001",
                source="agent-a",
                tried="baseline false-positive eval",
                result="found cluster around ambiguous refusals",
                next_action="test narrower data filter",
                rationale="cluster is measurable and tied to the contract",
                flag=["needs transfer check"],
            )

            self.assertEqual(packet["id"], "pkt_001")
            entry = store.get_workstream("ws_001")
            self.assertEqual(entry["contract"]["id"], "contract_001")

            live_state = store.get_live_state("ws_001")
            self.assertEqual(live_state["next_intended_action"], "test narrower data filter")
            self.assertEqual(
                live_state["rationale"],
                "cluster is measurable and tied to the contract",
            )
            self.assertIn("needs transfer check", live_state["flags"])

    def test_plain_artifact_path_becomes_structured_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="A3 false-positive reduction", program="safety-finetuning")

            packet = store.add_state_packet(
                "ws_001",
                source="agent-a",
                artifact=["runs/ws_001/baseline-report.md"],
            )

            artifact = packet["artifacts"][0]
            self.assertEqual(artifact["id"], "art_001")
            self.assertEqual(artifact["kind"], "artifact")
            self.assertEqual(artifact["path"], "runs/ws_001/baseline-report.md")
            self.assertEqual(artifact["produced_by"], "agent-a")
            self.assertTrue(artifact["review"]["local_only"])
            self.assertFalse(artifact["review"]["safe_to_reuse"])
            self.assertEqual(store.get_live_state("ws_001")["artifacts"], [artifact])

    def test_structured_artifact_reference_preserves_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="A3 false-positive reduction", program="safety-finetuning")

            packet = store.add_state_packet(
                "ws_001",
                source="agent-a",
                artifact_ref=[
                    {
                        "kind": "report",
                        "path": "runs/ws_001/baseline-report.md",
                        "description": "Baseline eval summary",
                        "claims": [
                            {
                                "id": "claim_cluster",
                                "text": "A baseline cluster is stable enough to inspect.",
                                "confidence": "medium",
                                "evidence": ["ev_stability"],
                                "caveats": ["human labels are missing"],
                            }
                        ],
                        "evidence": [
                            {
                                "id": "ev_stability",
                                "kind": "metric",
                                "summary": "Cluster assignments are stable across seeded runs.",
                                "path": "runs/ws_001/stability.json",
                            }
                        ],
                        "failed_attempts": ["unseeded run was too noisy"],
                        "uncertainty": "not yet validated",
                        "reproduction": {
                            "commands": ["uv run python src/evals/refusal_eval.py"],
                            "environment": ["python 3.12"],
                            "notes": "uses a fixed seed",
                        },
                        "suggested_follow_up": ["human-label nearest neighbors"],
                        "provenance": {
                            "code": ["src/evals/refusal_eval.py"],
                            "configs": ["configs/refusal_eval.toml"],
                            "datasets": ["data/refusal-benign-v1.jsonl"],
                            "models": ["qwen-8b-lora-run-003"],
                            "prompts": ["prompts/refusal-eval-v2.md"],
                            "evals": ["evals/refusal-fp-v1"],
                            "outputs": ["runs/ws_001/baseline-report.md"],
                        },
                    }
                ],
            )

            artifact = packet["artifacts"][0]
            self.assertEqual(artifact["id"], "art_001")
            self.assertEqual(artifact["kind"], "report")
            self.assertEqual(artifact["description"], "Baseline eval summary")
            self.assertEqual(artifact["claims"][0]["id"], "claim_cluster")
            self.assertEqual(artifact["claims"][0]["evidence"], ["ev_stability"])
            self.assertEqual(artifact["evidence"][0]["path"], "runs/ws_001/stability.json")
            self.assertEqual(artifact["failed_attempts"], ["unseeded run was too noisy"])
            self.assertEqual(artifact["uncertainty"], "not yet validated")
            self.assertEqual(
                artifact["reproduction"]["commands"],
                ["uv run python src/evals/refusal_eval.py"],
            )
            self.assertEqual(artifact["suggested_follow_up"], ["human-label nearest neighbors"])
            self.assertEqual(artifact["provenance"]["code"], ["src/evals/refusal_eval.py"])
            self.assertEqual(artifact["provenance"]["configs"], ["configs/refusal_eval.toml"])
            self.assertEqual(artifact["provenance"]["evals"], ["evals/refusal-fp-v1"])
            self.assertEqual(artifact["provenance"]["outputs"], ["runs/ws_001/baseline-report.md"])

    def test_ingest_run_bundle_appends_packet_and_artifact_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = RegistryStore.at(root / "store")
            store.write_contract_version("contract_001", 1, "# Contract\n")
            store.create_workstream(
                title="A3 false-positive reduction",
                program="safety-finetuning",
                contract_id="contract_001",
                contract_version=1,
            )
            bundle = root / "run-abc123"
            write_run_bundle(
                bundle,
                {
                    "workstream_id": "ws_001",
                    "contract": {"id": "contract_001", "version": 1},
                    "source": "podium/run-abc123",
                    "summary": "Audited the baseline cluster claim.",
                    "status": "completed_with_limitations",
                    "claims": [
                        "The baseline evidence currently supports seeded stability only."
                    ],
                    "evidence": [
                        {
                            "summary": "Report summarizes the stability audit.",
                            "path": "artifact/report.md",
                        }
                    ],
                    "limitations": ["Original model artifacts were unavailable."],
                    "next": ["Rerun with the original model."],
                    "used_refs": ["alexandria://papers/a3.md"],
                },
            )

            packet = store.ingest_run_bundle(bundle)

            self.assertEqual(packet["id"], "pkt_001")
            self.assertEqual(packet["source"], "podium/run-abc123")
            self.assertEqual(packet["result"], "Audited the baseline cluster claim.")
            self.assertEqual(packet["limitations"], ["Original model artifacts were unavailable."])
            self.assertEqual(packet["ingest"]["status"], "completed_with_limitations")

            artifact = packet["artifacts"][0]
            self.assertEqual(artifact["path"], str(bundle / "artifact"))
            self.assertEqual(artifact["description"], "Audited the baseline cluster claim.")
            self.assertEqual(artifact["status"], "completed_with_limitations")
            self.assertEqual(
                artifact["claims"][0]["text"],
                "The baseline evidence currently supports seeded stability only.",
            )
            self.assertEqual(artifact["evidence"][0]["path"], "artifact/report.md")
            self.assertEqual(artifact["limitations"], ["Original model artifacts were unavailable."])
            self.assertEqual(artifact["suggested_follow_up"], ["Rerun with the original model."])
            self.assertEqual(artifact["used_refs"], ["alexandria://papers/a3.md"])

            live_state = store.get_live_state("ws_001")
            self.assertEqual(live_state["limitations"], ["Original model artifacts were unavailable."])
            self.assertIn("limited", store.review_workstreams()[0]["review"]["reasons"])

    def test_ingest_run_bundle_requires_ready_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = RegistryStore.at(root / "store")
            store.write_contract_version("contract_001", 1, "# Contract\n")
            store.create_workstream(
                title="A3 false-positive reduction",
                program="safety-finetuning",
                contract_id="contract_001",
                contract_version=1,
            )
            bundle = root / "run-abc123"
            write_run_bundle(
                bundle,
                {
                    "workstream_id": "ws_001",
                    "contract": {"id": "contract_001", "version": 1},
                    "source": "podium/run-abc123",
                    "summary": "Audited the baseline cluster claim.",
                    "status": "completed",
                    "claims": [],
                    "evidence": [],
                    "limitations": [],
                    "next": [],
                    "used_refs": [],
                },
                ready=False,
            )

            with self.assertRaisesRegex(RegistryError, "missing .*READY"):
                store.ingest_run_bundle(bundle)

    def test_ingest_run_bundle_rejects_contract_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = RegistryStore.at(root / "store")
            store.write_contract_version("contract_001", 1, "# Contract\n")
            store.create_workstream(
                title="A3 false-positive reduction",
                program="safety-finetuning",
                contract_id="contract_001",
                contract_version=1,
            )
            bundle = root / "run-abc123"
            write_run_bundle(
                bundle,
                {
                    "workstream_id": "ws_001",
                    "contract": {"id": "contract_001", "version": 2},
                    "source": "podium/run-abc123",
                    "summary": "Audited the baseline cluster claim.",
                    "status": "completed",
                    "claims": [],
                    "evidence": [],
                    "limitations": [],
                    "next": [],
                    "used_refs": [],
                },
            )

            with self.assertRaisesRegex(RegistryError, "contract does not match"):
                store.ingest_run_bundle(bundle)

    def test_decision_can_target_artifact_or_claim_without_changing_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="A3 false-positive reduction", program="safety-finetuning")
            store.add_state_packet(
                "ws_001",
                source="agent-a",
                artifact_ref=[
                    {
                        "kind": "report",
                        "path": "runs/ws_001/baseline-report.md",
                        "claims": [
                            {
                                "id": "claim_cluster",
                                "text": "A baseline cluster is stable enough to inspect.",
                            }
                        ],
                    }
                ],
            )

            artifact_decision = store.add_decision(
                "ws_001",
                action="needs-critique",
                target_type="artifact",
                target_id="art_001",
                rationale="artifact is useful but needs a second pass",
            )
            claim_decision = store.add_decision(
                "ws_001",
                action="needs-replication",
                target_type="claim",
                target_id="art_001/claim_cluster",
                rationale="claim is plausible but not ready as shared context",
            )

            self.assertEqual(artifact_decision["target"], {"type": "artifact", "id": "art_001"})
            self.assertEqual(
                claim_decision["target"],
                {"type": "claim", "id": "art_001/claim_cluster"},
            )
            self.assertEqual(artifact_decision["status_after"], "planned")
            self.assertEqual(claim_decision["status_after"], "planned")
            self.assertEqual(store.get_workstream("ws_001")["status"], "planned")

    def test_brief_summarizes_claims_attention_and_next_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="A3 false-positive reduction", program="safety-finetuning")
            store.add_state_packet(
                "ws_001",
                source="agent-a",
                result="found a stable ambiguous-refusal cluster",
                rationale="cluster is measurable enough to inspect",
                artifact_ref=[
                    {
                        "kind": "report",
                        "path": "runs/ws_001/baseline-report.md",
                        "claims": [
                            {
                                "id": "claim_cluster",
                                "text": "A baseline cluster is stable enough to inspect.",
                                "confidence": "medium",
                            }
                        ],
                        "evidence": ["seeded runs agree on cluster membership"],
                    }
                ],
            )
            store.add_decision(
                "ws_001",
                action="safe-as-context",
                target_type="claim",
                target_id="art_001/claim_cluster",
                rationale="safe to include in the next research context with caveats",
            )

            brief = store.brief(program="safety-finetuning")

            self.assertEqual(brief["counts"]["workstreams"], 1)
            self.assertEqual(brief["counts"]["artifacts"], 1)
            self.assertEqual(brief["counts"]["claims"], 1)
            self.assertEqual(brief["claims"][0]["text"], "A baseline cluster is stable enough to inspect.")
            self.assertEqual(brief["claims"][0]["judgments"][0]["action"], "safe-as-context")
            self.assertIn("no_contract", brief["attention"][0]["reasons"])
            self.assertEqual(
                brief["next_context"]["safe_as_context"][0]["target"],
                {"type": "claim", "id": "art_001/claim_cluster"},
            )

    def test_brief_contract_review_rolls_up_claims_limitations_and_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.write_contract_version("contract_001", 1, "# Contract\n")
            store.write_contract_version("contract_002", 1, "# Other Contract\n")
            store.create_workstream(
                title="Cluster audit A",
                program="safety-finetuning",
                contract_id="contract_001",
                contract_version=1,
            )
            store.create_workstream(
                title="Cluster audit B",
                program="safety-finetuning",
                contract_id="contract_001",
                contract_version=1,
            )
            store.create_workstream(
                title="Other contract work",
                program="safety-finetuning",
                contract_id="contract_002",
                contract_version=1,
            )
            for workstream_id, source, claim_text in [
                ("ws_001", "agent-a", "Cluster stability is only seeded stability."),
                ("ws_002", "agent-b", "  cluster stability is only seeded stability.  "),
                ("ws_003", "agent-c", "This claim is out of scope for contract 001."),
            ]:
                store.add_state_packet(
                    workstream_id,
                    source=source,
                    result="audited cluster stability",
                    rationale="the contract asks whether the cluster claim is reliable",
                    artifact_ref=[
                        {
                            "path": f"runs/{workstream_id}/report.md",
                            "status": "completed_with_limitations",
                            "claims": [
                                {
                                    "id": "claim_stability",
                                    "text": claim_text,
                                }
                            ],
                            "evidence": ["report describes the stability axis"],
                            "limitations": ["Original model artifacts were unavailable."],
                            "used_refs": [
                                "alexandria://papers/a3-an-automated-alignment-agent-for-safety-finetun.md"
                            ],
                        }
                    ],
                )
            store.add_decision(
                "ws_001",
                action="needs-replication",
                target_type="claim",
                target_id="art_001/claim_stability",
                rationale="same claim should be rerun with the original model",
            )

            brief = store.brief(contract_id="contract_001")
            review = brief["contract_review"]

            self.assertEqual(brief["counts"]["workstreams"], 2)
            self.assertEqual(review["mode"], "deterministic")
            self.assertEqual(review["scope"], {"workstreams": 2, "artifacts": 2, "claims": 2})
            self.assertEqual(len(review["repeated_claims"]), 1)
            self.assertEqual(review["repeated_claims"][0]["count"], 2)
            self.assertEqual(
                review["repeated_claims"][0]["workstreams"],
                ["ws_001", "ws_002"],
            )
            self.assertEqual(len(review["shared_limitations"]), 1)
            self.assertEqual(review["shared_limitations"][0]["count"], 2)
            self.assertEqual(len(review["shared_used_refs"]), 1)
            self.assertEqual(review["shared_used_refs"][0]["count"], 2)
            self.assertEqual(
                review["review_queue"]["needs_replication"][0]["target"],
                {"type": "claim", "id": "art_001/claim_stability"},
            )
            self.assertEqual(
                [claim["workstream_id"] for claim in review["review_queue"]["unreviewed_claims"]],
                ["ws_002"],
            )
            self.assertIn("No deterministic contradiction inference yet", review["summary"][-1])

    def test_reference_check_resolves_explicit_alexandria_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            alexandria = root / "alexandria"
            note = alexandria / "papers" / "a3.md"
            note.parent.mkdir(parents=True)
            note.write_text(
                '---\ntitle: "A3 Note"\n---\n\n# Ignored H1\n\nBody.\n',
                encoding="utf-8",
            )
            store = RegistryStore.at(root / ".fab")
            store.add_source("alexandria", alexandria, uri_prefix="alexandria://")
            store.write_contract_version(
                "contract_001",
                1,
                "Use `alexandria://papers/a3.md` and `alexandria://papers/missing.md`.\n"
                "Also see https://example.com/context.\n",
            )

            result = store.check_references(contract_id="contract_001", version=1)

            by_uri = {entry["uri"]: entry["resolution"] for entry in result["explicit_refs"]}
            self.assertEqual(by_uri["alexandria://papers/a3.md"]["status"], "resolved")
            self.assertEqual(by_uri["alexandria://papers/a3.md"]["title"], "A3 Note")
            self.assertTrue(by_uri["alexandria://papers/a3.md"]["content_hash"].startswith("sha256:"))
            self.assertEqual(by_uri["alexandria://papers/missing.md"]["status"], "unresolved")
            self.assertEqual(by_uri["https://example.com/context"]["status"], "external")
            self.assertEqual(
                result["comparison"]["unresolved_explicit"][0]["uri"],
                "alexandria://papers/missing.md",
            )

    def test_brief_reference_review_compares_contract_and_used_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            alexandria = root / "alexandria"
            for relpath, title in [
                ("papers/a3.md", "A3 Note"),
                ("papers/extra.md", "Extra Note"),
            ]:
                path = alexandria / relpath
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"---\ntitle: \"{title}\"\n---\n\nBody.\n", encoding="utf-8")

            store = RegistryStore.at(root / ".fab")
            store.add_source("alexandria", alexandria, uri_prefix="alexandria://")
            store.write_contract_version(
                "contract_001",
                1,
                "Background: alexandria://papers/a3.md and alexandria://papers/not-used.md\n",
            )
            store.create_workstream(
                title="A3 false-positive reduction",
                program="safety-finetuning",
                contract_id="contract_001",
                contract_version=1,
            )
            store.add_state_packet(
                "ws_001",
                source="agent-a",
                rationale="checked explicit references",
                artifact_ref=[
                    {
                        "path": "runs/ws_001/report.md",
                        "claims": ["Reference comparison works."],
                        "used_refs": [
                            "alexandria://papers/a3.md",
                            "alexandria://papers/extra.md",
                        ],
                    }
                ],
            )

            brief = store.brief(contract_id="contract_001")
            references = brief["references"]

            self.assertEqual(brief["counts"]["explicit_refs"], 2)
            self.assertEqual(brief["counts"]["used_refs"], 2)
            self.assertEqual(
                references["comparison"]["used_not_explicit"],
                ["alexandria://papers/extra.md"],
            )
            self.assertEqual(
                references["comparison"]["explicit_not_used"],
                ["alexandria://papers/not-used.md"],
            )
            self.assertEqual(
                references["comparison"]["unresolved_explicit"][0]["uri"],
                "alexandria://papers/not-used.md",
            )

    def test_decision_can_change_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="Control protocol", program="control")

            decision = store.add_decision(
                "ws_001",
                action="quarantine",
                rationale="unexpected eval leakage path",
                actor="human",
            )

            self.assertEqual(decision["status_before"], "planned")
            self.assertEqual(decision["status_after"], "quarantined")
            self.assertEqual(store.get_workstream("ws_001")["status"], "quarantined")

    def test_links_related_workstreams(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="Direction A", program="pilot")
            store.create_workstream(title="Direction B", program="pilot")

            updated = store.link_workstreams("ws_001", "ws_002", relationship="related")

            self.assertEqual(updated["relationships"]["related"], ["ws_002"])

    def test_contract_versions_are_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))

            path = store.contract_version_path("contract_001", 1)

            self.assertEqual(path, Path(tmp) / "contracts" / "contract_001" / "v001.md")

    def test_contract_id_must_be_safe_path_segment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))

            with self.assertRaisesRegex(RegistryError, "invalid contract id"):
                store.contract_version_path("../contract_001", 1)

    def test_contract_version_write_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            path = store.write_contract_version("contract_001", 1, "# Contract\n")

            self.assertEqual(path.read_text(encoding="utf-8"), "# Contract\n")
            with self.assertRaisesRegex(RegistryError, "already exists"):
                store.write_contract_version("contract_001", 1, "# Changed\n")

    def test_attach_contract_requires_existing_versioned_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="A3 false-positive reduction", program="safety-finetuning")

            with self.assertRaisesRegex(RegistryError, "contract version not found"):
                store.attach_contract("ws_001", contract_id="contract_001", version=1)

            store.write_contract_version("contract_001", 1, "# Contract\n")
            updated = store.attach_contract("ws_001", contract_id="contract_001", version=1)

            self.assertEqual(updated["contract"], {"id": "contract_001", "version": 1})

    def test_attach_contract_locks_manual_contract_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.init()
            store.create_workstream(title="A3 false-positive reduction", program="safety-finetuning")
            path = store.contract_version_path("contract_001", 1)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Contract\n", encoding="utf-8")

            store.attach_contract("ws_001", contract_id="contract_001", version=1)

            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertFalse(mode & stat.S_IWUSR)

    def test_show_includes_attached_contract_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.write_contract_version("contract_001", 1, "# Contract\n\n## Brief\nTest.\n")
            store.create_workstream(
                title="A3 false-positive reduction",
                program="safety-finetuning",
                contract_id="contract_001",
                contract_version=1,
            )

            shown = store.show("ws_001")

            self.assertEqual(shown["attached_contract"]["id"], "contract_001")
            self.assertEqual(shown["attached_contract"]["version"], 1)
            self.assertTrue(shown["attached_contract"]["exists"])
            self.assertIn("## Brief", shown["attached_contract"]["text"])

    def test_review_flags_new_workstream_attention_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="Unscoped direction", program="pilot")

            review_items = store.review_workstreams()

            self.assertEqual(len(review_items), 1)
            reasons = review_items[0]["review"]["reasons"]
            self.assertIn("no_contract", reasons)
            self.assertIn("no_state_packet", reasons)
            self.assertIn("missing_rationale", reasons)

    def test_review_filters_by_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="Unscoped direction", program="pilot")
            store.write_contract_version("contract_001", 1, "# Contract\n")
            store.create_workstream(
                title="Scoped direction",
                program="pilot",
                contract_id="contract_001",
                contract_version=1,
            )

            review_items = store.review_workstreams(reason="no_contract")

            self.assertEqual([item["workstream"]["id"] for item in review_items], ["ws_001"])

    def test_review_flags_due_and_stale_workstreams(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.write_contract_version("contract_001", 1, "# Contract\n")
            store.create_workstream(
                title="A3 false-positive reduction",
                program="safety-finetuning",
                contract_id="contract_001",
                contract_version=1,
                next_review_due_at="2000-01-01",
            )
            store.add_state_packet(
                "ws_001",
                source="agent-a",
                result="baseline complete",
                rationale="result suggests a measurable false-positive cluster",
            )
            entry = store.get_workstream("ws_001")
            entry["timestamps"]["last_state_update_at"] = "2000-01-01T00:00:00Z"
            store.save_workstream(entry)

            reasons = store.review_workstreams()[0]["review"]["reasons"]

            self.assertIn("review_due", reasons)
            self.assertIn("stale", reasons)

    def test_decision_sets_next_review_due_at(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="Control protocol", program="control")

            decision = store.add_decision(
                "ws_001",
                action="continue",
                rationale="worth one more pass",
                next_review_due_at="2099-01-01",
            )

            self.assertEqual(decision["next_review_due_at"], "2099-01-01")
            self.assertEqual(
                store.get_workstream("ws_001")["timestamps"]["next_review_due_at"],
                "2099-01-01",
            )


if __name__ == "__main__":
    unittest.main()
