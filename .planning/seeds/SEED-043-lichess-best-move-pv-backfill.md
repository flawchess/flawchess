---
id: SEED-043
status: dormant
planted: 2026-06-13
planted_during: v1.26 Full-Game Eval Pipeline (Phase 117 deployed)
trigger_when: when the engine-best-move step-through display or SEED-039 tactic-motif tagging is about to ship and needs best_move/PV coverage on lichess games
scope: medium
---

# SEED-043: Lichess games lack engine best_move/PV — decide whether to bulk-reprocess

## Why This Matters

Phase 117 (deployed prod 2026-06-13, server `f38a3fce`) added per-position `best_move`
(UCI) + flaw-adjacent `pv` + auto-`classify_game_flaws` to the full-eval drain. Per
**D-117-12** the policy is **demand-driven backfill** (no mass re-enqueue) — but the
re-touch paths meant to backfill old games are **Phase 118** (not built yet). So right
after deploy, every pre-117 fully-analyzed game showed evals-but-no-flaws-and-no-best_move
(user aimfeld80 / user 28 hit this on chess.com games).

**16,861 lichess games** (`lichess_evals_at IS NOT NULL AND full_pv_completed_at IS NULL`)
still lack engine `best_move`/`pv`. They already have evals (lichess %eval) + flaws
(Phase 108 materialization + oracle counts), so the **Library flaw display works for
them** — but the future **engine-best-move step-through display** (D-117-01) and
**SEED-039 motif PVs** will have no data on lichess games until they're engine-reprocessed.

## Already handled (chess.com slice — NOT this seed)

On 2026-06-13 the **4,185** non-guest engine/chess.com games that Phase 116 fully eval'd
but that missed the 117 PV/flaw pass were manually re-enqueued:

```sql
UPDATE games SET full_evals_completed_at = NULL
WHERE full_evals_completed_at IS NOT NULL
  AND full_pv_completed_at IS NULL
  AND lichess_evals_at IS NULL
  AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = games.user_id AND u.is_guest);
```

The tier-3 derived drain (`full_evals_completed_at IS NULL AND NOT is_guest`,
`eval_queue_service.py:204-205`) re-picks them and re-runs the engine →
`best_move` + `pv` + flaws + oracle counts, reprocessing progressively via
round-robin/TC-weighted ordering over days. `still_stranded` for that set = 0.
(One-off `scripts/_reenqueue_117_pv_backfill.py` was used and deleted, not committed.)

## When to Surface

**Trigger:** when the engine-best-move step-through display (Phase 118+) or SEED-039
tactic-motif tagging is about to ship and needs `best_move`/`pv` coverage on **lichess**
games.

Options at that point:
- **(a) Bulk re-enqueue lichess games** — same UPDATE but `lichess_evals_at IS NOT NULL`.
  ~16.8k games ≈ ~2 days pool time. MUST preserve the lichess %eval (T-78-17 /
  D-116-04 preserve gate keeps `eval_cp` because `lichess_evals_at IS NOT NULL`) while
  still capturing `best_move`/`pv` from the same search.
- **(b) Demand-driven (recommended default)** — let Phase 118's per-user on-demand
  re-touch (explicit "analyze" / auto-window) cover only games users actually open.
  Cheaper, lazy, no big batch.
- **(c) best_move/PV-only pass** — would avoid the redundant eval recompute, but not
  currently possible: `engine.analyse()` returns eval + PV together; there's no
  PV-only mode.

**Recommendation:** (b) demand-driven unless a shipping feature needs full lichess
coverage up front.

## Broader gap (Phase 118 must account for)

The 117→118 window has **no automatic re-touch path**, so any game fully-analyzed under
Phase 116 (pre-117) is stranded (evals, no flaws/best_move) until 118 ships or a manual
re-enqueue. The chess.com slice is handled; **Phase 118 should explicitly cover
backfilling the rest**, or run a one-time global re-enqueue once 118's classify+PV path
is confirmed. Going forward, NEW games drained post-117 get the full treatment — no new
stranded games are created.

## Scope Estimate

**Medium.** Option (a) is operationally tiny (one UPDATE) but ~2 days of pool compute +
a soak to confirm lichess %eval preservation. Option (b) is mostly Phase 118 UX work it
already owns. The decision itself is small; the compute commitment is the real cost.

## Breadcrumbs

- `app/services/eval_drain.py` — full-ply drain, `_classify_and_fill_oracle`,
  `_mark_full_pv_completed`, WR-02/D-116-04 repoint onto `lichess_evals_at`.
- `app/services/eval_queue_service.py:204-205` — tier-3 derived pick predicate.
- `app/models/game.py` — `full_evals_completed_at`, `full_pv_completed_at`,
  `lichess_evals_at`, `is_analyzed` hybrid.
- `.planning/phases/117-priority-queue-flaw-integration/117-CONTEXT.md` — D-117-01/02/12.
- [[SEED-039-tactic-family-cause-of-error-flaw-tags]] — consumes the flaw-adjacent PV.
- `.planning/REQUIREMENTS.md` — EVAL-04 (best_move-for-all + flaw PV), Phase 118 EVUX-*.

## Notes

Diagnosed live in prod while monitoring the Phase 117 deploy (2026-06-13). The chess.com
re-enqueue was approved and executed; the lichess decision was deliberately deferred as
this seed.
