from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from fab.registry import RegistryError, RegistryStore, utc_now
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from fab.registry import RegistryError, RegistryStore, utc_now


SERVICE_NAME = "podium-shim"
MANIFEST_FIELDS = [
    "workstream_id",
    "contract",
    "source",
    "summary",
    "status",
    "claims",
    "evidence",
    "limitations",
    "next",
    "used_refs",
]
MANIFEST_STATUSES = ["completed", "completed_with_limitations", "failed"]


def safe_path_segment(value: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip(".-_")
    return cleaned or fallback


def default_run_id() -> str:
    return f"podium-{utc_now().replace(':', '').replace('-', '').replace('Z', 'Z').lower()}"


def read_attached_contract(store: RegistryStore, workstream: dict[str, Any]) -> tuple[dict[str, Any], str]:
    contract = workstream.get("contract") or {}
    contract_id = contract.get("id")
    version = contract.get("version")
    if not contract_id or version is None:
        raise RegistryError(f"workstream has no attached contract: {workstream['id']}")
    return {"id": contract_id, "version": version}, store.read_contract_version(contract_id, version)


def artifact_summaries(live_state: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for artifact in live_state.get("artifacts", []):
        result.append(
            {
                "id": artifact.get("id"),
                "path": artifact.get("path"),
                "description": artifact.get("description"),
                "status": artifact.get("status"),
                "claims": [
                    claim.get("text")
                    for claim in artifact.get("claims", [])
                    if isinstance(claim, dict) and claim.get("text")
                ],
                "limitations": artifact.get("limitations", []),
                "used_refs": artifact.get("used_refs", []),
            }
        )
    return result


def build_execution_request(
    *,
    store: RegistryStore,
    workstream_id: str,
    alexandria: Path,
    run_id: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    workstream = store.get_workstream(workstream_id)
    contract, contract_text = read_attached_contract(store, workstream)
    live_state = store.get_live_state(workstream_id)

    run_id = safe_path_segment(run_id or default_run_id(), fallback="podium-run")
    program = safe_path_segment(str(workstream.get("program") or "program"), fallback="program")
    output_relpath = Path("artifacts") / program / workstream_id / run_id
    output_bundle = alexandria / output_relpath
    output_relpath_str = output_relpath.as_posix()

    try:
        references = store.check_references(workstream_id=workstream_id)
    except RegistryError as exc:
        references = {
            "scope": {"type": "workstream", "workstream_id": workstream_id},
            "error": str(exc),
        }

    return {
        "schema_version": 1,
        "created_at": utc_now(),
        "service": SERVICE_NAME,
        "workstream": {
            "id": workstream["id"],
            "title": workstream.get("title"),
            "program": workstream.get("program"),
            "status": workstream.get("status"),
        },
        "contract": {
            **contract,
            "text": contract_text,
        },
        "prior_state": {
            "rationale": live_state.get("rationale"),
            "results": live_state.get("results", []),
            "limitations": live_state.get("limitations", []),
            "next_intended_action": live_state.get("next_intended_action"),
            "artifacts": artifact_summaries(live_state),
        },
        "references": references,
        "output": {
            "kind": "fab-run-bundle",
            "run_id": run_id,
            "bundle_relpath": output_relpath_str,
            "workspace_bundle_relpath": output_relpath_str,
            "workspace_manifest_relpath": f"{output_relpath_str}/manifest.json",
            "workspace_artifact_relpath": f"{output_relpath_str}/artifact",
            "workspace_ready_relpath": f"{output_relpath_str}/READY",
            "durable_target": {
                "kind": "alexandria",
                "bundle_relpath": output_relpath_str,
            },
            "handoff": (
                "Create the bundle at workspace_bundle_relpath in the execution workspace. "
                "If the platform provides a writable Alexandria checkout or upload target, "
                "copy or commit the same relative bundle there. Do not assume the local "
                "developer Alexandria path exists inside the remote sandbox."
            ),
        },
        "manifest_contract": {
            "required_fields": MANIFEST_FIELDS,
            "statuses": MANIFEST_STATUSES,
            "paths_are_relative_to": "bundle root",
            "ready_marker": "Write READY only after manifest.json and artifact/ are complete.",
        },
        "manifest_defaults": {
            "workstream_id": workstream_id,
            "contract": contract,
            "source": source or f"podium/{run_id}",
            "status": "completed_with_limitations",
            "claims": [],
            "evidence": [{"summary": "Report summarizes this run.", "path": "artifact/report.md"}],
            "limitations": [],
            "next": [],
            "used_refs": [],
        },
    }


def render_prompt(request: dict[str, Any]) -> str:
    workstream = request["workstream"]
    contract = request["contract"]
    output = request["output"]
    manifest_defaults = request["manifest_defaults"]

    return "\n".join(
        [
            "# Fab Remote Research Workstream",
            "",
            "You are running this workstream through an external execution platform. Do not clone or call Fab.",
            "Do the research work, then write one Fab-compatible run bundle to Alexandria.",
            "",
            "## Workstream",
            "",
            f"- id: {workstream['id']}",
            f"- title: {workstream.get('title') or '-'}",
            f"- program: {workstream.get('program') or '-'}",
            "",
            "## Output Location",
            "",
            f"Create the run bundle at `{output['workspace_bundle_relpath']}` relative to your execution workspace.",
            "Do not assume any local developer path, such as a `/Users/.../alexandria` checkout, exists in your sandbox.",
            f"The durable Alexandria target uses the same relative path: `{output['durable_target']['bundle_relpath']}`.",
            "If your execution platform provides a writable Alexandria checkout, object-store target, or git credentials, copy or commit the completed bundle there.",
            "If it does not, leave the completed bundle in the execution workspace for the platform or operator to retrieve.",
            "",
            "The required shape is:",
            "",
            "```text",
            "manifest.json",
            "artifact/",
            "  report.md",
            "  code/",
            "  results/",
            "  logs/",
            "READY",
            "```",
            "",
            "Write `READY` last, only after every artifact file and `manifest.json` are complete.",
            "",
            "## Manifest",
            "",
            "Use this manifest skeleton and fill in the research content:",
            "",
            "```json",
            json.dumps(manifest_defaults, indent=2, sort_keys=True),
            "```",
            "",
            "`status` must be one of: `completed`, `completed_with_limitations`, `failed`.",
            "Paths in `evidence` must be relative to the run-bundle root.",
            "Put blockers, uncertainty, missing data, or reproduction limits in `limitations`.",
            "Put prior notes, papers, or artifacts actually used in `used_refs`.",
            "",
            "## Prior State",
            "",
            "```json",
            json.dumps(request["prior_state"], indent=2, sort_keys=True),
            "```",
            "",
            "## Reference Check",
            "",
            "```json",
            json.dumps(request["references"], indent=2, sort_keys=True),
            "```",
            "",
            "## Contract",
            "",
            f"Contract id: `{contract['id']}` v{contract['version']}",
            "",
            contract["text"].rstrip(),
            "",
        ]
    )


def podium_payload(prompt: str, request: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "process_message",
        "content": {
            "text": prompt,
            "messages": [{"role": "user", "content": prompt}],
            "data": {"fab_execution_request": request},
        },
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare_request(
    *,
    store_path: Path,
    workstream_id: str,
    alexandria: Path,
    out: Path,
    run_id: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    store = RegistryStore.at(store_path)
    request = build_execution_request(
        store=store,
        workstream_id=workstream_id,
        alexandria=alexandria,
        run_id=run_id,
        source=source,
    )
    prompt = render_prompt(request)
    payload = podium_payload(prompt, request)

    out.mkdir(parents=True, exist_ok=True)
    request_path = out / "fab-execution-request.json"
    prompt_path = out / "prompt.md"
    payload_path = out / "podium-send.json"
    write_json(request_path, request)
    prompt_path.write_text(prompt, encoding="utf-8")
    write_json(payload_path, payload)
    alexandria_output_bundle = alexandria / request["output"]["durable_target"]["bundle_relpath"]

    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "workstream_id": workstream_id,
        "run_id": request["output"]["run_id"],
        "workspace_output_bundle": request["output"]["workspace_bundle_relpath"],
        "alexandria_output_bundle": str(alexandria_output_bundle),
        "request_path": str(request_path),
        "prompt_path": str(prompt_path),
        "podium_send_path": str(payload_path),
        "podium_send_command": f"podium send <instance-id> --json-input {payload_path}",
    }


def send_to_podium(
    *,
    instance_id: str,
    message_json: Path,
    podium_command: str,
    gateway: str | None = None,
    api_key: str | None = None,
    user_id: str | None = None,
) -> int:
    cmd = shlex.split(podium_command)
    if gateway:
        cmd.extend(["--gateway", gateway])
    if api_key:
        cmd.extend(["--api-key", api_key])
    cmd.extend(["send", instance_id, "--json-input", str(message_json)])
    if user_id:
        cmd.extend(["--user-id", user_id])
    return subprocess.run(cmd, check=False).returncode


def print_summary(summary: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return
    print(f"{summary['service']}: prepared {summary['workstream_id']} as {summary['run_id']}")
    print(f"- request: {summary['request_path']}")
    print(f"- prompt: {summary['prompt_path']}")
    print(f"- podium payload: {summary['podium_send_path']}")
    print(f"- workspace output bundle: {summary['workspace_output_bundle']}")
    print(f"- Alexandria output bundle: {summary['alexandria_output_bundle']}")
    print(f"- send: {summary['podium_send_command']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="podium-shim",
        description="Prepare Fab workstreams for execution by a Podium-hosted agent.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="write a Podium-sendable request for one workstream")
    prepare.add_argument("--store", default=".fab", type=Path)
    prepare.add_argument("--workstream-id", required=True)
    prepare.add_argument("--alexandria", required=True, type=Path)
    prepare.add_argument("--out", required=True, type=Path)
    prepare.add_argument("--run-id")
    prepare.add_argument("--source")
    prepare.add_argument("--json", action="store_true")

    send = sub.add_parser("send", help="send a prepared request to an existing Podium instance")
    send.add_argument("--instance-id", required=True)
    send.add_argument("--message-json", required=True, type=Path)
    send.add_argument(
        "--podium-command",
        default=os.environ.get("FAB_PODIUM_COMMAND", "podium"),
        help="Podium CLI command prefix; defaults to FAB_PODIUM_COMMAND or 'podium'",
    )
    send.add_argument("--gateway")
    send.add_argument("--api-key")
    send.add_argument("--user-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            summary = prepare_request(
                store_path=args.store,
                workstream_id=args.workstream_id,
                alexandria=args.alexandria,
                out=args.out,
                run_id=args.run_id,
                source=args.source,
            )
            print_summary(summary, as_json=args.json)
            return 0
        if args.command == "send":
            return send_to_podium(
                instance_id=args.instance_id,
                message_json=args.message_json,
                podium_command=args.podium_command,
                gateway=args.gateway,
                api_key=args.api_key,
                user_id=args.user_id,
            )
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
