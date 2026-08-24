from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fab.errors import RegistryError
from fab.refs import (
    ReferenceResolver,
    extract_explicit_uris,
    markdown_title,
    reference_check,
    resolution,
    resolve_source_uri,
    strip_yaml_quotes,
    uri_values,
)
from fab.store import RegistryStore


class UriExtractionTest(unittest.TestCase):
    def test_extracts_distinct_uris_and_trims_trailing_punctuation(self) -> None:
        text = (
            "See alexandria://papers/a.md, then (https://example.com/x). "
            "Wiki: https://en.wikipedia.org/wiki/Foo_(bar); `fab://ws_001` "
            "and alexandria://papers/a.md again."
        )

        self.assertEqual(
            extract_explicit_uris(text),
            [
                "alexandria://papers/a.md",
                "https://example.com/x",
                "https://en.wikipedia.org/wiki/Foo_(bar)",
                "fab://ws_001",
            ],
        )
        self.assertEqual(extract_explicit_uris("no references here"), [])

    def test_markdown_title_prefers_front_matter_then_first_heading(self) -> None:
        self.assertEqual(markdown_title('---\ntitle: "Quoted Title"\n---\n\n# Heading\n'), "Quoted Title")
        self.assertEqual(markdown_title("---\ntitle: 'Single'\n---\nBody\n"), "Single")
        self.assertEqual(markdown_title("---\nauthor: x\n---\n\n# From Heading\n"), "From Heading")
        self.assertEqual(markdown_title("---\ntitle:   \n---\n# Fallback\n"), "Fallback")
        self.assertEqual(markdown_title("---\ntitle: unterminated\n# Heading Wins\n"), "Heading Wins")
        self.assertIsNone(markdown_title("no headings here\n"))
        self.assertIsNone(markdown_title("#not a heading\n#  \n"))

    def test_strip_yaml_quotes_only_strips_matching_pairs(self) -> None:
        self.assertEqual(strip_yaml_quotes("  'a'  "), "a")
        self.assertEqual(strip_yaml_quotes('"b"'), "b")
        self.assertEqual(strip_yaml_quotes("'mixed\""), "'mixed\"")
        self.assertEqual(strip_yaml_quotes("'"), "'")

    def test_uri_values_dedups_sorts_and_skips_missing(self) -> None:
        self.assertEqual(uri_values([{"uri": "b://"}, {"uri": "a://"}, {"uri": None}, {"uri": "b://"}]), ["a://", "b://"])


class ResolverTest(unittest.TestCase):
    def test_external_and_unmatched_uris(self) -> None:
        resolver = ReferenceResolver({})

        external = resolver.resolve("https://example.com/paper")
        unmatched = resolver.resolve("fab://ws_001")

        self.assertEqual((external["status"], external["source"]), ("external", "http"))
        self.assertNotIn("error", external)
        self.assertEqual(unmatched["status"], "unresolved")
        self.assertEqual(unmatched["error"], "no configured source matches URI prefix")

    def test_source_escape_missing_and_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "alex"
            note = root / "papers" / "a.md"
            note.parent.mkdir(parents=True)
            note.write_text('---\ntitle: "A"\n---\n', encoding="utf-8")
            source = {"name": "alexandria", "path": str(root), "uri_prefix": "alexandria://"}
            resolver = ReferenceResolver({"alexandria": source})

            escape = resolver.resolve("alexandria://../outside.md")
            missing = resolver.resolve("alexandria://papers/missing.md")
            resolved = resolve_source_uri("alexandria", source, "alexandria://papers/a.md")

            self.assertEqual(escape["error"], "resolved path escapes source root")
            self.assertEqual(escape["source"], "alexandria")
            self.assertEqual(missing["error"], "referenced file does not exist")
            self.assertEqual(resolved["status"], "resolved")
            self.assertEqual(resolved["title"], "A")
            self.assertTrue(resolved["content_hash"].startswith("sha256:"))
            self.assertEqual(resolved["path"], str(note.resolve()))
            self.assertIsNone(resolved["git_commit"])
            self.assertIsNone(resolved["git_dirty"])

    def test_resolution_records_share_one_shape(self) -> None:
        record = resolution("u://x", "resolved", title="t")

        self.assertEqual(
            set(record),
            {"status", "uri", "source", "title", "content_hash", "git_commit", "git_dirty", "path"},
        )
        self.assertEqual(record["title"], "t")
        self.assertIn("error", resolution("u://x", "unresolved", error="why"))


class ReferenceCheckTest(unittest.TestCase):
    def test_argument_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.init()

            with self.assertRaisesRegex(RegistryError, "specify exactly one"):
                reference_check(store)
            with self.assertRaisesRegex(RegistryError, "specify exactly one"):
                reference_check(store, contract_id="contract_001", workstream_id="ws_001")
            with self.assertRaisesRegex(RegistryError, "contract version is required for contract_001"):
                store.check_references(contract_id="contract_001")

    def test_workstream_without_contract_has_no_explicit_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.create_workstream(title="Unscoped", program="pilot")
            store.add_state_packet(
                "ws_001",
                source="agent",
                artifact_ref=[{"path": "r.md", "used_refs": ["https://example.com/x"]}],
            )

            result = store.check_references(workstream_id="ws_001")

            self.assertEqual(result["scope"]["contract"], {"id": None, "version": None})
            self.assertEqual(result["explicit_refs"], [])
            self.assertEqual(result["comparison"]["used_not_explicit"], ["https://example.com/x"])
            self.assertEqual(result["used_refs"][0]["artifact_id"], "art_001")
            self.assertEqual(result["used_refs"][0]["resolution"]["status"], "external")

    def test_workstream_with_contract_compares_explicit_and_used_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.write_contract_version("contract_001", 1, "Read alexandria://a.md and alexandria://b.md\n")
            store.create_workstream(title="Scoped", program="pilot", contract_id="contract_001", contract_version=1)
            store.add_state_packet(
                "ws_001",
                source="agent",
                artifact_ref=[{"path": "r.md", "used_refs": ["alexandria://b.md", "alexandria://c.md"]}],
            )

            result = store.check_references(workstream_id="ws_001")

            self.assertEqual(result["scope"]["contract"], {"id": "contract_001", "version": 1})
            self.assertEqual(result["comparison"]["explicit_uris"], ["alexandria://a.md", "alexandria://b.md"])
            self.assertEqual(result["comparison"]["used_not_explicit"], ["alexandria://c.md"])
            self.assertEqual(result["comparison"]["explicit_not_used"], ["alexandria://a.md"])
            self.assertEqual(len(result["comparison"]["unresolved_explicit"]), 2, "no source configured")

    def test_brief_flags_unreadable_contract_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RegistryStore.at(Path(tmp))
            store.write_contract_version("contract_001", 1, "Refs: alexandria://a.md\n")
            store.create_workstream(title="A", program="pilot", contract_id="contract_001", contract_version=1)
            store.create_workstream(title="B", program="pilot", contract_id="contract_001", contract_version=1)
            store.contract_version_path("contract_001", 1).unlink()

            references = store.brief()["references"]

            self.assertEqual(len(references["explicit_refs"]), 1, "one entry per distinct contract")
            self.assertIsNone(references["explicit_refs"][0]["uri"])
            self.assertEqual(
                references["explicit_refs"][0]["resolution"]["error"],
                "contract version could not be read",
            )
            self.assertEqual(len(references["comparison"]["unresolved_explicit"]), 1)
            self.assertEqual(references["comparison"]["explicit_uris"], [])


if __name__ == "__main__":
    unittest.main()
