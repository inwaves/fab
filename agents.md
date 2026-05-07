### Further context on the philosophy behind fab

We are building for a near-future setting, perhaps 6 months out, perhaps 12,
perhaps 18, where agent autonomy is implied. Agents do not stop for interim
feedback and do not need handholding. They do useful work autonomously. Their
contributions are real, in the same way a human researcher's contributions are
real: not necessarily correct, not necessarily useful, but real.

There are hundreds of these agents running in parallel, and later thousands.
They read research briefs, design experiments, run them, and return outputs.
Those outputs come back to humans, who are now the bottleneck to progressing
alignment. There may only be a few hundred human alignment researchers. Assume
they are all working in the same organisation, with access to the same systems,
data, and institutional context.

Fab exists to widen that bottleneck: to let more alignment research
through while keeping the rigour and quality bar high. The bar is high because
errors can be catastrophic. Whatever this system does, it has one goal: help
humans make sense of agent-driven alignment research.

This system is one level up from agent harnessing. It is not about how agents
are executed, what their lifecycle looks like, what platform runs them, or where
they get compute. It is also not a control plane. We do not bank on having to
steer agents into useful work; we mostly assume that they can do useful work.
Later refinements may help encourage diversity and prevent mode collapse, but
Fab does not intervene in individual runs to correct them.

In this framing, the core problem is almost a pure information-flow problem.
There is a research contract. Agents read it, design work, run experiments, and
generate outputs. Those outputs are a data transform over the research
organisation's state of understanding. The ultimate goal is better updating and
eventual consolidation of that understanding.

There are many adjacent literatures we could draw from: agent swarms,
multi-agent systems, high-performance research teams, research management, and
more. We do not need to read all of that to build a good MVP. The MVP should
prove that the information flow is useful to human researchers.
