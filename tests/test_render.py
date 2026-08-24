from __future__ import annotations

import contextlib
import io
import unittest
from typing import Any

from fab import render


def capture(fn: Any, *args: Any) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        fn(*args)
    return buffer.getvalue()


class PrimitiveTest(unittest.TestCase):
    def test_dash_and_row(self) -> None:
        self.assertEqual([render.dash(value) for value in (None, "", [], 0, "x")], ["-", "-", "-", "0", "x"])
        self.assertEqual(render.row("a", None, 3), "a\t-\t3")

    def test_format_value(self) -> None:
        self.assertEqual(
            render.format_value({"id": "art_001", "kind": "report", "path": "r.md", "description": "Desc"}),
            "art_001 report r.md: Desc",
        )
        self.assertEqual(render.format_value({"id": "art_001", "kind": "report", "path": "r.md"}), "art_001 report r.md")
        self.assertEqual(render.format_value({"b": 1, "a": 2}), '{"a": 2, "b": 1}')
        self.assertEqual(render.format_value(7), "7")

    def test_section_prints_dash_when_empty(self) -> None:
        self.assertEqual(capture(render.section, "Title", []), "\nTitle\n-\n")
        self.assertEqual(capture(render.section, "Title", iter(["a", "b"])), "\nTitle\na\nb\n")

    def test_list_helpers(self) -> None:
        self.assertEqual(render.field_lines("x", []), ["x: -"])
        self.assertEqual(render.field_lines("x", ["a", {"k": 1}]), ["x:", "- a", '- {"k": 1}'])
        self.assertEqual(render.nested("c", []), [])
        self.assertEqual(render.nested("c", ["- a", "  b"]), ["  c:", "  - a", "    b"])
        self.assertEqual(render.grouped_lines("g", [], str), [])
        self.assertEqual(render.grouped_lines("g", [1, 2], lambda item: f"#{item}"), ["g:", "- #1", "- #2"])

    def test_labels(self) -> None:
        self.assertEqual(render.target_label({"workstream_id": "ws_001"}), "workstream:ws_001")
        self.assertEqual(render.target_label({"target": {"type": "claim", "id": "a/b"}}), "claim:a/b")
        self.assertEqual(render.target_label({"target": {}}), "workstream:-")
        self.assertEqual(render.contract_label(None), "-")
        self.assertEqual(render.contract_label({"id": "c", "version": 2, "exists": False}), "c v2 (missing)")
        self.assertEqual(render.contract_label({"id": "c", "version": 2, "exists": True}), "c v2")


class WorkstreamDetailTest(unittest.TestCase):
    def test_artifact_lines_cover_every_optional_block(self) -> None:
        artifact = {
            "id": "art_001",
            "kind": "dataset",
            "path": "runs/d.jsonl",
            "description": None,
            "uncertainty": "noisy",
            "limitations": ["l1", "l2"],
            "used_refs": ["alexandria://a.md"],
            "claims": [
                {"id": "c1", "text": "T", "confidence": None, "caveats": ["cav"]},
                {"id": "c2", "text": "U", "confidence": "high", "caveats": []},
            ],
            "evidence": [
                {"id": "e1", "kind": "sample", "summary": "S"},
                {"id": "e2", "kind": "metric", "summary": "M", "path": "p.json"},
            ],
            "reproduction": {"commands": ["run it"]},
        }

        self.assertEqual(
            render.artifact_lines([artifact]),
            [
                "artifacts:",
                "- art_001 dataset runs/d.jsonl: -",
                "  uncertainty: noisy",
                "  limitations: l1; l2",
                "  used refs: alexandria://a.md",
                "  claims:",
                "  - c1 (-): T",
                "    caveats: cav",
                "  - c2 (high): U",
                "  evidence:",
                "  - e1 sample: S",
                "  - e2 metric p.json: M",
                "  reproduce:",
                "  - run it",
            ],
        )
        self.assertEqual(render.artifact_lines([]), ["artifacts: -"])
        self.assertEqual(
            render.artifact_lines([{"id": "art_002", "path": "x", "description": "D"}]),
            ["artifacts:", "- art_002 artifact x: D"],
        )

    def test_packet_and_decision_lines(self) -> None:
        self.assertEqual(
            render.packet_line({"id": "pkt_001", "created_at": "t", "next_action": None, "rationale": None}),
            "- pkt_001 t: next=-; rationale=-",
        )
        self.assertEqual(
            render.decision_line(
                {"id": "dec_001", "created_at": "t", "action": "stop", "workstream_id": "ws_001", "status_after": "stopped", "rationale": "r"}
            ),
            "- dec_001 t: stop workstream:ws_001 -> stopped; r",
        )

    def test_detail_view_with_missing_contract_and_empty_state(self) -> None:
        data = {
            "workstream": {"id": "ws_001", "status": "planned", "program": "p", "title": "T", "timestamps": {}},
            "live_state": {},
            "attached_contract": {"id": "c", "version": 1, "exists": False},
            "review": {"reasons": []},
            "recent_packets": [],
            "recent_decisions": [],
        }

        out = capture(render.workstream_detail, data)

        self.assertTrue(out.startswith("ws_001\tplanned\tp\ntitle: T\ncontract: c v1 (missing)\nattention reasons: -\n"))
        self.assertIn("last state update: -\nnext attention due: -\n", out)
        self.assertIn("\nContract\n-\n", out)
        self.assertIn("\nLive State\ncurrent hypothesis: -\ncurrent plan: -\n", out)
        self.assertIn("experiments: -\nresults: -\nfailed attempts: -\n", out)
        self.assertIn("artifacts: -\n", out)
        self.assertTrue(out.endswith("\nRecent Packets\n-\n\nRecent Decisions\n-\n"))


