---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

<!-- Vendored from mattpocock/skills (MIT, (c) 2026 Matt Pocock), skills/productivity/grilling,
     fetched 2026-11-26. Two local changes, both marked "FlawChess": fact lookups and the
     write-back to the seed. Re-apply them when updating from upstream. -->

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Word each question so "yes" accepts your recommended answer.

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), find it yourself; don't ask the user for anything you could look up. **FlawChess:** look facts up from the main session. Anything that needs a database (the `flawchess-db`, `flawchess-prod-db`, `flawchess-benchmark-db` or Umami MCP servers) or Sentry must run in the main session, because subagents do not get the project MCP servers. Dispatch a sub-agent with a fresh context window only for a broad read of the code that would flood this context. Don't block on a lookup: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.

**FlawChess: write the result down.** When the session was about a seed in `.planning/seeds/` or a phase in `.planning/phases/`, write the settled decisions into that file once the user confirms: a dated "Settled Decisions" section in the seed, or the locked decisions in the phase's `CONTEXT.md`, each with its reason. Replace the open questions they answer; never start a second document for the same idea. Do this before any `/clear`.
