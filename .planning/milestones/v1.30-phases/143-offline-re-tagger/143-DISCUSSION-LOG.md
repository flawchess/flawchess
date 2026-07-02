# Phase 143: Offline Re-tagger - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-30
**Phase:** 143-offline-re-tagger
**Areas discussed:** Script strategy, Gate integration, Margin threading, Delta report

---

## Script strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Extend backfill_tactic_tags.py | Add gate mode + --margin to the existing script; one script, one code path | ✓ (Claude's recommendation, accepted) |
| New retag_flaws.py, shared module | Extract paging/worker/UPDATE engine into a module, build retag on top | |
| New retag_flaws.py, copy patterns | Standalone script borrowing patterns without sharing code | |

**User's choice:** Deferred to Claude ("Which option do you recommend?"). Recommended **extend +
`git mv` to `scripts/retag_flaws.py`**.
**Notes:** Once the gate goes live (Gate integration decision), backfill_tactic_tags.py's own
detector-refresh purpose also requires the blobs + gate, so the two tools are the same operation —
no coherent gate-free refresh tool remains to keep separate. `git mv` preserves history and gives
the roadmap-required name. User's prompt explicitly steered toward reusing the optimized script.

---

## Gate integration

| Option | Description | Selected |
|--------|-------------|----------|
| Offline-only until 145 | Shared gate helper called only by the re-tagger; live path gate-free until rollout | |
| Wire into live path now | Gate goes into the live classify path in 143; strongest single-path guarantee | ✓ |

**User's choice:** Wire into live path now.
**Notes:** Claude flagged that new games get gated at the provisional 0.35 margin before Phase 144
validates it. Accepted because Phase 145's corpus retag re-applies the final committed margin to
every flaw (including the 143→145 window), so it self-heals; only the constant changes, not the
wiring.

---

## Margin threading

| Option | Description | Selected |
|--------|-------------|----------|
| Parameterize gate functions | Add a margin param to apply_forcing_line_filter / is_solver_node_forced | ✓ |
| Set module constant at runtime | Re-tagger overrides the module global before the run | |

**User's choice:** Parameterize gate functions.
**Notes:** Worker-pool-safe (spawn workers re-import; a global override would have to be re-set per
worker), clean, testable. Committed constant stays the live default.

---

## Delta report

| Option | Description | Selected |
|--------|-------------|----------|
| Committed reports/ markdown | Timestamped per-motif removed/survived report, re-runnable, feeds 144 | ✓ |
| Stdout summary only | Print the delta table at end of run; not persisted | |

**User's choice:** Committed reports/ markdown.
**Notes:** Follows the benchmarks / db-report convention; regenerable on a --margin sweep.

---

## Claude's Discretion

- Exact CLI flag names beyond the locked set; combined-classify helper signature and location;
  report file path/format; blob-loading query shape; worker-payload shape for blobs across the
  process boundary.

## Deferred Ideas

- User-28 A/B diff + final margin commit — Phase 144.
- backfill_multipv.py --db prod + retag corpus rollout + chip-count monitoring — Phase 145.
- Solver-only blob storage optimization — locked to every-node storage in 141 D-03.

## Scope finding (not a deferral)

- GATE-03 (mate-priority) and GATE-04 (defender) logic + core tests were already implemented in
  Phase 141 (test docstring: "D-01 pulled forward from Phase 143"). Phase 143's GATE work is
  audit-and-fill against exact SC wording, notably a multi-ply branch-then-reconverge case.
