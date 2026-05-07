# Alignment Factory Research Note

Imported from `/Users/inwaves/ghq/github.com/inwaves/kb/research/alignment-factory/README.md`
on 2026-05-07. The KB source had uncommitted edits that match this repo's
registry/live-state direction; this copy intentionally preserves that latest
working version as local project context.

## Status

New research direction.

## Core Question

If many AI agents are doing alignment research in parallel, how can a human
researcher remain in charge: understand what is happening, steer what
continues, stop what is wasteful, interpret ambiguous results, and decide what
should be reused?

## Framing

The premise is that the agents will run. They will do days of research in less
than a day of wall-clock time, across many parallel workstreams. The bottleneck
is not whether work can be generated. The bottleneck is whether a human can
still lead the research organization.

Call the desired system an alignment factory: a research-management and control
layer for automated alignment work.

This is not primarily:

- an agent runtime;
- an agent harness;
- a report queue;
- a pile of papers, markdown, plots, and logs.

The factory is the layer that turns a large research population into cumulative,
governable progress.

## North Star

The useful analogy is that the human researcher leads an extremely large,
extremely productive team.

The system should help them answer:

- What is each workstream trying to establish?
- What has changed since the last review?
- Why is this workstream still worth running?
- Where are agents duplicating work, disagreeing, or relying on the same weak
  assumption?
- Which results are local observations, and which are safe for others to build
  on?
- What should continue, stop, merge, split, narrow, replicate, escalate, or be
  promoted?

If we lose track of this standard, we have lost the problem.

## Relationship To Existing KB Directions

- Alignment via AI Assistance is the strategic thesis and critique.
- Mitigations to Automated Alignment Research asks whether current mitigations
  can bridge us to useful AI-assisted alignment work.
- AI Control asks how to safely use untrusted models.
- Alignment Auditing asks how to uncover hidden problems before deployment.
- Harness Search studies safer agent scaffolds.

This direction sits above the workers and harnesses: it studies how a human-led
research organization remains observable, steerable, and cumulative when much
of the labor is automated.

## Central Primitive: Research Contract

The upstream primitive is the research contract. A contract defines the shape of
a workstream before results exist.

It should specify:

- research question and why it matters;
- relevant prior claims;
- allowed methods and disallowed shortcuts;
- what counts as progress, failure, and a result;
- what will not be accepted;
- expected intermediate artifacts;
- known traps;
- escalation triggers and stop conditions;
- relationship to other workstreams.

This is not asking agents to produce the answer the human wants. It is defining
the rules of the research game so that the work remains interpretable and
governable.

The contract is also an anti-sycophancy device. Instead of a human saying after
the fact, "I would trust it if X," and agents producing X-shaped evidence, the
contract says in advance what evidence is admissible and what paths are invalid.

## Layer 1: Workstream Supervision

A workstream is a running research effort under a contract.

The workstream has separate parts:

- Registry entry: stable identity, owner, parent program, status, links, and
  pointer to the current contract.
- Research contract: the human-authored or human-approved rules of the
  workstream.
- Live state: the current operational summary, updated from agent state packets
  and human decisions.
- History: prior state packets, artifacts, decisions, and deviations.

The factory tracks the live state:

- current hypothesis and plan;
- experiments run and results obtained;
- failed attempts and open blockers;
- deviations from the contract;
- resource usage;
- next intended action;
- reason for continuing.

The key field is reason for continuing. If a workstream cannot explain why
another unit of compute is likely to be useful, it should be flagged for stop,
merge, split, or human review.

This field belongs in the live state, not in the contract. Agents can propose it
in updates; the supervisor state records the current version; humans can
override it.

This is the pressure against research-shaped activity.

## Layer 2: Consolidation

The consolidation layer continuously compares work across workstreams. It should
not wait for polished final reports.

It looks for:

- duplicated effort;
- contradictory results;
- shared assumptions, datasets, evals, or methods;
- methods that keep failing;
- methods that appear promising;
- orphaned results;
- claims depending on weak evidence;
- areas with too much or too little activity.

This is where parallel exploration becomes cumulative research. Without
consolidation, a thousand agents are just a noisy crowd.

## Layer 3: Promotion

Promotion is how selected outputs become visible and reusable outside their
local workstream.

A promoted result should say:

- which workstream and contract produced it;
- which prior claims it bears on;
- which agents or humans reproduced, contradicted, or critiqued it;
- which assumptions it depends on;
- which downstream workstreams can safely use it;
- its allowed scope;
- what is explicitly not licensed by it.

