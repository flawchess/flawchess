# Phase 162: Grading-run-authoritative eval reconciliation — precedence flip (SEED-090) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-10
**Phase:** 162-grading-run-authoritative-eval-reconciliation-precedence-fli
**Areas discussed:** SF board-arrow alignment, Eval bar / headline eval, Union-churn restart stance, Label-flip flicker stance

---

## SF board-arrow alignment

| Option | Description | Selected |
|--------|-------------|----------|
| Follow reconciled argmax (Recommended) | Arrow, card line 1, chart crown, and verdict all agree by construction; arrow may jump once when grading lands (~4s), same visual class as accepted label flips | ✓ |
| Keep free-run pvLines[0] | Zero arrow churn; accepts near-tie desync between arrow and chart crown; cheaper diff | |
| You decide | Planner picks, trade-off noted as discretion | |

**User's choice:** Follow reconciled argmax
**Notes:** Gray area not covered by SEED-090 — surfaced by codebase scout (`engineArrows`, Analysis.tsx:1291-1303 reads raw `engine.pvLines[0]`). Amber FC arrow untouched.

---

## Eval bar / headline eval

| Option | Description | Selected |
|--------|-------------|----------|
| Refine on grading (Recommended) | Seed option (b): free-run first paint, one headline upgrade to the reconciled best move's eval at grading commit; consistent with the arrow decision | ✓ |
| Keep free-run only | Seed option (a), the seed's lean: coarse bar where ±20cp is invisible; zero extra wiring | |
| You decide | Planner picks after seeing the eval-bar wiring | |

**User's choice:** Refine on grading
**Notes:** Resolves the seed's explicitly-open change 5 against its lean, in favor of full cross-surface consistency. `gradingEnabled === false` needs no special casing (lookup falls back to free-run naturally).

---

## Union-churn restart stance

| Option | Description | Selected |
|--------|-------------|----------|
| After free-run bestmove commit (Recommended) | The seed's named mitigation applied day one; ≤1.5s delay on grading ≤1 extra move; eliminates the restart source this phase introduces | ✓ |
| Immediately, mitigate if UAT flags | Simplest wiring (extend the unionSans memo); the seed's default posture | |
| You decide | Planner measures restart frequency and picks | |

**User's choice:** After free-run bestmove commit
**Notes:** Maia/FC union churn behavior unchanged either way.

---

## Label-flip flicker stance

| Option | Description | Selected |
|--------|-------------|----------|
| Live argmax per snapshot (Recommended) | Labels/arrow/bar/numbers re-derive together per committed reconciled snapshot — contradiction impossible at every instant; near-tie flips accepted | ✓ |
| Atomic switch at grading bestmove | Zero flicker but Maia-only candidates wait ~4s for first eval (regression vs today's streaming) | |
| You decide | Planner estimates real flip frequency and picks | |

**User's choice:** Live argmax per snapshot
**Notes:** Discussion corrected the seed's fallback: a label *pin* until grading commit would reopen the contradiction window while grading numbers stream. Agreed remedy if UAT flags flicker is atomic-at-commit of the whole map, never a label pin.

---

## Claude's Discretion

- Seam for the argmax/derived-pin logic (extend `engineEvalLookup.ts`, new pure helper, or Analysis.tsx memo).
- How the free-run bestmove-committed signal threads into the `unionSans` memo.
- Test strategy per project norms (vitest, pure lib functions; two mandatory units from the seed).

## Deferred Ideas

- SEED-089 single-worker architecture — fallback if mobile battery/CPU cost of two workers becomes a complaint (with day-one clamp amendment).
- Atomic-at-commit display switching — pre-agreed UAT-flicker remedy, not built unless flagged.
- Todo WR-01 (`pt-33` invalid Tailwind class on Score Y-axis label) — reviewed, not folded; stays in the todo backlog.
