# Contract: <title>

Contract id: <contract_001>
Version: <1>
Program: <program-name>
Created: <YYYY-MM-DD>

## Research Question

What should this workstream investigate?

## Why It Matters

Why is this question worth spending agent and human attention on?

## Brief

Free-form instructions from the human research manager.

Write whatever context, hunches, uncertainty, taste, or caution seems useful.
The agent is expected to investigate missing background, surface assumptions,
and propose methods rather than only execute a pre-specified plan.

## Programme Shape

Optional. Describe the shape of the research batch Fab should ask an external
agent system to instantiate.

Examples:

- exploration width: 20 workstreams
- include independent replication attempts
- include critique workstreams
- separate exploration from validation
- keep method families diverse
- avoid letting every workstream optimize the same public metric

## Desired Output

What would be useful to receive back?

Examples:

- short research memo
- reproducible experiment
- artefact package with code, configs, logs, data pointers, and provenance
- ranked list of candidate methods
- critique of whether this direction is worth running
- implementation patch
- eval design
- replication attempt

## Attention Boundaries

Optional. This is not an exhaustive list of forbidden shortcuts.

Use this only for things the human already knows should trigger attention, such as:

- ask before spending more than a specified compute or API budget
- ask before training or adapting a model
- ask before publishing or sharing outputs
- ask before changing hidden evaluations
- stop and report if the result depends on private eval leakage

## Context

Optional links or notes:

- relevant KB notes
- papers
- prior artefact packages
- prior human judgments
- code paths
- prior workstreams
- datasets or evals
