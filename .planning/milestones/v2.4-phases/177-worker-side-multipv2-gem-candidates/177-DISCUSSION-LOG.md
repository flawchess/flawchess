# Phase 177: Worker-side MultiPV-2 gem-candidate searches, protocol v2 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-17
**Phase:** 177-worker-side-multipv2-gem-candidates
**Areas discussed:** Tier-4b worker lane shape, Drain's role after the shift, Double-claim / TTL leases

---

## Todo cross-reference

| Option | Description | Selected |
|--------|-------------|----------|
| Skip both | Neither touches the worker protocol / eval pipeline | ✓ |
| Fold 172 review findings | Client gem-sweep warnings (WR-01/03/05/06), frontend, likely obsolete since Phase 175 | |
| Fold bitboard storage | 12 BIGINT bitboard columns for partial-position queries, unrelated DB feature | |

**User's choice:** Skip both (recorded as reviewed-not-folded in CONTEXT.md deferred section)

---

## Tier-4b worker lane shape

### How do v2 workers reach tier-4b work?

| Option | Description | Selected |
|--------|-------------|----------|
| Extend idle fall-through | scope=idle falls through to tier-4b after tier-3 empties, v2-gated + flag-gated; zero new worker scheduling, ladder preserves lane priority | ✓ |
| Dedicated lease endpoint/scope | Separate /bestmove-lease or scope=bestmove; more protocol surface, allows backfill-only workers | |

### How does a tier-4b result come back / minimal apply path routing?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated submit endpoint | Small /bestmove-submit with own schema; minimal path structural, mirrors flaw-blob pair | ✓ |
| atomic-submit with mode discriminator | Reuse /atomic-submit with a payload flag; apply branches internally, discriminator worker-supplied | |

### How does the server validate submitted per-ply entries?

| Option | Description | Selected |
|--------|-------------|----------|
| Stateless recompute at apply | Server recomputes candidate-ply set from stored best_move/pv + book filter; drops/422s outsiders | ✓ |
| Persist leased plies, match on submit | Store candidate set in lease/job record; adds lease state + expiry for a re-derivable set | |

### Does BEST_MOVE_BACKFILL_ENABLED gate the worker lane?

| Option | Description | Selected |
|--------|-------------|----------|
| One flag gates both | Off = no tier-4b work for workers or drain; single switch per v2.4 D-05 rollout pattern | ✓ |
| Separate worker-lane flag | Independent flip of worker lane vs drain; one more env var | |

---

## Drain's role after the shift

### Should the server drain remain a tier-4b consumer?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, with tier-aware minimal path | Candidate searches only, minimal write, no reclassify; reuses server-side candidate/writer code; fixes every-ply re-eval bug; freed pool ≈ 1/3 fleet capacity | ✓ |
| Drop drain from tier-4b (workers-only) | Simplest; prod box stops being CPU-saturated 24/7; bug becomes moot | |

### How should fallback instrumentation split expected vs unexpected work?

| Option | Description | Selected |
|--------|-------------|----------|
| Tag by source path | Sentry dimension: drain-local (expected) vs worker-submit fallback (regression signal, ~zero) | ✓ |
| Count everything together | One counter; expected drain volume drowns the regression signal | |

### Explicit post-deploy measurement step?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit measurement step | HUMAN-UAT task re-measuring games/h, engine busy %, pool utilization, fallback counts vs SEED-111 baseline | ✓ |
| Ad-hoc observation | No formal step | |

---

## Double-claim / TTL leases

### Does TTL-lease work belong in this phase?

| Option | Description | Selected |
|--------|-------------|----------|
| Defer, but measure | Measurement step records double-claim rate; ≥~12% or growing → own follow-up; measure-before-optimize | ✓ |
| Cheap mitigation in-phase only | Low-cost claim primitive (atomic claim-stamp / SKIP LOCKED) if research confirms small | |
| Full TTL leases in this phase | Claim + expiry + reclaim; meaningfully grows phase scope | |

---

## Claude's Discretion

- Fresh-lane lease details (area offered, not selected): follow SEED-111 lean — `move_uci` per position in lease, book filtering server-side, optional book-ply count to trim superset.
- Endpoint/scope naming, lease/submit schema shapes, Sentry tag names, worker retry behavior for failed targeted searches.
- v1→v2 fleet upgrade sequencing across the 4 worker hosts.

## Deferred Ideas

- TTL-lease escalation (D-4) — revisit if post-shift double-claim rate stays ~12% or grows.
- uvicorn single-thread bottleneck — measure before optimizing (SEED-111 open question #3).
