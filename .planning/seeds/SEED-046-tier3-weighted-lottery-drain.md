---
id: SEED-046
status: promoted (→ Phase 119, v1.26, 2026-06-14)
planted: 2026-06-14
planted_during: v1.26 Full-Game Eval Pipeline (during Phase 118 execution)
trigger_when: after Phase 118 ships and the strict-recency tier-3 drain is observed in prod, or when users report no analysis progress after returning from an absence
scope: small (1 phase — service logic in _claim_tier3_derived + 1 partial-index migration)
---

# SEED-046: Recency-weighted lottery for tier-3 drain (replace winner-take-all last_activity ordering)

## Why This Matters

Phase 118's tier-3 idle drain orders the entire backlog by `users.last_activity DESC` as the
top key (`D-118-04`). This is **winner-take-all**: the single most-recently-active user's games
drain first, completely, before anyone else moves. Two problems:

- **Starvation is worse than "absent users wait."** If user A was active 2 days ago and user B
  1 day ago, *all* of A's games sit behind *all* of B's backlog. B may have thousands of games,
  so A gets zero until B is fully drained — even though A is "more recent than most."
- **Returning users see no momentum.** The goal is: a user comes back, browses, and the
  progress badge ticks at a decent pace. Winner-take-all only delivers that if they happen to be
  the single most-recent user.

Since **every user has a backlog**, this contention is real and continuous, not a corner case.

## Chosen Approach (option A — recency-weighted lottery)

Replace the strict `last_activity DESC` top key with a **weighted lottery over users**:

1. **Pick the user weighted by recency**, then **pick that user's best game** by the existing
   secondary order (TC bucket → `played_at DESC` → eval-need). Weighting the *user* (not the
   game) is essential — per-game weighting lets a user with 5000 games drown out a user with 50
   at the same recency. We want per-user share ∝ recency regardless of backlog size.
2. **Candidate users = `needs_engine_full_evals`** (`full_evals_completed_at IS NULL AND
   lichess_evals_at IS NULL`, see `app/models/game.py:223-238`), NOT all `full_evals_completed_at
   IS NULL`. Reuses the existing hybrid_property, which is documented as retained "for the planned
   per-user 'analyze my games' enqueue mode, which needs exactly this set." PV-backfill-only games
   (lichess %eval games needing only best-move/PV) are excluded from the lottery — see residual
   tier below.
3. **One-query weighted sampling** via Efraimidis–Spirakis:
   `ORDER BY -ln(random()) / weight LIMIT 1` over the distinct candidate users. Stateless, fits
   the current derived-SELECT model (no scheduler state, no eval_jobs row).
4. **Weight = decay(last_activity) + floor.** Exponential decay (`exp(-Δt / τ)`, half-life
   τ ≈ 1 day) plus a small floor so old/absent users never hit exactly zero. Single tunable knob.

### Honest framing (don't over-promise goal #1)

With universal backlog, a 20% "fairness slice" split across hundreds of absent users is ~0.1%
each — effectively invisible *while a user is away*. The real win is the **return-bumps-you-to-front**
mechanic: the moment a user browses, `last_activity` updates to ~now, so they immediately leap
near the front of the weighted lottery and the badge ticks briskly *within minutes of returning*.
Design and copy should promise "fast catch-up on return," not "lots done while you slept."

### PV-backfill as a residual tier

PV-backfill-only games (`full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL`) fall
*outside* the weighted user lottery. Drain them as a **residual fallback**: only when the weighted
engine lottery finds no candidate, keeping the existing `lichess_evals_at IS NOT NULL` deprioritization.

## Open Question (see research/questions.md)

Perf: the lottery runs over `SELECT DISTINCT user_id FROM games WHERE full_evals_completed_at IS
NULL AND lichess_evals_at IS NULL` each claim (~every 10s). On a large `games` table this wants a
**partial index** to stay cheap; verify the DISTINCT-users + ES pick stays sub-100ms per claim at
prod scale. That's the main implementation risk, not the lottery math.

## When to Surface

**Trigger:** after Phase 118 ships and the strict-recency drain is observed in prod (so the
weight curve / τ / floor are tuned against real `last_activity` distributions), or when users
report no progress after returning from an absence. Surfaces during `/gsd-new-milestone` when
scope matches.

## Scope Estimate

**Small** — one phase: rework the top-key ordering in `_claim_tier3_derived` into a
user-weighted lottery + game pick, add the PV-backfill residual fallback, one Alembic migration
(partial index on `(full_evals_completed_at, lichess_evals_at) WHERE both NULL`), tests, and a
prod-tuning pass on τ / floor.

## Breadcrumbs

- `app/services/eval_queue_service.py:185-241` — `_claim_tier3_derived`, the strict `last_activity
  DESC` top key (D-118-04) to be replaced by the weighted lottery
- `app/models/game.py:223-238` — `needs_engine_full_evals` hybrid_property = the lottery candidate
  predicate
- `app/services/eval_drain.py` — drain loop / tick that calls `claim_eval_job` (batch size, idle sleep)
- `SEED-043` — lichess best-move/PV backfill (the residual-tier work)
- Efraimidis–Spirakis weighted reservoir sampling: `ORDER BY -ln(random()) / weight LIMIT 1`

## Notes

Explored 2026-06-14 (`/gsd-explore`). User chose option A (weighted lottery) over option B
(reserved fairness slice). Phase 118 is not yet in prod; this is deliberately a follow-up so the
weighting is tuned against observed `last_activity` distributions rather than guessed.
