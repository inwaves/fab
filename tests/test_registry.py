from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from alignment_fab.registry import RegistryStore


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
            self.assertIsNone(live_state["reason_for_continuing"])

    def test_packet_updates_live_state_without_rewriting_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
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
                continue_reason="cluster is measurable and tied to the contract",
                flag=["needs transfer check"],
            )

            self.assertEqual(packet["id"], "pkt_001")
            entry = store.get_workstream("ws_001")
            self.assertEqual(entry["contract"]["id"], "contract_001")

            live_state = store.get_live_state("ws_001")
            self.assertEqual(live_state["next_intended_action"], "test narrower data filter")
            self.assertEqual(
                live_state["reason_for_continuing"],
                "cluster is measurable and tied to the contract",
            )
            self.assertIn("needs transfer check", live_state["flags"])

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


if __name__ == "__main__":
    unittest.main()

