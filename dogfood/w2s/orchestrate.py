#!/usr/bin/env python3
"""Weak-to-strong Fab dogfood orchestrator.

Pipeline:

    contract (fab) + seed
      -> podium coding-generic agent (live gateway)
      -> agent does synthetic research, writes a Fab bundle in its sandbox
      -> agent emits the bundle as base64 from ONE run_command; its stdout
         is surfaced by Podium's FabricBridge as a tool_result block, which
         we capture from the WebSocket stream (no RPC, no clean turn-end
         required)
      -> write the bundle into the local Alexandria checkout
      -> fab alexandria_ingester ingests it into the w2s store
      -> fab brief / attention digests the batch

Inference mode:
  W2S_FIRST_PARTY=1 (default)  first-party Anthropic via ANTHROPIC_API_KEY.
  W2S_FIRST_PARTY=0            route through Ensemble (note: the staging
                               Ensemble streaming endpoint currently rejects
                               the agent model id; first-party is the
                               working default).

Run with the interpreter that has `requests` + `websockets` installed
(the default sandbox venv). Subcommands:

    fab-init   init the w2s fab store + 5 workstreams on the contract
    deploy     bundle + deploy coding-generic to the live gateway, set secrets
    run --ws ws_001   drive one agent end-to-end and harvest its bundle
    ingest     run the Alexandria -> fab ingester
    brief      print the fab brief + attention for the program
    smoke      fab-init + deploy + run ws_001 + ingest + brief
    all        fab-init + deploy + run all 5 (concurrent) + ingest + brief
    stop-all   terminate all w2s-* instances
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import uuid
from pathlib import Path

import requests
import websockets

W2S = Path(__file__).resolve().parent


def _find_root() -> Path:
    """Locate the multi-repo parent (contains alexandria/, fab/, agents/).

    Works whether the harness lives at <root>/w2s or
    <root>/fab/dogfood/w2s. Override with W2S_ROOT.
    """
    env = os.environ.get("W2S_ROOT")
    if env:
        return Path(env).resolve()
    p = W2S
    for _ in range(6):
        if (p / "alexandria").is_dir() and (p / "fab").is_dir() and (p / "agents").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise SystemExit(
        "Cannot locate the multi-repo parent (a directory containing "
        "alexandria/, fab/, agents/). Set W2S_ROOT=/path/to/parent."
    )


ROOT = _find_root()
ALEX = ROOT / "alexandria"
FAB = ROOT / "fab"
AGENTS = ROOT / "agents"
PODIUM = ROOT / "podium"
AGENTLIB = ROOT / "agentlib"
FABRIC = ROOT / "fabric"
STORE = W2S / "store"
DIST = W2S / "dist"
LOGS = W2S / "logs"
STATE_FILE = W2S / "state.json"

PROGRAM = "weak-to-strong-pilot"
CONTRACT_ID = "contract_w2s_generalization"
CONTRACT_VERSION = 1
AGENT_TARGET = "agents.coding.generic.v2"
AGENT_TYPE = "coding-generic"  # == PodiumDeployment.name in v2
TENANT = "default"
SANDBOX_OUT = "fab_out"  # relative to agent sandbox $HOME

MODEL = os.environ.get("W2S_MODEL", "claude-sonnet-4-6")
# "1" = first-party Anthropic (working default); "0" = route via Ensemble.
FIRST_PARTY = os.environ.get("W2S_FIRST_PARTY", "1")

B64_BEGIN = "@@FABB64@@"
B64_END = "@@FABEND@@"

sys.path.insert(0, str(W2S))
from seeds import SEEDS, ORDER  # noqa: E402

GATEWAY = os.environ.get("PODIUM_GATEWAY", "").rstrip("/")
API_KEY = os.environ.get("PODIUM_API_KEY", "")
ENSEMBLE_URL = os.environ.get("ENSEMBLE_URL", "")
ENSEMBLE_API_KEY = os.environ.get("ENSEMBLE_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def log(msg: str) -> None:
    print(f"[w2s {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def hdr() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}"}


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(st: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(st, indent=2, sort_keys=True) + "\n")


# --------------------------------------------------------------------------
# fab store
# --------------------------------------------------------------------------

def _fab(*args: str, capture: bool = False) -> subprocess.CompletedProcess:
    cmd = ["uv", "run", "fab", "--store", str(STORE.resolve()), *args]
    return subprocess.run(cmd, cwd=str(FAB), check=False, text=True,
                          capture_output=capture)


def cmd_fab_init() -> None:
    contract = STORE / "contracts" / CONTRACT_ID / "v001.md"
    if not contract.exists():
        raise SystemExit(f"contract file missing: {contract}")
    STORE.mkdir(parents=True, exist_ok=True)
    r = _fab("init", capture=True)
    log(f"fab init: {(r.stdout or r.stderr).strip()}")
    rs = _fab("sources", "add", "alexandria", str(ALEX.resolve()),
              "--uri-prefix", "alexandria://", capture=True)
    log(f"fab sources add alexandria: rc={rs.returncode}")
    existing = _fab("list", "--json", capture=True)
    have = set()
    if existing.returncode == 0 and existing.stdout.strip():
        try:
            have = {w["id"] for w in json.loads(existing.stdout)}
        except Exception:
            have = set()
    for ws_id in ORDER:
        if ws_id in have:
            log(f"workstream {ws_id} already exists, skipping")
            continue
        seed = SEEDS[ws_id]
        r = _fab("create", "--id", ws_id, "--title", seed["title"],
                 "--program", PROGRAM, "--owner", "human",
                 "--contract-id", CONTRACT_ID,
                 "--contract-version", str(CONTRACT_VERSION),
                 "--json", capture=True)
        if r.returncode != 0:
            raise SystemExit(f"fab create {ws_id} failed: {r.stdout}\n{r.stderr}")
        log(f"created workstream {ws_id} ({seed['title']})")


# --------------------------------------------------------------------------
# deploy
# --------------------------------------------------------------------------

def cmd_deploy(force: bool = False) -> str:
    st = load_state()
    if st.get("deployment_id") and not force:
        log(f"reusing deployment {st['deployment_id']}")
        _store_secrets()
        return st["deployment_id"]

    DIST.mkdir(parents=True, exist_ok=True)
    bundle_dir = DIST / AGENT_TYPE
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)

    env = {**os.environ, "AGENTLIB_PATH": str(AGENTLIB),
           "FABRIC_PATH": str(FABRIC)}
    log(f"building bundle for {AGENT_TARGET} (local deps)...")
    r = subprocess.run(
        ["uv", "run", "agents", "deploy", AGENT_TARGET,
         "--bundle-only", "--out", str(DIST.resolve()),
         "--local-deps", "--source", "working"],
        cwd=str(AGENTS), env=env, text=True, capture_output=True)
    if r.returncode != 0 or not bundle_dir.exists():
        raise SystemExit(f"agents deploy --bundle-only failed:\n{r.stdout}\n{r.stderr}")
    log("bundle built")

    tarball = DIST / f"{AGENT_TYPE}.tar.gz"
    if tarball.exists():
        tarball.unlink()
    penv = {**os.environ, "PYTHONPATH": str(PODIUM)}
    r = subprocess.run(
        [sys.executable, "-m", "podium_cli.cli", "bundle",
         str(bundle_dir), "-o", str(tarball)],
        env=penv, text=True, capture_output=True)
    if r.returncode != 0 or not tarball.exists():
        raise SystemExit(f"podium bundle failed:\n{r.stdout}\n{r.stderr}")
    log(f"tarball {tarball.name} ({tarball.stat().st_size} bytes)")

    sha = hashlib.sha256(tarball.read_bytes()).hexdigest()
    with tarball.open("rb") as fh:
        resp = requests.post(
            f"{GATEWAY}/api/v1/deployments", headers=hdr(),
            files={"file": (tarball.name, fh, "application/gzip")},
            data={"checksum": f"sha256:{sha}"}, timeout=300)
    if resp.status_code not in (200, 201):
        raise SystemExit(f"deploy failed ({resp.status_code}): {resp.text[:800]}")
    body = resp.json()
    info = body.get("deployment_response") or body
    deployment_id = info.get("deployment_id")
    if not deployment_id:
        raise SystemExit(f"deploy response missing deployment_id: {body}")
    log(f"deployed: {deployment_id}")
    st["deployment_id"] = deployment_id
    save_state(st)
    _store_secrets()
    return deployment_id


def _store_secrets() -> None:
    secrets = {
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "ENSEMBLE_API_KEY": ENSEMBLE_API_KEY,
        "ENSEMBLE_URL": ENSEMBLE_URL,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "AGENTLIB_FIRST_PARTY": FIRST_PARTY,
    }
    url = f"{GATEWAY}/api/v1/tenants/{TENANT}/config/{AGENT_TYPE}/secrets"
    for k, v in secrets.items():
        if not v:
            log(f"secret {k} empty, skipping")
            continue
        resp = requests.post(
            url, headers={**hdr(), "Content-Type": "application/json"},
            json={"name": k, "value": v}, timeout=30)
        ok = resp.status_code in (200, 201)
        log(f"secret {k}: {'stored' if ok else f'FAILED {resp.status_code} {resp.text[:160]}'}")


# --------------------------------------------------------------------------
# task prompt
# --------------------------------------------------------------------------

def build_task(ws_id: str) -> str:
    seed = SEEDS[ws_id]
    emit_cmd = (
        'cd "$HOME" && tar -C "$HOME" -czf /tmp/fab_out.tgz fab_out && '
        "python3 -c \"import base64;print('" + B64_BEGIN +
        "'+base64.b64encode(open('/tmp/fab_out.tgz','rb').read()).decode()+'"
        + B64_END + "')\""
    )
    return f"""You are an autonomous AI-safety researcher. One workstream of a batch.

