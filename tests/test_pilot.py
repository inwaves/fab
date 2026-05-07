from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fab.pilot import PILOT_CONTRACT_ID, PILOT_PROGRAM, seed_pilot_fixture
from fab.registry import RegistryError, RegistryStore


class PilotFixtureTest(unittest.TestCase):
    def test_seed_pilot_fixture_creates_mixed_review_states(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))

            result = seed_pilot_fixture(store)

            self.assertEqual(result["contract"], {"id": PILOT_CONTRACT_ID, "version": 1})
            self.assertEqual(result["program"], PILOT_PROGRAM)
            self.assertEqual(store.existing_workstream_ids(), ["ws_001", "ws_002", "ws_003", "ws_004", "ws_005"])

            review_by_id = {
                item["workstream"]["id"]: item["review"]["reasons"]
                for item in store.review_workstreams()
            }

            self.assertNotIn("ws_001", review_by_id)
            self.assertIn("blocked", review_by_id["ws_002"])
            self.assertIn("flagged", review_by_id["ws_003"])
            self.assertIn("deviated", review_by_id["ws_004"])
            self.assertIn("no_contract", review_by_id["ws_005"])
            self.assertIn("no_state_packet", review_by_id["ws_005"])

            brief = store.brief(program=PILOT_PROGRAM)
            self.assertEqual(brief["counts"]["workstreams"], 5)
            self.assertEqual(brief["counts"]["artifacts"], 4)
            self.assertEqual(brief["counts"]["claims"], 4)
            self.assertIn("claim_filter_tradeoff", {claim["id"] for claim in brief["claims"]})

    def test_seed_pilot_fixture_requires_empty_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="Existing work", program="pilot")

            with self.assertRaisesRegex(RegistryError, "empty registry"):
                seed_pilot_fixture(store)


if __name__ == "__main__":
    unittest.main()
