from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fab
from fab.pilot import PILOT_CONTRACT_ID, seed_pilot_fixture
from fab.registry import RegistryStore
from fab.services.alexandria_ingester import (
    IngesterConfig,
    append_ledger,
    discover_ready_bundles,
    git_pull,
    main,
    print_summary,
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


def pilot_manifest(workstream_id: str, run: str, **overrides: object) -> dict:
    manifest: dict = {
        "workstream_id": workstream_id,
        "contract": {"id": PILOT_CONTRACT_ID, "version": 1},
        "source": f"alexandria/program/{workstream_id}/{run}",
        "summary": f"Summary for {run}.",
        "status": "completed",
        "claims": [],
        "evidence": [{"summary": "Report exists.", "path": "artifact/report.md"}],
        "limitations": [],
        "next": [],
        "used_refs": [],
    }
    manifest.update(overrides)
    return manifest


def write_alexandria_bundle(alexandria: Path, workstream_id: str, run: str, manifest: dict | None = None) -> Path:
    bundle = alexandria / "artifacts" / "program" / workstream_id / run
    (bundle / "artifact").mkdir(parents=True)
    (bundle / "artifact" / "report.md").write_text("# Report\n", encoding="utf-8")
    (bundle / "manifest.json").write_text(
        json.dumps(manifest or pilot_manifest(workstream_id, run)), encoding="utf-8"
    )
    (bundle / "READY").touch()
    return bundle


def capture(fn, *args, **kwargs) -> tuple[object, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        result = fn(*args, **kwargs)
    return result, buffer.getvalue()


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

    def test_ingester_ledgers_unreadable_manifest_instead_of_aborting_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            alexandria = root / "alexandria"
            bad = alexandria / "artifacts" / "program" / "ws_001" / "run-bad"
            (bad / "artifact").mkdir(parents=True)
            (bad / "manifest.json").mkdir()  # a directory where a file is required
            (bad / "READY").touch()

            good = alexandria / "artifacts" / "program" / "ws_002" / "run-good"
            (good / "artifact").mkdir(parents=True)
            (good / "artifact" / "report.md").write_text("# Good\n", encoding="utf-8")
            (good / "READY").touch()
            (good / "manifest.json").write_text(
                json.dumps(
                    {
                        "workstream_id": "ws_002",
                        "contract": {"id": "contract_pilot_a3_false_positive", "version": 1},
                        "source": "alexandria/program/ws_002/run-good",
                        "summary": "Good bundle after a bad one.",
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
            summary = run_once(IngesterConfig(alexandria=alexandria, store=store_path))

            self.assertEqual(summary["counts"]["discovered"], 2)
            self.assertEqual(summary["counts"]["errors"], 1)
            self.assertEqual(summary["counts"]["ingested"], 1)
            self.assertIsNone(summary["alexandria_head_commit"])

            entries = read_ledger(store_path / "ingest-ledger" / "alexandria.jsonl")
            by_status = {entry["status"]: entry for entry in entries}
            self.assertIn("regular file inside the bundle", by_status["error"]["error"])
            self.assertIsNone(by_status["error"]["manifest_sha256"])
            self.assertEqual(by_status["ingested"]["workstream_id"], "ws_002")


class IngesterOptionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.alexandria = self.root / "alexandria"
        self.alexandria.mkdir()
        self.store_path = self.root / ".fab"
        seed_pilot_fixture(RegistryStore.at(self.store_path))

    def test_read_ledger_tolerates_blank_lines_and_rejects_bad_entries(self) -> None:
        ledger = self.root / "ledger.jsonl"
        self.assertEqual(read_ledger(ledger), [])

        append_ledger(ledger, {"a": 1})
        ledger.write_text(ledger.read_text(encoding="utf-8") + "\n   \n", encoding="utf-8")
        self.assertEqual(read_ledger(ledger), [{"a": 1}])

        ledger.write_text('{"a": 1}\nnot json\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, r"invalid JSON in ledger .*:2:"):
            read_ledger(ledger)

        ledger.write_text("[1]\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "expected object"):
            read_ledger(ledger)

    def test_limit_defers_bundles_and_honours_explicit_ledger(self) -> None:
        write_alexandria_bundle(self.alexandria, "ws_002", "run-a")
        write_alexandria_bundle(self.alexandria, "ws_003", "run-b")
        ledger = self.root / "custom" / "ledger.jsonl"
        config = IngesterConfig(alexandria=self.alexandria, store=self.store_path, ledger=ledger, limit=1)
        self.assertEqual(config.ledger_path, ledger)

        first = run_once(config)
        second = run_once(config)
        third = run_once(config)

        self.assertEqual(first["counts"], {"discovered": 2, "ingested": 1, "skipped": 0, "deferred": 1, "errors": 0})
        self.assertEqual(first["ledger"], str(ledger.resolve()))
        self.assertEqual(
            [(item["bundle_relpath"], item["status"]) for item in first["bundles"]],
            [("artifacts/program/ws_002/run-a", "ingested"), ("artifacts/program/ws_003/run-b", "deferred")],
        )
        self.assertEqual(second["counts"], {"discovered": 2, "ingested": 1, "skipped": 1, "deferred": 0, "errors": 0})
        self.assertEqual(third["counts"]["skipped"], 2)
        self.assertEqual([entry["status"] for entry in read_ledger(ledger)], ["ingested", "ingested"])
        self.assertFalse((self.store_path / "ingest-ledger").exists())
        self.assertEqual(RegistryStore.at(self.store_path).list_packets("ws_003")[-1]["source"], "alexandria/program/ws_003/run-b")

    def test_nothing_to_discover_without_artifacts_root(self) -> None:
        self.assertEqual(discover_ready_bundles(self.alexandria), [])

        summary = run_once(IngesterConfig(alexandria=self.alexandria, store=self.store_path))

        self.assertEqual(summary["counts"]["discovered"], 0)
        self.assertEqual(summary["bundles"], [])
        self.assertFalse(Path(summary["ledger"]).exists())
        self.assertIsNone(summary["alexandria_head_commit"])
        self.assertIsNone(summary["alexandria_dirty"])

    def test_pull_runs_git_pull_on_the_resolved_checkout(self) -> None:
        with mock.patch("fab.services.alexandria_ingester.git_pull") as pull:
            run_once(IngesterConfig(alexandria=self.alexandria, store=self.store_path, pull=True))

        pull.assert_called_once_with(self.alexandria.resolve())

    def test_git_pull_is_fast_forward_only(self) -> None:
        with mock.patch("fab.services.alexandria_ingester.subprocess.run") as run:
            git_pull(Path("/repo"))

        run.assert_called_once_with(["git", "-C", "/repo", "pull", "--ff-only"], check=True)

    def test_module_entry_point(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(Path(fab.__file__).resolve().parent.parent)}

        result = subprocess.run(
            [sys.executable, "-m", "fab.services.alexandria_ingester", "--alexandria", str(self.alexandria), "--store", str(self.store_path)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("alexandria-ingester: discovered=0 "))

    def test_print_summary_text_and_json(self) -> None:
        summary = {
            "service": "alexandria-ingester",
            "counts": {"discovered": 3, "ingested": 1, "skipped": 1, "deferred": 0, "errors": 1},
            "bundles": [
                {"status": "ingested", "bundle_relpath": "a", "packet_id": "pkt_002"},
                {"status": "error", "bundle_relpath": "b", "error": "boom"},
                {"status": "skipped", "bundle_relpath": "c"},
            ],
        }

        _, text = capture(print_summary, summary, as_json=False)
        _, as_json = capture(print_summary, summary, as_json=True)

        self.assertEqual(
            text,
            "alexandria-ingester: discovered=3 ingested=1 skipped=1 deferred=0 errors=1\n"
            "- ingested\ta pkt_002\n- error\tb boom\n- skipped\tc\n",
        )
        self.assertEqual(json.loads(as_json), summary)

    def test_main_exit_codes_and_flags(self) -> None:
        write_alexandria_bundle(self.alexandria, "ws_002", "run-good")
        write_alexandria_bundle(
            self.alexandria, "ws_999", "run-bad", pilot_manifest("ws_999", "run-bad")
        )
        base = ["--alexandria", str(self.alexandria), "--store", str(self.store_path)]

        code, text = capture(main, base)
        self.assertEqual(code, 1)
        self.assertTrue(text.startswith("alexandria-ingester: discovered=2 ingested=1 skipped=0 deferred=0 errors=1\n"))

        code, as_json = capture(main, [*base, "--allow-errors", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(as_json)["counts"], {"discovered": 2, "ingested": 0, "skipped": 1, "deferred": 0, "errors": 1})

        for bad in (["--limit", "0"], ["--poll-interval", "0"]):
            with self.subTest(bad=bad):
                with self.assertRaises(SystemExit):
                    capture(main, [*base, *bad])

        with mock.patch("fab.services.alexandria_ingester.time.sleep", side_effect=KeyboardInterrupt) as sleep:
            code, _ = capture(main, [*base, "--poll-interval", "5", "--allow-errors"])
        self.assertEqual(code, 0)
        sleep.assert_called_once_with(5.0)


if __name__ == "__main__":
    unittest.main()
