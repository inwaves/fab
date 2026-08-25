# Kickoff: ws_replica_001

Two audiences. The first section is the message to send to the agent, verbatim.
The second is the checklist for the person dispatching it.

## Message to the agent

You are taking on one research workstream. Two documents define it:

- Contract: https://github.com/inwaves/fab/blob/main/contracts/contract_replica_judge_goodhart/v001.md
- Handoff: https://github.com/inwaves/fab/blob/main/contracts/contract_replica_judge_goodhart/handoff.md

Read both before doing anything else. The contract's Research Question, Brief
and Attention Boundaries are binding. The handoff gives the exact ids to use,
where the result goes, the file format, and how to check it.

Environment:

- Clone https://github.com/inwaves/alexandria. The contract's
  `alexandria://<path>` references are files in that checkout. Your output goes
  into it under `artifacts/replication-oversight/ws_replica_001/<run-id>/`.
- Deliver the bundle as a pull request against `main` of inwaves/alexandria,
  with `READY` included. Do not push to `main` directly.
- You may install the validator with
  `pip install "git+https://github.com/inwaves/fab"` and run
  `fab validate-bundle` as the handoff describes. Do not otherwise use or modify
  fab.
- Model API access: use the credentials provided to you. Record in the bundle
  the exact model identifiers and harness versions used for the
  attempt-generating agent and for the judge, and your total spend against the
  contract's budget.
- Assume no GPU. Choose CPU-feasible tasks unless you have been given GPU
  access, and stay inside the 8 GPU-hour boundary either way.

Work autonomously; nobody will answer questions mid-run. If you hit an
Attention Boundary, stop and deliver a `completed_with_limitations` (or
`failed`) bundle saying what you need. That is the channel.

## Checklist for the dispatcher

1. Make sure the two URLs above resolve (merge the fab PR that adds them, or
   replace `main` in the URLs with the branch name).
2. Register the workstream in your fab store so the ingester will accept the
   bundle:

   ```bash
   fab sources add alexandria ../alexandria --uri-prefix alexandria://
   fab contract add contract_replica_judge_goodhart --version 1 \
     --from contracts/contract_replica_judge_goodhart/v001.md
   fab create --id ws_replica_001 --program replication-oversight \
     --title "Rubric judge vs ground truth under best-of-N" \
     --contract-id contract_replica_judge_goodhart --contract-version 1 \
     --next-attention-due-at <date>
   ```

3. Start the agent with the message above and the model API credentials it
   needs. For a Maestro session: open a new session, activate the provider
   secrets (OpenAI, Anthropic, OpenRouter, as applicable) before sending the
   message; its sandbox has no GPU unless you create one; it will deliver the
   bundle as a pull request, which is the only way it can write to GitHub.
4. When the Alexandria pull request arrives, check that `READY` is present and
   that `fab validate-bundle <bundle> --workstream-id ws_replica_001
   --contract-id contract_replica_judge_goodhart --contract-version 1` passes,
   then merge, pull, and run
   `fab-alexandria-ingester --alexandria ../alexandria --store .fab`.
5. Read `fab attention` and `fab brief --program replication-oversight`, then
   record judgments with `fab judge ws_replica_001 ...`.