# Research question (contract {CONTRACT_ID} v{CONTRACT_VERSION})

When does naive weak-label finetuning ELICIT a strong model's latent
capability vs. train it to IMITATE the weak supervisor's systematic errors,
and which cheap, ground-truth-free signals predict failure early? Weak-to-
strong (W2S) generalization is the cleanest empirical analogy for
superalignment; the dominant failure mode is imitation.

# Your workstream

workstream_id: {ws_id}
title: {seed['title']}

# Seed idea (explore THIS)

{seed['idea']}

# Hard boundaries

- Synthetic / small-model / CPU-fast ONLY. NO LLM training, NO external paid
  inference, NO large downloads, NO web search. Self-contained Python, runs
  in a few minutes.
- Run your code; base every claim on real numbers you produced.
- Honestly record limitations, negatives, shortcuts, and Goodhart / held-out
  leakage risk.
- Keep the bundle SMALL (total `fab_out` well under ~40 KB): report.md
  concise (< ~1000 words), 1-3 small code files, small results files. No
  binary plots.

# Build the bundle in $HOME/{SANDBOX_OUT}/

    $HOME/{SANDBOX_OUT}/
      manifest.json
      artifact/report.md
      artifact/code/...      (code you wrote and ran)
      artifact/results/...   (numbers/logs the claims rest on)