class BriefRenderTest(unittest.TestCase):
    def test_empty_brief_renders_dashes(self) -> None:
        out = capture(render.brief, {})

        self.assertTrue(
            out.startswith("Fab brief\t-\tall\ncounts\tworkstreams=0\tattention=0\tartifacts=0\tclaims=0\tdecisions=0\n")
        )
        for heading in ("Attention", "Workstreams", "Claims", "Contract Review", "References", "Next Context"):
            self.assertIn(f"\n{heading}\n-\n", out)

    def test_populated_brief_renders_every_optional_line(self) -> None:
        data = {
            "generated_at": "now",
            "filters": {"program": "p", "contract_id": None, "stale_days": 7},
            "counts": {"workstreams": 1, "attention": 1, "artifacts": 1, "claims": 1, "decisions": 2},
            "attention": [{"workstream_id": "ws_001", "reasons": ["blocked", "stale"], "title": "T"}],
            "workstreams": [
                {
                    "id": "ws_001",
                    "status": "running",
                    "title": "T",
                    "results": ["r1", "r2"],
                    "limitations": ["lim"],
                    "next_intended_action": "next",
                }
            ],
            "claims": [
                {
                    "workstream_id": "ws_001",
                    "ref": "art_001/c1",
                    "confidence": "high",
                    "judgments": [{"action": "reject"}, {"action": None}],
                    "text": "Claim",
                }
            ],
            "contract_review": {
                "mode": "deterministic",
                "summary": ["s1"],
                "repeated_claims": [{"count": 2, "workstreams": ["ws_001", "ws_002"], "text": "Claim"}],
                "shared_limitations": [{"count": 2, "limitation": "lim"}],
                "shared_used_refs": [{"count": 3, "ref": "alexandria://a.md"}],
                "review_queue": {"needs_replication": [1], "needs_critique": [], "do_not_propagate": [1, 2]},
            },
            "references": {
                "explicit_refs": [1],
                "used_refs": [1, 2],
                "comparison": {
                    "used_not_explicit": ["u://1"],
                    "explicit_not_used": ["e://1"],
                    "unresolved_explicit": [{"uri": "e://1", "resolution": {"status": "unresolved", "error": "boom"}}],
                    "unresolved_used": [{"uri": "u://1", "resolution": {"status": "unresolved"}}],
                },
            },
            "next_context": {
                "trusted_local": [],
                "do_not_propagate": [{"workstream_id": "ws_001", "target": None, "rationale": "bad"}],
            },
        }

        out = capture(render.brief, data)

        self.assertTrue(out.startswith("Fab brief\tnow\tprogram=p, stale_days=7\n"))
        self.assertIn("counts\tworkstreams=1\tattention=1\tartifacts=1\tclaims=1\tdecisions=2\n", out)
        self.assertIn("\nAttention\n- ws_001: blocked,stale; T\n", out)
        self.assertIn("\nWorkstreams\n- ws_001\trunning\tT\n  result: r2\n  limitation: lim\n  next: next\n", out)
        self.assertIn("\nClaims\n- ws_001/art_001/c1 (high) [reject]: Claim\n", out)
        self.assertIn(
            "\nContract Review\nmode: deterministic\n- s1\n"
            "repeated claims:\n- 2x across ws_001, ws_002: Claim\n"
            "shared limitations:\n- 2x: lim\n"
            "shared refs:\n- 3x: alexandria://a.md\n"
            "review queue: needs_replication=1 needs_critique=0 do_not_propagate=2\n",
            out,
        )
        self.assertIn(
            "\nReferences\ncounts: explicit=1 used=2 used_not_explicit=1 explicit_not_used=1\n"
            "unresolved:\n- e://1: boom\n- u://1: unresolved\n"
            "used refs not explicit in contract:\n- u://1\n"
            "explicit contract refs not used:\n- e://1\n",
            out,
        )
        self.assertTrue(out.endswith("\nNext Context\ndo_not_propagate:\n- ws_001 workstream:-; bad\n"))

    def test_contract_review_without_queue_entries_omits_queue_line(self) -> None:
        lines = render.contract_review_lines({"mode": "deterministic", "summary": [], "review_queue": {}})

        self.assertEqual(lines, ["mode: deterministic"])
        self.assertEqual(render.contract_review_lines({}), [])
        self.assertEqual(render.reference_lines({}), [])

    def test_refs_check_scope_headers(self) -> None:
        contract_scope = {"scope": {"type": "contract", "contract": {"id": "c", "version": 1}}, "explicit_refs": [], "used_refs": [], "comparison": {}}
        workstream_scope = {"scope": {"type": "workstream", "workstream_id": "ws_001"}}

        self.assertTrue(capture(render.refs_check, contract_scope).startswith("refs\tcontract:c/v1\n\nReferences\ncounts: explicit=0 used=0 used_not_explicit=0 explicit_not_used=0\n"))
        self.assertTrue(capture(render.refs_check, workstream_scope).startswith("refs\tworkstream:ws_001\n"))
        self.assertEqual(capture(render.refs_check, {}), "refs\n\nReferences\n-\n")


