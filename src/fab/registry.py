"""Compatibility facade for the Fab registry.

The implementation lives in focused modules:

- :mod:`fab.store` -- :class:`RegistryStore`, the file-backed store
- :mod:`fab.status` -- lifecycle statuses, transitions and judgment actions
- :mod:`fab.artifacts` -- artefact reference normalisation
- :mod:`fab.manifest` -- remote run-bundle manifests
- :mod:`fab.livestate` -- live-state shape and packet merging
- :mod:`fab.review` -- attention rules
- :mod:`fab.brief` -- the cross-workstream brief
- :mod:`fab.refs` -- explicit reference extraction and resolution
- :mod:`fab.provenance` -- content hashes and git metadata
- :mod:`fab.util` -- time, JSON I/O and identifier helpers

Every name that was importable from ``fab.registry`` before the split is still
importable here, so ``from fab.registry import RegistryStore`` and friends keep
working; ``tests/test_registry_facade.py`` pins that list. Helpers introduced
by the split (for example ``ensure_status``, ``attention_items``,
``reference_check``) are intentionally only available from their own modules.
New code should import from the concrete module.

One behavioural change is deliberate: :func:`git_output` now returns ``""`` for
a successful git command with no output (it used to return ``None``), so
:func:`git_dirty` reports a clean tree as ``False`` rather than unknown.
"""

from __future__ import annotations

from fab.artifacts import (
    ARTIFACT_PROVENANCE_FIELDS,
    artifact_ids,
    artifact_target_exists,
    claim_target_exists,
    normalize_artifact_claims,
    normalize_artifact_evidence,
    normalize_artifact_provenance,
    normalize_artifact_ref,
    normalize_artifact_refs,
    normalize_artifact_reproduction,
    normalize_artifact_review,
)
from fab.brief import (
    artifact_ref_from_summary,
    brief_artifact_summary,
    brief_claim_summary,
    build_brief,
    claim_ref_from_summary,
    contract_review_from_brief,
    grouped_artifact_statuses,
    grouped_artifact_strings,
    grouped_claims,
    matching_decisions,
    next_context_from_decisions,
    normalized_comparison_text,
    sorted_unique,
)
from fab.errors import RegistryError
from fab.livestate import empty_live_state, merge_packet_into_live_state
from fab.manifest import (
    REMOTE_RUN_STATUSES,
    RunBundle,
    normalize_manifest_string,
    normalize_manifest_string_list,
    normalize_run_contract,
    normalize_run_evidence,
    normalize_run_manifest,
    read_run_bundle,
    require_manifest_field,
    validate_manifest_paths,
)
from fab.provenance import (
    git_commit_for_path,
    git_dirty,
    git_head,
    git_output,
    sha256_file,
    sha256_path,
)
from fab.refs import (
    TRAILING_URI_PUNCTUATION,
    URI_RE,
    ReferenceResolver,
    extract_explicit_uris,
    markdown_title,
    reference_check_result,
    resolve_source_uri,
    strip_yaml_quotes,
    uri_values,
)
from fab.review import REVIEW_REASONS, attached_contract_summary, review_reasons, review_summary
from fab.status import (
    STATUS_TRANSITIONS,
    TERMINAL_STATUSES,
    VALID_DECISION_ACTIONS,
    VALID_DECISION_TARGET_TYPES,
    VALID_STATUSES,
    ensure_status_transition,
    normalize_decision_target,
    status_after_for_action,
)
from fab.store import (
    READ_ONLY_FILE_MODE,
    RELATIONSHIP_LIST_FIELDS,
    RegistryStore,
    contract_version_filename,
)
from fab.util import (
    SAFE_ID_RE,
    append_unique,
    compact_id,
    ensure_safe_id,
    normalize_string_list,
    parse_datetime,
    read_json,
    utc_now,
    write_json,
)

__all__ = [
    "ARTIFACT_PROVENANCE_FIELDS",
    "READ_ONLY_FILE_MODE",
    "RELATIONSHIP_LIST_FIELDS",
    "REMOTE_RUN_STATUSES",
    "REVIEW_REASONS",
    "SAFE_ID_RE",
    "STATUS_TRANSITIONS",
    "TERMINAL_STATUSES",
    "TRAILING_URI_PUNCTUATION",
    "URI_RE",
    "VALID_DECISION_ACTIONS",
    "VALID_DECISION_TARGET_TYPES",
    "VALID_STATUSES",
    "ReferenceResolver",
    "RegistryError",
    "RegistryStore",
    "RunBundle",
    "append_unique",
    "artifact_ids",
    "artifact_ref_from_summary",
    "artifact_target_exists",
    "attached_contract_summary",
    "brief_artifact_summary",
    "brief_claim_summary",
    "build_brief",
    "claim_ref_from_summary",
    "claim_target_exists",
    "compact_id",
    "contract_review_from_brief",
    "contract_version_filename",
    "empty_live_state",
    "ensure_safe_id",
    "ensure_status_transition",
    "extract_explicit_uris",
    "git_commit_for_path",
    "git_dirty",
    "git_head",
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
    "read_run_bundle",
    "reference_check_result",
    "require_manifest_field",
    "resolve_source_uri",
    "review_reasons",
    "review_summary",
    "sha256_file",
    "sha256_path",
    "sorted_unique",
    "status_after_for_action",
    "strip_yaml_quotes",
    "uri_values",
    "utc_now",
    "validate_manifest_paths",
    "write_json",
]
