# Phase 141: JSONB Schema + Gate Logic - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-29
**Phase:** 141-jsonb-schema-gate-logic
**Areas discussed:** Mate handling scope, JSONB leak prevention, JSONB blob node coverage

This phase was already heavily pre-decided by the `/gsd-explore` design note
(`notes/tactic-forcing-line-gate.md`), the research SUMMARY, and the roadmap success criteria.
Locked-by-note items (inline JSONB columns, blob shape, constants, solver-only uniqueness,
`llm_log.py` pattern) were carried forward, not re-asked. Only the genuinely open implementation
decisions were discussed.

---

## Mate handling scope (141 vs 143 boundary)

| Option | Description | Selected |
|--------|-------------|----------|
| Full mate hierarchy now | Gate module implements complete mate-priority logic in 141; Phase 143 just calls it | ✓ |
| Margin + mate-in-1 only | 141 gate does win-prob margin + simple escape hatches; full hierarchy built in Phase 143 | |

**User's choice:** Full mate hierarchy now
**Notes:** Keeps all gate math in one independently-unit-testable module. Phase 143's mate-test
success criterion becomes verification-via-re-tagger rather than a second implementation.

---

## JSONB leak prevention (STORE-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Mapper-level `deferred()` | `deferred=True` on both columns; never load on `select(GameFlaw)` unless undeferred | ✓ |
| Explicit per-site projections | Rewrite all 5 query sites to explicit column lists | |
| Both (defer + audit) | `deferred=True` structural guarantee + audit the 5 sites + regression test | ✓ (final form) |

**User's choice:** Mapper-level `deferred()` — user asked for clarification on what it meant, then
delegated the final call ("I trust you to pick the best solution here").
**Notes:** Settled on `deferred=True` as the primary mechanism PLUS an audit of all 5
`select(GameFlaw)` sites and a regression test (belt-and-suspenders). Flagged the SC-wording
nuance: roadmap SC #4 literally says "explicit column projections," but `deferred=True` satisfies
the intent more robustly; verifier should accept defer+audit. Async caveat noted: implicit access
of a deferred attr raises `MissingGreenlet` (fail-loud).

---

## JSONB blob node coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Every node (note's rec) | MultiPV=2 entry at every node along the line; max flexibility | ✓ |
| Solver nodes only | Entries only at solver nodes; halves cost, no defender data | |

**User's choice:** Every node (delegated to Claude; aligns with the design note's recommendation)
**Notes:** 141 only fixes the blob's index semantics (entry per ply); the actual fill is Phase 142.
Solver-only is captured as a deferred later optimization.

---

## Claude's Discretion

- Final JSONB leak strategy (defer + audit + regression test) — user delegated.
- Node-coverage choice — user delegated; followed the design note.
- Exact function/type signatures in `forcing_line_gate.py`, Alembic migration boilerplate, and the
  precise form of the regression test.

## Deferred Ideas

- Solver-only blob storage (cost optimization) — later.
- `game_flaw_pv_lines` sidecar table — fallback if `game_flaws` must stay narrow.
- Phases 142–145 work (engine pass, re-tagger, A/B validation, backfill/rollout).
- Tablebase (Syzygy) uniqueness signal — v2 (GATEX-04), out of scope.
