"""Seed ideas for the weak-to-strong-pilot Fab dogfood.

Each entry maps a Fab workstream id to a distinct research direction the
agent should explore under the shared `contract_w2s_generalization` contract.
The seeds are intentionally diverse, but a few share assumptions (synthetic
teacher-student setup, PGR as the headline metric) so that Fab's deterministic
contract review can surface repeated claims and shared limitations across the
batch.

Keep seeds bounded: synthetic / small-model, CPU-fast, no LLM training.
"""

from __future__ import annotations

PROGRAM = "weak-to-strong-pilot"
CONTRACT_ID = "contract_w2s_generalization"
CONTRACT_VERSION = 1

SEEDS: dict[str, dict[str, str]] = {
    "ws_001": {
        "title": "PGR vs. imitation regime map (naive weak-label finetuning)",
        "idea": (
            "Build a synthetic teacher-student W2S simulation: a low-capacity "
            "'weak supervisor' (e.g. logistic regression / shallow MLP) trained "
            "on ground truth, used to label a disjoint set; a higher-capacity "
            "'strong student' trained ONLY on those weak labels. Sweep the "
            "weak-strong capability gap and the weak supervisor's label-noise / "
            "systematic-bias level. Produce a 2D regime map of "
            "performance-gap-recovered (PGR) and a separate 'imitation score' "
            "(agreement with the weak supervisor's *errors* specifically). "
            "Characterize where naive weak-label finetuning elicits latent "
            "capability vs. learns to imitate supervisor mistakes."
        ),
    },
    "ws_002": {
        "title": "Auxiliary confidence loss: does it actually reduce imitation?",
        "idea": (
            "Reuse a synthetic teacher-student W2S setup. Implement the "
            "auxiliary confidence loss (encourage confident student predictions "
            "even when they disagree with the weak label) and ablate its weight. "
            "Measure the trade-off between (a) ground-truth recovery / PGR and "
            "(b) imitation of injected systematic supervisor bias. Identify "
            "whether the confidence loss separates 'learning the task' from "
            "'copying the labeler', or merely trades imitation for "
            "overconfident error, as a function of how structured the weak "
            "supervisor's bias is."
        ),
    },
    "ws_003": {
        "title": "Bootstrapping through intermediate capacities vs. one big jump",
        "idea": (
            "Test the bootstrapping claim from the original W2S paper in a "
            "synthetic setup: instead of weak->strong directly, go "
            "weak->medium->strong, relabelling at each stage. Vary the "
            "weak-strong capability gap. Quantify when staged bootstrapping "
            "beats a single weak->strong jump and when it just compounds "
            "supervisor error. Report the gap regime where bootstrapping helps "
            "and where it is neutral or harmful."
        ),
    },
    "ws_004": {
        "title": "Goodhart / held-out leakage audit for automated W2S researchers",
        "idea": (
            "This is a critique/red-team workstream. Design and run a small "
            "experiment that demonstrates how repeated submission of a method's "
            "predictions to a held-out PGR-style scoring signal inflates "
            "apparent W2S progress (the automated-W2S-researcher Goodhart "
            "caveat). Quantify the optimism bias as a function of number of "
            "submissions / tuning rounds, and propose a concrete protocol "
            "(e.g. submission budget, fresh holdout rotation) that bounds it. "
            "Be explicit about how this failure would look from inside Fab."
        ),
    },
    "ws_005": {
        "title": "Bias-variance early-warning signals for W2S failure",
        "idea": (
            "Operationalize the bias-variance perspective into ground-truth-"
            "free, in-training indicators (e.g. student-vs-weak disagreement "
            "dynamics, prediction variance across seeds/subsets, calibration "
            "drift, confidence on weak-disagreement examples). On a synthetic "
            "W2S pipeline with controllable supervisor bias, test whether any "
            "indicator predicts low final PGR / high imitation BEFORE the "
            "ground-truth evaluation is revealed. Report ROC-style separation "
            "and the indicator's failure cases."
        ),
    },
}

ORDER = ["ws_001", "ws_002", "ws_003", "ws_004", "ws_005"]