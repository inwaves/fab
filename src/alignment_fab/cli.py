from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from alignment_fab.registry import RegistryError, RegistryStore, VALID_STATUSES


DEFAULT_STORE = ".alignment-fab"


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def print_workstream_row(item: dict[str, Any]) -> None:
    state_at = item.get("timestamps", {}).get("last_state_update_at") or "-"
    contract = item.get("contract", {})
    contract_label = contract.get("id") or "-"
    print(
        f"{item['id']}\t{item.get('status', '-')}\t{item.get('program', '-')}\t"
        f"{contract_label}\t{state_at}\t{item.get('title', '')}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alignment-fab",
        description="Manage the Alignment Fab workstream registry.",
    )
    parser.add_argument(
        "--store",
        default=DEFAULT_STORE,
        help=f"registry store path (default: {DEFAULT_STORE})",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize the registry store")
    init.add_argument("--json", action="store_true")

    create = sub.add_parser("create", help="create a workstream registry entry")
    create.add_argument("--id", dest="workstream_id")
    create.add_argument("--title", required=True)
    create.add_argument("--program", required=True)
    create.add_argument("--owner")
    create.add_argument("--status", default="planned", choices=sorted(VALID_STATUSES))
    create.add_argument("--contract-id")
    create.add_argument("--contract-version", type=int)
    create.add_argument("--artifact-root")
    create.add_argument("--next-review-due-at")
    create.add_argument("--json", action="store_true")

    list_cmd = sub.add_parser("list", help="list workstreams")
    list_cmd.add_argument("--status", choices=sorted(VALID_STATUSES))
    list_cmd.add_argument("--program")
    list_cmd.add_argument("--json", action="store_true")

    show = sub.add_parser("show", help="show one workstream with live state")
    show.add_argument("workstream_id")
    show.add_argument("--json", action="store_true")

    status = sub.add_parser("status", help="set a workstream lifecycle status")
    status.add_argument("workstream_id")
    status.add_argument("status", choices=sorted(VALID_STATUSES))
    status.add_argument("--json", action="store_true")

    attach = sub.add_parser("attach-contract", help="attach a contract pointer")
    attach.add_argument("workstream_id")
    attach.add_argument("--contract-id", required=True)
    attach.add_argument("--version", type=int)
    attach.add_argument("--json", action="store_true")

    link = sub.add_parser("link", help="link two workstreams")
    link.add_argument("workstream_id")
    link.add_argument("target_id")
    link.add_argument(
        "--relationship",
        default="related",
        choices=["parent", "children", "related", "blocks", "blocked_by"],
    )
    link.add_argument("--json", action="store_true")

    packet = sub.add_parser("packet", help="append a state packet and update live state")
    packet.add_argument("workstream_id")
    packet.add_argument("--source", required=True)
    packet.add_argument("--changed")
    packet.add_argument("--tried")
    packet.add_argument("--failed")
    packet.add_argument("--result")
    packet.add_argument("--next", dest="next_action")
    packet.add_argument("--continue-reason")
    packet.add_argument("--blocker", action="append")
    packet.add_argument("--deviation", action="append")
    packet.add_argument("--flag", action="append")
    packet.add_argument("--artifact", action="append")
    packet.add_argument("--json", action="store_true")

    decide = sub.add_parser("decide", help="record a human steering decision")
    decide.add_argument("workstream_id")
    decide.add_argument(
        "--action",
        required=True,
        choices=[
            "continue",
            "pause",
            "stop",
            "complete",
            "quarantine",
            "merge",
            "split",
            "replicate",
            "escalate",
            "promote",
        ],
    )
    decide.add_argument("--rationale", required=True)
    decide.add_argument("--actor")
    decide.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = RegistryStore.at(Path(args.store))

    try:
        if args.command == "init":
            store.init()
            result = {"store": str(store.root), "initialized": True}
            print_json(result) if args.json else print(f"Initialized {store.root}")
            return 0

        if args.command == "create":
            result = store.create_workstream(
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
            print_json(result) if args.json else print_workstream_row(result)
            return 0

        if args.command == "list":
            result = store.list_workstreams(status=args.status, program=args.program)
            if args.json:
                print_json(result)
            else:
                print("id\tstatus\tprogram\tcontract\tlast_state_update\ttitle")
                for item in result:
                    print_workstream_row(item)
            return 0

        if args.command == "show":
            result = store.show(args.workstream_id)
            print_json(result)
            return 0

        if args.command == "status":
            result = store.set_status(args.workstream_id, args.status)
            print_json(result) if args.json else print_workstream_row(result)
            return 0

        if args.command == "attach-contract":
            result = store.attach_contract(
                args.workstream_id,
                contract_id=args.contract_id,
                version=args.version,
            )
            print_json(result) if args.json else print_workstream_row(result)
            return 0

        if args.command == "link":
            result = store.link_workstreams(
                args.workstream_id,
                args.target_id,
                relationship=args.relationship,
            )
            print_json(result) if args.json else print_workstream_row(result)
            return 0

        if args.command == "packet":
            result = store.add_state_packet(
                args.workstream_id,
                source=args.source,
                changed=args.changed,
                tried=args.tried,
                failed=args.failed,
                result=args.result,
                next_action=args.next_action,
                continue_reason=args.continue_reason,
                blocker=args.blocker,
                deviation=args.deviation,
                flag=args.flag,
                artifact=args.artifact,
            )
            print_json(result) if args.json else print(f"Added {result['id']} to {args.workstream_id}")
            return 0

        if args.command == "decide":
            result = store.add_decision(
                args.workstream_id,
                action=args.action,
                rationale=args.rationale,
                actor=args.actor,
            )
            print_json(result) if args.json else print(f"Recorded {result['id']} for {args.workstream_id}")
            return 0

    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unhandled command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

