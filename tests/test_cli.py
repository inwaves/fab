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

import fab
from fab.cli import main
from fab.pilot import PILOT_CONTRACT_ID, PILOT_PROGRAM
from fab.store import RegistryStore


def run_cli(*args: str) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(list(args))
    return code, stdout.getvalue(), stderr.getvalue()


def write_pilot_bundle(bundle: Path, *, workstream_id: str = "ws_001") -> None:
    artifact = bundle / "artifact"
    artifact.mkdir(parents=True)
    (artifact / "report.md").write_text("# Report\n", encoding="utf-8")
    (bundle / "READY").touch()
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "workstream_id": workstream_id,
                "contract": {"id": PILOT_CONTRACT_ID, "version": 1},
                "source": f"alexandria/{PILOT_PROGRAM}/{workstream_id}/run-001",
                "summary": "Replicated the baseline cluster with human labels.",
                "status": "completed",
                "claims": ["Human labels confirm the ambiguous-refusal cluster."],
                "evidence": [{"summary": "Report.", "path": "artifact/report.md"}],
                "limitations": [],
                "next": [],
                "used_refs": ["alexandria://papers/automated-weak-to-strong-researcher.md"],
            }
        ),
        encoding="utf-8",
    )


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.store = str(self.root / ".fab")

    def fab(self, *args: str, expect: int = 0) -> str:
        """Run ``fab --store <tmp> <args>``; return stdout on success, stderr on failure."""
        code, out, err = run_cli("--store", self.store, *args)
        self.assertEqual(code, expect, f"fab {' '.join(args)}\nstdout:\n{out}\nstderr:\n{err}")
        return out if expect == 0 else err

    def test_init_renders_text_or_json(self) -> None:
        self.assertEqual(self.fab("init").strip(), f"Initialized {self.store}")
        self.assertEqual(
            json.loads(self.fab("init", "--json")),
            {"store": self.store, "initialized": True},
        )

    def test_pilot_fixture_and_list_render_tables(self) -> None:
        seeded = self.fab("pilot-fixture").splitlines()
        self.assertEqual(seeded[0], f"Seeded pilot fixture in {self.store}")
        self.assertEqual(seeded[1], f"contract\t{PILOT_CONTRACT_ID}\tv1")
        self.assertIn("- uv run fab show ws_003 --brief", seeded)

        lines = self.fab("list").splitlines()
        self.assertEqual(lines[0], "id\tstatus\tprogram\tcontract\tlast_state_update\ttitle")
        self.assertEqual(len(lines), 6)
        self.assertTrue(lines[1].startswith(f"ws_001\trunning\t{PILOT_PROGRAM}\t{PILOT_CONTRACT_ID}\t"))
        self.assertTrue(lines[5].startswith(f"ws_005\tplanned\t{PILOT_PROGRAM}\t-\t-\t"))
        self.assertEqual(len(self.fab("list", "--status", "running").splitlines()), 2)

    def test_attention_renders_reasons(self) -> None:
        self.fab("pilot-fixture")
        lines = self.fab("attention").splitlines()

        self.assertEqual(
            lines[0],
            "id\tstatus\tprogram\tattention_reasons\tlast_state_update\tnext_attention_due\ttitle",
        )
        self.assertEqual([line.split("\t")[0] for line in lines[1:]], ["ws_002", "ws_003", "ws_004", "ws_005"])
        ws_005 = lines[4].split("\t")
        self.assertEqual(ws_005[3], "no_contract,no_state_packet,missing_rationale")
        self.assertEqual(self.fab("attention", "--reason", "flagged").splitlines()[1].split("\t")[0], "ws_003")

    def test_brief_renders_every_section(self) -> None:
        self.fab("pilot-fixture")
        out = self.fab("brief", "--program", PILOT_PROGRAM)

        self.assertTrue(out.startswith("Fab brief\t"))
        self.assertIn("counts\tworkstreams=5\tattention=4\tartifacts=4\tclaims=4\tdecisions=1", out)
        for heading in ("Attention", "Workstreams", "Claims", "Contract Review", "References", "Next Context"):
            self.assertIn(f"\n{heading}\n", out)
        self.assertIn("- ws_003: flagged; Narrow data-filter attempt", out)
        self.assertIn("- ws_003/art_001/claim_filter_tradeoff (medium-low): ", out)
        self.assertIn("mode: deterministic", out)
        self.assertIn("counts: explicit=3 used=0 used_not_explicit=0 explicit_not_used=3", out)
        self.assertIn("\nNext Context\n-\n", out)

    def test_show_defaults_to_json_and_brief_renders_detail(self) -> None:
        self.fab("pilot-fixture")

        data = json.loads(self.fab("show", "ws_003"))
        self.assertEqual(data["workstream"]["id"], "ws_003")
        self.assertEqual(data["review"]["reasons"], ["flagged"])

        out = self.fab("show", "ws_003", "--brief")
        self.assertTrue(out.startswith(f"ws_003\tplanned\t{PILOT_PROGRAM}\n"))
        self.assertIn(f"contract: {PILOT_CONTRACT_ID} v1\n", out)
        self.assertIn("\nContract\n# Contract: A3 False-Positive Reduction Pilot", out)
        self.assertIn("\nLive State\ncurrent hypothesis: -\n", out)
        self.assertIn("flags:\n- possible shortcut", out)
        self.assertIn(
            "artifacts:\n- art_001 plot runs/ws_003/filter-tradeoff-plot.png: "
            "False-positive versus target-detection tradeoff\n",
            out,
        )
        self.assertIn("  claims:\n  - claim_filter_tradeoff (medium-low): ", out)
        self.assertIn("    caveats: public eval may reward easier retained examples", out)
        self.assertIn("  reproduce:\n  - uv run python pilot/evals/filter_tradeoff.py", out)
        self.assertIn("\nRecent Decisions\n-\n", out)

    def test_refs_check_reports_contract_and_workstream_scopes(self) -> None:
        self.fab("pilot-fixture")

        out = self.fab("refs", "check", "--contract-id", PILOT_CONTRACT_ID, "--version", "1")
        self.assertEqual(out.splitlines()[0], f"refs\tcontract:{PILOT_CONTRACT_ID}/v1")
        self.assertIn("counts: explicit=3 used=0 used_not_explicit=0 explicit_not_used=3", out)
        self.assertIn(
            "- alexandria://papers/automated-weak-to-strong-researcher.md: "
            "no configured source matches URI prefix",
            out,
        )

        out = self.fab("refs", "check", "--workstream-id", "ws_005")
        self.assertEqual(out.splitlines()[0], "refs\tworkstream:ws_005")
        self.assertIn("counts: explicit=0 used=0", out)

    def test_sources_add_and_list(self) -> None:
        self.fab("init")
        self.assertEqual(self.fab("sources", "list").strip(), "sources: -")

        out = self.fab("sources", "add", "alexandria", str(self.root), "--uri-prefix", "alexandria://")
        self.assertEqual(out.strip(), "Added source alexandria")

        lines = self.fab("sources", "list").splitlines()
        self.assertEqual(lines, ["name\turi_prefix\tpath", f"alexandria\talexandria://\t{self.root}"])

    def test_create_rejects_path_traversal_ids(self) -> None:
        self.fab("init")

        err = self.fab("create", "--id", "../../escaped", "--title", "x", "--program", "y", expect=2)
        self.assertIn("error: invalid workstream id: ../../escaped", err)
        self.assertEqual([path.name for path in self.root.rglob("*.json")], [])

        err = self.fab("show", "../../escaped", expect=2)
        self.assertIn("invalid workstream id", err)

    def test_status_and_judge_respect_lifecycle_transitions(self) -> None:
        self.fab("pilot-fixture")
        self.assertEqual(
            self.fab("judge", "ws_001", "--action", "complete", "--rationale", "done").strip(),
            "Recorded dec_002 for ws_001",
        )

        err = self.fab("judge", "ws_001", "--action", "continue", "--rationale", "oops", expect=2)
        self.assertIn("invalid status transition: completed -> running", err)
        err = self.fab("status", "ws_001", "running", expect=2)
        self.assertIn("completed is terminal", err)

        out = self.fab("status", "ws_001", "running", "--force")
        self.assertTrue(out.startswith("ws_001\trunning\t"))

    def test_packet_ingest_and_link_receipts(self) -> None:
        self.fab("pilot-fixture")

        out = self.fab("packet", "ws_002", "--source", "human", "--result", "labels arrived")
        self.assertEqual(out.strip(), "Added pkt_002 to ws_002")

        err = self.fab("packet", "ws_002", "--source", "x", "--artifact-json", "{not json", expect=2)
        self.assertIn("invalid artifact JSON", err)

        bundle = self.root / "inbox" / "run-001"
        write_pilot_bundle(bundle)
        out = self.fab("ingest-run", "--from", str(bundle))
        self.assertEqual(out.strip(), f"Ingested pkt_002 from {bundle}")

        out = self.fab("link", "ws_001", "ws_002", "--relationship", "blocks")
        self.assertTrue(out.startswith("ws_001\trunning\t"))
        self.assertEqual(
            json.loads(self.fab("show", "ws_001"))["workstream"]["relationships"]["blocks"],
            ["ws_002"],
        )

        brief = json.loads(self.fab("brief", "--program", PILOT_PROGRAM, "--json"))
        self.assertEqual(brief["counts"]["used_refs"], 1)
        self.assertEqual(brief["references"]["comparison"]["used_not_explicit"], [])

    def test_uninitialized_store_is_a_clean_error(self) -> None:
        err = self.fab("list", expect=2)
        self.assertIn("registry is not initialized", err)

    def test_create_with_contract_and_attach_contract(self) -> None:
        self.fab("init")
        RegistryStore.at(Path(self.store)).write_contract_version("contract_001", 1, "# Contract\n")

        out = self.fab(
            "create", "--title", "Scoped", "--program", "pilot",
            "--contract-id", "contract_001", "--contract-version", "1",
            "--owner", "human", "--next-attention-due-at", "2099-01-01",
        )
        self.assertEqual(out.strip(), "ws_001\tplanned\tpilot\tcontract_001\t-\tScoped")

        err = self.fab("create", "--title", "Half", "--program", "pilot", "--contract-version", "1", expect=2)
        self.assertIn("contract version cannot be set without contract id", err)
        err = self.fab("create", "--title", "Bad", "--program", "pilot", "--next-attention-due-at", "soon", expect=2)
        self.assertIn("invalid datetime: soon", err)

        self.fab("create", "--title", "Unscoped", "--program", "pilot")
        out = self.fab("attach-contract", "ws_002", "--contract-id", "contract_001", "--version", "1")
        self.assertTrue(out.startswith("ws_002\tplanned\tpilot\tcontract_001\t"))
        err = self.fab("attach-contract", "ws_002", "--contract-id", "contract_404", "--version", "1", expect=2)
        self.assertIn("contract version not found", err)

    def test_show_json_wins_over_brief_and_attention_all_lists_clear_workstreams(self) -> None:
        self.fab("pilot-fixture")

        data = json.loads(self.fab("show", "ws_001", "--brief", "--json"))
        self.assertEqual(data["workstream"]["id"], "ws_001")

        lines = self.fab("attention", "--all").splitlines()
        self.assertEqual([line.split("\t")[0] for line in lines[1:]], ["ws_001", "ws_002", "ws_003", "ws_004", "ws_005"])
        self.assertEqual(lines[1].split("\t")[3], "-")
        self.assertEqual(len(json.loads(self.fab("attention", "--status", "planned", "--json"))), 4)

    def test_judge_claim_target_with_due_date_feeds_next_context(self) -> None:
        self.fab("pilot-fixture")

        out = self.fab(
            "judge", "ws_003", "--target-type", "claim", "--target-id", "art_001/claim_filter_tradeoff",
            "--action", "needs-replication", "--rationale", "replicate first",
            "--actor", "human", "--next-attention-due-at", "2099-01-01",
        )
        self.assertEqual(out.strip(), "Recorded dec_001 for ws_003")

        brief = json.loads(self.fab("brief", "--contract-id", PILOT_CONTRACT_ID, "--json"))
        self.assertEqual(brief["counts"]["workstreams"], 4, "ws_005 has no contract")
        self.assertEqual(
            brief["next_context"]["needs_replication"][0]["target"],
            {"type": "claim", "id": "art_001/claim_filter_tradeoff"},
        )

        text = self.fab("brief", "--contract-id", PILOT_CONTRACT_ID)
        self.assertIn("(medium-low) [needs-replication]: The narrow filter", text)
        self.assertIn("review queue: needs_replication=1 needs_critique=0 do_not_propagate=0", text)
        self.assertIn("\nNext Context\nneeds_replication:\n- ws_003 claim:art_001/claim_filter_tradeoff; replicate first", text)

        err = self.fab(
            "judge", "ws_003", "--target-type", "claim", "--target-id", "art_001/claim_missing",
            "--action", "reject", "--rationale", "x", expect=2,
        )
        self.assertIn("claim target not found", err)

    def test_packet_artifacts_are_numbered_after_existing_ones(self) -> None:
        self.fab("pilot-fixture")

        err = self.fab("packet", "ws_001", "--source", "x", "--artifact-json", "[1, 2]", expect=2)
        self.assertIn("artifact JSON must be an object", err)

        packet = json.loads(
            self.fab(
                "packet", "ws_001", "--source", "human",
                "--artifact-json", '{"path": "runs/ws_001/notes.md", "kind": "note"}',
                "--artifact", "runs/ws_001/extra.md",
                "--blocker", "waiting on labels", "--deviation", "used a new eval", "--flag", "check",
                "--tried", "t", "--failed", "f", "--changed", "c", "--next", "n", "--rationale", "r",
                "--json",
            )
        )
        self.assertEqual([artifact["id"] for artifact in packet["artifacts"]], ["art_002", "art_003"])
        self.assertEqual(packet["artifacts"][1]["kind"], "note")
        self.assertEqual(packet["blockers"], ["waiting on labels"])
        self.assertEqual(packet["deviations"], ["used a new eval"])
        self.assertEqual(packet["flags"], ["check"])
        self.assertEqual((packet["tried"], packet["failed"], packet["changed"]), ("t", "f", "c"))

    def test_list_and_brief_filters(self) -> None:
        self.fab("pilot-fixture")
        self.fab("create", "--title", "Other", "--program", "other-program")

        self.assertEqual(len(self.fab("list", "--program", "other-program").splitlines()), 2)
        self.assertEqual(len(self.fab("list", "--program", PILOT_PROGRAM, "--status", "planned").splitlines()), 5)
        brief = json.loads(self.fab("brief", "--program", "other-program", "--stale-days", "30", "--json"))
        self.assertEqual(brief["counts"]["workstreams"], 1)
        self.assertEqual(brief["filters"]["stale_days"], 30)
        err = self.fab("brief", "--stale-days", "0", expect=2)
        self.assertIn("invalid stale days", err)

    def test_argparse_rejects_unknown_choices(self) -> None:
        self.fab("pilot-fixture")
        for args in (("status", "ws_001", "bogus"), ("judge", "ws_001", "--action", "ship", "--rationale", "x"), ("nope",)):
            with self.subTest(args=args):
                with self.assertRaises(SystemExit) as raised:
                    run_cli("--store", self.store, *args)
                self.assertEqual(raised.exception.code, 2)

    def test_module_entry_point(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(Path(fab.__file__).resolve().parent.parent)}

        result = subprocess.run(
            [sys.executable, "-m", "fab.cli", "--store", self.store, "init"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"Initialized {self.store}")

    def test_contract_add_show_and_register(self) -> None:
        contract_file = self.root / "contract.md"
        contract_file.write_text(
            "# Contract: Example\n\nSee alexandria://papers/a.md and https://x.test/p.\n",
            encoding="utf-8",
        )

        out = self.fab("contract", "add", "contract_001", "--version", "1", "--from", str(contract_file))
        stored = Path(self.store) / "contracts" / "contract_001" / "v001.md"
        self.assertEqual(
            out.splitlines(),
            [f"Added contract contract_001 v1 -> {stored}", "title: Contract: Example", "explicit refs: 2"],
        )
        self.assertEqual(
            self.fab("contract", "show", "contract_001", "--version", "1").rstrip("\n"),
            contract_file.read_text(encoding="utf-8").rstrip("\n"),
        )
        data = json.loads(self.fab("contract", "add", "contract_001", "--version", "2", "--from", str(contract_file), "--json"))
        self.assertEqual(data["explicit_refs"], ["alexandria://papers/a.md", "https://x.test/p"])

        err = self.fab("contract", "add", "contract_001", "--version", "1", "--from", str(contract_file), expect=2)
        self.assertIn("contract version already exists", err)
        err = self.fab("contract", "add", "contract_002", "--version", "1", "--from", str(self.root / "missing.md"), expect=2)
        self.assertIn("cannot read contract file", err)
        err = self.fab("contract", "show", "contract_404", "--version", "1", expect=2)
        self.assertIn("contract version not found", err)

        out = self.fab("create", "--title", "Scoped", "--program", "p", "--contract-id", "contract_001", "--contract-version", "2")
        self.assertTrue(out.startswith("ws_001\tplanned\tp\tcontract_001\t"))
        self.assertIn("explicit=2", self.fab("refs", "check", "--workstream-id", "ws_001"))

    def test_validate_bundle_without_a_store(self) -> None:
        bundle = self.root / "inbox" / "run-001"
        write_pilot_bundle(bundle)

        out = self.fab(
            "validate-bundle", str(bundle),
            "--workstream-id", "ws_001",
            "--contract-id", PILOT_CONTRACT_ID, "--contract-version", "1",
        )
        self.assertEqual(out.splitlines()[0], f"valid\t{bundle}")
        self.assertIn(f"workstream: ws_001\ncontract: {PILOT_CONTRACT_ID} v1\nstatus: completed\n", out)
        self.assertIn("counts\tclaims=1\tevidence=1\tlimitations=0\tnext=0\tused_refs=1", out)
        data = json.loads(self.fab("validate-bundle", str(bundle), "--json"))
        self.assertEqual(data["run"]["workstream_id"], "ws_001")
        self.assertEqual(data["artifact_dir"], str(bundle / "artifact"))
        self.assertFalse(Path(self.store).exists(), "validation must not create a store")

        err = self.fab("validate-bundle", str(bundle), "--workstream-id", "ws_002", expect=2)
        self.assertIn("manifest workstream_id is ws_001, expected ws_002", err)
        err = self.fab("validate-bundle", str(bundle), "--contract-id", PILOT_CONTRACT_ID, "--contract-version", "2", expect=2)
        self.assertIn("manifest contract is", err)
        err = self.fab("validate-bundle", str(bundle), "--contract-id", PILOT_CONTRACT_ID, expect=2)
        self.assertIn("must be given together", err)
        (bundle / "READY").unlink()
        err = self.fab("validate-bundle", str(bundle), expect=2)
        self.assertIn("missing READY", err)


if __name__ == "__main__":
    unittest.main()