Do not collapse three questions:

1. Did the agent do valid local work?
2. Should this workstream continue?
3. Can others safely build on this result?

A result can be valid but not worth continuing. A workstream can be worth
continuing without having a promotable result. A result can be real but unsafe
to share broadly because others will overuse it.

## Human Control Surface

The main UI should be a research-operations control surface, not a result queue.

It should organize:

```text
research program
-> workstreams
-> contracts
-> live hypotheses
-> experiments
-> blockers
-> conflicts
-> promoted results
-> proposed next actions
```

The human mostly intervenes at control points:

- continue or stop;
- merge or split workstreams;
- narrow a claim;
- change an eval;
- require independent replication;
- escalate to human/manual review;
- promote a result for reuse;
- quarantine a result or workstream.

The interface should surface decisions, not activity.

## What Counts As Progress

The factory must not optimize for visible throughput. It should ask whether a
workstream:

- resolved uncertainty;
- killed a bad direction;
- produced something another workstream can safely use;
- revealed a flaw in an eval, method, or assumption;
- changed what a competent researcher would do next;
- converged with independent work without sharing the same failure mode.

The danger is managerial illusion: clean dashboards over shallow work. Progress
bars, confidence tags, and dependency graphs can hide the absence of real
progress.

## Minimal Build

Start with a workstream supervisor for one concrete alignment area, such as:

- A3-style safety finetuning;
- automated weak-to-strong experiments;
- model-organism studies;
- control-protocol experiments.

The first derisking experiment:

> Can one researcher use contracts, consolidation, and a supervisor interface to
> manage 50 parallel agent workstreams better than they can manage ordinary
> reports from 5-10 workstreams?

Test whether the researcher can:

- kill weak workstreams;
- redirect confused ones;
- identify duplicated effort;
- catch invalid results;
- select useful intermediate results;
- decide what should be exposed to other agents or humans.

If this does not materially improve human steering, the architecture is not
working.

## MVP Tooling

Manual supervision does not mean no tooling. It means the first version avoids a
full automation platform and builds only the surface needed for a human to steer
workstreams.

Minimum components:

- Workstream registry: one stable record per workstream, with owner, parent
  program, status, links, and pointer to the current contract and live state.
- Contract editor: a structured template for defining admissible methods,
  invalid shortcuts, progress criteria, stop conditions, and escalation
  triggers.
- Live-state view: current hypothesis, plan, next action, blockers, deviations,
  and reason for continuing.
- State packet format: every agent run or human update emits a compact update:
  what changed, what was tried, what failed, what is proposed next, why
  continuing is worthwhile, and what should be flagged.
- Supervisor board: a table/detail UI for scanning workstreams, filtering stale
  or suspicious ones, and taking actions like continue, stop, merge, split,
  replicate, escalate, or promote.
- Artifact links: the system links to reports, logs, code, plots, and datasets,
  but does not organize itself around those files.
- Consolidation pass: a lightweight agent or script clusters related
  workstreams, flags duplicates and contradictions, and proposes managerial
  interventions for human review.
- Decision log: every human intervention is recorded with a short rationale and
  updates the workstream state.

This is enough to run the pilot. The agent runtime can remain external as long
as it can produce state packets and artifact links.

## Failure Modes

- Managerial illusion: the system shows control while the frontier barely
  moves.
- Contract Goodharting: agents optimize for what contracts reward rather than
  what the research needs.
- Premature structure: the system forces exploratory work into fake categories.
- Consolidation loss: compression hides the ambiguity that mattered.
- Promotion laundering: local results become reusable before their scope is
  understood.
- Research monoculture: workstreams converge on easy-to-measure directions.
- Human rubber-stamping: the system produces too many proposed interventions for
  real judgment.
- Capability acceleration: automated alignment work also accelerates general AI
  R&D.

## Current Take

The alignment factory is the control layer for a future where AI agents do much
of the alignment labor.

The core problem is not "can agents produce research?" They can. The problem is
whether a human researcher can continue to lead the resulting research
organization: preserving observability, consolidating parallel work,
interrupting waste, interpreting ambiguous results, and deciding where the team
should go next.

## Key Anchors

The KB keeps the paper notes. The most relevant anchors are:

- Automated Weak-to-Strong Researcher
- A3: An Automated Alignment Agent for Safety Finetuning
- Automated Researchers Can Subtly Sandbag
- Trustworthy Agents in Practice
- AI Control
- Alignment Auditing
- Mitigations to Automated Alignment Research
- Harness Search

Created in KB: 2026-05-05.
