# Strategic Context

This condenses the KB research surrounding Alignment Fab. It is not a
replacement for the KB; it is the minimum project context needed to start
building without reopening every note.

## Why Alignment Fab Exists

The automated alignment researcher thesis says, roughly: build systems that are
safe enough to help with alignment, use them to produce alignment progress
faster than capabilities advance, and rely on humans to steer and verify the
process.

The KB critique is not that AI-assisted alignment research is useless. It is
that the thesis is brittle:

- "sufficiently aligned" is not operationally defined;
- more AI-generated research does not automatically mean real progress;
- competitive pressure pushes capability faster than safety;
- plausible but subtly wrong research may be a more likely failure mode than
  explicit scheming;
- all major legs rely on legible intermediate computation, which may erode;
- deployment safety is not the same as alignment.

The part that survives is narrower and more actionable: use AI assistance on
bounded alignment subproblems where verification is tractable, and make the
research production system itself the object of study.

Alignment Fab is that production-system layer.

## The Bridge Question

The KB's "Mitigations to Automated Alignment Research" note frames the central
transition problem:

Can current containment, monitoring, automated auditing, research epistemics,
and governance safely bridge us to AI-assisted alignment work that genuinely
scales?

The least developed part is AI-assisted research epistemics. If agents generate
many hypotheses and experiments, the bottleneck becomes judgment:

- Which results are real?
- Which replicate?
- Which transfer across datasets, models, and scaffolds?
- Which are dangerous to pursue or publish?
- Which should change the alignment agenda?

Candidate mechanisms from the KB include:

- separating proposal, execution, judging, replication, and synthesis;
- hidden tests and private evaluation APIs;
- independent replication by different model families and scaffolds;
- adversarial critique agents;
- provenance tracking for every dataset, prompt, code artifact, and result;
- human review for agenda-setting decisions;
- capability-impact review before scaling or releasing methods;
- live research maps that track what has been tried, what failed, and what later
  invalidated earlier conclusions.

Alignment Fab should begin with the parts a human supervisor needs before any of
that is automated: contracts, state, decisions, provenance pointers, and
reviewable intervention points.

## Lessons From Adjacent Directions

### Automated Weak-to-Strong Researcher

Anthropic's automated W2S researcher is strong evidence that agents can make
useful empirical progress when the task is tightly scoped and outcome-gradable.
It is weaker evidence that agents can choose the right problem, metric, threat
model, or interpretation.

Design implication: Alignment Fab should treat eval design and evidence
admissibility as first-class contract fields, not incidental notes.

### A3 Safety Finetuning

A3 shows an automated loop for known safety failures: generate adversarial and
benign data, finetune, evaluate, and iterate. It is a good pilot candidate
because it has clear artifacts, repeated runs, visible false-positive risks, and
natural stop/escalation conditions.

Design implication: state packets need to capture not just "score improved" but
also data provenance, benign-counterpart behavior, OOD checks, forgetting
checks, and what would invalidate the apparent fix.

### AI Control

AI control assumes the model may be misaligned and asks whether a deployment
protocol still prevents unacceptable outcomes. It emphasizes bounded action
channels, synchronous review for high-stakes actions, trusted/untrusted model
gaps, and adversarial evaluation.

Design implication: future workstream contracts should have explicit tool,
network, filesystem, model-training, eval-access, and human-gate assumptions.

### Alignment Auditing

AuditBench exposes the tool-to-agent gap: tools can surface evidence that agents
fail to use, misunderstand, or synthesize into correct hypotheses.

Design implication: Alignment Fab should not only link artifacts. It should
record claims, evidence, uncertainty, and human decisions in a way that lets
auditors reconstruct why a result happened and why it was trusted or rejected.

### Harness Search

Harness Search treats the deployed agent loop as part of the system: prompts,
scratchpad format, memory policy, observation formatting, retry logic, and tool
schema all affect behavior.

Design implication: the harness/scaffold should be recorded as part of
workstream provenance whenever agent behavior or safety is being evaluated.

### Frontier-Relative Monitorability

This line asks whether CoT monitorability depends on task difficulty relative to
model capability. It is a strong pilot candidate because it has a concrete
experimental design and a clear supervision need: many runs, multiple model
families, difficulty bins, monitorability metrics, and hidden failure modes.

Design implication: Alignment Fab should support experiments where the same
contract produces many related workstreams and consolidation is the real value.

## Product Commitments

Alignment Fab should optimize for human judgment, not throughput.

That means:

- contracts before results;
- live state separate from contracts;
- reason for continuing as a required supervisory pressure;
- decisions and rationales recorded append-only;
- artifact links with provenance rather than artifact sprawl;
- consolidation before final reports;
- promotion rules before shared reuse;
- explicit quarantine paths for suspicious workstreams or claims.

The first version can stay deliberately local and file-backed. The important
thing is to get the primitives right before adding agent runners or dashboards.