class TableAndReceiptTest(unittest.TestCase):
    def test_sources_table(self) -> None:
        self.assertEqual(capture(render.sources, []), "sources: -\n")
        self.assertEqual(
            capture(render.sources, [{"name": "alex", "uri_prefix": "alexandria://", "path": "/tmp/alex"}]),
            "name\turi_prefix\tpath\nalex\talexandria://\t/tmp/alex\n",
        )

    def test_workstream_and_attention_tables(self) -> None:
        self.assertEqual(
            capture(render.workstream_table, []),
            "id\tstatus\tprogram\tcontract\tlast_state_update\ttitle\n",
        )
        item = {
            "workstream": {
                "id": "ws_001",
                "status": "planned",
                "program": "p",
                "title": "T",
                "timestamps": {"next_review_due_at": "2099-01-01"},
            },
            "review": {"reasons": ["stale", "blocked"]},
        }
        out = capture(render.attention_table, [item])
        self.assertEqual(out.splitlines()[1], "ws_001\tplanned\tp\tstale,blocked\t-\t2099-01-01\tT")
        self.assertEqual(
            capture(render.workstream, {"id": "ws_001", "status": "running", "program": "p", "contract": {"id": "c"}, "title": "T"}),
            "ws_001\trunning\tp\tc\t-\tT\n",
        )

    def test_receipts(self) -> None:
        self.assertEqual(capture(render.initialized, {"store": "/s"}), "Initialized /s\n")
        self.assertEqual(capture(render.source_added, {"name": "alex"}), "Added source alex\n")
        self.assertEqual(capture(render.packet_added, {"id": "pkt_001", "workstream_id": "ws_001"}), "Added pkt_001 to ws_001\n")
        self.assertEqual(
            capture(render.run_ingested, {"id": "pkt_002", "ingest": {"bundle_path": "/b"}}),
            "Ingested pkt_002 from /b\n",
        )
        self.assertEqual(
            capture(render.judgment_recorded, {"id": "dec_001", "workstream_id": "ws_001"}),
            "Recorded dec_001 for ws_001\n",
        )

    def test_pilot_fixture_receipt(self) -> None:
        result = {
            "store": "/s",
            "contract": {"id": "c", "version": 1},
            "workstreams": [{"id": "ws_001", "status": "planned", "program": "p", "contract": {"id": "c"}, "title": "T"}],
            "next_commands": ["uv run fab attention"],
        }

        self.assertEqual(
            capture(render.pilot_fixture, result),
            "Seeded pilot fixture in /s\ncontract\tc\tv1\nworkstreams\nws_001\tplanned\tp\tc\t-\tT\nnext\n- uv run fab attention\n",
        )


if __name__ == "__main__":
    unittest.main()
