"""Explicit prior-context references: URI extraction, resolution and comparison.

Contracts name their context as ``scheme://`` URIs; artefacts record the
references they actually used. A :class:`ReferenceResolver` maps URIs onto
configured local sources and pins each file with a content hash and git commit.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fab.errors import RegistryError
from fab.provenance import git_commit_for_path, git_dirty, sha256_path

if TYPE_CHECKING:
    from fab.store import RegistryStore

URI_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s<>\]`\"']+")
TRAILING_URI_PUNCTUATION = ".,;:"
HTTP_SCHEMES = ("http://", "https://")


def extract_explicit_uris(text: str) -> list[str]:
    """Return the distinct ``scheme://`` URIs in ``text`` in first-seen order."""
    uris: list[str] = []
    for match in URI_RE.finditer(text):
        uri = match.group(0).rstrip(TRAILING_URI_PUNCTUATION)
        while uri.endswith(")") and uri.count("(") < uri.count(")"):
            uri = uri[:-1]
        if uri and uri not in uris:
            uris.append(uri)
    return uris


def strip_yaml_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def markdown_title(text: str) -> str | None:
    """Prefer a front-matter ``title:``; fall back to the first ``# `` heading."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                if line.startswith("title:"):
                    title = strip_yaml_quotes(line.split(":", 1)[1])
                    if title:
                        return title
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            if title:
                return title
    return None


def resolution(uri: str, status: str, **fields: Any) -> dict[str, Any]:
    """Build a resolution record with every field present, then overlay ``fields``."""
    record: dict[str, Any] = {
        "status": status,
        "uri": uri,
        "source": None,
        "title": None,
        "content_hash": None,
        "git_commit": None,
        "git_dirty": None,
        "path": None,
    }
    record.update(fields)
    return record


class ReferenceResolver:
    """Resolve ``scheme://`` URIs against configured local sources.

    Sources are read once when the resolver is built, and both URI resolutions
    and each source root's git dirty state are memoised. A brief that touches
    the same reference from many artefacts therefore costs one hash and at most
    two git subprocesses per distinct file, instead of one ``sources.json``
    read and two git spawns per mention.
    """

    def __init__(self, sources: dict[str, dict[str, Any]]) -> None:
        self._sources = [(name, sources[name]) for name in sorted(sources)]
        self._resolutions: dict[str, dict[str, Any]] = {}
        self._dirty_by_root: dict[Path, bool | None] = {}

    @classmethod
    def for_store(cls, store: RegistryStore) -> ReferenceResolver:
        return cls(store.read_sources()["sources"])

    def resolve(self, uri: str) -> dict[str, Any]:
        if uri not in self._resolutions:
            self._resolutions[uri] = self._resolve(uri)
        return dict(self._resolutions[uri])

    def contract_entries(self, contract_id: str, version: int, text: str) -> list[dict[str, Any]]:
        return [
            {
                "contract": {"id": contract_id, "version": version},
                "uri": uri,
                "resolution": self.resolve(uri),
            }
            for uri in extract_explicit_uris(text)
        ]

    def used_entries(self, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Resolve ``used_refs`` for records carrying ``workstream_id``, ``id`` and ``used_refs``."""
        return [
            {
                "workstream_id": artifact.get("workstream_id"),
                "artifact_id": artifact.get("id"),
                "uri": uri,
                "resolution": self.resolve(uri),
            }
            for artifact in artifacts
            for uri in artifact.get("used_refs", [])
        ]

    def _resolve(self, uri: str) -> dict[str, Any]:
        for name, source in self._sources:
            prefix = source.get("uri_prefix")
            if prefix and uri.startswith(prefix):
                return self.resolve_in_source(name, source, uri)
        if uri.startswith(HTTP_SCHEMES):
            return resolution(uri, "external", source="http")
        return resolution(uri, "unresolved", error="no configured source matches URI prefix")

    def _root_dirty(self, root: Path) -> bool | None:
        if root not in self._dirty_by_root:
            self._dirty_by_root[root] = git_dirty(root) if root.exists() else None
        return self._dirty_by_root[root]

    def resolve_in_source(self, name: str, source: dict[str, Any], uri: str) -> dict[str, Any]:
        """Resolve ``uri`` against one named source, assuming its prefix already matched."""
        prefix = str(source.get("uri_prefix") or "")
        root = Path(str(source.get("path") or "")).expanduser().resolve()
        path = (root / uri[len(prefix):].lstrip("/")).resolve()
        base = {"source": name, "path": str(path), "git_dirty": self._root_dirty(root)}
        try:
            path.relative_to(root)
        except ValueError:
            return resolution(uri, "unresolved", error="resolved path escapes source root", **base)
        if not path.is_file():
            return resolution(uri, "unresolved", error="referenced file does not exist", **base)
        text = path.read_text(encoding="utf-8", errors="replace")
        return resolution(
            uri,
            "resolved",
            title=markdown_title(text),
            content_hash=sha256_path(path),
            git_commit=git_commit_for_path(root, path),
            **base,
        )


