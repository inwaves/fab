from __future__ import annotations

from typing import Any

from fab.registry import RegistryError, RegistryStore


PILOT_CONTRACT_ID = "contract_pilot_a3_false_positive"
PILOT_PROGRAM = "safety-finetuning-pilot"


PILOT_CONTRACT_TEXT = """# Contract: A3 False-Positive Reduction Pilot

Contract id: contract_pilot_a3_false_positive
Version: 1
Program: safety-finetuning-pilot
Created: 2026-05-07

## Research Question

Can A3-style safety finetuning reduce false positives on benign refusal-adjacent
queries without weakening detection of the target failure mode?

## Why It Matters

An automated safety-finetuning loop that reduces visible unsafe behavior but
raises false positives can look safer while making the model less useful and
possibly hiding regressions. False-positive behavior is therefore a good pilot
domain for testing whether Fab helps a human inspect and compare a batch of
agentic research directions without reading loose reports.

## Brief

Treat this as a small black-box-agent pilot. Try a few plausible directions for
understanding or reducing false positives. Surface uncertainty directly. If a
result depends on suspicious eval access, narrow benchmark artifacts, missing
benign labels, or a tradeoff against target failure detection, flag it rather
than making the result sound cleaner than it is.

The human wants to learn whether these workstreams are understandable through
contracts, state packets, artefact pointers, attention queues, and judgment
records.

## Desired Output

- a research artefact package per workstream;
- enough code, provenance, and evidence to inspect the reported result;
- a clear account of why the result matters or needs follow-up;
- flags or blockers when the result is not ready to trust.

## Attention Boundaries

- ask before training or adapting a model;
- stop and report if any result depends on private eval leakage;
- flag any method that appears to reduce false positives by suppressing
  detection of the target failure mode.

## Context

- KB: `papers/a3-an-automated-alignment-agent-for-safety-finetun.md`
- KB: `papers/automated-weak-to-strong-researcher.md`
- KB: `papers/the-last-human-written-paper-agent-native-research-artifacts.md`
"""


