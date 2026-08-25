"""Command-line entry point for the Fab registry.

Each subcommand is a small handler ``(store, args) -> result`` that returns a
JSON-serialisable value and never prints. Rendering is decided once in
:func:`main`: ``--json`` emits the result verbatim, otherwise the renderer
registered for the command (see :mod:`fab.render`) runs. argparse's
``set_defaults`` carries the handler and renderer on the parsed namespace, so
there is no command dispatch chain to keep in sync.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fab import render
from fab.errors import RegistryError
from fab.manifest import read_run_bundle
from fab.pilot import seed_pilot_fixture
from fab.refs import extract_explicit_uris, markdown_title
from fab.review import DEFAULT_STALE_DAYS, REVIEW_REASONS
from fab.status import VALID_DECISION_ACTIONS, VALID_DECISION_TARGET_TYPES, VALID_STATUSES
from fab.store import RELATIONSHIP_CHOICES, RegistryStore

DEFAULT_STORE = ".fab"

Handler = Callable[[RegistryStore, argparse.Namespace], Any]
Renderer = Callable[[Any], None]
JsonPredicate = Callable[[argparse.Namespace], bool]


def parse_json_object(value: str, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RegistryError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RegistryError(f"{label} JSON must be an object")
    return parsed


# ---------------------------------------------------------------- handlers


def cmd_init(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    store.init()
    return {"store": str(store.root), "initialized": True}


def cmd_pilot_fixture(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return seed_pilot_fixture(store)


def cmd_create(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return store.create_workstream(
        title=args.title,
        program=args.program,
        owner=args.owner,
        workstream_id=args.workstream_id,
        status=args.status,
        contract_id=args.contract_id,
        contract_version=args.contract_version,
        artifact_root=args.artifact_root,
        next_review_due_at=args.next_review_due_at,
    )


def cmd_list(store: RegistryStore, args: argparse.Namespace) -> list[dict[str, Any]]:
    return store.list_workstreams(status=args.status, program=args.program)


def cmd_sources_add(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return store.add_source(args.name, args.path, uri_prefix=args.uri_prefix)


def cmd_sources_list(store: RegistryStore, args: argparse.Namespace) -> list[dict[str, Any]]:
    return store.list_sources()


def cmd_refs_check(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return store.check_references(
        contract_id=args.contract_id,
        version=args.version,
        workstream_id=args.workstream_id,
    )


def cmd_contract_add(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.contract_file)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RegistryError(f"cannot read contract file {path}: {exc.strerror or exc}") from exc
    stored = store.write_contract_version(args.contract_id, args.version, text)
    return {
        "contract": {"id": args.contract_id, "version": args.version},
        "path": str(stored),
        "title": markdown_title(text),
        "explicit_refs": extract_explicit_uris(text),
    }


def cmd_contract_show(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "contract": {"id": args.contract_id, "version": args.version},
        "path": str(store.contract_version_path(args.contract_id, args.version)),
        "text": store.read_contract_version(args.contract_id, args.version),
    }


def cmd_validate_bundle(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    """Validate a bundle exactly as ingest would, without reading or writing the store."""
    if (args.contract_id is None) != (args.contract_version is None):
        raise RegistryError("--contract-id and --contract-version must be given together")
    bundle = read_run_bundle(args.bundle_path)
    run = bundle.run
    if args.workstream_id and run["workstream_id"] != args.workstream_id:
        raise RegistryError(
            f"manifest workstream_id is {run['workstream_id']}, expected {args.workstream_id}"
        )
    expected_contract = {"id": args.contract_id, "version": args.contract_version}
    if args.contract_id and run["contract"] != expected_contract:
        raise RegistryError(f"manifest contract is {run['contract']}, expected {expected_contract}")
    return {
        "bundle_path": str(bundle.path),
        "manifest_path": str(bundle.manifest_path),
        "artifact_dir": str(bundle.artifact_dir),
        "run": run,
    }


def cmd_attention(store: RegistryStore, args: argparse.Namespace) -> list[dict[str, Any]]:
    return store.review_workstreams(
        status=args.status,
        program=args.program,
        reason=args.reason,
        stale_days=args.stale_days,
        include_clear=args.all,
    )


def cmd_brief(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return store.brief(
        program=args.program,
        contract_id=args.contract_id,
        stale_days=args.stale_days,
    )


def cmd_show(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return store.show(args.workstream_id)


def cmd_status(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return store.set_status(args.workstream_id, args.status, force=args.force)


def cmd_attach_contract(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return store.attach_contract(
        args.workstream_id,
        contract_id=args.contract_id,
        version=args.version,
    )


def cmd_link(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return store.link_workstreams(
        args.workstream_id,
        args.target_id,
        relationship=args.relationship,
    )


def cmd_packet(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    artifact_refs = [
        parse_json_object(value, label="artifact")
        for value in (args.artifact_json or [])
    ]
    return store.add_state_packet(
        args.workstream_id,
        source=args.source,
        changed=args.changed,
        tried=args.tried,
        failed=args.failed,
        result=args.result,
        next_action=args.next_action,
        rationale=args.rationale,
        blocker=args.blocker,
        deviation=args.deviation,
        flag=args.flag,
        artifact=args.artifact,
        artifact_ref=artifact_refs,
    )


def cmd_ingest_run(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return store.ingest_run_bundle(args.bundle_path)


def cmd_judge(store: RegistryStore, args: argparse.Namespace) -> dict[str, Any]:
    return store.add_decision(
        args.workstream_id,
        action=args.action,
        rationale=args.rationale,
        actor=args.actor,
        next_review_due_at=args.next_review_due_at,
        target_type=args.target_type,
        target_id=args.target_id,
    )


# ------------------------------------------------------------------ parser


def json_requested(args: argparse.Namespace) -> bool:
    return bool(args.json)


def show_json_requested(args: argparse.Namespace) -> bool:
    """``show`` prints JSON unless the human ``--brief`` view was asked for."""
    return bool(args.json) or not args.brief


def add_command(
    subparsers: argparse._SubParsersAction,
    name: str,
    *,
    help: str,
    run: Handler,
    render: Renderer,
    wants_json: JsonPredicate = json_requested,
) -> argparse.ArgumentParser:
    """Register a leaf command with its handler, renderer and ``--json`` flag."""
    parser = subparsers.add_parser(name, help=help)
    parser.add_argument("--json", action="store_true", help="print the JSON result instead of text")
    parser.set_defaults(run=run, render=render, wants_json=wants_json)
    return parser


def add_workstream_id(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("workstream_id")


def add_workstream_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--status", choices=sorted(VALID_STATUSES))
    parser.add_argument("--program")


def add_stale_days(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS)


def add_next_attention_due(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--next-attention-due-at", dest="next_review_due_at")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fab",
        description="Manage the Fab research protocol store.",
    )
    parser.add_argument(
        "--store",
        default=DEFAULT_STORE,
        help=f"registry store path (default: {DEFAULT_STORE})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add_command(
        sub,
        "init",
        help="initialize the registry store",
        run=cmd_init,
        render=render.initialized,
    )
    add_command(
        sub,
        "pilot-fixture",
        help="seed an empty store with a simulated pilot",
        run=cmd_pilot_fixture,
        render=render.pilot_fixture,
    )

    create = add_command(
        sub,
        "create",
        help="create a workstream registry entry",
        run=cmd_create,
        render=render.workstream,
    )
    create.add_argument("--id", dest="workstream_id")
    create.add_argument("--title", required=True)
    create.add_argument("--program", required=True)
    create.add_argument("--owner")
    create.add_argument("--status", default="planned", choices=sorted(VALID_STATUSES))
    create.add_argument("--contract-id")
    create.add_argument("--contract-version", type=int)
    create.add_argument("--artifact-root")
    add_next_attention_due(create)

    list_cmd = add_command(
        sub,
        "list",
        help="list workstreams",
        run=cmd_list,
        render=render.workstream_table,
    )
    add_workstream_filters(list_cmd)

    sources = sub.add_parser("sources", help="manage external source adapters")
    sources_sub = sources.add_subparsers(dest="sources_command", required=True)
    sources_add = add_command(
        sources_sub,
        "add",
        help="register a source URI prefix",
        run=cmd_sources_add,
        render=render.source_added,
    )
    sources_add.add_argument("name")
    sources_add.add_argument("path")
    sources_add.add_argument("--uri-prefix", required=True)
    add_command(
        sources_sub,
        "list",
        help="list configured sources",
        run=cmd_sources_list,
        render=render.sources,
    )

    refs = sub.add_parser("refs", help="check explicit prior-context references")
    refs_sub = refs.add_subparsers(dest="refs_command", required=True)
    refs_check = add_command(
        refs_sub,
        "check",
        help="resolve explicit references",
        run=cmd_refs_check,
        render=render.refs_check,
    )
    refs_target = refs_check.add_mutually_exclusive_group(required=True)
    refs_target.add_argument("--workstream-id")
    refs_target.add_argument("--contract-id")
    refs_check.add_argument("--version", type=int)

    contract = sub.add_parser("contract", help="register and read contract versions")
    contract_sub = contract.add_subparsers(dest="contract_command", required=True)
    contract_add = add_command(
        contract_sub,
        "add",
        help="register a contract version from a Markdown file and lock it read-only",
        run=cmd_contract_add,
        render=render.contract_added,
    )
    contract_add.add_argument("contract_id")
    contract_add.add_argument("--version", required=True, type=int)
    contract_add.add_argument(
        "--from",
        dest="contract_file",
        required=True,
        help="path to the Markdown contract to register",
    )
    contract_show = add_command(
        contract_sub,
        "show",
        help="print a registered contract version",
        run=cmd_contract_show,
        render=render.contract_text,
    )
    contract_show.add_argument("contract_id")
    contract_show.add_argument("--version", required=True, type=int)

    attention = add_command(
        sub,
        "attention",
        help="list workstreams needing human attention",
        run=cmd_attention,
        render=render.attention_table,
    )
    add_workstream_filters(attention)
    attention.add_argument("--reason", choices=sorted(REVIEW_REASONS))
    add_stale_days(attention)
    attention.add_argument(
        "--all",
        action="store_true",
        help="include workstreams with no attention reasons",
    )

    brief = add_command(
        sub,
        "brief",
        help="summarize current work for human review",
        run=cmd_brief,
        render=render.brief,
    )
    brief.add_argument("--program")
    brief.add_argument("--contract-id")
    add_stale_days(brief)

    show = add_command(
        sub,
        "show",
        help="show one workstream with live state",
        run=cmd_show,
        render=render.workstream_detail,
        wants_json=show_json_requested,
    )
    add_workstream_id(show)
    show.add_argument("--brief", action="store_true", help="print a human inspection view")

    status = add_command(
        sub,
        "status",
        help="set a workstream lifecycle status",
        run=cmd_status,
        render=render.workstream,
    )
    add_workstream_id(status)
    status.add_argument("status", choices=sorted(VALID_STATUSES))
    status.add_argument(
        "--force",
        action="store_true",
        help="bypass lifecycle transition rules (for correcting mistakes)",
    )

    attach = add_command(
        sub,
        "attach-contract",
        help="attach a contract pointer",
        run=cmd_attach_contract,
        render=render.workstream,
    )
    add_workstream_id(attach)
    attach.add_argument("--contract-id", required=True)
    attach.add_argument("--version", required=True, type=int)

    link = add_command(
        sub,
        "link",
        help="link two workstreams",
        run=cmd_link,
        render=render.workstream,
    )
    add_workstream_id(link)
    link.add_argument("target_id")
    link.add_argument("--relationship", default="related", choices=RELATIONSHIP_CHOICES)

    packet = add_command(
        sub,
        "packet",
        help="append a state packet and update live state",
        run=cmd_packet,
        render=render.packet_added,
    )
    add_workstream_id(packet)
    packet.add_argument("--source", required=True)
    packet.add_argument("--changed")
    packet.add_argument("--tried")
    packet.add_argument("--failed")
    packet.add_argument("--result")
    packet.add_argument("--next", dest="next_action")
    packet.add_argument("--rationale")
    packet.add_argument("--blocker", action="append")
    packet.add_argument("--deviation", action="append")
    packet.add_argument("--flag", action="append")
    packet.add_argument("--artifact", action="append")
    packet.add_argument("--artifact-json", action="append")

    ingest = add_command(
        sub,
        "ingest-run",
        help="ingest a completed remote run bundle",
        run=cmd_ingest_run,
        render=render.run_ingested,
    )
    ingest.add_argument("--from", dest="bundle_path", required=True)

    validate = add_command(
        sub,
        "validate-bundle",
        help="validate a run bundle's layout and manifest without touching the store",
        run=cmd_validate_bundle,
        render=render.bundle_valid,
    )
    validate.add_argument("bundle_path")
    validate.add_argument("--workstream-id", help="require this workstream id in the manifest")
    validate.add_argument("--contract-id", help="require this contract id (with --contract-version)")
    validate.add_argument("--contract-version", type=int)

    judge = add_command(
        sub,
        "judge",
        help="record a human judgment",
        run=cmd_judge,
        render=render.judgment_recorded,
    )
    add_workstream_id(judge)
    judge.add_argument("--action", required=True, choices=sorted(VALID_DECISION_ACTIONS))
    judge.add_argument(
        "--target-type",
        default="workstream",
        choices=sorted(VALID_DECISION_TARGET_TYPES),
    )
    judge.add_argument("--target-id")
    judge.add_argument("--rationale", required=True)
    judge.add_argument("--actor")
    add_next_attention_due(judge)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = RegistryStore.at(Path(args.store))
    try:
        result = args.run(store, args)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.wants_json(args):
        render.print_json(result)
    else:
        args.render(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
