# Phase 149: Retire & Prune - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-04
**Phase:** 149-retire-prune
**Areas discussed:** Worker Heartbeats (PRUNE-06)

---

## Area selection

| Gray area | Selected for discussion |
|-----------|-------------------------|
| "Unknown" result representation (PRUNE-03) | |
| Durable import guard (PRUNE-05) | |
| worker_heartbeats (PRUNE-06) | ✓ |
| Deletion scope confirm (PRUNE-01/02) | |

User narrowed to a single area; treated the other three as locked-by-requirements.

---

## Worker Heartbeats (PRUNE-06)

### Write cadence

| Option | Description | Selected |
|--------|-------------|----------|
| Every live submit | Upsert on each entry/flaw-blob/atomic submit (~7.5 upserts/s by PK). Real-time last_seen. | ✓ |
| Throttled | Only upsert if last_seen older than ~30s. Read-then-write branch, staler liveness. | |
| Defer the whole table | Drop PRUNE-06 — no reader exists yet. | |

**User's choice:** Every live submit.
**Notes:** User first deflected this question with "Explain why we need a worker heartbeat table" — asked for the justification before committing. Justification given: (1) no server-side worker registry exists today (identity lives only in access logs); (2) prod logs rotate ~hourly and that gap already caused a wrong "server-pool did it" diagnosis; (3) the table makes the milestone's "fleet fully on atomic" safety claim a standing query instead of a one-off grep. Honest caveat surfaced: no consumer (UI/alert) is built this phase. User accepted and picked "every live submit".

### Counts to accumulate

| Option | Description | Selected |
|--------|-------------|----------|
| Submits + plies | Cumulative submit_count + evals_submitted (sum of len(evals)). | ✓ |
| Submits only | Just submit_count. | |
| Per-lane counts | Separate counters per lane (3× columns). | |

**User's choice:** Submits + plies (recommended).

### Version storage

| Option | Description | Selected |
|--------|-------------|----------|
| Both, schema_version nullable | sf_version (string, every lane) + worker_schema_version (int, nullable, only atomic). | ✓ |
| sf_version only | Just the Stockfish version string. | |

**User's choice:** Both, worker_schema_version nullable (recommended).

### Trigger events

| Option | Description | Selected |
|--------|-------------|----------|
| Submits only | Only the 3 live submits upsert. | ✓ |
| Leases + submits | Also upsert on lease (doubles writes). | |

**User's choice:** Submits only (recommended).

### Worker IP (`last_ip`) — follow-up

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add last_ip | Nullable last_ip TEXT from request.client.host (already the real worker IP in prod via uvicorn --proxy-headers). | ✓ |
| No, keep to R15 columns | Stick to literal worker_id/version/last_seen/counts; IP stays in access logs only. | |

**User's choice:** Yes, add last_ip.
**Notes:** User raised this after the initial four decisions. IP is the most trustworthy fleet-identity signal (worker_id is self-reported/advisory; IP maps to real topology). Free in prod — request.client.host already resolves the true remote IP via --proxy-headers/--forwarded-allow-ips. Flagged as beyond the literal R15 column list; approved deliberately. Minimal GDPR surface (operator-owned worker machines, not end-users). Captured as CONTEXT.md D-06.

---

## Claude's Discretion

User explicitly delegated the remaining three gray areas as locked-by-requirements, to be captured as sensible defaults (not re-litigated) in CONTEXT.md:
- PRUNE-03 unknown-result flow → default: skip game via existing `None` channel + Sentry context (don't widen `GameResult`).
- PRUNE-05 import guard → default: partial unique index + create row in request handler; on IntegrityError return existing job HTTP 200 (preserve current contract); in-memory guard becomes a fast-path pre-check only.
- PRUNE-01/02 deletion scope → surgical Gen-1 test removal (keep entry/atomic/flaw-blob tests); remove tier-2 lane logic but keep its DB column.

## Deferred Ideas

None — discussion stayed within phase scope. Milestone-level deferrals already live in SEED-080.
