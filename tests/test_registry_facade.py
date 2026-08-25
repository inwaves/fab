"""Pin the compatibility surface of ``fab.registry``.

Every name below was importable from ``fab.registry`` before the module was split
and must remain importable from the facade.
"""

from __future__ import annotations

import unittest

import fab.registry as registry

PRE_SPLIT_NAMES = (
    "ARTIFACT_PROVENANCE_FIELDS",
    "READ_ONLY_FILE_MODE",
    "RELATIONSHIP_LIST_FIELDS",
    "REMOTE_RUN_STATUSES",
    "REVIEW_REASONS",
    "SAFE_ID_RE",
    "TERMINAL_STATUSES",
    "TRAILING_URI_PUNCTUATION",
    "URI_RE",
    "VALID_DECISION_ACTIONS",
    "VALID_DECISION_TARGET_TYPES",
    "VALID_STATUSES",
    "RegistryError",
    "RegistryStore",
    "append_unique",
    "artifact_ids",
    "artifact_ref_from_summary",
    "artifact_target_exists",
    "attached_contract_summary",
    "brief_artifact_summary",
    "brief_claim_summary",
    "claim_ref_from_summary",
    "claim_target_exists",
    "compact_id",
    "contract_review_from_brief",
    "contract_version_filename",
    "empty_live_state",
    "ensure_safe_id",
    "extract_explicit_uris",
    "git_commit_for_path",
    "git_dirty",
    "git_output",
    "grouped_artifact_statuses",
    "grouped_artifact_strings",
    "grouped_claims",
    "markdown_title",
    "matching_decisions",
    "merge_packet_into_live_state",
    "next_context_from_decisions",
    "normalize_artifact_claims",
    "normalize_artifact_evidence",
    "normalize_artifact_provenance",
    "normalize_artifact_ref",
    "normalize_artifact_refs",
    "normalize_artifact_reproduction",
    "normalize_artifact_review",
    "normalize_decision_target",
    "normalize_manifest_string",
    "normalize_manifest_string_list",
    "normalize_run_contract",
    "normalize_run_evidence",
    "normalize_run_manifest",
    "normalize_string_list",
    "normalized_comparison_text",
    "parse_datetime",
    "read_json",
    "reference_check_result",
    "require_manifest_field",
    "resolve_source_uri",
    "review_reasons",
    "review_summary",
    "sha256_path",
    "sorted_unique",
    "status_after_for_action",
    "strip_yaml_quotes",
    "uri_values",
    "utc_now",
    "validate_manifest_paths",
    "write_json",
)

PRE_SPLIT_STORE_METHODS = (
    "add_decision",
    "add_source",
    "add_state_packet",
    "attach_contract",
    "brief",
    "check_references",
    "contract_reference_entries",
    "contract_version_path",
    "create_workstream",
    "decision_path",
    "ensure_contract_exists",
    "ensure_ready",
    "existing_workstream_ids",
    "get_live_state",
    "get_workstream",
    "ingest_run_bundle",
    "init",
    "link_workstreams",
    "list_decisions",
    "list_packets",
    "list_sources",
    "list_workstreams",
    "live_state_path",
    "lock_contract_version",
    "packet_path",
    "read_contract_version",
    "read_sources",
    "reference_review",
    "resolve_reference",
    "review_workstreams",
    "save_workstream",
    "set_status",
    "show",
    "used_reference_entries",
    "workstream_path",
    "write_contract_version",
    "write_sources",
)


class RegistryFacadeTest(unittest.TestCase):
    def test_every_pre_split_name_is_exported(self) -> None:
        for name in PRE_SPLIT_NAMES:
            with self.subTest(name=name):
                self.assertTrue(hasattr(registry, name), f"fab.registry lacks {name}")
                self.assertIn(name, registry.__all__)

    def test_all_entries_resolve(self) -> None:
        for name in registry.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(registry, name))

    def test_every_pre_split_store_method_exists(self) -> None:
        for name in PRE_SPLIT_STORE_METHODS:
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(registry.RegistryStore, name, None)), name)


if __name__ == "__main__":
    unittest.main()
