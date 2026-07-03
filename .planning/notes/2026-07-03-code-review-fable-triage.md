---
title: Code-review (fable 2026-07-02) triage — what to fix now vs defer, and why
date: 2026-07-03
context: /gsd-explore session routing reports/code-review-fable-2026-07-02.md
---

# Code-review triage — 2026-07-02 fable report

Decision record from the `/gsd-explore` session that triaged
`reports/code-review-fable-2026-07-02.md`. The report is high quality, but a chunk of its
"High" severity is **leverage/headroom** ranking, not **broken-now** ranking. We did NOT
adopt "implement all High + Medium-High" wholesale.

## Severity discrepancies to know (table vs. section)

Two items are **High** in their detail section but **Medium** in the ranked summary table:

- **1.2 SECRET_KEY fail-closed** — section `(High, latent)`, table row #9 says Medium.
- **5.1 quintile significance test anti-conservative** — section `(High)`, table row #10
  buries it in a Medium "stats fixes" bundle. This one flips user-visible significance
  verdicts (p≈0.048 reported vs p≈0.16 true), so it's a live wrong-output bug.

## Grounding: prod is healthy

Prod baseline (`reports/db-stats/db-report-prod-2026-07-02.md`): 12 GB, 686k games, cache
hit 99.86%, **no recurring query above ~300 ms**, both data-integrity checks PASS. That's
why the big performance items are headroom, not current pain.

## Decision — three tiers

**Fix now — trivial security/ops hardening** → `/gsd-quick` batch
(todo `2026-07-03-code-review-security-ops-hardening-batch.md`):
- #1 unauthenticated `GET /api/imports/{job_id}` + sanitize `error` (live IDOR + raw
  `str(exc)` leak to anon clients)
- #3 `ix_game_flaws_blob_backfill` autogenerate-ignorelist line + restore 4 missing dev
  indexes + existence assertion (**time-bomb**: next autogenerate drops the 348M-scan index)
- #1.2 SECRET_KEY startup guard (latent, trivial)
- #11 worker eval bound-validation (Pydantic Field bounds; stops retry-loop holes)
- `ANALYZE opening_position_eval` (stats 28× off)

**Fix soon — pipeline & tactics correctness** → next-milestone phase
(todo `2026-07-03-code-review-pipeline-tactic-correctness-phase.md`):
- #4 tactic prod defects (`has_forced_mate` no-op → deep mates never tag; `fen_map` loses
  ep/castling → corrupt motif geometry) — **live wrong output today**
- #2 entry-drain all-fail circuit breaker (WR-05 mirror)
- 5.1 quintile covariance term (paired-cohort variance)
- 2.7 per-game try/except so one malformed platform game can't abort the whole import
- (cheap add) #6 one-line `entry_eval_lease_expiry > now()` guard

**Defer — real debt, but we have headroom** → seeds:
- #5 per-request `game_positions` aggregation elimination → **SEED-077** (whole phase:
  migration + backfill + multi-repo rewrite; report itself says "won't survive 10× growth",
  nothing >300 ms today)
- #7 chess.com archive streaming → **SEED-078** (ties to OOM history, but that cause was
  already traced/mitigated per prod config; revisit if OOMs recur)

## Explicitly NOT scheduled now
#8 to_thread offloading, #12/#13 schema/poller hardening, #15 frontend code-splitting,
#14/6.2.1 tactic recall (trapped-piece empty-escape is the one positive-sum recall gain —
capture separately if a tactics-recall milestone opens).

## Why push back on #5
It's the biggest effort item and the least urgent by the report's own prod data. The 135 s
incident it cites (quick-260617-pu4) already happened and was mitigated. Doing the durable
import-time-columns rewrite now buys headroom we already have — premature.
