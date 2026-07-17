---
id: SEED-109
status: dormant
planted: 2026-07-16
planted_during: v2.4 (post Phase 174 execution + verification)
trigger_when: before Phase 176 (Backfill) is planned — this decision changes what 176 backfills; insert as a phase ahead of 176
scope: medium
requirements: GEMS-01, GEMS-02, GEMS-03
related: SEED-108 (this milestone), SEED-054 (best-move PV at flaw ply — created the flaw-ply exemption), SEED-043 (lichess best-move/PV backfill), SEED-023 (two-lane import defer Stockfish)
---

# SEED-109: Full-analyze lichess-eval games and retire the lichess-eval special-case lane

## Why This Matters

Phase 174 delivered backend gem/great detection, but its verification surfaced a
real coverage gap: **lichess-eval games get gem/great coverage only on
flaw-adjacent + hole plies, not on every out-of-book best-move ply** — so
genuine gems on these games are silently missed.

A "lichess-eval game" is `games.lichess_evals_at IS NOT NULL`: a lichess import
that arrived WITH lichess's precomputed `%eval` annotations, so we deliberately
skip the full Stockfish analysis pass and reuse lichess's evals (the SEED-054 /
D-117 optimization). That single-line `%eval` carries no best move, no PV, and
no runner-up — everything gem detection needs. The `eval_drain` local lane
filters `targets` down to holes + flaw-adjacent plies before the candidate
builder runs (`app/services/eval_drain.py:738-745`), so:

- `_contiguous_san_prefix` sees no ply 0 → `find_opening_ply_count` returns
  `book_plies ≈ 0` → the out-of-book gate silently no-ops, and
- non-flaw, non-hole plies never carry a Stockfish `best_move`, so they can't be
  nominated as `played == best` candidates at all.

### Prod scale (measured 2026-07-16)

| Platform | Games | lichess-eval (in the gap) | % of platform |
|---|---|---|---|
| chess.com | 480,392 (67%) | 0 | — |
| lichess | 238,009 (33%) | 43,055 | 18% |
| **All** | 718,406 | **43,055** | **6.0%** |

So ~43k existing prod games (6.0% of all, 18% of lichess) are affected, plus
~6% of new games going forward. (Dev DB shows only 2.8% because dev is 93%
chess.com — do not size this from dev.)

## The Decision (Option C — chosen 2026-07-16)

Rather than a cheap-but-inconsistent heuristic (nominate `played == best` from
the stored per-ply eval delta, then targeted MultiPV-2 for the margin — viable
but a different gem criterion than every other lane), **make lichess games
first-class**:

1. **Going forward:** stop special-casing lichess imports that arrive with
   `%eval`. Run the same full Stockfish analysis pass we run for chess.com /
   non-eval-lichess games, so every game gets uniform best-move + PV + MultiPV-2
   coverage. lichess's `%eval` can still seed/skip where it's genuinely
   equivalent, but it must no longer suppress the best-move pass gem detection
   depends on.
2. **Backfill:** fully analyze the ~43k existing lichess-eval games so their
   gem/great rows are complete (opportunistically, via the tier-4 lottery
   pattern Phase 176 already uses).
3. **Simplification upside:** this lets us delete the lichess-eval special-case
   lane — the `is_lichess_eval_game` `targets` filter, the flaw-ply exemption
   (SEED-054), and the eval-only dedup transplant path all collapse into the one
   full-analysis lane. Net code reduction, not addition.

### Tradeoff being accepted

Full Stockfish on 43k existing games + ~6% more of new games. The remote worker
fleet absorbs this (binding constraints are RAM + DB, not local CPU — see the
`remote_workers_cover_pool` note); at ~8k games/day throughput the one-time
backfill is days, not weeks. We give up the "reuse lichess's free evals" compute
saving (SEED-054) in exchange for uniform, first-class gem/flaw/PV coverage and
a simpler pipeline.

## Scope / Suggested Phase Shape

Insert a phase in v2.4 **before** Phase 176 (its outcome changes what 176
backfills):

- Remove the `lichess_evals_at IS NOT NULL` suppression from the full-drain /
  entry-ply scheduling so lichess-eval games enter the normal Stockfish pass.
- Decide the fate of stored `lichess_evals_at` evals (keep as a display/seed
  source vs. overwrite with our own) — reconcile with the eval-provenance rules
  (SEED-087 / SEED-089 / SEED-090).
- Retire the special-case lane: `eval_drain.py` `targets` filter + flaw-ply
  exemption + eval-only dedup transplant; keep the tests that guard the
  invariants they protected.
- Backfill 43k lichess-eval games (tier-4 lottery, opportunistic — the Phase 176
  mechanism).
- Re-run Phase 174's verification: the "every newly analyzed game stores a
  candidate row for each out-of-book ply" truth should now hold for all lanes.

## Breadcrumbs

- `app/services/eval_drain.py:738-745` — the `is_lichess_eval_game` `targets`
  filter that starves the builder.
- `app/services/eval_drain.py:161-181, 986-1071` — `lichess_evals_at IS NULL`
  scoping across the drain (tier-3 lottery, entry-ply).
- `app/services/eval_apply.py:1724-1744` — `_contiguous_san_prefix` (the
  book_plies collapse symptom).
- `app/services/eval_apply.py:1786-1799` — candidate gate requiring an
  `engine_result_map` best_uci lichess plies lack.
- `.planning/phases/174-backend-maia-inference-best-move-storage-spike-gated/174-VERIFICATION.md`
  — the gap finding (Truth 2) and CR-01/WR-02 in `174-REVIEW.md`.
- `.planning/seeds/closed/SEED-054-best-move-pv-at-flaw-ply.md` — the flaw-ply
  exemption this seed would retire.
