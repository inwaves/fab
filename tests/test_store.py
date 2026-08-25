from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path

from fab.errors import RegistryError
from fab.store import RegistryStore, contract_version_filename


class StoreValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.store = RegistryStore.at(self.root / ".fab")

    def test_contract_version_filenames(self) -> None:
        self.assertEqual(contract_version_filename(12), "v012.md")
        with self.assertRaisesRegex(RegistryError, "invalid contract version: 0"):
            contract_version_filename(0)
        with self.assertRaisesRegex(RegistryError, "invalid contract version"):
            self.store.contract_version_path("contract_001", -1)

    def test_uninitialized_store(self) -> None:
        self.assertTrue(self.store.is_empty())
        self.assertEqual(self.store.existing_workstream_ids(), [])
        for call in (self.store.list_workstreams, self.store.list_sources):
            with self.assertRaisesRegex(RegistryError, "registry is not initialized"):
                call()
        with self.assertRaisesRegex(RegistryError, "registry is not initialized"):
            self.store.check_references(contract_id="contract_001", version=1)

    def test_sources(self) -> None:
        self.store.init()
        self.store.sources_path.write_text('{"sources": []}', encoding="utf-8")
        with self.assertRaisesRegex(RegistryError, "sources registry must contain a sources object"):
            self.store.read_sources()
        with self.assertRaisesRegex(RegistryError, "invalid source name"):
            self.store.add_source("bad/name", self.root, uri_prefix="x://")
        with self.assertRaisesRegex(RegistryError, "source uri prefix is required"):
            self.store.add_source("ok", self.root, uri_prefix="")

        self.store.sources_path.unlink()
        self.assertEqual(self.store.read_sources(), {"sources": {}})
        self.store.add_source("zeta", "~/notes", uri_prefix="zeta://")
        self.store.add_source("alpha", self.root, uri_prefix="alpha://")

        listed = self.store.list_sources()

        self.assertEqual([source["name"] for source in listed], ["alpha", "zeta"])
        self.assertEqual(listed[1]["path"], str(Path("~/notes").expanduser()))
        self.assertEqual(self.store.resolve_reference("alpha://nothing.md")["status"], "unresolved")
        self.assertEqual(self.store.resolver().resolve("https://x")["status"], "external")

    def test_contract_guards(self) -> None:
        with self.assertRaisesRegex(RegistryError, "contract version is required for contract_001"):
            self.store.ensure_contract_exists("contract_001", None)
        with self.assertRaisesRegex(RegistryError, "contract version not found"):
            self.store.read_contract_version("contract_001", 1)

        path = self.store.write_contract_version("contract_001", 1, "# C\n")

        self.assertFalse(stat.S_IMODE(path.stat().st_mode) & stat.S_IWUSR)
        self.assertEqual(self.store.read_contract_version("contract_001", 1), "# C\n")
        with self.assertRaisesRegex(RegistryError, "contract version cannot be set without contract id"):
            self.store.create_workstream(title="x", program="p", contract_version=1)
        with self.assertRaisesRegex(RegistryError, "contract version is required"):
            self.store.create_workstream(title="x", program="p", contract_id="contract_001")
        with self.assertRaisesRegex(RegistryError, "invalid status: shipped"):
            self.store.create_workstream(title="x", program="p", status="shipped")
        self.assertEqual(self.store.existing_workstream_ids(), [])
        self.assertEqual(
            self.store.contract_reference_entries("contract_001", 1, "see https://x")[0]["resolution"]["status"],
            "external",
        )

    def test_duplicate_and_custom_workstream_ids(self) -> None:
        self.store.create_workstream(title="a", program="p", workstream_id="ws_custom", owner="human")
        with self.assertRaisesRegex(RegistryError, "workstream already exists: ws_custom"):
            self.store.create_workstream(title="b", program="p", workstream_id="ws_custom")

        generated = self.store.create_workstream(title="c", program="p", status="running", artifact_root="runs/c")

        self.assertEqual(generated["id"], "ws_001")
        self.assertEqual(generated["status"], "running")
        self.assertEqual(generated["links"]["artifact_root"], "runs/c")
        self.assertEqual(self.store.get_workstream("ws_custom")["human_owner"], "human")
        self.assertEqual(self.store.existing_workstream_ids(), ["ws_001", "ws_custom"])
        self.assertFalse(self.store.is_empty())

    def test_list_filters(self) -> None:
        self.store.create_workstream(title="a", program="p1")
        self.store.create_workstream(title="b", program="p2")
        self.store.create_workstream(title="c", program="p1")
        self.store.set_status("ws_003", "running")

        ids = lambda items: [item["id"] for item in items]  # noqa: E731 - local shorthand
        self.assertEqual(ids(self.store.list_workstreams(program="p1")), ["ws_001", "ws_003"])
        self.assertEqual(ids(self.store.list_workstreams(status="running")), ["ws_003"])
        self.assertEqual(ids(self.store.list_workstreams(status="running", program="p2")), [])
        with self.assertRaisesRegex(RegistryError, "invalid status: bogus"):
            self.store.set_status("ws_001", "bogus")

    def test_link_relationships(self) -> None:
        self.store.create_workstream(title="a", program="p")
        self.store.create_workstream(title="b", program="p")

        with self.assertRaisesRegex(RegistryError, "cannot link a workstream to itself"):
            self.store.link_workstreams("ws_001", "ws_001")
        with self.assertRaisesRegex(RegistryError, "not found"):
            self.store.link_workstreams("ws_001", "ws_404")
        with self.assertRaisesRegex(
            RegistryError, "invalid relationship: friends; valid: parent, children, related, blocks, blocked_by"
        ):
            self.store.link_workstreams("ws_001", "ws_002", relationship="friends")

        self.store.link_workstreams("ws_001", "ws_002", relationship="parent")
        self.store.link_workstreams("ws_001", "ws_002", relationship="blocked_by")
        updated = self.store.link_workstreams("ws_001", "ws_002", relationship="blocked_by")

        self.assertEqual(updated["relationships"]["parent"], "ws_002")
        self.assertEqual(updated["relationships"]["blocked_by"], ["ws_002"])
        self.assertEqual(updated["relationships"]["related"], [])

    def test_show_limits_recent_history(self) -> None:
        self.store.create_workstream(title="a", program="p")
        for index in range(7):
            self.store.add_state_packet("ws_001", source=f"agent-{index}", result=f"r{index}", rationale="why")
        for index in range(6):
            self.store.add_decision("ws_001", action="escalate", rationale=f"d{index}")

        shown = self.store.show("ws_001")

        self.assertEqual([packet["id"] for packet in shown["recent_packets"]], [f"pkt_00{n}" for n in range(3, 8)])
        self.assertEqual([decision["id"] for decision in shown["recent_decisions"]], [f"dec_00{n}" for n in range(2, 7)])
        self.assertEqual(len(shown["live_state"]["results"]), 7)
        self.assertIsNone(shown["attached_contract"])
        self.assertIn("no_contract", shown["review"]["reasons"])
        self.assertEqual(self.store.get_workstream("ws_001")["status"], "planned")

    def test_used_reference_entries_and_reference_review_delegates(self) -> None:
        self.store.init()
        artifacts = [{"workstream_id": "ws_001", "id": "art_001", "used_refs": ["https://x", "fab://y"]}]

        used = self.store.used_reference_entries(artifacts)
        review = self.store.reference_review([{"id": "ws_001", "contract": None}], artifacts)

        self.assertEqual([entry["resolution"]["status"] for entry in used], ["external", "unresolved"])
        self.assertEqual(review["scope"], {"type": "brief"})
        self.assertEqual(review["comparison"]["used_not_explicit"], ["fab://y", "https://x"])
        self.assertEqual(len(review["comparison"]["unresolved_used"]), 1)


if __name__ == "__main__":
    unittest.main()
