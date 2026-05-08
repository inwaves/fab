from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from fab.cli import main as fab_main


FIXTURE_RELATIVE_PATH = Path(
    "artifacts/safety-finetuning-pilot/ws_001/fab-ingest-smoke-001"
)
FIXTURE_SOURCE = "alexandria/safety-finetuning-pilot/ws_001/fab-ingest-smoke-001"


def alexandria_repo() -> Path:
    configured = os.environ.get("FAB_ALEXANDRIA_REPO")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "alexandria"


def run_fab_cli(*args: str) -> str:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = fab_main(list(args))
    if code != 0:
        raise AssertionError(
            f"fab {' '.join(args)} exited {code}\nstdout:\n{stdout.getvalue()}\nstderr:\n{stderr.getvalue()}"
        )
    return stdout.getvalue()


class AlexandriaIngestIntegrationTest(unittest.TestCase):
    def test_alexandria_smoke_fixture_ingests_through_cli(self) -> None:
        repo = alexandria_repo()
        bundle = repo / FIXTURE_RELATIVE_PATH
        if not bundle.exists():
            self.skipTest(
                f"Alexandria smoke fixture not found at {bundle}; "
                "set FAB_ALEXANDRIA_REPO to run this integration test"
            )

        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / ".fab"

            run_fab_cli("--store", str(store), "pilot-fixture", "--json")
            output = run_fab_cli(
                "--store",
                str(store),
                "ingest-run",
                "--from",
                str(bundle),
                "--json",
            )

            packet = json.loads(output)
            self.assertEqual(packet["id"], "pkt_002")
            self.assertEqual(packet["workstream_id"], "ws_001")
            self.assertEqual(packet["source"], FIXTURE_SOURCE)
            self.assertEqual(packet["ingest"]["bundle_path"], str(bundle))
            self.assertEqual(packet["ingest"]["status"], "completed_with_limitations")
            self.assertEqual(
                packet["limitations"],
                [
                    "This is a connection smoke test; it does not validate commit watching or exactly-once ingest."
                ],
            )

            artifact = packet["artifacts"][0]
            self.assertEqual(artifact["path"], str(bundle / "artifact"))
            self.assertEqual(artifact["status"], "completed_with_limitations")
            self.assertEqual(
                artifact["claims"][0]["text"],
                "A completed Alexandria run bundle can be ingested into a Fab pilot store without the agent cloning Fab.",
            )
            self.assertEqual(artifact["evidence"][0]["path"], "artifact/report.md")
            self.assertEqual(artifact["evidence"][1]["path"], "artifact/results/smoke-result.json")
            self.assertEqual(
                artifact["used_refs"],
                [
                    "alexandria://papers/a3-an-automated-alignment-agent-for-safety-finetun.md",
                    "fab://contract/contract_pilot_a3_false_positive/v1",
                    "fab://ws_001",
                ],
            )

            attention = json.loads(
                run_fab_cli(
                    "--store",
                    str(store),
                    "attention",
                    "--reason",
                    "limited",
                    "--json",
                )
            )
            self.assertEqual([item["workstream"]["id"] for item in attention], ["ws_001"])


if __name__ == "__main__":
    unittest.main()
