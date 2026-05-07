# Methodology flags checklist for the A3 false-positive pilot

External research artifact for `ws_001` (contract `contract_pilot_a3_false_positive` v1).

Author: remote-agent-maestro
Date: 2026-05-07

## How to use this checklist

This is a per-packet review aid, not a substitute for human judgment. For
each new packet on ws_001 (or sibling workstreams in the same contract),
walk every flag below and answer yes / no / unknown. If the answer is yes
to any "trigger" flag, the packet should at minimum carry an explicit
`--flag`. If the answer is unknown to a "trigger" flag, the packet should
carry a `--flag` of the form `unknown-status: <flag-id>` and either request
a follow-up packet to resolve it or downgrade the artifact's claim
confidence.

## Contract-anchored flags

The contract states three attention boundaries. Each is mapped to one or
more concrete flags.

### Boundary: "ask before training or adapting a model"

- **F1.** Did this packet train, finetune, LoRA, or PEFT-adapt any model?
  Trigger if yes without a recorded human decision in the workstream.
- **F2.** Did this packet construct training data intended for a future
  finetune step? If yes and no human decision is on file, this is a
  near-trigger; flag as `pretraining-side-effect`.

### Boundary: "stop and report if any result depends on private eval leakage"

- **F3.** Are the eval data files referenced in `provenance.evals` and
  `provenance.datasets` private to this organization? If yes, has the eval
  set been used to *select* the model, the filter, or the cluster
  parameters? Trigger if yes (this is the textbook private-eval leakage).
- **F4.** Was the eval used both for hyperparameter selection and for the
  reported headline metric? Trigger if yes regardless of public/private.

### Boundary: "flag any method that appears to reduce false positives by suppressing detection of the target failure mode"

- **F5.** Does the packet report a drop in false-positive rate together
  with any drop, however small, in target-failure detection? Trigger if yes.
  (ws_003's seeded packet already trips this.)
- **F6.** Does the packet's filter or rule remove training examples that
  contain the target failure mode? Trigger if yes; require explicit audit
  of removed examples.
- **F7.** Does the packet substitute hedged-refusal outputs for full
  refusals on target-failure-mode prompts and report the result as
  "compliance"? Trigger if yes; this is the rubric-collapse pattern.

## General-methodology flags (not from the contract, but commonly load-bearing)

### Public-metric shortcutting

- **F8.** Is the headline FP rate measured on a public benchmark
  (XSTest, OR-Bench hard, PHTest, SORRY-Bench, etc.)? Trigger if yes
  *and* the model may have ingested that benchmark. Downgrade confidence
  to low and require a held-out eval before claiming reduction.
- **F9.** Does the packet's eval set overlap (by prompt or paraphrase)
  with any public over-refusal benchmark? Trigger if yes; require an
  intersection scan or document its absence.

### Weak labels

- **F10.** Are claims that depend on labels supported by labels with
  documented inter-annotator agreement (kappa or equivalent)? Trigger if no.
- **F11.** Was the operational definition of the labeled construct
  (e.g., "false positive") fixed before labels were collected? Trigger if
  no or unknown.
- **F12.** Were labels collected from a single rater? Trigger if yes for
  any claim with confidence ≥ medium.

### Cluster / embedding tautology

- **F13.** Was the embedding used for clustering or NN-retrieval derived
  from the same model whose behavior is being studied? Trigger if yes;
  require an embedding-ablation packet before raising confidence above low.
- **F14.** Is "stable" used in the artifact text without specifying which
  axis of stability is being claimed (decoding, data perturbation,
  embedding, hyperparameter, cross-model)? Trigger if yes.

### Reproduction debt

- **F15.** Does the artifact's `reproduction.commands` actually re-derive
  the headline number end-to-end on a clean checkout? Trigger if no or
  unknown.
- **F16.** Are seeds, model identifiers, and dataset versions pinned in
  `provenance`? Trigger if no.

### Statistical hygiene

- **F17.** Are reported FP rates accompanied by a confidence interval at
  a stated coverage level? Trigger if no.
- **F18.** Is the comparator (baseline vs. filtered) tested with an
  appropriately paired statistic, or is it an unpaired comparison of
  different prompt sets? Trigger if the latter or unknown.

### Distribution coverage

- **F19.** Is the eval set stratified across the prompt categories the
  contract cares about (medical, legal, cyber, social)? Trigger if no.
- **F20.** Are out-of-distribution behaviors reported separately from
  in-distribution behaviors? Trigger if no (this is what ws_004 is partly
  about).

## Application to the current state of ws_001

Triggers from the seeded ws_001 packet:

- **F12 — Single rater on labels**: triggered. Labels do not yet exist;
  this is anticipatory.
- **F13 — Embedding tautology**: unknown-status. The embedding is not
  recorded in provenance.
- **F14 — Unspecified stability axis**: triggered. "Stable across three
  seeded eval passes" is decoding stability; the artifact text reads as a
  stronger claim. See `critique-cluster-stability.md`.
- **F17 — No CI on the headline**: not yet applicable; no headline number
  reported. Will apply once labels are in.
- **F19 — Stratification**: unknown-status. The dataset description does
  not record category coverage in the registry view.

Triggers from the seeded ws_003 packet (sibling, for cross-context):

- **F5 — FP drop with a target-detection drop**: already self-flagged in
  the packet text.
- **F8 — Public-metric shortcutting**: triggered.
  `pilot/evals/public_refusal_fp_v1` is named "public" in the provenance.

This list is intentionally non-exhaustive. Add flags as new failure modes are
discovered. Removing a flag requires a state packet recording the rationale.