from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from fab.pilot import seed_pilot_fixture
from fab.registry import (
    REVIEW_REASONS,
    RegistryError,
    RegistryStore,
    VALID_DECISION_ACTIONS,
    VALID_DECISION_TARGET_TYPES,
    VALID_STATUSES,
)


DEFAULT_STORE = ".fab"


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def parse_json_object(value: str, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RegistryError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RegistryError(f"{label} JSON must be an object")
    return parsed


def print_workstream_row(item: dict[str, Any]) -> None:
    state_at = item.get("timestamps", {}).get("last_state_update_at") or "-"
    contract = item.get("contract", {})
    contract_label = contract.get("id") or "-"
    print(
        f"{item['id']}\t{item.get('status', '-')}\t{item.get('program', '-')}\t"
        f"{contract_label}\t{state_at}\t{item.get('title', '')}"
    )


def print_review_row(item: dict[str, Any]) -> None:
    workstream = item["workstream"]
    review = item["review"]
    state_at = workstream.get("timestamps", {}).get("last_state_update_at") or "-"
    due_at = workstream.get("timestamps", {}).get("next_review_due_at") or "-"
    reasons = ",".join(review.get("reasons", [])) or "-"
    print(
        f"{workstream['id']}\t{workstream.get('status', '-')}\t"
        f"{workstream.get('program', '-')}\t{reasons}\t{state_at}\t{due_at}\t"
        f"{workstream.get('title', '')}"
    )


def print_review_detail(data: dict[str, Any]) -> None:
    workstream = data["workstream"]
    live_state = data["live_state"]
    contract = data.get("attached_contract")
    review = data["review"]

    contract_label = "-"
    if contract:
        contract_label = f"{contract['id']} v{contract['version']}"
        if not contract.get("exists"):
            contract_label += " (missing)"

    print(f"{workstream['id']}\t{workstream.get('status', '-')}\t{workstream.get('program', '-')}")
    print(f"title: {workstream.get('title', '')}")
    print(f"contract: {contract_label}")
    print(f"attention reasons: {', '.join(review.get('reasons', [])) or '-'}")
    print(f"last state update: {workstream.get('timestamps', {}).get('last_state_update_at') or '-'}")
    print(f"next attention due: {workstream.get('timestamps', {}).get('next_review_due_at') or '-'}")

    print("\nContract")
    if contract and contract.get("text"):
        print(contract["text"].rstrip())
    else:
        print("-")

    print("\nLive State")
    print(f"current hypothesis: {live_state.get('current_hypothesis') or '-'}")
    print(f"current plan: {live_state.get('current_plan') or '-'}")
    print(f"next intended action: {live_state.get('next_intended_action') or '-'}")
    print(f"current rationale: {live_state.get('rationale') or '-'}")
    print_list("experiments", live_state.get("experiments", []))
    print_list("results", live_state.get("results", []))
    print_list("failed attempts", live_state.get("failed_attempts", []))
    print_list("blockers", live_state.get("blockers", []))
    print_list("deviations", live_state.get("deviations", []))
    print_list("flags", live_state.get("flags", []))
    print_artifacts_detail(live_state.get("artifacts", []))

    print("\nRecent Packets")
    packets = data.get("recent_packets", [])
    if packets:
        for packet in packets:
            print(
                f"- {packet['id']} {packet.get('created_at', '-')}: "
                f"next={packet.get('next_action') or '-'}; "
                f"rationale={packet.get('rationale') or '-'}"
            )
    else:
        print("-")

    print("\nRecent Decisions")
    decisions = data.get("recent_decisions", [])
    if decisions:
        for decision in decisions:
            print(
                f"- {decision['id']} {decision.get('created_at', '-')}: "
                f"{decision.get('action')} {decision_target_label(decision)} "
                f"-> {decision.get('status_after')}; "
                f"{decision.get('rationale')}"
            )
    else:
        print("-")


def print_brief(data: dict[str, Any]) -> None:
    filters = data.get("filters", {})
    counts = data.get("counts", {})
    filter_bits = [
        f"{key}={value}"
        for key, value in filters.items()
        if value is not None
    ]
    print(f"Fab brief\t{data.get('generated_at', '-')}\t{', '.join(filter_bits) or 'all'}")
    print(
        "counts\t"
        f"workstreams={counts.get('workstreams', 0)}\t"
        f"attention={counts.get('attention', 0)}\t"
        f"artifacts={counts.get('artifacts', 0)}\t"
        f"claims={counts.get('claims', 0)}\t"
        f"decisions={counts.get('decisions', 0)}"
    )

    print("\nAttention")
    attention = data.get("attention", [])
    if attention:
        for item in attention:
            print(
                f"- {item.get('workstream_id')}: "
                f"{','.join(item.get('reasons', [])) or '-'}; "
                f"{item.get('title', '')}"
            )
    else:
        print("-")

    print("\nWorkstreams")
    workstreams = data.get("workstreams", [])
    if workstreams:
        for item in workstreams:
            print(
                f"- {item.get('id')}\t{item.get('status', '-')}\t"
                f"{item.get('title', '')}"
            )
            if item.get("results"):
                print(f"  result: {item['results'][-1]}")
            if item.get("next_intended_action"):
                print(f"  next: {item['next_intended_action']}")
    else:
        print("-")

    print("\nClaims")
    claims = data.get("claims", [])
    if claims:
        for claim in claims:
            judgment_actions = [
                str(decision.get("action"))
                for decision in claim.get("judgments", [])
                if decision.get("action")
            ]
            judgment_suffix = (
                f" [{', '.join(judgment_actions)}]"
                if judgment_actions
                else ""
            )
            confidence = claim.get("confidence") or "-"
            print(
                f"- {claim.get('workstream_id')}/{claim.get('ref')} "
                f"({confidence}){judgment_suffix}: {claim.get('text')}"
            )
    else:
        print("-")

    print("\nNext Context")
    next_context = data.get("next_context", {})
    printed = False
    for bucket, items in next_context.items():
        if not items:
            continue
        printed = True
        print(f"{bucket}:")
        for item in items:
            target = item.get("target") or {}
            print(
                f"- {item.get('workstream_id')} "
                f"{target.get('type', 'workstream')}:{target.get('id', '-')}; "
                f"{item.get('rationale')}"
            )
    if not printed:
        print("-")


def print_list(label: str, values: list[Any]) -> None:
    if not values:
        print(f"{label}: -")
        return
    print(f"{label}:")
    for value in values:
        print(f"- {format_list_value(value)}")


def print_artifacts_detail(artifacts: list[dict[str, Any]]) -> None:
    if not artifacts:
        print("artifacts: -")
        return

    print("artifacts:")
    for artifact in artifacts:
        print(
            f"- {artifact.get('id')} {artifact.get('kind', 'artifact')} "
            f"{artifact.get('path', '-')}: {artifact.get('description') or '-'}"
        )
        if artifact.get("uncertainty"):
            print(f"  uncertainty: {artifact['uncertainty']}")
        claims = artifact.get("claims", [])
        if claims:
            print("  claims:")
            for claim in claims:
                confidence = claim.get("confidence") or "-"
                print(f"  - {claim.get('id')} ({confidence}): {claim.get('text')}")
                if claim.get("caveats"):
                    print(f"    caveats: {', '.join(claim['caveats'])}")
        evidence = artifact.get("evidence", [])
        if evidence:
            print("  evidence:")
            for item in evidence:
                path = f" {item['path']}" if item.get("path") else ""
                print(
                    f"  - {item.get('id')} {item.get('kind', 'evidence')}{path}: "
                    f"{item.get('summary')}"
                )
        reproduction = artifact.get("reproduction") or {}
        commands = reproduction.get("commands") or []
        if commands:
            print("  reproduce:")
            for command in commands:
                print(f"  - {command}")


def format_list_value(value: Any) -> str:
    if isinstance(value, dict):
        if {"id", "kind", "path"}.issubset(value):
            description = f": {value['description']}" if value.get("description") else ""
            return f"{value['id']} {value['kind']} {value['path']}{description}"
        return json.dumps(value, sort_keys=True)
    return str(value)


def decision_target_label(decision: dict[str, Any]) -> str:
    target = decision.get("target")
    if not target:
        return f"workstream:{decision.get('workstream_id', '-')}"
    return f"{target.get('type', 'workstream')}:{target.get('id', '-')}"


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

    init = sub.add_parser("init", help="initialize the registry store")
    init.add_argument("--json", action="store_true")

    pilot = sub.add_parser("pilot-fixture", help="seed an empty store with a simulated pilot")
    pilot.add_argument("--json", action="store_true")

    create = sub.add_parser("create", help="create a workstream registry entry")
    create.add_argument("--id", dest="workstream_id")
    create.add_argument("--title", required=True)
    create.add_argument("--program", required=True)
    create.add_argument("--owner")
    create.add_argument("--status", default="planned", choices=sorted(VALID_STATUSES))
    create.add_argument("--contract-id")
    create.add_argument("--contract-version", type=int)
    create.add_argument("--artifact-root")
    create.add_argument("--next-attention-due-at", dest="next_review_due_at")
    create.add_argument("--json", action="store_true")

    list_cmd = sub.add_parser("list", help="list workstreams")
    list_cmd.add_argument("--status", choices=sorted(VALID_STATUSES))
    list_cmd.add_argument("--program")
    list_cmd.add_argument("--json", action="store_true")

    attention = sub.add_parser("attention", help="list workstreams needing human attention")
    attention.add_argument("--status", choices=sorted(VALID_STATUSES))
    attention.add_argument("--program")
    attention.add_argument("--reason", choices=sorted(REVIEW_REASONS))
    attention.add_argument("--stale-days", type=int, default=7)
    attention.add_argument("--all", action="store_true", help="include workstreams with no attention reasons")
    attention.add_argument("--json", action="store_true")

    brief = sub.add_parser("brief", help="summarize current work for human review")
    brief.add_argument("--program")
    brief.add_argument("--contract-id")
    brief.add_argument("--stale-days", type=int, default=7)
    brief.add_argument("--json", action="store_true")

    show = sub.add_parser("show", help="show one workstream with live state")
    show.add_argument("workstream_id")
    show.add_argument("--brief", action="store_true", help="print a human inspection view")
    show.add_argument("--json", action="store_true")

    status = sub.add_parser("status", help="set a workstream lifecycle status")
    status.add_argument("workstream_id")
    status.add_argument("status", choices=sorted(VALID_STATUSES))
    status.add_argument("--json", action="store_true")

    attach = sub.add_parser("attach-contract", help="attach a contract pointer")
    attach.add_argument("workstream_id")
    attach.add_argument("--contract-id", required=True)
    attach.add_argument("--version", required=True, type=int)
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
    packet.add_argument("--rationale")
    packet.add_argument("--blocker", action="append")
    packet.add_argument("--deviation", action="append")
    packet.add_argument("--flag", action="append")
    packet.add_argument("--artifact", action="append")
    packet.add_argument("--artifact-json", action="append")
    packet.add_argument("--json", action="store_true")

    judge = sub.add_parser("judge", help="record a human judgment")
    judge.add_argument("workstream_id")
    judge.add_argument(
        "--action",
        required=True,
        choices=sorted(VALID_DECISION_ACTIONS),
    )
    judge.add_argument(
        "--target-type",
        default="workstream",
        choices=sorted(VALID_DECISION_TARGET_TYPES),
    )
    judge.add_argument("--target-id")
    judge.add_argument("--rationale", required=True)
    judge.add_argument("--actor")
    judge.add_argument("--next-attention-due-at", dest="next_review_due_at")
    judge.add_argument("--json", action="store_true")

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

        if args.command == "pilot-fixture":
            result = seed_pilot_fixture(store)
            if args.json:
                print_json(result)
            else:
                print(f"Seeded pilot fixture in {store.root}")
                print(f"contract\t{result['contract']['id']}\tv{result['contract']['version']}")
                print("workstreams")
                for item in result["workstreams"]:
                    print_workstream_row(item)
                print("next")
                for command in result["next_commands"]:
                    print(f"- {command}")
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

        if args.command == "attention":
            result = store.review_workstreams(
                status=args.status,
                program=args.program,
                reason=args.reason,
                stale_days=args.stale_days,
                include_clear=args.all,
            )
            if args.json:
                print_json(result)
            else:
                print("id\tstatus\tprogram\tattention_reasons\tlast_state_update\tnext_attention_due\ttitle")
                for item in result:
                    print_review_row(item)
            return 0

        if args.command == "brief":
            result = store.brief(
                program=args.program,
                contract_id=args.contract_id,
                stale_days=args.stale_days,
            )
            print_json(result) if args.json else print_brief(result)
            return 0

        if args.command == "show":
            result = store.show(args.workstream_id)
            if args.brief and not args.json:
                print_review_detail(result)
            else:
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
            artifact_refs = [
                parse_json_object(value, label="artifact")
                for value in (args.artifact_json or [])
            ]
            result = store.add_state_packet(
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
            print_json(result) if args.json else print(f"Added {result['id']} to {args.workstream_id}")
            return 0

        if args.command == "judge":
            result = store.add_decision(
                args.workstream_id,
                action=args.action,
                rationale=args.rationale,
                actor=args.actor,
                next_review_due_at=args.next_review_due_at,
                target_type=args.target_type,
                target_id=args.target_id,
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
