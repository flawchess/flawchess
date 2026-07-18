# Phase 177 — D-07 Post-Deploy Measurement

**Recorded:** 2026-07-17 ~18:00–18:35 UTC (deploy `3efc7172` live ~17:45 UTC; local worker upgraded to v2 and restarted 17:41 UTC)
**Baseline:** SEED-111 "Measured baseline (2026-07-17)" (pre-shift, 4 v1 worker hosts)
**Instruments:** read-only prod DB (tunnel), live backend access logs (<1h window only), 60s `/proc`-tick CPU samples (local box + server), Sentry source tags.

## Headline caveat: partial rollout

Only the local box (194.191.211.24, 8 engines, `--worker-id ai-slim`) is actually running the v2 script. **All three Hetzner workers (88.198.44.252, 88.198.19.214, 95.217.146.94) are still v1** — wire-verified: their `/atomic-lease` calls carry no `worker_schema_version` param, so the server's v2 gate 204s them off the whole atomic lane (by design). They poll all rungs continuously and do ~nothing. The figures below are therefore a **1-of-4-host** measurement; they still confirm the shift's mechanism, but server-pool relief is understated and fleet throughput is not yet at its ceiling. Re-measure after the Hetzner hosts pull the new `scripts/remote_eval_worker.py` and restart.

## Before/after table

| # | Metric | Baseline (pre-shift) | Post-deploy (partial rollout) | Verdict |
|---|--------|----------------------|-------------------------------|---------|
| 1 | games/h stamped (`best_moves_completed_at` growth) | ~550/h | **600/h** (60-min window); 691/h pace over the last 25 min | ↑ ~9–26% with only 1 of 4 hosts contributing |
| 2 | Worker submits/h | 629/h fleet (local box 370/h; Hetzner 104/83/72) | Local box **~380–600/h** (159 submits/25 min; 101/10 min in a hot window); Hetzner ~0 (v1-gated) | Local box alone ≈ old 4-host fleet total |
| 3 | Server pool utilization | 8 engines ~92% busy | **~71.6%** mean over 60s (per-engine 69–73%) | ↓ ~20 pts; still elevated because the in-process drain is covering the work the gated Hetzner hosts no longer take; expect a further drop post-full-rollout |
| 4 | Local worker engine busy % (60s) | ~68% | **90.5%** (aggregate ticks across engine churn, 8 engines) | Near the ~95% target; submit round-trip idle largely eliminated |
| 5 | worker-submit-fallback count (Sentry `source='worker-submit-fallback'`) | expect ~zero | **0 events** | ~zero, with instrument caveat below |
| 6 | Double-claim rate | ~12%/h | **Not measurable this window** (see below) | D-08: **defer** TTL-lease escalation |

## Verdicts and caveats

### Fallback verdict (D-06 regression signal): ~zero, watch

No Sentry events tagged `source='worker-submit-fallback'` since deploy. Instrument caveat: the shipped instrumentation (`_build_best_move_candidates`) applies `set_tag`/`set_context` when the fallback branch fires but does not `capture_message` — so Sentry only counts fallbacks that *error*; a successful silent fallback is invisible. Structurally, a v2 worker computes second-best for every candidate ply it identifies with the same rule the server uses, so submit-path fallbacks should genuinely be ~zero. One anomaly flagged for watch: a single `POST /atomic-submit` **422** from the upgraded local box (~18:00 UTC), likely a stale lease from before the worker restart hitting the tamper guard; one occurrence in ~50 min of observation, not sustained. Investigate only if it recurs.

### Double-claim / D-08 recommendation: defer

The baseline ~12%/h figure came from cross-host worker-log correlation (duplicate `Atomic-leased game_id=` lines). With effectively one active worker host this window, cross-host double-claims cannot occur, and the remaining claimant pair (local box vs server drain) is not observable from access logs (no game_id) or the DB (submits are idempotent upserts, no counter). **Recommendation: defer TTL-lease escalation (D-08)**; re-measure double-claim after the Hetzner hosts are on v2. Current single-dominant-host regime makes double-claim waste smaller than baseline by construction.

### Tier-4b lane: not yet exercised (expected)

Zero `/bestmove-lease` calls since deploy. This is correct ladder behavior, not a bug: rung 5 fires only when rungs 1–4 all 204, and the local v2 box finds tier-3 work at rung 3 on essentially every cycle (103 lease-200s in a 10-min window). The tier-4b backlog stands at **447,374** analyzed-unstamped games (`full_evals_completed_at IS NOT NULL AND best_moves_completed_at IS NULL`); it will begin draining when tier-3 empties or when upgraded Hetzner workers idle down the ladder. Follow-up check: confirm `Bestmove-leased` lines appear in worker logs during a quiet period.

### Blob backfill (tier-4) non-regression: confirmed structurally + snapshot recorded

Rung order is unchanged (rung 5 strictly after rung 4), so blob backfill cannot be starved by the new lane. Observed rung-4 grants were near zero this window (4× `flaw-blob-lease` 200 in ~16 min, then none), consistent with lottery odds against a small remaining pool, not with a regression. Coverage snapshot for future diff (no timestamp column exists on `game_flaws`): **89,113 flaws without pv-line blobs of 3,415,824 total (97.4% coverage)** on analyzed games.

## Raw observations

- Fresh 10-min window (~18:00–18:10 UTC): local box 103 idle-scope lease 200s, 101 atomic submits; Hetzner ~2,800 polls, all 204.
- 25-min window: 159 worker submits vs 288 games completed — the server drain completes the difference (server pool 71.6% busy is the drain working, not MultiPV-2 submit overhead).
- Stamped totals: 5,608 games with `best_moves_completed_at`; 600 in the last hour.
- Server pool per-engine 60s busy: 71/72/72/72/73/69/71/73%.
- Local engines per-engine equivalent: 90.5% (aggregate 724% of one core across 8 engines, churn-tolerant sample).

## Follow-ups

1. **Upgrade the 3 Hetzner workers to v2** (pull + restart) — until then they contribute nothing to the atomic lane.
2. Re-spot-check after full rollout: server pool % (expect further drop), fleet submits/h, first `Bestmove-leased` sightings, double-claim rate (D-08 data).
3. Watch for recurrence of the atomic-submit 422 and any `worker-submit-fallback`-tagged Sentry events.
