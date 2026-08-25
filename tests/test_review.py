from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from fab.errors import RegistryError
from fab.review import (
    REVIEW_REASONS,
    attached_contract_summary,
    attention_items,
    ensure_review_reason,
    ensure_stale_days,
    review_reasons,
    review_summary,
)
from fab.store import RegistryStore
from fab.util import current_time, format_datetime


class AttentionReasonTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = RegistryStore.at(Path(self._tmp.name) / ".fab")
        self.store.write_contract_version("contract_001", 1, "# Contract\n")

    def scoped(self, **kwargs: object) -> dict:
        return self.store.create_workstream(
            title="Scoped",
            program="pilot",
            contract_id="contract_001",
            contract_version=1,
            **kwargs,
        )

    def reasons(self, workstream_id: str, *, stale_days: int = 7) -> list[str]:
        return review_reasons(
            self.store,
            self.store.get_workstream(workstream_id),
            self.store.get_live_state(workstream_id),
            self.store.list_packets(workstream_id),
            stale_days=stale_days,
            now=current_time(),
        )

    def test_validation_helpers(self) -> None:
        ensure_review_reason(None)
        ensure_review_reason("stale")
        ensure_stale_days(1)
        with self.assertRaisesRegex(RegistryError, "invalid stale days: 0"):
            ensure_stale_days(0)
        with self.assertRaisesRegex(RegistryError, "invalid review reason: bogus; valid: "):
            ensure_review_reason("bogus")
        with self.assertRaisesRegex(RegistryError, "invalid stale days"):
            self.store.review_workstreams(stale_days=0)
        with self.assertRaisesRegex(RegistryError, "invalid stale days"):
            self.store.brief(stale_days=-1)
        with self.assertRaisesRegex(RegistryError, "invalid review reason"):
            self.store.review_workstreams(reason="bogus")
        self.assertIn("invalid_contract_pointer", REVIEW_REASONS)

    def test_paused_and_quarantined_still_report_state_gaps(self) -> None:
        self.scoped()
        self.store.set_status("ws_001", "running")
        self.store.set_status("ws_001", "paused")
        self.assertEqual(self.reasons("ws_001"), ["paused", "no_state_packet", "missing_rationale"])

        self.store.set_status("ws_001", "quarantined")
        self.assertEqual(self.reasons("ws_001"), ["quarantined", "no_state_packet", "missing_rationale"])

    def test_terminal_statuses_report_only_due_dates_and_status(self) -> None:
        self.scoped(next_review_due_at="2000-01-01")
        self.store.set_status("ws_001", "running")
        self.store.set_status("ws_001", "completed")
        self.assertEqual(self.reasons("ws_001"), ["review_due"])

        self.scoped()
        self.store.set_status("ws_002", "running")
        self.store.set_status("ws_002", "stopped")
        self.assertEqual(self.reasons("ws_002"), [])
        self.assertEqual(self.store.review_workstreams(), [
            item for item in self.store.review_workstreams() if item["workstream"]["id"] == "ws_001"
        ])

    def test_invalid_timestamps_are_flagged_rather_than_fatal(self) -> None:
        entry = self.scoped()
        entry["timestamps"]["next_review_due_at"] = "soon"
        entry["timestamps"]["last_state_update_at"] = "yesterday"
        self.store.save_workstream(entry)

        reasons = self.reasons("ws_001")

        self.assertIn("invalid_review_due_at", reasons)
        self.assertIn("invalid_last_state_update_at", reasons)
        self.assertEqual(
            [item["workstream"]["id"] for item in attention_items(self.store, reason="invalid_review_due_at")],
            ["ws_001"],
        )

    def test_contract_file_problems_are_distinct_reasons(self) -> None:
        entry = self.scoped()
        path = self.store.contract_version_path("contract_001", 1)
        path.unlink()
        self.assertIn("missing_contract_file", self.reasons("ws_001"))
        summary = attached_contract_summary(self.store, entry)
        self.assertEqual(summary["exists"], False)
        self.assertNotIn("text", summary)

        entry["contract"] = {"id": "../evil", "version": 1}
        self.store.save_workstream(entry)
        self.assertIn("invalid_contract_pointer", self.reasons("ws_001"))

        self.assertIsNone(attached_contract_summary(self.store, {"contract": {"id": None, "version": None}}))
        self.assertIsNone(attached_contract_summary(self.store, {}))

    def test_stale_threshold_follows_stale_days(self) -> None:
        self.scoped()
        self.store.add_state_packet("ws_001", source="agent", result="r", rationale="because")
        entry = self.store.get_workstream("ws_001")
        entry["timestamps"]["last_state_update_at"] = format_datetime(current_time() - timedelta(days=3))
        self.store.save_workstream(entry)

        self.assertEqual(self.reasons("ws_001", stale_days=7), [])
        self.assertEqual(self.reasons("ws_001", stale_days=2), ["stale"])

        summary = review_summary(self.store, entry, self.store.get_live_state("ws_001"), self.store.list_packets("ws_001"), stale_days=2)
        self.assertEqual(summary["reasons"], ["stale"])
        self.assertEqual(summary["stale_days"], 2)
        self.assertTrue(summary["reviewed_at"].endswith("Z"))

    def test_attention_items_can_include_clear_workstreams(self) -> None:
        self.scoped(next_review_due_at="2099-01-01")
        self.store.add_state_packet("ws_001", source="agent", result="r", rationale="because", next_action="more")

        self.assertEqual(self.store.review_workstreams(), [])

        items = attention_items(self.store, include_clear=True)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["review"]["reasons"], [])
        self.assertEqual(
            items[0]["live_state"],
            {
                "updated_at": items[0]["workstream"]["timestamps"]["last_state_update_at"],
                "next_intended_action": "more",
                "rationale": "because",
            },
        )


if __name__ == "__main__":
    unittest.main()
