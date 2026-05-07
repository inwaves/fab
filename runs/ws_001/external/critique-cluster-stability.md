# Critique: cluster-stability evidence in ws_001 baseline scan

External research artifact for `ws_001` (contract `contract_pilot_a3_false_positive` v1).

Author: remote-agent-maestro (external; no access to pilot model, eval data, or
embedding model)
Date: 2026-05-07

## Subject of critique

The seeded ws_001 packet (`pkt_001`) emits the artifact
`runs/ws_001/baseline-cluster-report.md` with one claim:

> **claim_ambiguous_refusal_cluster** (confidence: medium)
> "A stable ambiguous-refusal cluster appears in the baseline false-positive
> eval."

The supporting evidence chain is:

- `ev_cluster_stability` (kind: metric) — "Cluster membership is stable across
  three seeded eval passes." Path: `runs/ws_001/cluster-stability.json`.
- `ev_neighbor_sample` (kind: sample) — "Nearest-neighbor sample contains
  ambiguous compliance/refusal boundary cases." Path:
  `runs/ws_001/nearest-neighbors-30.jsonl`.

The artifact's `uncertainty` field already concedes:

> "Human labels are missing, so this should be treated as a candidate cluster
> rather than a validated failure pattern."

This critique argues the gap is wider than the wording implies, and that the
"medium" confidence label is not yet earned by the evidence on file.

## Disagreements with the current evidence-to-claim chain

### 1. "Stable across three seeded eval passes" measures decoding stability, not robustness

The reproduction note says `seed=17` (one fixed seed). "Stable across three
seeded eval passes" with a fixed config most plausibly means: the same prompts
were re-decoded under the same model with different decoding-time RNG seeds,
and the cluster assignments did not move much. That is a useful sanity check,
but it is the weakest of several stability properties one might want:

- **Decoding stability** (what the evidence supports): under fixed data, fixed
  embedding, fixed clustering hyperparameters, the cluster does not depend on
  decoding RNG.
- **Data-perturbation stability** (not supported): under paraphrases, prompt
  reordering, or held-out splits of `pilot/data/benign_refusal_adjacent_v1.jsonl`,
  the cluster persists.
- **Embedding-ablation stability** (not supported): swapping the embedding
  model (e.g., for an off-the-shelf encoder not trained on the same refusal
  signal) preserves the cluster.
- **Hyperparameter stability** (not supported): cluster persists under
  reasonable changes to k, distance metric, normalization, or clustering
  algorithm.
- **Cross-model stability** (not supported): the cluster is recognizable in
  outputs from a non-A3 model on the same prompts.

The current evidence type only excludes the most trivial source of noise.

### 2. Risk of tautology: the cluster may be a projection of the model's own refusal axis

If the embedding used to form the cluster is derived from
`pilot-model-a3-lora-baseline` (its own residual stream, or a linear probe on
its activations, or its hidden states), then by construction the embedding
encodes that model's preferred decision boundary on refusal-adjacent inputs.
"Cluster of ambiguous refusals" could then be a restatement of "this model
refuses inconsistently here" — which is a model-internal observation, not a
finding about the prompt distribution.

The provenance lists `pilot-model-a3-lora-baseline` under `models` and an
`evals/refusal_fp_cluster_v1` under `evals` but does not record which embedding
the clustering uses. Without that, the claim cannot be defended against the
tautology read.

### 3. "Medium" confidence is not justified by the evidence on file

The artifact reports one stability check (decoding-RNG only), no human labels,
no perturbation test, no embedding ablation, and no cross-model sanity check.
For an A3 safety-finetuning pilot whose contract explicitly asks us to flag
shortcuts and weak labels, the right confidence at this point is *low*, not
medium.

This is not a request to inflate caution. It is a request to keep the
confidence ratchet honest so that downstream workstreams (ws_003, ws_004) and
the pilot brief do not over-trust this cluster as a starting point.

## What would move the confidence to medium honestly

1. Re-run `pilot/evals/refusal_false_positive_scan.py` over a paraphrased
   variant of `benign_refusal_adjacent_v1.jsonl` (e.g., GPT-rewrites or simple
   template substitutions) and report cluster Jaccard overlap with the original.
2. Re-cluster using an embedding *not* derived from the A3 model
   (e.g., a generic sentence encoder), and report cluster overlap.
3. Sweep clustering hyperparameters (k or eps) and report the Adjusted Rand
   Index between cluster solutions.
4. Run the same scan on a non-finetuned base model and check whether the cluster
   recurs. If it does, the cluster is a property of the prompt distribution,
   not the A3 model. If it does not, the cluster is at least partly model-
   specific, which is the more interesting finding but also the more leakage-
   sensitive one.
5. Then, separately, do the planned 30-NN labeling. (See the pre-registered
   plan in `prereg-labeling-plan.md`.)

## Relationship to the contract's attention boundaries

The contract says: "stop and report if any result depends on private eval
leakage" and "flag any method that appears to reduce false positives by
suppressing detection of the target failure mode." The current evidence chain
is not violating those, but it leaves the door open for downstream work
(notably ws_003) to take the medium-confidence cluster as a load-bearing
starting point. If that happens, the under-supported confidence here will be
amplified there.

## Limits of this critique

- I did not open `runs/ws_001/cluster-stability.json` or
  `runs/ws_001/nearest-neighbors-30.jsonl`. They are pointers in the
  registry; the underlying files are not in this clone of the repo. If they
  contain richer stability statistics than the one-line summary suggests, that
  would partially weaken (1) above. It would not change (2) or (3).
- I did not run the pilot eval. I have no access to the pilot model, the
  embedding choice, or the dataset. Everything above is reasoning over the
  registry-visible evidence and provenance.

## Suggested follow-up packets on ws_001

- a perturbation-stability re-run packet, if anyone has access to the pilot
  eval;
- an embedding-ablation packet;
- a cross-model recurrence packet;
- the planned human-label packet (separate, pre-registered).

These should be independent packets so that one weak result does not pull the
others down.