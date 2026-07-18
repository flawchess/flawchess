---
phase: 177-worker-side-multipv2-gem-candidates
plan: "05"
subsystem: observability
tags: [measurement, prod, sentry, remote-eval-worker]

# Dependency graph
requires:
  - phase: 177 plans 01-04
    provides: protocol v2 + tier-4b lane + drain minimal path + worker script v2 (deployed to prod as 3efc7172, PR #260)
provides:
  - 177-MEASUREMENT.md — D-07 before/after table vs SEED-111 baseline with fallback + double-claim verdicts
affects: [D-08 TTL-lease decision (defer), Hetzner worker rollout follow-up]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Churn-tolerant /proc tick sampling (1s polls, per-pid deltas summed across engine restarts) for worker engine busy %"
    - "Wire-level rollout verification via access-log query strings (worker_schema_version param presence identifies v2 hosts)"

key-files:
  created:
    - .planning/phases/177-worker-side-multipv2-gem-candidates/177-MEASUREMENT.md
  modified: []

key-decisions:
  - "D-08: TTL-lease escalation DEFERRED — double-claim not measurable in the single-active-host window; re-measure after Hetzner v2 rollout"
  - "Phase closed with partial-rollout caveat recorded (user-approved): 3 Hetzner workers wire-verified still v1; follow-ups documented in MEASUREMENT.md"

patterns-established: []

duration: ~40min (live-prod observation window 18:00-18:35 UTC)
completed: 2026-07-17
---

# Phase 177 Plan 05: D-07 Post-Deploy Measurement Summary

**Measurement recorded against the SEED-111 2026-07-17 baseline; user approved closure with partial-rollout caveat.**

## What was measured

All six D-07 figures, from read-only prod DB + live access logs + 60s CPU samples:

1. **games/h stamped:** 600/h (60m) / 691/h (25m pace) vs ~550/h baseline — up with only 1 of 4 hosts active.
2. **Worker submits/h:** local box ~380–600/h alone (≈ old 4-host fleet total of 629/h); Hetzner ~0.
3. **Server pool:** 71.6% busy vs ~92% baseline (−20 pts; drain still covering gated Hetzner slack).
4. **Local worker engines:** 90.5% busy vs ~68% baseline (target ~95%) — submit round-trip idle eliminated.
5. **worker-submit-fallback:** 0 Sentry events; instrument caveat (only errored fallbacks captured) documented; one atomic-submit 422 flagged for watch.
6. **Double-claim:** not measurable single-host; **D-08 recommendation: defer** TTL leases.

Blob backfill non-regression confirmed structurally (rung order unchanged) with a 97.4%-coverage snapshot (89,113 flaws pending) recorded for future diff.

## Key finding

Only the local box runs v2 — all three Hetzner workers still send version-less lease URLs (v1) and are gated to 204s. Follow-up: pull + restart workers on the Hetzner hosts, then spot-check server pool %, first `Bestmove-leased` sightings, and double-claim rate.

## Self-Check: PASSED

- 177-MEASUREMENT.md exists with all six before/after figures, fallback verdict, and D-08 recommendation (commit 6921a4b1).
- No fabricated data: every figure traces to a named instrument and window.
