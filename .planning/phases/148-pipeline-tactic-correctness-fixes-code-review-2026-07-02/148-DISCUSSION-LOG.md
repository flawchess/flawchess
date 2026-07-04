# Phase 148: Pipeline & tactic correctness fixes (code-review 2026-07-02) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-04
**Phase:** 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02
**Areas discussed:** Item 4 mate fallback, Item 3 stats depth, Item 5 scoping depth, Plan structure (all delegated to Claude)

---

The phase is fully specified by the source todo
(`2026-07-03-code-review-pipeline-tactic-correctness-phase.md`) and its triage note,
which prescribe the fix strategy and file:line anchors for all five items. Four genuine
forks were surfaced; the user selected **"I'll leave the decisions to you"** for all of
them. Resolutions below.

## Item 4 — tactic mate fallback (recall vs precision)

| Option | Description | Selected |
|--------|-------------|----------|
| Tag generic `mate` | Recall-favoring; todo default. Truncated forced-mate PVs still tag | ✓ |
| Suppress | Precision-favoring; skip the tag when the capped PV doesn't checkmate | |

**Resolution:** Tag generic `mate`. `has_forced_mate` derives from a real engine mate
score, so a truncated PV is a genuine mate, not a false positive — suppressing loses a
real tag. Skip geometry-dependent subtypes on truncated lines. Re-run the precision gate.

## Item 3 — quintile significance stats depth

| Option | Description | Selected |
|--------|-------------|----------|
| Covariance-correction term | Cheap, point estimates unchanged, reuses existing test; todo default | ✓ |
| Full paired test | Larger rewrite of the overlap handling for the same corrected verdict | |

**Resolution:** Covariance term. Least invasive, reuses `compute_score_difference_test`.

## Item 5 — entry-submit scoping depth

| Option | Description | Selected |
|--------|-------------|----------|
| Minimum guard | One-line `entry_eval_lease_expiry > now()`; todo default | ✓ |
| Full echoed-ids | Return claimed `game_ids` from `/entry-lease`, stamp only intersection | |

**Resolution:** Minimum guard. Operator-error-triggered, low real-world likelihood; the
full version is captured as a deferred idea.

## Plan structure

| Option | Description | Selected |
|--------|-------------|----------|
| Split by subsystem | Cohesive per-subsystem plans, each with its own test + verify | ✓ (recommended) |
| Single plan | All five fixes in one plan | |

**Resolution:** Recommend subsystem split (tactics / eval-lease / stats / import);
final decomposition is the planner's call. Every item gets its own test + verify loop.

---

## Claude's Discretion

- All four forks above (user delegated).
- Exact test fixture selection and precise covariance algebra, within the CONTEXT.md
  decisions and the todo's verification notes.

## Deferred Ideas

- Item 5 full echoed-`game_ids` scoping (seed candidate).
- SEED-077 (import-time aggregation columns), SEED-078 (chess.com archive streaming) —
  deferred in the triage, not this phase.