def resolve_source_uri(source_name: str, source: dict[str, Any], uri: str) -> dict[str, Any]:
    """Resolve one URI against one source without sharing a resolver."""
    return ReferenceResolver({source_name: source}).resolve_in_source(source_name, source, uri)


def uri_values(entries: list[dict[str, Any]]) -> list[str]:
    return sorted({entry["uri"] for entry in entries if entry.get("uri")})


def unresolved_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        entry for entry in entries
        if (entry.get("resolution") or {}).get("status") == "unresolved"
    ]


def reference_check_result(
    scope: dict[str, Any],
    explicit_refs: list[dict[str, Any]],
    used_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    explicit_uris = set(uri_values(explicit_refs))
    used_uris = set(uri_values(used_refs))
    return {
        "scope": scope,
        "explicit_refs": explicit_refs,
        "used_refs": used_refs,
        "comparison": {
            "explicit_uris": sorted(explicit_uris),
            "used_uris": sorted(used_uris),
            "used_not_explicit": sorted(used_uris - explicit_uris),
            "explicit_not_used": sorted(explicit_uris - used_uris),
            "unresolved_explicit": unresolved_entries(explicit_refs),
            "unresolved_used": unresolved_entries(used_refs),
        },
    }


def contract_refs(
    store: RegistryStore,
    resolver: ReferenceResolver,
    contract_id: str,
    version: int,
) -> list[dict[str, Any]]:
    text = store.read_contract_version(contract_id, version)
    return resolver.contract_entries(contract_id, version, text)


def reference_check(
    store: RegistryStore,
    *,
    contract_id: str | None = None,
    version: int | None = None,
    workstream_id: str | None = None,
) -> dict[str, Any]:
    """Resolve explicit refs for one contract version or one workstream."""
    if bool(workstream_id) == bool(contract_id):
        raise RegistryError("specify exactly one of workstream_id or contract_id")
    resolver = ReferenceResolver.for_store(store)

    if workstream_id:
        entry = store.get_workstream(workstream_id)
        live_state = store.get_live_state(workstream_id)
        contract = entry.get("contract") or {}
        contract_id = contract.get("id")
        version = contract.get("version")
        explicit: list[dict[str, Any]] = []
        if contract_id and version is not None:
            explicit = contract_refs(store, resolver, contract_id, version)
        used = resolver.used_entries(
            [
                {
                    "workstream_id": workstream_id,
                    "id": artifact.get("id"),
                    "used_refs": artifact.get("used_refs", []),
                }
                for artifact in live_state.get("artifacts", [])
            ]
        )
        scope = {
            "type": "workstream",
            "workstream_id": workstream_id,
            "contract": {"id": contract_id, "version": version},
        }
        return reference_check_result(scope, explicit, used)

    if version is None:
        raise RegistryError(f"contract version is required for {contract_id}")
    explicit = contract_refs(store, resolver, str(contract_id), version)
    scope = {"type": "contract", "contract": {"id": contract_id, "version": version}}
    return reference_check_result(scope, explicit, [])


def brief_reference_review(
    store: RegistryStore,
    workstreams: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare every distinct attached contract's explicit refs with artefact used refs."""
    resolver = ReferenceResolver.for_store(store)
    explicit: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for workstream in workstreams:
        contract = workstream.get("contract") or {}
        contract_id = contract.get("id")
        version = contract.get("version")
        if not contract_id or version is None:
            continue
        key = (str(contract_id), int(version))
        if key in seen:
            continue
        seen.add(key)
        try:
            explicit.extend(contract_refs(store, resolver, *key))
        except RegistryError:
            explicit.append(
                {
                    "contract": {"id": key[0], "version": key[1]},
                    "uri": None,
                    "resolution": {
                        "status": "unresolved",
                        "error": "contract version could not be read",
                    },
                }
            )
    return reference_check_result({"type": "brief"}, explicit, resolver.used_entries(artifacts))
