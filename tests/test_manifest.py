from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

from fab.errors import RegistryError
from fab.manifest import (
    REMOTE_RUN_STATUSES,
    RunBundle,
    bundle_file,
    is_within,
    normalize_run_manifest,
    read_run_bundle,
    run_artifact_ref,
    validate_manifest_paths,
)

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "run-manifest.schema.json"


def valid_manifest(**overrides: object) -> dict:
    manifest: dict = {
        "workstream_id": "ws_001",
        "contract": {"id": "contract_001", "version": 1},
        "source": "podium/run-1",
        "summary": "Did the thing.",
        "status": "completed",
        "claims": ["a", "  ", "b"],
        "evidence": ["plain", {"summary": "with path", "path": "artifact/report.md"}],
        "limitations": [],
        "next": ["again"],
        "used_refs": ["alexandria://a.md"],
    }
    manifest.update(overrides)
    return manifest


def rejection_cases() -> list[tuple[object, str]]:
    """Manifests ``normalize_run_manifest`` must reject, with the expected message."""
    missing = valid_manifest()
    del missing["summary"]
    return [
        ([], "run manifest must be an object"),
        (missing, "run manifest missing field: summary"),
        (valid_manifest(source=""), "run manifest source must be a non-empty string"),
        (valid_manifest(summary="   "), "run manifest summary must be a non-empty string"),
        (valid_manifest(workstream_id=5), "run manifest workstream_id must be a non-empty string"),
        (valid_manifest(workstream_id="../ws"), "invalid workstream id"),
        (valid_manifest(status="done"), "invalid run manifest status: done; valid: completed, completed_with_limitations, failed"),
        (valid_manifest(claims="x"), "run manifest claims must be a list"),
        (valid_manifest(claims=[1]), "run manifest claims entries must be strings"),
        (valid_manifest(contract="x"), "run manifest contract must be an object"),
        (valid_manifest(contract={"id": "c", "version": "1"}), "contract.version must be a positive integer"),
        (valid_manifest(contract={"id": "c", "version": True}), "contract.version must be a positive integer"),
        (valid_manifest(contract={"id": "c", "version": 0}), "contract.version must be a positive integer"),
        (valid_manifest(contract={"id": "../c", "version": 1}), "invalid contract id"),
        (valid_manifest(evidence="x"), "run manifest evidence must be a list"),
        (valid_manifest(evidence=[1]), "run manifest evidence entries must be objects"),
        (valid_manifest(evidence=[{"summary": ""}]), "evidence.summary must be a non-empty string"),
        (valid_manifest(evidence=[{"summary": "s", "path": 3}]), "evidence.path must be a non-empty string"),
        (valid_manifest(evidence=[{"summary": "s", "path": "  "}]), "evidence.path must be a non-empty string"),
    ]


class ManifestSchemaTest(unittest.TestCase):
    def test_valid_manifest_normalises_blank_strings_and_plain_evidence(self) -> None:
        run = normalize_run_manifest(valid_manifest())

        self.assertEqual(run["claims"], ["a", "b"])
        self.assertEqual(run["evidence"], [{"summary": "plain"}, {"summary": "with path", "path": "artifact/report.md"}])
        self.assertEqual(run["contract"], {"id": "contract_001", "version": 1})
        self.assertEqual(set(REMOTE_RUN_STATUSES), {"completed", "completed_with_limitations", "failed"})

    def test_rejections(self) -> None:
        for manifest, message in rejection_cases():
            with self.subTest(message=message):
                with self.assertRaisesRegex(RegistryError, message):
                    normalize_run_manifest(manifest)


class ManifestJsonSchemaTest(unittest.TestCase):
    """``schemas/run-manifest.schema.json`` must agree with ``normalize_run_manifest``."""

    @classmethod
    def setUpClass(cls) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        cls.validator = jsonschema.Draft202012Validator(schema)

    def test_accepts_what_the_normaliser_accepts(self) -> None:
        accepted = [
            valid_manifest(),
            valid_manifest(evidence=["plain string evidence"]),
            valid_manifest(extra_field="ignored by both"),
            valid_manifest(status="failed", claims=[], evidence=[], next=[], used_refs=[]),
            valid_manifest(evidence=[{"summary": "nested", "path": "artifact/results/a.b/c.csv"}]),
        ]
        for manifest in accepted:
            with self.subTest(manifest=manifest):
                self.validator.validate(manifest)
                normalize_run_manifest(manifest)

    def test_rejects_what_the_normaliser_rejects(self) -> None:
        for manifest, message in rejection_cases():
            with self.subTest(message=message):
                self.assertFalse(self.validator.is_valid(manifest), message)

    def test_rejects_paths_that_escape_or_are_uris(self) -> None:
        for path in ("/etc/passwd", "../x", "artifact/../../x", "a/..", "http://example.com/x"):
            with self.subTest(path=path):
                self.assertFalse(self.validator.is_valid(valid_manifest(evidence=[{"summary": "s", "path": path}])))


class BundleLayoutTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.bundle = self.root / "run-1"

    def write_bundle(self, manifest: dict | None = None, *, ready: bool = True) -> None:
        (self.bundle / "artifact").mkdir(parents=True)
        (self.bundle / "artifact" / "report.md").write_text("# R\n", encoding="utf-8")
        (self.bundle / "manifest.json").write_text(json.dumps(manifest or valid_manifest()), encoding="utf-8")
        if ready:
            (self.bundle / "READY").touch()

    def test_validate_manifest_paths_rules(self) -> None:
        self.write_bundle()
        validate_manifest_paths(self.bundle, [{"summary": "no path"}, {"summary": "ok", "path": "artifact/report.md"}])
        cases = [
            ("/etc/passwd", "must be relative to bundle root"),
            ("artifact/../../x", "must be relative to bundle root"),
            ("http://example.com/x", "must be relative, not a URI"),
            ("artifact/missing.md", "run manifest path not found: artifact/missing.md"),
        ]
        for path, message in cases:
            with self.subTest(path=path):
                with self.assertRaisesRegex(RegistryError, message):
                    validate_manifest_paths(self.bundle, [{"summary": "x", "path": path}])

    def test_read_run_bundle_layout_errors(self) -> None:
        with self.assertRaisesRegex(RegistryError, "run bundle is not a directory"):
            read_run_bundle(self.bundle)

        self.write_bundle(ready=False)
        with self.assertRaisesRegex(RegistryError, "run bundle is missing READY"):
            read_run_bundle(self.bundle)

        (self.bundle / "READY").mkdir()
        with self.assertRaisesRegex(RegistryError, "READY must be a regular file inside the bundle"):
            read_run_bundle(self.bundle)
        (self.bundle / "READY").rmdir()
        (self.bundle / "READY").touch()

        (self.bundle / "manifest.json").unlink()
        with self.assertRaisesRegex(RegistryError, "run bundle is missing manifest.json"):
            read_run_bundle(self.bundle)
        (self.bundle / "manifest.json").write_text(json.dumps(valid_manifest()), encoding="utf-8")

        (self.bundle / "artifact" / "report.md").unlink()
        (self.bundle / "artifact").rmdir()
        with self.assertRaisesRegex(RegistryError, "artifact directory not found"):
            read_run_bundle(self.bundle)

    def test_read_run_bundle_returns_validated_bundle(self) -> None:
        self.write_bundle()

        bundle = read_run_bundle(str(self.bundle))

        self.assertIsInstance(bundle, RunBundle)
        self.assertEqual(bundle.path, self.bundle)
        self.assertEqual(bundle.manifest_path, self.bundle / "manifest.json")
        self.assertEqual(bundle.artifact_dir, self.bundle / "artifact")
        self.assertEqual(bundle.run["claims"], ["a", "b"])
        self.assertEqual(
            run_artifact_ref(bundle),
            {
                "path": str(self.bundle / "artifact"),
                "description": "Did the thing.",
                "status": "completed",
                "claims": ["a", "b"],
                "evidence": [{"summary": "plain"}, {"summary": "with path", "path": "artifact/report.md"}],
                "limitations": [],
                "suggested_follow_up": ["again"],
                "used_refs": ["alexandria://a.md"],
            },
        )

    def test_containment_helpers(self) -> None:
        self.write_bundle()
        self.assertTrue(is_within(self.bundle, self.bundle / "artifact" / "report.md"))
        self.assertFalse(is_within(self.bundle, self.bundle / ".." / "elsewhere"))
        self.assertEqual(bundle_file(self.bundle, "READY"), self.bundle / "READY")


if __name__ == "__main__":
    unittest.main()
