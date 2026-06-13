from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fab.registry import RegistryError, RegistryStore
from services.podium_shim import prepare_request


class PodiumShimTest(unittest.TestCase):
    def test_prepare_request_writes_podium_payload_without_requiring_fab_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_path = root / ".fab"
            store = RegistryStore.at(store_path)
            store.write_contract_version(
                "contract_001",
                1,
                "# Contract\n\nStudy weak-to-strong generalisation with Alexandria context.\n",
            )
            store.create_workstream(
                title="Weak-to-strong replication sketch",
                program="safety-finetuning pilot",
                workstream_id="ws_001",
                contract_id="contract_001",
                contract_version=1,
            )

            out = root / "podium-request"
            summary = prepare_request(
                store_path=store_path,
                workstream_id="ws_001",
                alexandria=root / "alexandria",
                out=out,
                run_id="run_001",
                source="podium/test-instance/run_001",
            )

            request = json.loads((out / "fab-execution-request.json").read_text(encoding="utf-8"))
            payload = json.loads((out / "podium-send.json").read_text(encoding="utf-8"))
            prompt = (out / "prompt.md").read_text(encoding="utf-8")
            expected_relpath = "artifacts/safety-finetuning-pilot/ws_001/run_001"
            expected_alexandria_bundle = root / "alexandria" / expected_relpath

            self.assertEqual(summary["workstream_id"], "ws_001")
            self.assertEqual(
                summary["workspace_output_bundle"],
                expected_relpath,
            )
            self.assertEqual(
                summary["alexandria_output_bundle"],
                str(expected_alexandria_bundle),
            )
            self.assertEqual(request["contract"]["id"], "contract_001")
            self.assertIn("Study weak-to-strong generalisation", request["contract"]["text"])
            self.assertEqual(
                request["output"]["bundle_relpath"],
                expected_relpath,
            )
            self.assertNotIn("alexandria", request["output"])
            self.assertEqual(
                request["output"]["workspace_manifest_relpath"],
                f"{expected_relpath}/manifest.json",
            )
            self.assertEqual(
                request["output"]["durable_target"],
                {
                    "kind": "alexandria",
                    "bundle_relpath": expected_relpath,
                },
            )
            self.assertEqual(
                request["manifest_defaults"]["source"],
                "podium/test-instance/run_001",
            )
            self.assertEqual(payload["type"], "process_message")
            self.assertEqual(payload["content"]["messages"][0]["role"], "user")
            self.assertEqual(
                payload["content"]["data"]["fab_execution_request"]["workstream"]["id"],
                "ws_001",
            )
            self.assertIn("Do not clone or call Fab", prompt)
            self.assertIn("relative to your execution workspace", prompt)
            self.assertIn("Do not assume any local developer path", prompt)
            self.assertIn("Write `READY` last", prompt)
            self.assertIn('"workstream_id": "ws_001"', prompt)

    def test_prepare_request_requires_attached_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_path = root / ".fab"
            store = RegistryStore.at(store_path)
            store.create_workstream(
                title="Unattached work",
                program="safety-finetuning",
                workstream_id="ws_001",
            )

            with self.assertRaisesRegex(RegistryError, "no attached contract"):
                prepare_request(
                    store_path=store_path,
                    workstream_id="ws_001",
                    alexandria=root / "alexandria",
                    out=root / "podium-request",
                    run_id="run_001",
                )


if __name__ == "__main__":
    unittest.main()
