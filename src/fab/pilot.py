from __future__ import annotations

from typing import Any

from fab.errors import RegistryError
from fab.store import RegistryStore


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
contracts, state packets, artefact packages, briefs, attention queues, and
judgment records.

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

- alexandria://papers/a3-an-automated-alignment-agent-for-safety-finetun.md
- alexandria://papers/automated-weak-to-strong-researcher.md
- alexandria://papers/the-last-human-written-paper-agent-native-research-artifacts.md
"""


def seed_pilot_fixture(store: RegistryStore) -> dict[str, Any]:
    """Seed an empty registry with a simulated black-box-agent pilot."""
    store.init()
    if not store.is_empty():
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
                "claims": [
                    {
                        "id": "claim_ambiguous_refusal_cluster",
                        "text": "A stable ambiguous-refusal cluster appears in the baseline false-positive eval.",
                        "confidence": "medium",
                        "evidence": ["ev_cluster_stability", "ev_neighbor_sample"],
                        "caveats": ["nearest-neighbor labels still need human validation"],
                    }
                ],
                "evidence": [
                    {
                        "id": "ev_cluster_stability",
                        "kind": "metric",
                        "summary": "Cluster membership is stable across three seeded eval passes.",
                        "path": "runs/ws_001/cluster-stability.json",
                    },
                    {
                        "id": "ev_neighbor_sample",
                        "kind": "sample",
                        "summary": "Nearest-neighbor sample contains ambiguous compliance/refusal boundary cases.",
                        "path": "runs/ws_001/nearest-neighbors-30.jsonl",
                    },
                ],
                "uncertainty": "Human labels are missing, so this should be treated as a candidate cluster rather than a validated failure pattern.",
                "reproduction": {
                    "commands": [
                        "uv run python pilot/evals/refusal_false_positive_scan.py --config pilot/configs/ws_001.toml"
                    ],
                    "environment": ["python 3.12", "seed=17"],
                    "notes": "Expected output is the cluster report plus nearest-neighbor sample.",
                },
                "suggested_follow_up": [
                    "label the 30 nearest neighbors before reusing this cluster as context"
                ],
                "provenance": {
                    "code": ["pilot/evals/refusal_false_positive_scan.py"],
                    "configs": ["pilot/configs/ws_001.toml"],
                    "datasets": ["pilot/data/benign_refusal_adjacent_v1.jsonl"],
                    "models": ["pilot-model-a3-lora-baseline"],
                    "prompts": ["pilot/prompts/refusal_eval_v1.md"],
                    "evals": ["pilot/evals/refusal_fp_cluster_v1"],
                    "outputs": [
                        "runs/ws_001/baseline-cluster-report.md",
                        "runs/ws_001/nearest-neighbors-30.jsonl",
                    ],
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
                "claims": [
                    {
                        "id": "claim_counterparts_surface_over_refusal",
                        "text": "Generated benign counterparts reveal over-refusal cases, but labels are too noisy for training or evaluation.",
                        "confidence": "low",
                        "evidence": ["ev_counterpart_audit"],
                        "caveats": [
                            "generation model may have copied harmful framing into nominally benign prompts"
                        ],
                    }
                ],
                "evidence": [
                    {
                        "id": "ev_counterpart_audit",
                        "kind": "sample_audit",
                        "summary": "Spot-check found useful over-refusal candidates alongside label noise.",
                        "path": "runs/ws_002/counterpart-spot-check.md",
                    }
                ],
                "failed_attempts": [
                    "automatic benign-label heuristic did not separate harmless medical, legal, and cybersecurity counterparts reliably"
                ],
                "uncertainty": "The dataset is useful for inspection but not yet reliable enough to drive finetuning.",
                "reproduction": {
                    "commands": [
                        "uv run python pilot/scripts/generate_counterparts.py --input pilot/data/harmful_seed_prompts_v1.jsonl --output runs/ws_002/generated-benign-counterparts.jsonl"
                    ],
                    "environment": ["python 3.12", "temperature=0.7"],
                },
                "suggested_follow_up": [
                    "create a small human-labeled benign counterpart set before fitting any filter"
                ],
                "provenance": {
                    "code": ["pilot/scripts/generate_counterparts.py"],
                    "datasets": ["pilot/data/harmful_seed_prompts_v1.jsonl"],
                    "models": ["sim-agent-counterparts"],
                    "prompts": ["pilot/prompts/benign_counterpart_generation.md"],
                    "evals": [],
                    "outputs": ["runs/ws_002/generated-benign-counterparts.jsonl"],
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
                "claims": [
                    {
                        "id": "claim_filter_tradeoff",
                        "text": "The narrow filter drops public false positives but slightly reduces target-failure detection.",
                        "confidence": "medium-low",
                        "evidence": ["ev_tradeoff_curve"],
                        "caveats": [
                            "public eval may reward easier retained examples",
                            "target-failure detection drop blocks reuse without replication",
                        ],
                    }
                ],
                "evidence": [
                    {
                        "id": "ev_tradeoff_curve",
                        "kind": "plot",
                        "summary": "False-positive rate drops while target-failure detection drops slightly.",
                        "path": "runs/ws_003/filter-tradeoff-plot.png",
                    }
                ],
                "uncertainty": "The apparent improvement may be a shortcut rather than a safer model behavior.",
                "reproduction": {
                    "commands": [
                        "uv run python pilot/evals/filter_tradeoff.py --config pilot/configs/ws_003.toml"
                    ],
                    "environment": ["python 3.12", "seed=23"],
                },
                "suggested_follow_up": [
                    "inspect removed training examples before treating the filter as useful"
                ],
                "provenance": {
                    "code": ["pilot/evals/filter_tradeoff.py"],
                    "configs": ["pilot/configs/ws_003.toml"],
                    "datasets": [
                        "pilot/data/safety_finetune_train_v1.jsonl",
                        "pilot/data/public_refusal_eval_v1.jsonl",
                    ],
                    "models": ["pilot-model-filter-candidate-003"],
                    "prompts": ["pilot/prompts/refusal_eval_v1.md"],
                    "evals": ["pilot/evals/public_refusal_fp_v1"],
                    "outputs": ["runs/ws_003/filter-tradeoff-plot.png"],
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
                "claims": [
                    {
                        "id": "claim_partial_ood_transfer",
                        "text": "The baseline cluster partially transfers OOD, with a distribution shift toward medical advice prompts.",
                        "confidence": "medium",
                        "evidence": ["ev_ood_shift"],
                        "caveats": [
                            "medical-advice-heavy distribution was not in the original contract"
                        ],
                    }
                ],
                "evidence": [
                    {
                        "id": "ev_ood_shift",
                        "kind": "report",
                        "summary": "OOD transfer preserves part of the cluster signal but shifts the strongest cases toward medical advice.",
                        "path": "runs/ws_004/ood-transfer-note.md",
                    }
                ],
                "uncertainty": "The transfer result changes the next eval design, not the answer to the original contract.",
                "reproduction": {
                    "commands": [
                        "uv run python pilot/evals/ood_transfer_check.py --config pilot/configs/ws_004.toml"
                    ],
                    "environment": ["python 3.12", "seed=31"],
                },
                "suggested_follow_up": [
                    "split medical-advice prompts from the OOD set before interpreting transfer"
                ],
                "provenance": {
                    "code": ["pilot/evals/ood_transfer_check.py"],
                    "configs": ["pilot/configs/ws_004.toml"],
                    "datasets": ["pilot/data/benign_medical_advice_ood_v1.jsonl"],
                    "models": ["pilot-model-a3-lora-baseline"],
                    "prompts": ["pilot/prompts/medical_advice_refusal_eval.md"],
                    "evals": ["pilot/evals/ood_refusal_transfer_v1"],
                    "outputs": ["runs/ws_004/ood-transfer-note.md"],
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
        "store": str(store.root),
        "contract": {"id": PILOT_CONTRACT_ID, "version": 1},
        "program": PILOT_PROGRAM,
        "workstreams": store.list_workstreams(),
        "next_commands": [
            "uv run fab attention",
            "uv run fab attention --all",
            f"uv run fab brief --program {PILOT_PROGRAM}",
            "uv run fab show ws_003 --brief",
        ],
    }
