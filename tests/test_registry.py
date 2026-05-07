from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path

from fab.registry import RegistryError, RegistryStore


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
                        "provenance": {
                            "code": ["src/evals/refusal_eval.py"],
                            "datasets": ["data/refusal-benign-v1.jsonl"],
                            "models": ["qwen-8b-lora-run-003"],
                            "prompts": ["prompts/refusal-eval-v2.md"],
                            "evals": ["evals/refusal-fp-v1"],
                        },
                    }
                ],
            )

            artifact = packet["artifacts"][0]
            self.assertEqual(artifact["id"], "art_001")
            self.assertEqual(artifact["kind"], "report")
            self.assertEqual(artifact["description"], "Baseline eval summary")
            self.assertEqual(artifact["provenance"]["code"], ["src/evals/refusal_eval.py"])
            self.assertEqual(artifact["provenance"]["evals"], ["evals/refusal-fp-v1"])

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
