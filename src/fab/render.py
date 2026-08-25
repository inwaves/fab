"""Text renderers for the Fab CLI.

Every renderer takes the JSON-serialisable result a command handler produced
and prints a human-readable view. Handlers never print; renderers never read
the store. The small helpers at the top (``row``, ``table``, ``section``,
``field_lines``) give every command the same tab-separated and
blank-line-separated shape.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from typing import Any

WORKSTREAM_COLUMNS = ("id", "status", "program", "contract", "last_state_update", "title")
ATTENTION_COLUMNS = (
    "id",
    "status",
    "program",
    "attention_reasons",
    "last_state_update",
    "next_attention_due",
    "title",
)
SOURCE_COLUMNS = ("name", "uri_prefix", "path")
BRIEF_COUNT_KEYS = ("workstreams", "attention", "artifacts", "claims", "decisions")
LIVE_STATE_LISTS = (
    ("experiments", "experiments"),
    ("results", "results"),
    ("failed attempts", "failed_attempts"),
    ("blockers", "blockers"),
    ("limitations", "limitations"),
    ("deviations", "deviations"),
    ("flags", "flags"),
)


# --------------------------------------------------------------- primitives


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def dash(value: Any) -> str:
    """Render a missing or empty value as ``-``."""
    if value is None or value == "" or value == []:
        return "-"
    return str(value)


def row(*cells: Any) -> str:
    return "\t".join(dash(cell) for cell in cells)


def table(columns: Iterable[str], rows: Iterable[str]) -> None:
    print(row(*columns))
    for line in rows:
        print(line)


def section(title: str, lines: Iterable[str]) -> None:
    """Print a titled block preceded by a blank line, or ``-`` when empty."""
    print(f"\n{title}")
    printed = False
    for line in lines:
        print(line)
        printed = True
    if not printed:
        print("-")


def field_lines(label: str, values: list[Any]) -> list[str]:
    """``label: -`` for an empty list, else ``label:`` followed by bullets."""
    if not values:
        return [f"{label}: -"]
    return [f"{label}:"] + [f"- {format_value(value)}" for value in values]


def nested(label: str, lines: list[str]) -> list[str]:
    """Indent a labelled sub-list one level; an empty list renders nothing."""
    if not lines:
        return []
    return [f"  {label}:"] + [f"  {line}" for line in lines]


def grouped_lines(label: str, items: list[Any], fmt: Callable[[Any], str]) -> list[str]:
    """``label:`` followed by one bullet per item; nothing when there are none."""
    if not items:
        return []
    return [f"{label}:"] + [f"- {fmt(item)}" for item in items]


def format_value(value: Any) -> str:
    if isinstance(value, dict):
        if {"id", "kind", "path"}.issubset(value):
            description = f": {value['description']}" if value.get("description") else ""
            return f"{value['id']} {value['kind']} {value['path']}{description}"
        return json.dumps(value, sort_keys=True)
    return str(value)


def timestamps(item: dict[str, Any]) -> dict[str, Any]:
    return item.get("timestamps") or {}


def target_label(decision: dict[str, Any]) -> str:
    target = decision.get("target")
    if not target:
        return f"workstream:{decision.get('workstream_id', '-')}"
    return f"{target.get('type', 'workstream')}:{target.get('id', '-')}"


# ------------------------------------------------------------ workstreams


def workstream_row(item: dict[str, Any]) -> str:
    return row(
        item.get("id"),
        item.get("status"),
        item.get("program"),
        (item.get("contract") or {}).get("id"),
        timestamps(item).get("last_state_update_at"),
        item.get("title"),
    )


def attention_row(item: dict[str, Any]) -> str:
    workstream = item["workstream"]
    review = item["review"]
    return row(
        workstream.get("id"),
        workstream.get("status"),
        workstream.get("program"),
        ",".join(review.get("reasons", [])),
        timestamps(workstream).get("last_state_update_at"),
        timestamps(workstream).get("next_review_due_at"),
        workstream.get("title"),
    )


def workstream(item: dict[str, Any]) -> None:
    print(workstream_row(item))


def workstream_table(items: list[dict[str, Any]]) -> None:
    table(WORKSTREAM_COLUMNS, (workstream_row(item) for item in items))


def attention_table(items: list[dict[str, Any]]) -> None:
    table(ATTENTION_COLUMNS, (attention_row(item) for item in items))


# ------------------------------------------------------ one-line receipts


def initialized(result: dict[str, Any]) -> None:
    print(f"Initialized {result['store']}")


def source_added(result: dict[str, Any]) -> None:
    print(f"Added source {result['name']}")


def packet_added(packet: dict[str, Any]) -> None:
    print(f"Added {packet['id']} to {packet['workstream_id']}")


def run_ingested(packet: dict[str, Any]) -> None:
    print(f"Ingested {packet['id']} from {packet['ingest']['bundle_path']}")


def judgment_recorded(decision: dict[str, Any]) -> None:
    print(f"Recorded {decision['id']} for {decision['workstream_id']}")


# ------------------------------------------------------------------ sources


def sources(items: list[dict[str, Any]]) -> None:
    if not items:
        print("sources: -")
        return
    table(
        SOURCE_COLUMNS,
        (row(item.get("name"), item.get("uri_prefix"), item.get("path")) for item in items),
    )


# ------------------------------------------------------------ pilot fixture


def pilot_fixture(result: dict[str, Any]) -> None:
    print(f"Seeded pilot fixture in {result['store']}")
    print(row("contract", result["contract"]["id"], f"v{result['contract']['version']}"))
    print("workstreams")
    for item in result["workstreams"]:
        print(workstream_row(item))
    print("next")
    for command in result["next_commands"]:
        print(f"- {command}")


# ------------------------------------------------------- workstream detail


def workstream_detail(data: dict[str, Any]) -> None:
    """The ``show --brief`` view: header, contract text, live state, recent history."""
    entry = data["workstream"]
    live_state = data["live_state"]
    contract = data.get("attached_contract")
    review = data["review"]

    print(row(entry["id"], entry.get("status"), entry.get("program")))
    print(f"title: {entry.get('title', '')}")
    print(f"contract: {contract_label(contract)}")
    print(f"attention reasons: {', '.join(review.get('reasons', [])) or '-'}")
    print(f"last state update: {dash(timestamps(entry).get('last_state_update_at'))}")
    print(f"next attention due: {dash(timestamps(entry).get('next_review_due_at'))}")

    contract_text = (contract or {}).get("text")
    section("Contract", [contract_text.rstrip()] if contract_text else [])
    section("Live State", live_state_lines(live_state))
    section("Recent Packets", [packet_line(packet) for packet in data.get("recent_packets", [])])
    section(
        "Recent Decisions",
        [decision_line(decision) for decision in data.get("recent_decisions", [])],
    )


def contract_label(contract: dict[str, Any] | None) -> str:
    if not contract:
        return "-"
    label = f"{contract['id']} v{contract['version']}"
    if not contract.get("exists"):
        label += " (missing)"
    return label


def live_state_lines(live_state: dict[str, Any]) -> list[str]:
    lines = [
        f"current hypothesis: {dash(live_state.get('current_hypothesis'))}",
        f"current plan: {dash(live_state.get('current_plan'))}",
        f"next intended action: {dash(live_state.get('next_intended_action'))}",
        f"current rationale: {dash(live_state.get('rationale'))}",
    ]
    for label, key in LIVE_STATE_LISTS:
        lines.extend(field_lines(label, live_state.get(key, [])))
    lines.extend(artifact_lines(live_state.get("artifacts", [])))
    return lines


def artifact_lines(artifacts: list[dict[str, Any]]) -> list[str]:
    if not artifacts:
        return ["artifacts: -"]
    lines = ["artifacts:"]
    for artifact in artifacts:
        lines.append(
            f"- {artifact.get('id')} {artifact.get('kind', 'artifact')} "
            f"{artifact.get('path', '-')}: {dash(artifact.get('description'))}"
        )
        if artifact.get("uncertainty"):
            lines.append(f"  uncertainty: {artifact['uncertainty']}")
        if artifact.get("limitations"):
            lines.append(f"  limitations: {'; '.join(artifact['limitations'])}")
        if artifact.get("used_refs"):
            lines.append(f"  used refs: {', '.join(artifact['used_refs'])}")
        lines.extend(nested("claims", claim_detail_lines(artifact.get("claims", []))))
        lines.extend(nested("evidence", [evidence_line(item) for item in artifact.get("evidence", [])]))
        commands = (artifact.get("reproduction") or {}).get("commands") or []
        lines.extend(nested("reproduce", [f"- {command}" for command in commands]))
    return lines


def claim_detail_lines(claims: list[dict[str, Any]]) -> list[str]:
    lines = []
    for claim in claims:
        lines.append(f"- {claim.get('id')} ({dash(claim.get('confidence'))}): {claim.get('text')}")
        if claim.get("caveats"):
            lines.append(f"  caveats: {', '.join(claim['caveats'])}")
    return lines


def evidence_line(item: dict[str, Any]) -> str:
    path = f" {item['path']}" if item.get("path") else ""
    return f"- {item.get('id')} {item.get('kind', 'evidence')}{path}: {item.get('summary')}"


def packet_line(packet: dict[str, Any]) -> str:
    return (
        f"- {packet['id']} {packet.get('created_at', '-')}: "
        f"next={dash(packet.get('next_action'))}; "
        f"rationale={dash(packet.get('rationale'))}"
    )


def decision_line(decision: dict[str, Any]) -> str:
    return (
        f"- {decision['id']} {decision.get('created_at', '-')}: "
        f"{decision.get('action')} {target_label(decision)} "
        f"-> {decision.get('status_after')}; {decision.get('rationale')}"
    )


# -------------------------------------------------------------------- brief


def brief(data: dict[str, Any]) -> None:
    filters = data.get("filters") or {}
    counts = data.get("counts") or {}
    filter_bits = [f"{key}={value}" for key, value in filters.items() if value is not None]
    print(row("Fab brief", data.get("generated_at"), ", ".join(filter_bits) or "all"))
    print("counts\t" + "\t".join(f"{key}={counts.get(key, 0)}" for key in BRIEF_COUNT_KEYS))

    section("Attention", attention_lines(data.get("attention", [])))
    section("Workstreams", workstream_summary_lines(data.get("workstreams", [])))
    section("Claims", claim_lines(data.get("claims", [])))
    section("Contract Review", contract_review_lines(data.get("contract_review") or {}))
    section("References", reference_lines(data.get("references") or {}))
    section("Next Context", next_context_lines(data.get("next_context") or {}))


def attention_lines(items: list[dict[str, Any]]) -> list[str]:
    return [
        f"- {item.get('workstream_id')}: "
        f"{','.join(item.get('reasons', [])) or '-'}; {item.get('title', '')}"
        for item in items
    ]


def workstream_summary_lines(items: list[dict[str, Any]]) -> list[str]:
    lines = []
    for item in items:
        lines.append(f"- {row(item.get('id'), item.get('status'), item.get('title'))}")
        if item.get("results"):
            lines.append(f"  result: {item['results'][-1]}")
        if item.get("limitations"):
            lines.append(f"  limitation: {item['limitations'][-1]}")
        if item.get("next_intended_action"):
            lines.append(f"  next: {item['next_intended_action']}")
    return lines


def claim_lines(claims: list[dict[str, Any]]) -> list[str]:
    lines = []
    for claim in claims:
        actions = [
            str(decision.get("action"))
            for decision in claim.get("judgments", [])
            if decision.get("action")
        ]
        suffix = f" [{', '.join(actions)}]" if actions else ""
        lines.append(
            f"- {claim.get('workstream_id')}/{claim.get('ref')} "
            f"({dash(claim.get('confidence'))}){suffix}: {claim.get('text')}"
        )
    return lines


def contract_review_lines(review: dict[str, Any]) -> list[str]:
    if not review:
        return []
    lines = [f"mode: {review.get('mode', '-')}"]
    lines.extend(f"- {item}" for item in review.get("summary", []))
    lines.extend(
        grouped_lines(
            "repeated claims",
            review.get("repeated_claims", []),
            lambda group: (
                f"{group.get('count', 0)}x across "
                f"{', '.join(group.get('workstreams', []))}: {group.get('text')}"
            ),
        )
    )
    lines.extend(
        grouped_lines(
            "shared limitations",
            review.get("shared_limitations", []),
            lambda group: f"{group.get('count', 0)}x: {group.get('limitation')}",
        )
    )
    lines.extend(
        grouped_lines(
            "shared refs",
            review.get("shared_used_refs", []),
            lambda group: f"{group.get('count', 0)}x: {group.get('ref')}",
        )
    )
    queue = review.get("review_queue", {})
    queue_counts = {
        name: len(queue.get(name, []))
        for name in ("needs_replication", "needs_critique", "do_not_propagate")
    }
    if any(queue_counts.values()):
        lines.append(
            "review queue: " + " ".join(f"{name}={count}" for name, count in queue_counts.items())
        )
    return lines


def reference_lines(review: dict[str, Any]) -> list[str]:
    if not review:
        return []
    comparison = review.get("comparison", {})
    lines = [
        "counts: "
        f"explicit={len(review.get('explicit_refs', []))} "
        f"used={len(review.get('used_refs', []))} "
        f"used_not_explicit={len(comparison.get('used_not_explicit', []))} "
        f"explicit_not_used={len(comparison.get('explicit_not_used', []))}"
    ]
    unresolved = comparison.get("unresolved_explicit", []) + comparison.get("unresolved_used", [])
    lines.extend(grouped_lines("unresolved", unresolved, unresolved_line))
    lines.extend(
        grouped_lines(
            "used refs not explicit in contract",
            comparison.get("used_not_explicit", []),
            str,
        )
    )
    lines.extend(
        grouped_lines(
            "explicit contract refs not used",
            comparison.get("explicit_not_used", []),
            str,
        )
    )
    return lines


def unresolved_line(entry: dict[str, Any]) -> str:
    resolution = entry.get("resolution") or {}
    return f"{entry.get('uri')}: {resolution.get('error') or resolution.get('status')}"


def next_context_lines(next_context: dict[str, list[dict[str, Any]]]) -> list[str]:
    lines = []
    for bucket, items in next_context.items():
        if not items:
            continue
        lines.append(f"{bucket}:")
        for item in items:
            target = item.get("target") or {}
            lines.append(
                f"- {item.get('workstream_id')} "
                f"{target.get('type', 'workstream')}:{target.get('id', '-')}; "
                f"{item.get('rationale')}"
            )
    return lines


# --------------------------------------------------------------- refs check


def refs_check(data: dict[str, Any]) -> None:
    scope = data.get("scope", {})
    if scope.get("type") == "contract":
        contract = scope.get("contract", {})
        print(row("refs", f"contract:{contract.get('id')}/v{contract.get('version')}"))
    elif scope.get("type") == "workstream":
        print(row("refs", f"workstream:{scope.get('workstream_id')}"))
    else:
        print("refs")
    section("References", reference_lines(data))
