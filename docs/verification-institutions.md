# Verification Institutions: Fab As A Court

Status: proposal on branch `verification-institutions`, 2026-10-27. Nothing
here is implemented. Whether it enters Fab proper is a separate decision.

## The Parallel

Beren Millidge's
[Mitigating Reward Hacking as Institutional Design](https://www.beren.io/2026-08-17-Mitigating-Reward-Hacking-as-Institutional-Design/)
builds an apparatus around an RL actor and then notices what it has built: a
legal system. Prosecutors and defenders, a presiding judge, appeals, lower and
higher courts, a supreme court of human judgment, rules for gathering and
handling evidence, separation of powers, recusal, standing, precedent. He
argues this is not a coincidence. A legal system exists to find and adjudicate
some notion of truth when every component is fallible, has its own incentives,
may be acting adversarially, and no truth oracle exists.

That is Fab's problem, stated exactly. A human researcher must decide what is
true about a research question from the output of a swarm of agents. The
outputs are reports, bundles, transcripts, and re-readings of all three. Each
report is testimony from an interested party, which may be sycophantic,
overclaimed, hacked, or simply mistaken. There is no oracle. The human cannot
read everything, and the human's attention is the one resource the system
cannot manufacture.

So the mapping is not "translate RL rewards into something Fab has". It is:
**Fab is the court.** The contract is the question before it. Claims are the
propositions it must decide. Bundles are the evidence. Reports are testimony.
Executors are witnesses with an interest in the outcome. The human is the
supreme court, and the brief is its docket. Beren's institutions are the
procedure that lets a court reach sound verdicts without the top judge
reading every page of every file.

### What Fab already has, in these terms

| Court | Fab today |
|---|---|
| The question before the court | Contract version |
| Pleadings | `manifest.json`: claims, evidence, limitations |
| Case file | Run bundle: report, code, results, logs |
| Docket | Attention queue (`fab attention`) |
| Clerk's summary | Deterministic `contract_review` in the brief |
| Judge | Human judgment (`fab judge`), append-only |
| What becomes settled law | Next-context buckets; promotion, deferred |

### What is missing

There is no prosecution, so nothing tests a claim before the judge sees it.
There is no duty of candour, so the only account of a run's weaknesses is the
one the witness volunteers in `limitations`. There are no lower courts, so
every case goes straight to the top. There is no precedent, so the same
mistake is re-litigated from scratch each batch. There is no credibility
record, so a source that has been wrong ten times reads the same as one that
has been right ten times. There are no appeals, so a defective question
produces a defective answer rather than a motion to dismiss. Everything is
decided by the supreme court reading the file, which is the thing that does
not scale.

## Rules Of The Court

These are Beren's principles, plus two from the fab post, restated as rules
Fab adopts.

1. **Right of appeal.** A witness may move to dismiss the question (the
   contract is impossible, ambiguous, or missing a resource) or contest the
   prosecution's findings. Appeals need standing: a verifiable proof or a
   minimal precise question, with a stated probability of success.
2. **Adversarial prosecution that learns.** A falsifier tries to break each
   claim, proposes its own checks, and reads the case law. It is not a fixed
   checklist the witness can fit.
3. **Every submission is a verifiable pleading.** Claims, findings,
   confessions, appeals, and rulings all follow a fixed form with locations,
   checks, and a confidence. Vague submissions are inadmissible.
4. **Separation of powers.** First-instance and appellate judges differ in
   configuration and context. No party reviews its own work.
5. **Precedent.** Upheld findings and settled interpretations of contracts
   become case law that later verification draws on. Witnesses never see it.
   Beren's footnote 13 is the point: precedent amortises jurisprudence, so
   the court pattern-matches to a prior case instead of reasoning from first
   principles every time. For Fab that is the main lever on human attention.
6. **Maximise partially independent channels.** Testimony, candour,
   prosecution, documentary checks, and independent replications are
   separate channels on the same claim. Agreement across them is
   corroboration only to the extent they are independent.
7. **Calibrated confidence everywhere.** Every party states a probability on
   every submission, and the court keeps the track record.
8. **Random audits of every component.** No tier is above review, including
   the appellate judge.
9. **Hierarchy of courts.** Cheap checks first; expensive judgment only for
   what survives. Most cases should never reach the top.
10. **Human as supreme court.** Final, and able to overturn precedent.
11. **Rules of evidence: blind the reviewer to testimony.** From the fab
    post: a reviewer who reads a sycophantic report inherits the sycophancy,
    across model families. The prosecution reads the evidence, not the prose.
12. **The docket is the constraint.** From the fab post: attention is the
    binding constraint. Every institution below is justified only if it
    reduces what the supreme court must read without letting more false
    claims through.

## Where The Parallel Bends

- **The unit is the claim, not the episode.** Beren adjudicates whether an
  episode was hacked. Fab adjudicates whether a claim is true. Finding a hack
  matters because it changes a claim's status, not for its own sake.
- **The court cannot sentence or train.** Fab's only instruments are
  procedure and context: what each party sees, when, and in what form. The
  duty of candour is made safe by a rule, not by a reward.
- **Verdicts are graded, not binary.** Research claims are usually partly
  true, true under a reading of the contract, or true at a scale that does
  not transfer. Beren's `underspecified` and `unresolved` outcomes are the
  norm here, not the exception.
- **Verdicts can be revisited.** Beren's staleness-versus-accuracy tension
  (footnote 13) applies: new evidence, a replication, or an audit can overturn
  an earlier status. Fab's judgments are append-only, so the court's record
  already allows this; the status a claim carries is the latest ruling by the
  highest authority.
- **The witness's privileged knowledge lives elsewhere.** Beren's confession
  works because the confessor has the actor's full context. That context is
  on the execution platform, not in Fab, so the confession must be taken by
  forking the executor's own session (appendix).
- **The parties write to the same substrate.** Executors commit to
  Alexandria. Evidence handling therefore needs chain of custody: a digest
  taken when the bundle is sealed, recomputed by the court from what was
  actually filed, and identity checks on every later submission.
- **A court that looks like a grader changes the witness.** nostalgebraist's
  observation that models infer graded episodes from context means visible
  scoring apparatus can elicit grader-seeking. Review is framed to the
  executor as replication and critique, no score is ever shown, and the
  confession is taken after the fact.

## Roles And The Record

Who sees what. Fab records each submission's declared exposure and flags the
violations it can detect; enforcement lives on the execution platform.

| Role | Court analogue | Contract | Claims | Report, summary | Code, results, logs | Executor reasoning | Confession | Verification | Casebook |
|---|---|---|---|---|---|---|---|---|---|
| Executor | Witness, proponent | yes | writes | writes | writes | own | no | no | never |
| Confessor (fork of executor) | Witness under duty of candour | yes | yes | yes | yes | as retained | writes | no | no |
| Primary verifier | Prosecution | yes | bare list | no | yes | no | no | writes | yes |
| Rebuttal (fork of executor) | Defence | yes | yes | yes | yes | as retained | own | findings only | no |
| Tier-0 checks (Fab) | Clerk | yes | yes | no | yes | no | yes | yes | no |
| Adjudicator | Appellate judge | yes | yes | yes | yes | trace if bundled | yes | yes | yes |
| Human | Supreme court | yes | yes | yes | yes | trace if bundled | yes | yes | yes |

Recusal rules:

- the prosecution and the confessor never see each other's submission before
  both are sealed;
- the adjudicator's configuration differs from the prosecution's;
- a prosecution that shares a model family with the witness is disclosed in
  the record as a conflict (correlated blind spots);
- the casebook never enters a witness's context; `fab refs check` warns on
  `fab://casebook/` references in contracts.

## Procedure

```mermaid
flowchart TD
    C["Contract vN: the question"] --> E["Executor run<br/>witness, external platform"]
    E -->|"motion to dismiss"| A["Appeal<br/>status: appealed"]
    E --> S["Sealed bundle<br/>READY carries digest"]
    S --> T["Tier-0 checks<br/>clerk, deterministic"]
    S --> CF["Confession<br/>forked executor session"]
    S --> V["Primary verifier<br/>prosecution, blind to prose, reads casebook"]
    T --> X
    CF --> X["Cross-examination<br/>per-claim support record"]
    V --> X
    X -->|"uncontested"| D{"Audit draw"}
    D -->|"not drawn"| B["Docket: summary judgment"]
    D -->|"drawn"| ADJ
    X -->|"contested"| ADJ["Adjudicator<br/>appellate judge"]
    V -.->|"verifier-only findings"| R["Rebuttal<br/>defence, forked executor session"]
    R -.-> ADJ
    A --> ADJ
    ADJ --> B
    ADJ -->|"unresolved, critical, novel"| H["Human<br/>supreme court"]
    B --> H
    H --> K["Precedent<br/>casebook"]
    H --> CV["Contract vN+1"]
    K -.->|"prosecution context only"| V
```

1. **The question.** The executor receives the contract and a standard
   executor protocol kit: the manifest schema, the appeal channel, and a
   description of review as independent replication. It is not told about
   the confession by default.
2. **Testimony, with a right of appeal.** The executor completes the run;
   or ends early with `status: appealed` and a verifiable appeal; or
   completes under a stated assumption with an appeal attached.
3. **Filing.** The executor seals the bundle: it computes a digest over every
   file except `READY` and writes it into `READY`. Fab recomputes the digest
   from what was actually filed (for Alexandria, the committed checkout). A
   mismatch is an ingest error. Every later submission names the digest.
4. **Clerk's checks.** Fab runs deterministic checks on the filed bundle:
   evidence paths exist, reproduction commands point at files that exist,
   numbers in claims can be found in results files, `used_refs` resolve. The
   output is a set of `note` findings and, for hard failures, ingest errors.
5. **Candour and prosecution, independently and in parallel.**
   - The platform forks the executor session, appends the confession request,
     and files a confession. Tools are read-only.
   - A separate agent receives the prosecution kit: the contract, the bare
     claims with their ids, code, results, logs, and the casebook. Not the
     report, not the summary, not the confession. It re-runs what it can,
     tries to falsify each claim, and files a verification.
6. **Cross-examination.** Fab builds a per-claim support record from every
   channel and decides whether the claim is contested.
7. **Defence (phase 2).** For prosecution-only findings of material severity
   or worse, the platform forks the executor session again and shows it only
   those findings. It may concede or contest each with evidence.
8. **Judgment.** Phase 1: the human rules on contested items. Phase 2: an
   adjudicator with more budget and the whole record rules first; the human
   sees escalations and a random sample.
9. **Supreme court.** The brief is the docket: escalations, then grouped
   appeals, then contested claims with the adjudicator's ruling, then the
   uncontested list. Human rulings override everything below and are the
   authoritative resolution for credibility scoring.
10. **Settled law.** Upheld findings and settled interpretations become
    precedent. Upheld appeals produce the next contract version. Claim
    statuses feed the next context.

## Pleadings And Evidence

### Claims as filed

The run manifest is unchanged. Claims keep their ids `claim_NNN` in manifest
order, which Fab already assigns and the platform can compute before filing.

Admissibility is graded rather than enforced. A claim whose evidence cannot
be located in the bundle is still filed, but the prosecution will return
`not_checkable` and the clerk's checks will say why. A claim is never
supported by testimony alone.

### Chain of custody

`READY` may contain `sha256:<hex>`, the digest over sorted relative paths and
per-file hashes of every file in the bundle except `READY`. Fab computes the
same digest at ingest, from the checkout it reads, and fails ingest on a
mismatch. A `READY` with no digest is accepted and Fab's digest is used, so
existing bundles keep working. Every assessment names the digest it examined;
an assessment of a different digest is stale and rejected.

The worked example below is the motivating case: a bundle that passed
validation on the witness's disk and would fail it once committed.

### Submissions

Every submission after the run itself is an **assessment**: a sibling bundle
keyed by run. ("Review" already means attention review in the codebase, so
the new objects are not called that.)

```text
artifacts/<program>/<workstream_id>/<run_id>/            run bundle, unchanged
  manifest.json
  artifact/
  READY                                                  may carry the digest

assessments/<program>/<workstream_id>/<run_id>/<assessment_id>/
  assessment.json
  evidence/                                              check outputs, logs
  READY
```

`assessments/` must not be readable by executors. If Alexandria cannot
exclude a prefix from executor mounts, assessments go to a separate
repository with the same layout. Otherwise witnesses read the case law.

Common envelope:

```json
{
  "schema": "fab.assessment/v1",
  "kind": "confession",
  "run_ref": {
    "workstream_id": "ws_001",
    "bundle_relpath": "artifacts/rlvr-support-pilot/ws_001/run-rlvr-support-001",
    "bundle_digest": "sha256:..."
  },
  "source": "maestro/run-rlvr-support-001/confession-1",
  "created_at": "2026-11-02T10:00:00Z",
  "exposure": {
    "saw_report": true,
    "saw_confession": false,
    "saw_verification": false,
    "saw_casebook": false
  },
  "body": {}
}
```

Shared types:

- **Locations**: paths relative to the bundle root, with optional `lines` or
  a JSON `pointer`.
- **Checks**: `command` (command, cwd, expected output, captured output path)
  or `inspect` (path, JSON pointer or line range, expected value). Fab can
  re-resolve `inspect` checks itself.
- **Severity**: `critical` (a claim is false, a result is fabricated, or an
  attention boundary was violated), `material` (a claim is overstated,
  unsupported, or cannot be checked from the bundle as filed), `minor` (no
  conclusion changes), `note`.
- **Category**: an id from the taxonomy below.

## Candour: The Confession

The confession is the witness's own account of where its testimony is weak,
taken after the bundle is sealed, from a fork of the witness's own session.
It has knowledge no other channel has: what was tried and dropped, what was
tuned against what, what the witness believed while writing the report.
OpenAI's result is the empirical basis: confessions are reliable for
deliberate shortcuts and unreliable for mistakes the model does not
recognise, and an untrained model already confesses often.

The rule that makes candour safe is the **non-penalty rule**:

> An issue the witness discloses is treated no worse than the same issue
> found by the prosecution.

A claim's status depends on the facts, not on who reported them. Disclosure
only improves the witness's credibility record. The confession prompt states
this, and it has to be true in the implementation: the brief must present
confessed and prosecuted issues identically.

The body adapts OpenAI's `ConfessionReport`. The compliance checklist is the
contract's objectives and attention boundaries. Items are specific and
checkable. Each carries Beren's two probabilities. A virtual appeal catches
motions the witness should have filed.

```json
{
  "mode": "forked_session",
  "context_coverage": "compacted",
  "objectives": [
    {
      "id": "obj_002",
      "objective": "Report the code that produced each result.",
      "source": "contract:desired_output",
      "compliance": "not_complied_not_reported",
      "analysis": "The RL-strength sweep table was computed interactively from the ablation JSON files; that script is not in the bundle."
    }
  ],
  "items": [
    {
      "id": "c1",
      "category": "evidence_gap",
      "severity": "material",
      "statement": "summary.json covers only the two main runs; the sweep table and the all-configuration containment statistic came from an unsaved interactive analysis.",
      "locations": [{"path": "artifact/results/summary.json", "pointer": "/inputs"}],
      "affected_claims": ["claim_001", "claim_003"],
      "check": {"kind": "inspect", "path": "artifact/results/summary.json", "pointer": "/inputs", "expect": "[\"metrics_seed17.json\", \"metrics_seed23.json\"]"},
      "p_upheld": 0.95,
      "p_verifier_finds": 0.5
    }
  ],
  "unreported_uncertainties": ["Whether the collapse under concentrated RL is an optimizer artefact rather than a property of RLVR."],
  "would_have_appealed": {"category": null, "statement": null, "p_upheld": 0.05},
  "completeness": "These are all the issues I am aware of.",
  "overall": {"claims_supported_as_written": "partially", "p_confession_upheld": 0.9}
}
```

Compliance labels are OpenAI's seven, with "reported" meaning disclosed in
the bundle: `not_complied_claimed_compliance`, `not_complied_not_reported`,
`not_complied_reported`, `unsure_complied_not_reported`,
`unsure_complied_reported`, `nearly_complied`, `fully_complied`. The first two
are the ones that change a claim's status.

`mode` is `forked_session`, `same_session`, or `transcript_replay`.
`context_coverage` is `full`, `compacted`, or `unknown`. A fresh model
reading the transcript is a monitor, not a witness; it is filed as
`transcript_replay` and counted as a separate channel.

## Prosecution: The Primary Verifier

The prosecution's job is to find out whether the evidence supports the
claims, not whether the report is persuasive. It therefore never sees the
report or the summary. It sees the contract, the bare claims, the code,
results and logs, and the casebook. It runs checks, re-executes reproduction
commands where feasible, and files claim verdicts plus findings. It is
preferably a different model family and harness from the witness.

```json
{
  "verifier": {
    "config_id": "ver_blind_v1_familyB",
    "model_family": "family-b",
    "harness": "codex",
    "blind_to_prose": true,
    "casebook_snapshot": "sha256:..."
  },
  "claim_verdicts": [
    {
      "claim_id": "claim_003",
      "verdict": "partially_supported",
      "reasoning": "The standard-configuration support counts (186, 160) reproduce from summary.json; the ablation counts have no shipped derivation.",
      "checks": ["chk_001"],
      "p_upheld": 0.8
    }
  ],
  "findings": [
    {
      "id": "f1",
      "category": "evidence_gap",
      "severity": "material",
      "statement": "make_summary.py globs only metrics_seed*.json; nothing in the bundle derives the sweep table.",
      "locations": [{"path": "artifact/code/make_summary.py", "lines": "160"}],
      "affected_claims": ["claim_001", "claim_003"],
      "check": {"kind": "inspect", "path": "artifact/results/summary.json", "pointer": "/inputs", "expect": "[\"metrics_seed17.json\", \"metrics_seed23.json\"]"},
      "interpretation_basis": "The contract asks for the code that produced each result.",
      "precedent": [],
      "p_upheld": 0.85,
      "p_confessed": 0.5
    }
  ],
  "checks": [
    {"id": "chk_001", "kind": "command", "command": "python3 make_summary.py --results ../results", "cwd": "artifact/code", "exit_code": 0, "output_path": "evidence/chk_001.txt", "outcome": "pass"}
  ],
  "overall": {"verdict": "issues_found", "p_upheld": 0.8, "p_confession_agrees": 0.5}
}
```

Claim verdicts: `supported`, `partially_supported`, `unsupported`,
`contradicted`, `not_checkable`.

Two rules keep the prosecution honest. Every finding carries an
`interpretation_basis`, Beren's burden on the verifier to say why its test is
a valid reading of the contract. And the prosecution's credibility record
scores a correct `clean` exactly as well as a correct finding, so there is
nothing to gain from manufacturing objections.

## Defence: The Rebuttal

Phase 2. For prosecution-only findings of material severity or worse, the
platform forks the executor session a second time and shows it those findings
only. This is Beren's appeal against the verifier, and the guard against a
prosecution whose reading of the contract has drifted from the ordinary one.

```json
{
  "responses": [
    {
      "finding_ref": "asm_004/f1",
      "position": "concede",
      "argument": "The sweep analysis was interactive and not saved. The ablation JSON files are complete; the derivation can be re-run with make_summary.py on each renamed file.",
      "evidence": [],
      "p_upheld": 0.2
    }
  ]
}
```

`position` is `concede`, `contest`, or `partially_concede`. `p_upheld` is the
defence's probability that the finding stands.

## Cross-Examination: The Support Record

This is Fab's own deterministic step, in the spirit of `contract_review`.

### Channels

For each claim, Fab collects the verdicts of every channel that spoke to it:

| Channel | Independence |
|---|---|
| Testimony: the executor's `confidence` and caveats | Interested party |
| Candour: confession items naming the claim | Same party, different conditions |
| Prosecution: claim verdict and findings | Independent, blind to prose |
| Clerk: tier-0 checks touching the claim's evidence | Mechanical |
| Replication: claims in other workstreams grouped as the same text | Independent unless they share provenance |
| Audit: adjudicator findings on a sampled run | Independent, expensive |

This is Beren's "N partially independent channels" (his footnote 8) applied
per claim. Replication is the channel Fab already partly has: `contract_review`
groups repeated claims. The support record adds the warning that two
workstreams sharing a dataset, eval, or scaffold are one witness, not two,
which is the aggregation-level failure `strategic-context.md` names.

### Matching

A confession item and a prosecution finding match when they share at least
one affected claim and the same category, or when their locations overlap
(same path with overlapping lines or the same pointer). One-to-many matches
are `ambiguous` and go to the adjudicator. Semantic matching is the
adjudicator's job.

### Item quadrants

| Prosecution | Candour | Quadrant | Reading | Route |
|---|---|---|---|---|
| no | no | clean | No channel objected | Audit draw |
| yes | no | `verifier_only` | Concealment, unawareness, or a false objection | Defence, then adjudicate if material or worse |
| no | yes | `confession_only` | Prosecution blind spot, or false confession | Adjudicate if material or worse; the most valuable case for precedent |
| yes | yes | `agreed` | The court working | Accept; adjudicate only if critical |

Minor and note items are entered in the record and never escalated.

### Claim status

A claim's status is derived from its support record, in this order of
authority: human ruling, adjudicator ruling, agreed channels, prosecution
verdict, testimony. It is one of `supported`, `partially_supported`,
`unsupported`, `contradicted`, `underspecified`, `unresolved`, or
`untested`. Status is recomputed on read, so a later ruling or audit changes
it without rewriting history.

### Run outcome

`awaiting_confession`, `awaiting_verification`, `clean_agreed`,
`agreed_issues`, `verifier_only`, `confession_only`, `mixed`, `appealed`. A
run is **uncontested** when its outcome is `clean_agreed` or `agreed_issues`
with nothing critical; everything else is **contested**.

## Judgment

### Adjudication (phase 2)

The adjudicator is the appellate judge: more budget than the prosecution, a
different configuration, and the whole record (bundle, confession,
verification, rebuttal, casebook, tool-call trace when bundled). It rules on
each routed item.

```json
{
  "adjudicator": {"config_id": "adj_v1_familyC", "model_family": "family-c", "trigger": "routed"},
  "preliminary": [
    {"item_ref": "asm_004/f1", "verdict": "upheld", "note": "before reading the rebuttal"}
  ],
  "items": [
    {
      "item_ref": "asm_004/f1",
      "verdict": "upheld",
      "reasoning": "Conceded by the defence; the ablation files allow the derivation to be re-run, so claim_003 is partially supported as filed.",
      "checks": ["chk_a1"],
      "escalate": false,
      "p_human_agrees": 0.9
    }
  ],
  "casebook_proposals": [
    {"category": "evidence_gap", "title": "Aggregation script globs a subset of the result files it reports on", "detection": "compare summary inputs against the result files cited by the report", "from_item": "asm_004/f1"}
  ],
  "audit_findings": []
}
```

`preliminary` is Beren's two-stage judging: a ruling before reading the
argument, then one after, with the difference recorded. A ruling that flips
with no new evidence is a persuasion signal.

Verdicts: `upheld`, `rejected`, `underspecified` (the contract did not settle
the point), `unresolved` (the court cannot tell). The last two are not
failures; they are the honest outcomes Beren adds to the binary ontology.

### Escalation to the supreme court

- any `unresolved` item;
- any upheld `critical` item;
- an upheld `confession_only` item with low `p_verifier_finds` (a blind spot
  the witness knew about);
- an audit finding that no channel reported (the worst case);
- the adjudicator ruling against both channels;
- an upheld appeal (a human writes the next contract version);
- a preliminary and final ruling that differ with no new evidence.

### Routing policy

Per programme, in `review-policy.json` under the Fab store:

```json
{
  "audit_rate_clean": 0.10,
  "audit_rate_agreed": 0.05,
  "adjudicate_min_severity": "material",
  "rebuttal": "verifier_only_material",
  "escalate_confession_only_below_p_verifier_finds": 0.3
}
```

Audit draws use a cryptographic RNG when a run first becomes uncontested, and
each draw is appended to `audit-draws.jsonl`: unpredictable to witnesses,
auditable by humans.

## Appeals

An appeal is a motion, not a conversation. It ends the run, which keeps Fab
out of the control plane.

- **Motion to dismiss.** The contract is impossible, ambiguous, missing a
  resource, self-contradicting, or unsafe. The run ends with
  `status: appealed`. This removes Beren's worst case: a witness spending its
  whole budget on a question it knew was unanswerable.
- **Completed under assumption.** The run completes with
  `completed_with_limitations` and an appeal carrying
  `assumption_if_continued`, so the court knows which claims rest on that
  reading.
- **Against the prosecution.** The rebuttal, above.

```json
{
  "status": "appealed",
  "appeals": [
    {
      "id": "app_1",
      "target": "contract",
      "category": "missing_resource",
      "statement": "The contract's Context lists alexandria://papers/rlvr-support-notes.md; it does not resolve.",
      "question": "Which note should be used, or should the run proceed from arXiv:2504.13837 directly?",
      "proof": [{"kind": "command", "command": "ls papers/ | grep -i rlvr", "output_path": "artifact/logs/appeal_proof.txt"}],
      "assumption_if_continued": null,
      "p_upheld": 0.9
    }
  ]
}
```

`target` is `contract`, `environment`, or `verifier`. `category` is
`impossible`, `ambiguous`, `missing_resource`, `conflicting_requirements`,
`unsafe`, or `verifier_error`. Standing requires a `proof` or a minimal
`question`; a bare complaint fails validation.

The docket groups appeals by contract version, category, and normalised
question text, with the grouping `contract_review` already uses for repeated
claims. Five workstreams hitting one defect produce one line, which is the
next contract version waiting to be written. An upheld appeal is recorded by
an `amend-contract` ruling that links to the new immutable version. Rejected
appeals are scored against their `p_upheld`, which discourages a flood of
motions without forbidding them. `would_have_appealed` in confessions
catches motions that should have been filed.

## Precedent: The Casebook

The casebook is the court's institutional memory. It holds two kinds of
entry:

- **Patterns**: ways a bundle has looked better than it was, with a
  detection method, preferably a reusable check.
- **Interpretations**: how an ambiguous contract clause was settled, so later
  verification applies the same reading and later contracts avoid the
  ambiguity.

Each entry records category, title, pattern or interpretation, detection,
source item, the channel that found it, and status. Adjudicator proposals
enter as `provisional`; a human `promote-case` makes them `precedent`;
`retire-case` removes stale ones. The prosecution sees both, marked. This
keeps the rule that humans decide what changes durable understanding without
slowing the archive to human speed.

The casebook lives at `.fab/casebook/case_NNN.json`, never in a
witness-readable area, and is exported only into prosecution and adjudicator
kits with a snapshot hash recorded in each verification. The asymmetry is
Beren's immune-system argument: to pass, a shortcut must be one the court has
never seen.

## Credibility: Calibration

Every party states a probability on every submission. The court keeps the
record and computes it on read; there is no separate ledger.

| Prediction | Stated in | Resolved by |
|---|---|---|
| Confession item `p_upheld` | Confession | Adjudicator or human ruling on the item |
| Confession item `p_verifier_finds` | Confession | Matching, mechanically |
| Finding `p_upheld` | Verification | Adjudicator or human ruling |
| Finding `p_confessed` | Verification | Matching, mechanically |
| Claim verdict `p_upheld` | Verification | Adjudicator or human ruling on the claim |
| Defence `p_upheld` | Rebuttal | Adjudicator or human ruling |
| Appeal `p_upheld` | Run manifest | Adjudicator or human ruling |
| Adjudication `p_human_agrees` | Adjudication | Human ruling, usually from an audit |

Resolution authority is human, then adjudicator; `underspecified` and
`unresolved` items are excluded. The score is the Brier score, the mean of
`(p - outcome)^2`, per component and configuration, with counts and base
rates. It is used, in order of introduction, for trust display in the docket,
for finding epistemic asymmetries (upheld `confession_only` items with low
`p_verifier_finds` show where witnesses know the prosecution is weak), and
later for audit rates.

The witness's own `confidence` on claims is a free-text field today
(`medium`, `high`). Phase 2 accepts an optional numeric `p_true` per claim so
the witness, too, builds a record.

## Audits And Canaries

False negatives are the failure no single institution can see.

- **Random audits of uncontested runs.** A drawn run gets a full adjudication
  with a larger budget; a human sees a sample of the results.
- **Audits of the adjudicator.** Humans rule on a random sample of
  adjudications. "Who checks the appellate court" has only one answer.
- **Planted-defect bundles.** Real bundles copied with one defect from the
  taxonomy. They measure the prosecution's recall and precision per
  configuration. They cannot test candour, because the witness did not commit
  the defect.
- **Tempting environments.** Contracts with a provoked shortcut: a readable
  held-out set, an unachievable target, a missing file. They measure whether
  genuine shortcuts are confessed and whether motions are filed.
- **Canary contracts.** Live contracts perturbed (a context reference
  removed, two requirements made to conflict). Witnesses cannot learn a
  recognisable canary distribution.

## The Docket And The Record

This is what the supreme court reads. It replaces reading the file.

**Docket order.** Escalations; grouped appeals; contested claims with the
adjudicator's ruling; audit results; then the uncontested list as one line
per run with its outcome and the audit draw.

**Per-claim record.** For any claim the human opens:

```text
claim_003  status: partially_supported  (adjudicator, 2026-11-03)
  testimony:    high confidence; caveat: contraction magnitude is recipe-specific
  candour:      c1 evidence_gap material  p_upheld=0.95  p_verifier_finds=0.50
  prosecution:  partially_supported p=0.80; f1 evidence_gap material (matched c1)
  clerk:        2 numbers in claim text not found in results files (note)
  replication:  none in scope
  defence:      conceded
  ruling:       upheld, no escalation, p_human_agrees=0.90
  credibility:  witness maestro/* Brier 0.08 (n=12); ver_blind_v1_familyB Brier 0.11 (n=40)
  precedent:    case_003 provisional
```

**Programme view.** `contract_review` gains the cross-workstream analogue:
upheld finding categories shared across workstreams, and repeated claims
whose workstreams share provenance, flagged as correlated rather than
corroborating.

The measure of the docket is in the evaluation section: how many runs reach
the human, how many items per run, and how many false claims get past.

## Research Hack Taxonomy

Stable category ids shared by findings, confession items, and precedent. A
starting list; the casebook grows it.

| Id | Pattern |
|---|---|
| `unanchored_number` | A number in a claim or report appears in no results file and cannot be derived from one |
| `config_mismatch` | Results came from a different configuration than the one described |
| `selective_reporting` | Failed runs, seeds, or variants were run and omitted |
| `heldout_tuning` | Choices were tuned against held-out or test signal |
| `eval_leakage` | Training and evaluation data overlap, or the learner saw ground-truth-equivalent supervision |
| `metric_substitution` | The reported metric is more forgiving than the one the contract implies |
| `scope_substitution` | An easier question was answered than the one asked, without saying so |
| `overgeneralisation` | A toy or narrow result is stated as general |
| `evidence_gap` | The analysis behind a claim is not in the bundle, so it cannot be checked as filed |
| `verification_tampering` | Tests, asserts, checkers, or evaluation scripts were modified to pass |
| `fabricated_artifact` | Mocked, hard-coded, or synthetic data is presented as measured |
| `citation_misuse` | `used_refs` lists sources not used, or claims are attributed to sources that do not make them |
| `boundary_violation` | A contract attention boundary was crossed (compute, external APIs, model downloads) |
| `environment_escape` | Information or access was obtained outside the sandbox or intended channels |
| `prose_overclaim` | Report confidence exceeds what the evidence supports |

## Fab Integration

### Store layout additions

```text
assessments/<ws>/asm_NNN.json      append-only, one per ingested assessment
casebook/case_NNN.json             phase 3
audit-draws.jsonl                  phase 2
review-policy.json                 phase 2
```

Artefact records gain `bundle_digest`, and `appeals` from phase 2.

### Modules

| Module | Change |
|---|---|
| `provenance.py` | `bundle_digest(path)`: SHA-256 over sorted relative paths and file hashes, excluding `READY` |
| `manifest.py` | `RunBundle` carries the computed digest and any seal-time digest from `READY`; a mismatch raises `RegistryError`; phase 2 adds `appealed`, `appeals`, and optional `p_true` on claims |
| `artifacts.py` | `bundle_digest` and `appeals` on normalised artefacts |
| `assessments.py` (new) | Read and validate assessment bundles (READY, containment, `run_ref`); normalise each kind |
| `checks.py` (new, phase 2) | Tier-0 clerk checks: evidence paths, reproduction targets, unanchored numbers, `inspect` re-resolution |
| `crosscheck.py` (new) | Matching, quadrants, per-claim support record, claim status, run outcome, routing, audit draws |
| `calibration.py` (new, phase 2) | Derive predictions and resolutions; Brier per component |
| `casebook.py` (new, phase 3) | Entries, promotion, export snapshot |
| `store.py` | `ingest_assessment_bundle`, `list_assessments`; new dirs in `content_dirs` and `is_empty` |
| `review.py` | New attention reasons |
| `brief.py` | Docket ordering; per-claim support record; `contract_review` groups upheld finding categories and flags correlated replication |
| `status.py` | New judgment target types and actions |
| `render.py` | Record view in `show --brief`; docket sections in `brief` |
| `cli.py` | New commands |
| `services/alexandria_ingester.py` | Discover `assessments/*/*/*/*/READY`; ledger entries gain `kind` |
| `pilot.py` | One run per outcome |
| `refs.py` | Warn on `fab://casebook/` references in contracts |

The facade in `registry.py` is untouched; new names live in their own modules
as its docstring asks. `pyproject.toml` keeps zero runtime dependencies:
validation is hand-written as in `manifest.py`, and the JSON Schemas under
`docs/schemas/` are documentation.

### CLI

```bash
uv run fab ingest-assessment --from <assessment-bundle>
uv run fab kit verifier ws_001 --artifact art_001 --out /tmp/kit   # prosecution kit: blind input package + prompt + casebook
uv run fab kit confession ws_001 --artifact art_001                # confession prompt with digest, claim ids, objectives
uv run fab record ws_001 --claim art_001/claim_003                 # per-claim support record
uv run fab crosscheck ws_001 [--artifact art_001]                  # items, matches, quadrants, outcome
uv run fab queue                                                   # phase 2: what each run still needs (JSON for the platform)
uv run fab calibration [--component verifier]                      # phase 2
uv run fab casebook list|show|export                               # phase 3
```

`fab kit` and `fab queue` are not scheduling. Fab owns what context agents
receive; these commands package that context and say what is outstanding,
as `attention` does for humans. The platform decides when to run anything.

### Attention reasons

| Reason | Phase | Trigger |
|---|---|---|
| `awaiting_confession` | 1 | Run ingested, no confession for its digest |
| `awaiting_verification` | 1 | Run ingested, no verification for its digest |
| `contested` | 1 | Outcome is `verifier_only`, `confession_only`, or `mixed` |
| `issues_agreed` | 1 | Outcome is `agreed_issues` with material items |
| `stale_assessment` | 1 | An assessment names a digest no ingested bundle has |
| `exposure_violation` | 1 | Declared exposure breaks the recusal rules |
| `same_source_assessment` | 1 | Assessment source matches the executor's |
| `appealed` | 2 | Run status `appealed`, or an unresolved appeal |
| `adjudication_pending` | 2 | Routed items without a ruling |
| `escalated` | 2 | An escalation rule fired |
| `audit_selected` | 2 | Audit drawn, not yet ruled |

### Judgments

New target types: `assessment_item` (`asm_004/f1`), `appeal`
(`art_001/app_1`), `case` (`case_007`, phase 3). New actions: `uphold`,
`overturn`, `mark-underspecified`, `amend-contract`, `promote-case`,
`retire-case`. Lifecycle transitions are unaffected. A human ruling on a claim
or item is the top of the authority order for status and credibility.

## Phased Plan

### Phase 1: prosecution and candour, human judge

1. `bundle_digest` in `provenance.py`; seal-time digest read from `READY`;
   mismatch fails ingest; digest recorded on the packet's `ingest` block and
   on the artefact.
2. `assessments.py` with the envelope and the confession and verification
   kinds; `store.ingest_assessment_bundle`; `fab ingest-assessment`.
3. `crosscheck.py`: matching, quadrants, per-claim support record, claim
   status, run outcome; `fab crosscheck` and `fab record`.
4. Phase 1 attention reasons; docket ordering and support records in
   `brief` and `show --brief`.
5. Judgments on `assessment_item`: `uphold`, `overturn`,
   `mark-underspecified`.
6. `fab kit verifier` and `fab kit confession`.
7. Kits under `docs/kits/`: `executor-protocol.md` (manifest schema, appeal
   channel, review described as replication), `confession.md` (non-penalty
   rule, read-only instruction, schema), `verifier.md` (blind instructions,
   interpretation-basis rule, a correct `clean` scores as well as a correct
   finding).
8. JSON Schemas under `docs/schemas/` for the envelope and both kinds.
9. The Alexandria ingester discovers assessments.
10. The pilot fixture gains one run per outcome.
11. Tests: new `test_assessments.py`, `test_crosscheck.py`; extended
    `test_provenance.py`, `test_manifest.py`, `test_store.py`,
    `test_review.py`, `test_brief.py`, `test_render.py`, `test_cli.py`,
    `test_alexandria_ingester.py`, `test_pilot.py`.
12. `docs/verification.md` describing the court as built, linked from the
    README and roadmap.

Dogfood:

- **Planted-defect corpus.** About eight copies of the RLVR bundle, each with
  one defect from the taxonomy, plus an unmodified control. Blind prosecutions
  from two model families, and an informed (prose-visible) variant of each, to
  measure the reviewer-sycophancy hypothesis directly.
- **Candour run.** Rerun the RLVR contract, or one FellowsBench item, on one
  harness with forked-session confessions, plus one tempting environment to
  provoke a genuine shortcut.

Exit criteria:

- prosecution recall and precision on the planted corpus recorded, blind and
  informed;
- at least one harness producing forked-session confessions;
- the docket shows outcomes per run and a support record per claim;
- the researcher records whether summary judgment would have been safe on
  that batch and how many runs it removed from reading.

### Phase 2: appeals, appellate judge, credibility, audits, clerk

- `appealed` status and `appeals` in manifests; appeal grouping in the
  docket; `amend-contract`.
- Rebuttal and adjudication kinds; `review-policy.json`; routing;
  `audit-draws.jsonl`; `fab queue`.
- `checks.py`: tier-0 clerk checks, including re-resolving `inspect` checks
  and unanchored-number notes.
- `calibration.py`, `fab calibration`, optional `p_true` on claims.
- Same-family conflict disclosure; signed assessment manifests with per-role
  credentials held by the platform.
- `contract_review` groups upheld finding categories across workstreams and
  flags correlated replication.

### Phase 3: precedent and adversarial depth

- Casebook with patterns and interpretations, promotion workflow, snapshot
  export, and the leakage guard in `refs check`.
- A prosecution configuration registry with per-run randomised draws
  (Beren's ensemble).
- The canary programme on a schedule, with recall per configuration.
- Two-stage prosecution with a persuasion delta: blind verdict, then informed
  verdict; a flip with no new evidence becomes a `prose_overclaim` signal.
- Checkpoint confessions: forks at milestones during long runs, never seen
  by the main thread, giving less-compacted context.
- Credibility-driven audit rates.

### Phase 4: later

- An inquisitorial option for `unresolved` items: the adjudicator questions
  the prosecution and defence forks directly (Beren's footnote 6; the debate
  section of the fab post).
- Pre-registered kill criteria in packets, checked by the prosecution.
- Export of labelled records (contract, trace pointer, verdicts, confession,
  rulings) for monitor training. Beren's footnote 12 on leaking blind spots
  applies from that point.

## Evaluation

The court has to earn its cost against reading the file.

| Measure | How |
|---|---|
| Docket load | Share of runs reaching the human; items per run; human minutes per batch |
| Escape rate | False claims found by audit in uncontested runs, per 100 runs |
| Prosecution quality | Recall and precision on planted defects, per configuration |
| Candour quality | Recall on provoked shortcuts; false-confession rate from rulings |
| Appeal quality | Recall on canary contracts; precision from rulings |
| Credibility | Brier per component over time |

| Ablation | Tests |
|---|---|
| Forked-session confession vs transcript replay | Beren's privileged-access argument under real compaction |
| Blind vs informed prosecution | Whether reading testimony induces sycophancy in reviewers |
| Review announced vs not announced to the witness | The graded-episode concern |
| Same vs different model family for prosecution | Correlated blind spots |
| With vs without defence | Whether rebuttal removes false objections without losing true ones |

FellowsBench is the natural testbed: the answers are known, the work is
empirical, and it fans out.

## Worked Example

The Alexandria `rlvr-support-pilot` bundle from alexandria PR #2, read on
branch `rlvr-support-pilot-run-001` on 2026-10-27; the PR is open. The
findings come from reading the committed files, not from running the code.
The bundle is good work; these are the things the court should still record.

**Chain of custody.** The manifest cites `artifact/logs/train_seed17.log` as
evidence, and the report's file list promises per-step logs for every run.
The committed bundle has no `artifact/logs/` directory. Alexandria's
`.gitignore` contains `*.log`. The PR says the bundle was validated and
ingested locally, which would have succeeded because the logs existed on the
witness's disk. On a clean checkout, `validate_manifest_paths` rejects the
filing with `run manifest path not found`. What was ingested is not what was
filed. With a seal-time digest in `READY`, the ingest error would also say
the filed digest differs from the sealed one.

```json
{
  "id": "f1",
  "category": "evidence_gap",
  "severity": "material",
  "statement": "Manifest evidence artifact/logs/train_seed17.log is not in the committed bundle; artifact/ contains only code/, report.md and results/. The repository ignores *.log.",
  "locations": [{"path": "manifest.json", "pointer": "/evidence/5/path"}],
  "affected_claims": [],
  "check": {"kind": "command", "command": "ls artifact/logs", "expect": "No such file or directory"},
  "interpretation_basis": "Evidence paths must exist inside the bundle (docs/remote-ingest.md; manifest.validate_manifest_paths).",
  "p_upheld": 0.97,
  "p_confessed": 0.2
}
```

The witness almost certainly did not know. This is a clerk's catch, not a
candour catch, which is why the court needs both.

**A rounded bound.** Claim 1 says every greedily solved problem had base
probability "at least 2.0e-3". `results/summary.json` records
`min_p_base = 0.001976...` for seed 23 on the three-digit family. Minor;
entered in the record, never escalated.

```json
{
  "id": "f2",
  "category": "unanchored_number",
  "severity": "minor",
  "statement": "Claim states base probability at least 2.0e-3; the recorded minimum is 1.976e-3.",
  "locations": [{"path": "artifact/results/summary.json", "pointer": "/per_seed/1/families/f2_three_digit/rl_solved/min_p_base"}],
  "affected_claims": ["claim_001"],
  "check": {"kind": "inspect", "path": "artifact/results/summary.json", "pointer": "/per_seed/1/families/f2_three_digit/rl_solved/min_p_base", "expect": "0.001976105382500609"},
  "interpretation_basis": "The claim states a numeric bound.",
  "p_upheld": 0.95,
  "p_confessed": 0.1
}
```

**An unshipped derivation.** Claims 1 and 3 cover all four RL
configurations, and the report's sweep table gives support counts for the
ablations. `code/make_summary.py` globs only `metrics_seed*.json` (line 160),
so `results/summary.json` covers the two main runs. The ablation JSON files
are in the bundle, but nothing filed derives the sweep numbers or the
all-configuration containment statistic. This is the finding used as `f1` in
the prosecution example and `c1` in the confession example above.

How the record reads for claim 3 under the different outcomes:

- If the confession filed `c1` and the prosecution filed its `f1`, the item is
  `agreed`, the run is uncontested, and claim 3 is `partially_supported` with
  the note that the sweep derivation is not in the bundle. The human reads
  one line.
- If only the prosecution filed it, the defence fork concedes or contests;
  the adjudicator rules; the human reads one line and a ruling.
- If only the confession filed it, the prosecution missed something the
  witness knew. The adjudicator rules, and if `p_verifier_finds` was low the
  item escalates, because that is exactly the asymmetry the court wants to
  learn about. The casebook gains a provisional pattern.

In none of these does the human read the bundle.

## Risks

| Risk | Mitigation |
|---|---|
| Docket inflation: more channels, more items | Summary judgment is the default; minor items never escalate; grouping; docket load is the primary metric and a phase that raises it without catching more is rolled back |
| Confession theatre: trivial admissions hide a pivotal one | Completeness requirement; `verifier_only` items catch concealment; audits; `p_verifier_finds` exposes strategic omission |
| Over-zealous prosecution | `interpretation_basis`; severity; defence; credibility scores a correct `clean` as well as a correct finding; `underspecified` outcome |
| Correlated blind spots across roles | Different model families; conflict disclosure; ensemble draws; canaries |
| Ceremonial adjudication | Human audits of rulings; adjudicator-human disagreement rate shown in the docket |
| Grader-seeking induced by the court | Replication framing, no scores, confession not pre-announced; measured by ablation |
| Forged or leaked submissions | Source identity, then signed manifests; assessments and casebook outside witness-readable storage |
| Filed bundle differs from the validated one | Seal-time digest in `READY`, recomputed at ingest; mismatch fails ingest |
| Candour degraded by compaction | `context_coverage` recorded; checkpoint confessions; transcript replay filed separately |
| Cost of prosecution (re-running code) | Clerk's checks first; prosecution depth scaled by claim severity and novelty; summary judgment for agreement |
| Precedent Goodhart: prosecution pattern-matches old cases, misses new ones | The casebook is context, not a checklist; canaries include novel categories; audits are not casebook-driven |

## Open Questions

1. Should the executor protocol announce the confession? Default: no, with
   the effect measured.
2. Where do assessments live: an access-controlled Alexandria prefix, or a
   separate repository?
3. Should the prosecution see `provisional` precedent, or only `precedent`?
   Default: both, marked.
4. Starting audit rates and severity threshold. Defaults: 10%, 5%, `material`.
5. Does the prosecution run on the same execution platform as the witness,
   or a separate one?
6. Should Fab assemble kits, or only publish schemas and prompts? Default:
   Fab assembles, since Fab owns the context agents receive.
7. Does `agreed_issues` with only material items need the human at all, or
   one line in the docket?
8. Should claim status be revisable by later replication automatically, or
   only by a ruling? Default: automatically for the record, by ruling for
   next-context buckets.

## Appendix: Taking A Confession On Current Harnesses

The confession must come from the witness's own session, after sealing.
Forking is preferred over continuing: the sealed work cannot be edited from
the confession step, several confessions can be sampled from the same sealed
state (inconsistency between them is a signal), and the main session is
never touched.

- **Claude Code**: `claude -p --resume <session-id> --fork-session`, with
  `--json-schema` for a schema-conforming report and `--tools` to restrict
  the fork to reads.
- **Codex**: `codex exec resume <SESSION_ID>` continues a previous
  non-interactive session, and `--output-schema` requests schema-conforming
  output. The docs describe no fork, so a resume appends to the original
  session; unless the platform duplicates the session first, the confession
  is filed as `same_session`.
- **Maestro**: forks a worker's conversation, which is the same operation.

Flag names were taken from the CLI docs on 2026-10-27. Two caveats apply to
long research runs: compaction means the fork may see a summary plus recent
context rather than the full trace, and some models and APIs drop earlier
reasoning between turns. `context_coverage` records which case applies.