def seed_pilot_fixture(store: RegistryStore) -> dict[str, Any]:
    """Seed an empty registry with a simulated black-box-agent pilot."""
    store.init()
    if store.existing_workstream_ids():
        raise RegistryError("pilot fixture requires an empty registry store")

    store.write_contract_version(PILOT_CONTRACT_ID, 1, PILOT_CONTRACT_TEXT)

    store.create_workstream(
        title="Baseline false-positive cluster scan",
        program=PILOT_PROGRAM,
        workstream_id="ws_001",
        contract_id=PILOT_CONTRACT_ID,
        contract_version=1,
        artifact_root="runs/ws_001",
        next_review_due_at="2099-01-01",
    )
    store.add_state_packet(
        "ws_001",
        source="sim-agent-baseline",
        tried="ran baseline false-positive eval over benign refusal-adjacent prompts",
        result="found a stable cluster around ambiguous compliance/refusal boundaries",
        next_action="sample 30 nearest neighbors and label whether they are true false positives",
        rationale="cluster is measurable, reproducible, and directly tied to the contract question",
        artifact_ref=[
            {
                "kind": "report",
                "path": "runs/ws_001/baseline-cluster-report.md",
                "description": "Baseline cluster scan summary",
                "provenance": {
                    "code": ["pilot/evals/refusal_false_positive_scan.py"],
                    "datasets": ["pilot/data/benign_refusal_adjacent_v1.jsonl"],
                    "models": ["pilot-model-a3-lora-baseline"],
                    "prompts": ["pilot/prompts/refusal_eval_v1.md"],
                    "evals": ["pilot/evals/refusal_fp_cluster_v1"],
                },
            }
        ],
    )
    store.add_decision(
        "ws_001",
        action="continue",
        rationale="Promising enough to preserve; next step should validate the cluster with human labels.",
        actor="human",
        next_review_due_at="2099-01-01",
    )

    store.create_workstream(
        title="Benign counterpart expansion",
        program=PILOT_PROGRAM,
        workstream_id="ws_002",
        contract_id=PILOT_CONTRACT_ID,
        contract_version=1,
        artifact_root="runs/ws_002",
    )
    store.add_state_packet(
        "ws_002",
        source="sim-agent-counterparts",
        tried="generated benign counterparts for known harmful prompts",
        result="counterparts reveal several over-refusal cases, but label quality is uneven",
        next_action="request a small human-labeled benign counterpart set before fitting any filter",
        rationale="work is useful only if the benign labels can be trusted",
        blocker=["benign counterpart labels are too noisy for training or evaluation"],
        artifact_ref=[
            {
                "kind": "dataset",
                "path": "runs/ws_002/generated-benign-counterparts.jsonl",
                "description": "Generated benign counterpart candidates",
                "provenance": {
                    "code": ["pilot/scripts/generate_counterparts.py"],
                    "datasets": ["pilot/data/harmful_seed_prompts_v1.jsonl"],
                    "models": ["sim-agent-counterparts"],
                    "prompts": ["pilot/prompts/benign_counterpart_generation.md"],
                    "evals": [],
                },
            }
        ],
    )

    store.create_workstream(
        title="Narrow data-filter attempt",
        program=PILOT_PROGRAM,
        workstream_id="ws_003",
        contract_id=PILOT_CONTRACT_ID,
        contract_version=1,
        artifact_root="runs/ws_003",
    )
    store.add_state_packet(
        "ws_003",
        source="sim-agent-filter",
        tried="trained a simple filter to remove ambiguous benign prompts from the safety finetuning set",
        result="false positives drop on the public eval, but target-failure detection also drops slightly",
        next_action="inspect whether the filter removed hard safety examples before using this result",
        rationale="there may be a real tradeoff, but current result is not trustworthy enough to use",
        flag=["possible shortcut: public-eval false-positive reduction may be coming from easier retained examples"],
        artifact_ref=[
            {
                "kind": "plot",
                "path": "runs/ws_003/filter-tradeoff-plot.png",
                "description": "False-positive versus target-detection tradeoff",
                "provenance": {
                    "code": ["pilot/evals/filter_tradeoff.py"],
                    "datasets": [
                        "pilot/data/safety_finetune_train_v1.jsonl",
                        "pilot/data/public_refusal_eval_v1.jsonl",
                    ],
                    "models": ["pilot-model-filter-candidate-003"],
                    "prompts": ["pilot/prompts/refusal_eval_v1.md"],
                    "evals": ["pilot/evals/public_refusal_fp_v1"],
                },
            }
        ],
    )

    store.create_workstream(
        title="OOD transfer check",
        program=PILOT_PROGRAM,
        workstream_id="ws_004",
        contract_id=PILOT_CONTRACT_ID,
        contract_version=1,
        artifact_root="runs/ws_004",
    )
    store.add_state_packet(
        "ws_004",
        source="sim-agent-transfer",
        tried="tested the baseline cluster hypothesis on a different benign-query distribution",
        result="cluster partially transfers, but the strongest signal shifts to medical-advice prompts",
        next_action="split out medical-advice prompts before interpreting the transfer result",
        rationale="transfer result changes what the next eval should control for",
        deviation=["agent tested a medical-advice-heavy OOD set not mentioned in the original brief"],
        artifact_ref=[
            {
                "kind": "report",
                "path": "runs/ws_004/ood-transfer-note.md",
                "description": "OOD transfer check with distribution caveat",
                "provenance": {
                    "code": ["pilot/evals/ood_transfer_check.py"],
                    "datasets": ["pilot/data/benign_medical_advice_ood_v1.jsonl"],
                    "models": ["pilot-model-a3-lora-baseline"],
                    "prompts": ["pilot/prompts/medical_advice_refusal_eval.md"],
                    "evals": ["pilot/evals/ood_refusal_transfer_v1"],
                },
            }
        ],
    )

    store.create_workstream(
        title="Unscoped speculative rewrite",
        program=PILOT_PROGRAM,
        workstream_id="ws_005",
        artifact_root="runs/ws_005",
    )

    return {
        "contract": {"id": PILOT_CONTRACT_ID, "version": 1},
        "program": PILOT_PROGRAM,
        "workstreams": store.list_workstreams(),
        "next_commands": [
            "uv run fab attention",
            "uv run fab attention --all",
            "uv run fab show ws_003 --brief",
        ],
    }
