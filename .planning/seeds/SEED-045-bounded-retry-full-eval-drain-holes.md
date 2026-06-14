---
id: SEED-045
status: dormant
planted: 2026-06-14
planted_during: v1.26 Full-Game Eval Pipeline (during Phase 118 execution)
trigger_when: next eval-pipeline / eval-drain / analysis-coverage phase, or when users report partially-analyzed games
scope: small (1 phase — service logic + 1 migration + backfill consideration)
---

# SEED-045: Bounded-retry for full-eval drain holes (fix D-116-07 unconditional completion stamp)

## Why This Matters

`app/services/eval_drain.py::_mark_full_evals_completed` stamps `full_evals_completed_at`
**unconditionally**, even when non-terminal plies are engine holes. So a game can be marked
"fully analyzed" while still carrying genuine mid-game eval gaps. With Phase 118 shipping a
user-facing tier-1 "Analyze" button, users now trigger this path directly and see the gaps
(a game they explicitly asked to analyze comes back partially evaluated). "Analyze" should
mean all positions get analyzed.

How holes arise:
- `D-09`: engine error/timeout on a position leaves that row's eval NULL and the drain
  continues.
- Post-move storage (`SEED-044`): row k holds the eval of position k+1, so an engine hole at
  position k+1 leaves row k NULL.
- `D-116-07` then stamps completion unconditionally — deliberately, to avoid a game with a
  permanently-unevaluable ply churning the drain forever.

## Evidence

Dev game **642474** (stamped `full_evals_completed_at` 2026-06-14T10:13 via a tier-1 click) —
132 positions:
- 103 cp-scored (`eval_cp` set) — analyzed
- 23 mate-scored (`eval_cp` NULL, `eval_mate` set) — analyzed (engine reports mate-in-N, not cp)
- 2 terminal holes (plies 130-131) — legitimate (checkmate / after-mate, no eval possible)
- **4 genuine mid-game holes (plies 54, 58, 59, 62)** — ply 59 also has `best_move` NULL (total engine miss)

Holes appeared in *today's* drain run, which points at transient timeout under Stockfish pool
contention — so a retry would very likely fill them.

## Chosen Fix (bounded retry)

Do NOT stamp `full_evals_completed_at` while non-terminal, non-mate holes remain; re-pick the
game up to `MAX_EVAL_ATTEMPTS` (~3); after the cap, stamp complete anyway (accept permanent
holes) + one aggregated Sentry event. Fills transient holes while keeping `D-116-07`'s
infinite-re-pick protection (a deterministically-unevaluable ply can't loop forever).

Define a **hole** = `eval_cp IS NULL AND eval_mate IS NULL AND ply is not the terminal
game-over ply`. Mate-scored plies (`eval_mate` set) and terminal game-over plies are NOT holes.

Implementation notes:
- Per-game attempt counter — `games.full_eval_attempts` SmallInteger + Alembic migration —
  incremented per drain tick when holes remain.
- The full-drain re-pick query gate must include not-yet-exhausted, hole-bearing games.
- Backfill: games ALREADY stamped complete with holes won't be re-picked — needs a one-off
  pass (extend `scripts/backfill_eval.py`) or a sweep to clear `full_evals_completed_at` /
  re-enqueue those games.

## When to Surface

**Trigger:** the next eval-pipeline / eval-drain / analysis-coverage phase, or when users
report partially-analyzed games. Surfaces during `/gsd-new-milestone` when scope matches.

## Scope Estimate

**Small** — one phase: service-logic change in `_mark_full_evals_completed` + the full-drain
re-pick gate, one Alembic migration (`games.full_eval_attempts`), tests, and a backfill
decision for already-stamped games.

## Breadcrumbs

- `app/services/eval_drain.py::_mark_full_evals_completed` (~line 439) — the unconditional stamp (D-116-07)
- `app/services/eval_drain.py::_apply_full_eval_results` (~line 344) — `failed_ply_count` (hole counter) + D-116-07 hole comment (~line 420)
- `app/services/eval_drain.py` ~line 936 — D-09 engine error/timeout skip-row
- `SEED-044` — post-move storage convention (the +1 shift that turns a position-eval hole into a row NULL)
- Game model: `Game.needs_engine_full_evals` / `Game.has_engine_full_evals` (full-eval gates)
- `scripts/backfill_eval.py` — candidate home for the already-stamped-games backfill

## Notes

Surfaced (not caused) by Phase 118's tier-1 "Analyze" button. Phase 118 itself is complete and
verified; this is a pre-existing Phase 116/117 eval-drain design issue, intentionally kept out
of Phase 118 scope. User chose the bounded-retry approach (2026-06-14).