manifest.json — EXACTLY these fields, valid JSON:

{{
  "workstream_id": "{ws_id}",
  "contract": {{"id": "{CONTRACT_ID}", "version": {CONTRACT_VERSION}}},
  "source": "podium/{AGENT_TYPE}/{ws_id}",
  "summary": "<2-4 sentence plain account of what you found>",
  "status": "completed" | "completed_with_limitations" | "failed",
  "claims": ["<specific claim>", ...],
  "evidence": [{{"summary": "<support>", "path": "artifact/results/<file>"}}],
  "limitations": ["<caveat / shortcut / leakage risk>", ...],
  "next": ["<follow-up>", ...],
  "used_refs": ["alexandria://papers/weak-to-strong-generalization.md"]
}}

Every evidence path must exist in the bundle. status is usually
completed_with_limitations — be honest.

# Completion protocol (MANDATORY)

There is NO test suite. Do NOT run pytest. Do NOT paste file contents or
base64 into chat. When the research is done and the bundle exists:

1. Call the run_command tool EXACTLY ONCE as your FINAL action, with:
   - command: {emit_cmd}
   - max_tokens: 8000000
   - timeout: 180
   Its output contains {B64_BEGIN}...{B64_END} — that IS the deliverable.
2. Immediately STOP. Do not re-verify, rebuild, or call more tools. End turn.

