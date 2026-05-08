from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fab.pilot import seed_pilot_fixture
from fab.registry import RegistryStore
from services.alexandria_ingester import (
    IngesterConfig,
    read_ledger,
    run_once,
)


FIXTURE_RELATIVE_PATH = Path(
    "artifacts/safety-finetuning-pilot/ws_001/fab-ingest-smoke-001"
)


def alexandria_repo() -> Path:
    configured = os.environ.get("FAB_ALEXANDRIA_REPO")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "alexandria"


class AlexandriaIngesterServiceTest(unittest.TestCase):
    def test_ingester_ingests_alexandria_fixture_once(self) -> None:
        repo = alexandria_repo()
        bundle = repo / FIXTURE_RELATIVE_PATH
        if not bundle.exists():
            self.skipTest(
                f"Alexandria smoke fixture not found at {bundle}; "
                "set FAB_ALEXANDRIA_REPO to run this integration test"
            )

        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / ".fab"
            seed_pilot_fixture(RegistryStore.at(store_path))

            first = run_once(IngesterConfig(alexandria=repo, store=store_path))
            self.assertEqual(first["counts"]["discovered"], 1)
            self.assertEqual(first["counts"]["ingested"], 1)
            self.assertEqual(first["counts"]["errors"], 0)
            self.assertEqual(first["bundles"][0]["packet_id"], "pkt_002")

            second = run_once(IngesterConfig(alexandria=repo, store=store_path))
            self.assertEqual(second["counts"]["discovered"], 1)
            self.assertEqual(second["counts"]["ingested"], 0)
            self.assertEqual(second["counts"]["skipped"], 1)
            self.assertEqual(second["counts"]["errors"], 0)

            ledger_path = store_path / "ingest-ledger" / "alexandria.jsonl"
            entries = read_ledger(ledger_path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["status"], "ingested")
            self.assertEqual(entries[0]["packet_id"], "pkt_002")
            self.assertEqual(entries[0]["bundle_relpath"], FIXTURE_RELATIVE_PATH.as_posix())
            self.assertEqual(entries[0]["manifest_path"], str(bundle / "manifest.json"))
            self.assertEqual(len(entries[0]["manifest_sha256"]), 64)

            live_state = RegistryStore.at(store_path).get_live_state("ws_001")
            self.assertEqual(live_state["artifacts"][-1]["path"], str(bundle / "artifact"))
            self.assertEqual(
                live_state["limitations"],
                [
                    "This is a connection smoke test; it does not validate commit watching or exactly-once ingest."
                ],
            )

    def test_ingester_records_errors_without_marking_bundle_ingested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            alexandria = root / "alexandria"
            bundle = alexandria / "artifacts" / "program" / "ws_999" / "run-bad"
            artifact = bundle / "artifact"
            artifact.mkdir(parents=True)
            (artifact / "report.md").write_text("# Bad run\n", encoding="utf-8")
            (bundle / "READY").touch()
            (bundle / "manifest.json").write_text(
                json.dumps(
                    {
                        "workstream_id": "ws_999",
                        "contract": {"id": "missing_contract", "version": 1},
                        "source": "alexandria/program/ws_999/run-bad",
                        "summary": "This bundle targets a missing workstream.",
                        "status": "completed",
                        "claims": [],
                        "evidence": [{"summary": "Report exists.", "path": "artifact/report.md"}],
                        "limitations": [],
                        "next": [],
                        "used_refs": [],
                    }
                ),
                encoding="utf-8",
            )

            store_path = root / ".fab"
            seed_pilot_fixture(RegistryStore.at(store_path))
            config = IngesterConfig(alexandria=alexandria, store=store_path)

            first = run_once(config)
            second = run_once(config)

            self.assertEqual(first["counts"]["errors"], 1)
            self.assertEqual(second["counts"]["errors"], 1)
            self.assertEqual(second["counts"]["skipped"], 0)

            entries = read_ledger(store_path / "ingest-ledger" / "alexandria.jsonl")
            self.assertEqual([entry["status"] for entry in entries], ["error", "error"])
            self.assertIn("ws_999", entries[0]["error"])


if __name__ == "__main__":
    unittest.main()