Do the research now, then run the emit command once and stop."""


# --------------------------------------------------------------------------
# websocket driver + harvest
# --------------------------------------------------------------------------

def ws_url(instance_id: str) -> str:
    base = GATEWAY.replace("https://", "wss://").replace("http://", "ws://")
    return f"{base}/api/v1/instances/{instance_id}/connect"


_WSV = int(websockets.__version__.split(".")[0])


def _connect(instance_id: str):
    url = ws_url(instance_id)
    kw = dict(max_size=64 * 1024 * 1024, ping_interval=20, ping_timeout=60)
    if _WSV >= 14:
        return websockets.connect(url, additional_headers=hdr(), **kw)
    return websockets.connect(url, extra_headers=hdr(), **kw)


def _iter_events(frame):
    seen: list[dict] = []

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("type"), str):
                seen.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(frame)
    return seen


def _msg_payload(text: str) -> str:
    return json.dumps({
        "type": "process_message",
        "content": {"text": text,
                    "messages": [{"role": "user", "content": text}]},
    })


TERMINAL = {"conversation.turn_ended", "runtime.run_completed",
            "runtime.run_failed"}


def harvest_from_buffer(buf: str) -> bytes | None:
    """Pick the base64 segment that decodes to a gzip/tar.

    RunCommand echoes the emit command (`$ ... python3 -c "...@@FABB64@@'+
    ...+'@@FABEND@@"`) before stdout, so the command source itself yields a
    decoy marker pair. Scan every pair and keep the one that is a valid
    gzip stream.
    """
    best: bytes | None = None
    for raw in re.findall(
        re.escape(B64_BEGIN) + r"(.*?)" + re.escape(B64_END), buf, re.S
    ):
        blob = re.sub(r"\s+", "", raw).replace("\\n", "").replace("\\", "")
        if len(blob) < 64:
            continue
        pad = (-len(blob)) % 4
        try:
            data = base64.b64decode(blob + ("=" * pad))
        except Exception:
            continue
        if data[:2] == b"\x1f\x8b":  # gzip magic -> tar.gz bundle
            if best is None or len(data) > len(best):
                best = data
    return best


async def drive_agent(instance_id: str, ws_id: str, max_seconds: int) -> str:
    """Send the task, stream frames, capture assistant text + tool_result
    outputs. Stop as soon as the base64 end-marker is captured (the bundle
    is in hand and any subsequent agent looping is irrelevant)."""
    LOGS.mkdir(parents=True, exist_ok=True)
    frame_log = (LOGS / f"{ws_id}.frames.jsonl").open("w")
    parts: list[str] = []
    captured_blocks: set[str] = set()
    deadline = time.monotonic() + max_seconds
    task = build_task(ws_id)

    def _take_block_output(blk: dict) -> None:
        bid = blk.get("blockId") or ""
        if bid and bid in captured_blocks:
            return
        kind = blk.get("blockKind")
        if kind == "text" and blk.get("text"):
            parts.append("\n" + str(blk["text"]))
            if bid:
                captured_blocks.add(bid)
        elif kind == "tool_result":
            j = blk.get("json") or {}
            out = j.get("output")
            if out:
                parts.append("\n" + str(out))
                if bid:
                    captured_blocks.add(bid)

    async with _connect(instance_id) as ws:
        await ws.send(_msg_payload(task))
        log(f"{ws_id}: task sent, streaming (budget {max_seconds}s)...")
        last_beat = time.monotonic()
        seen_activity = False
        run_failed = False
        while time.monotonic() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=120)
            except asyncio.TimeoutError:
                if seen_activity and time.monotonic() - last_beat > 600:
                    log(f"{ws_id}: 600s silent after activity; stopping stream")
                    break
                continue
            last_beat = time.monotonic()
            try:
                frame = json.loads(raw)
            except (ValueError, TypeError):
                continue
            frame_log.write(json.dumps(frame) + "\n")
            frame_log.flush()
            terminal = False
            for ev in _iter_events(frame):
                et = ev.get("type", "")
                if et in ("presentation.item_created",
                          "presentation.block_started",
                          "presentation.block_delta",
                          "runtime.usage_reported"):
                    seen_activity = True
                if et in ("presentation.block_delta",):
                    d = ev.get("delta") or {}
                    if d.get("text"):
                        parts.append(d["text"])
                elif et in ("presentation.block_started",
                            "presentation.block_completed"):
                    blk = ev.get("block") or {}
                    _take_block_output(blk)
                elif et == "conversation.turn_ended":
                    for k in ("finalText", "endMessage"):
                        if ev.get(k):
                            parts.append("\n" + ev[k])
                    terminal = True
                elif et == "runtime.run_failed":
                    run_failed = True
                    terminal = True
                elif et in TERMINAL:
                    terminal = True
            buf = "".join(parts)
            if harvest_from_buffer(buf) is not None:
                log(f"{ws_id}: decodable bundle captured from stream")
                break
            if terminal:
                if run_failed and harvest_from_buffer(buf) is None:
                    log(f"{ws_id}: runtime.run_failed (no bundle yet)")
                else:
                    log(f"{ws_id}: terminal event seen")
                break
        frame_log.close()
    return "".join(parts)


# --------------------------------------------------------------------------
# bundle -> alexandria
# --------------------------------------------------------------------------

VALID_STATUS = {"completed", "completed_with_limitations", "failed"}


def _coerce_str_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [x if isinstance(x, str) else json.dumps(x) for x in v if x]
    return [str(v)]


def repair_manifest(raw: dict, ws_id: str, bundle_root: Path) -> dict:
    m = dict(raw) if isinstance(raw, dict) else {}
    m["workstream_id"] = ws_id
    m["contract"] = {"id": CONTRACT_ID, "version": CONTRACT_VERSION}
    src = m.get("source")
    m["source"] = src if isinstance(src, str) and src.strip() else f"podium/{AGENT_TYPE}/{ws_id}"
    summary = m.get("summary")
    if not (isinstance(summary, str) and summary.strip()):
        summary = SEEDS[ws_id]["title"]
    m["summary"] = summary
    status = m.get("status")
    m["status"] = status if status in VALID_STATUS else "completed_with_limitations"
    m["claims"] = _coerce_str_list(m.get("claims"))
    m["limitations"] = _coerce_str_list(m.get("limitations"))
    m["next"] = _coerce_str_list(m.get("next"))
    m["used_refs"] = _coerce_str_list(m.get("used_refs"))
    ev_out = []
    for item in (m.get("evidence") or []):
        if isinstance(item, str):
            ev_out.append({"summary": item})
        elif isinstance(item, dict):
            s = item.get("summary") or item.get("description") or item.get("text")
            if not (isinstance(s, str) and s.strip()):
                continue
            e: dict = {"summary": s}
            p = item.get("path")
            if isinstance(p, str) and p and "://" not in p and ".." not in Path(p).parts:
                if (bundle_root / p).exists():
                    e["path"] = p
            ev_out.append(e)
    if not ev_out:
        ev_out = [{"summary": m["summary"], "path": "artifact/report.md"}]
    m["evidence"] = ev_out
    return m


def _safe_extract(tf: tarfile.TarFile, dest: Path) -> None:
    dest = dest.resolve()
    for m in tf.getmembers():
        if not (m.isfile() or m.isdir()):
            log(f"skip non-regular tar member: {m.name}")
            continue
        if m.name.startswith("/") or Path(m.name).is_absolute():
            log(f"skip absolute-path tar member: {m.name}")
            continue
        target = (dest / m.name).resolve()
        if target != dest and dest not in target.parents:
            log(f"skip path-traversal tar member: {m.name}")
            continue
        try:
            tf.extract(m, dest, filter="data")
        except TypeError:
            tf.extract(m, dest)


def write_to_alexandria(ws_id: str, tgz: bytes) -> Path | None:
    run_id = f"run-{time.strftime('%Y%m%dT%H%M%S')}"
    dest = ALEX / "artifacts" / PROGRAM / ws_id / run_id
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    tmp = dest / "_extract"
    tmp.mkdir()
    try:
        with tarfile.open(fileobj=io.BytesIO(tgz), mode="r:gz") as tf:
            _safe_extract(tf, tmp)
    except Exception as e:
        log(f"{ws_id}: bundle extract failed ({e}); discarding")
        shutil.rmtree(dest, ignore_errors=True)
        return None
    roots = [p for p in tmp.iterdir() if p.is_dir()]
    src = roots[0] if len(roots) == 1 and (roots[0] / "manifest.json").exists() else tmp
    if not (src / "manifest.json").exists():
        for cand in tmp.rglob("manifest.json"):
            src = cand.parent
            break

    artifact_src = src / "artifact"
    artifact_dst = dest / "artifact"
    if artifact_src.is_dir():
        shutil.copytree(artifact_src, artifact_dst)
    else:
        artifact_dst.mkdir(parents=True, exist_ok=True)
        (artifact_dst / "report.md").write_text(
            f"# {SEEDS[ws_id]['title']}\n\n(agent produced no artifact/ dir)\n")

    try:
        raw = json.loads((src / "manifest.json").read_text())
    except Exception:
        raw = {}
    manifest = repair_manifest(raw, ws_id, dest)
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (dest / "READY").write_text("")
    shutil.rmtree(tmp)
    log(f"{ws_id}: wrote bundle -> {dest.relative_to(ROOT)}")
    return dest


# --------------------------------------------------------------------------
# instance lifecycle
# --------------------------------------------------------------------------

def create_instance(deployment_id: str, ws_id: str) -> str:
    instance_id = f"w2s-{ws_id}-{uuid.uuid4().hex[:8]}"
    body = {"deployment_id": deployment_id, "agent_id": instance_id}
    if FIRST_PARTY == "0":
        body["config_overrides"] = {"model.name": MODEL}
    resp = requests.post(
        f"{GATEWAY}/api/v1/instances",
        headers={**hdr(), "Content-Type": "application/json"},
        json=body, timeout=60)
    if resp.status_code not in (200, 201):
        raise SystemExit(f"{ws_id}: instance create failed "
                         f"({resp.status_code}): {resp.text[:400]}")
    iid = resp.json().get("instance_id") or instance_id
    log(f"{ws_id}: instance {iid} created")
    return iid


def stop_instance(instance_id: str) -> None:
    try:
        requests.delete(f"{GATEWAY}/api/v1/instances/{instance_id}",
                         headers=hdr(), timeout=60)
    except Exception:
        pass


async def run_one(deployment_id: str, ws_id: str, max_seconds: int,
                   keep: bool = False, attempts: int = 3) -> bool:
    for attempt in range(1, attempts + 1):
        iid = create_instance(deployment_id, ws_id)
        await asyncio.sleep(5)
        ok = False
        try:
            buf = await drive_agent(iid, ws_id, max_seconds)
            (LOGS / f"{ws_id}.capture.txt").write_text(buf)
            tgz = harvest_from_buffer(buf)
            if not tgz:
                log(f"{ws_id}: attempt {attempt}/{attempts} HARVEST FAILED")
            elif write_to_alexandria(ws_id, tgz) is not None:
                log(f"{ws_id}: harvested bundle ({len(tgz)} bytes) [attempt {attempt}]")
                ok = True
        except Exception as e:
            log(f"{ws_id}: attempt {attempt}/{attempts} error: {e!r}")
        finally:
            if not (keep and ok):
                stop_instance(iid)
        if ok:
            return True
    log(f"{ws_id}: FAILED after {attempts} attempts")
    return False


# --------------------------------------------------------------------------
# ingest + brief
# --------------------------------------------------------------------------

def cmd_ingest() -> None:
    r = subprocess.run(
        ["uv", "run", "python", "-m", "services.alexandria_ingester",
         "--alexandria", str(ALEX.resolve()),
         "--store", str(STORE.resolve()), "--json"],
        cwd=str(FAB), text=True, capture_output=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode not in (0, 1):
        raise SystemExit(f"ingester crashed: {r.stderr}")


def cmd_brief() -> None:
    for args in (["brief", "--program", PROGRAM], ["attention", "--all"]):
        r = _fab(*args, capture=True)
        print(f"\n===== fab {' '.join(args)} =====")
        print(r.stdout.strip() or r.stderr.strip())


def cmd_stop_all() -> None:
    try:
        r = requests.get(f"{GATEWAY}/api/v1/instances", headers=hdr(), timeout=30)
        items = r.json().get("instances", [])
    except Exception:
        items = []
    for it in items:
        iid = it.get("instance_id", "")
        if iid.startswith("w2s-"):
            stop_instance(iid)
            log(f"stopped {iid}")


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="W2S Fab dogfood orchestrator")
    ap.add_argument("command", choices=[
        "fab-init", "deploy", "run", "ingest", "brief",
        "smoke", "all", "stop-all"])
    ap.add_argument("--ws", help="workstream id for `run`")
    ap.add_argument("--max-seconds", type=int, default=1800,
                    help="per-agent wall budget (default 1800)")
    ap.add_argument("--force-deploy", action="store_true")
    ap.add_argument("--keep", action="store_true",
                    help="keep instances running after run")
    args = ap.parse_args()

    if not GATEWAY or not API_KEY:
        raise SystemExit("PODIUM_GATEWAY / PODIUM_API_KEY not set")

    if args.command == "fab-init":
        cmd_fab_init()
    elif args.command == "deploy":
        cmd_deploy(force=args.force_deploy)
    elif args.command == "ingest":
        cmd_ingest()
    elif args.command == "brief":
        cmd_brief()
    elif args.command == "stop-all":
        cmd_stop_all()
    elif args.command == "run":
        if not args.ws:
            raise SystemExit("--ws required for run")
        dep = load_state().get("deployment_id")
        if dep:
            _store_secrets()
        else:
            dep = cmd_deploy()
        ok = asyncio.run(run_one(dep, args.ws, args.max_seconds, args.keep))
        raise SystemExit(0 if ok else 1)
    elif args.command == "smoke":
        cmd_fab_init()
        dep = cmd_deploy(force=args.force_deploy)
        ok = asyncio.run(run_one(dep, "ws_001", args.max_seconds, args.keep))
        if ok:
            cmd_ingest()
            cmd_brief()
        raise SystemExit(0 if ok else 1)
    elif args.command == "all":
        cmd_fab_init()
        dep = cmd_deploy(force=args.force_deploy)

        async def _all():
            return await asyncio.gather(*[
                run_one(dep, ws, args.max_seconds, args.keep) for ws in ORDER
            ], return_exceptions=True)

        res = asyncio.run(_all())
        for ws, r in zip(ORDER, res):
            log(f"{ws}: {'OK' if r is True else f'FAIL ({r})'}")
        cmd_ingest()
        cmd_brief()


if __name__ == "__main__":
    main()