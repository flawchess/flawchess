# Phase 123: Remote-worker fan-out for entry-ply (import-time) eval on big first imports - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-16
**Phase:** 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big
**Areas discussed:** Server-pool lease participation, Tuning knobs as config, Worker ladder mechanics, Worker mode activation, Distinctive worker IDs (folded)

---

## Server-pool lease participation

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — server claims via lease in v1 | _pick_pending_game_ids sets/honors the lease so server + workers never touch the same game; natural completion of D-3. | ✓ |
| No — worker-only lease, server unchanged (fast-follow) | Server keeps plain LIFO pick, may redundantly re-eval a leased game (idempotent, just wasted CPU). | |

**User's choice:** Yes — server claims via lease in v1.
**Notes:** Confirmed the D-5 backlog gate stays remote-lease-only; the server always drains regardless of backlog depth.

---

## Tuning knobs as config

| Option | Description | Selected |
|--------|-------------|----------|
| Env vars, like existing eval settings | ENTRY_EVAL_* settings, retune on prod with a restart. | |
| Named constants in code | Module-level constants; retune = code change + deploy. | ✓ |
| Mix — threshold env, rest constants | Only the "measure live" threshold is an env var. | |

**User's choice:** Named constants in code.
**Notes:** Consistent with the project's "tweak the constant" preference; values expected to lock quickly after one live measurement.

---

## Worker ladder mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Worker orchestrates, /lease gains a tier-scope param | scope=explicit → /entry-lease → scope=idle; endpoints stay single-purpose; optional param → old workers unaffected. | ✓ |
| Server unifies into one /lease, discriminated response | One round-trip, tagged union; batched payload rides the single-game lease endpoint; not backward-compatible without capability negotiation. | |
| Worker tries /entry-lease first, then /lease | Simplest wiring but violates D-1 tier-1-on-top ordering. | |

**User's choice:** Option 1 (worker orchestrates, optional scope param) — after a follow-up exchange.
**Notes:** User asked whether option 1 needs more round-trips than option 2 and flagged backward-compatibility / a smooth worker-update path as priorities. Clarified: option 2 is always 1 round-trip but changes the /lease response shape (breaks old workers without negotiation); option 1 does up to 3 round-trips but only on the idle/tier-3 path, and with `scope` optional (absent = legacy bundled behavior) old workers keep working unchanged — server deploys first, worker binaries upgrade at leisure, mixed fleet is safe. User locked option 1 explicitly.

---

## Worker mode activation

| Option | Description | Selected |
|--------|-------------|----------|
| On by default in the new binary | Upgraded worker drives the full ladder automatically; D-5 gate makes always-on safe. | ✓ |
| Opt-in via CLI flag / env | Operator chooses which boxes run depth-15; extra knob. | |
| On by default, with an opt-OUT flag | Default on plus --no-entry-ply escape hatch. | |

**User's choice:** On by default in the new binary.

### Observability column (entry_eval_leased_by)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add leased_by | One extra nullable column set at lease time; mirrors eval_jobs observability. | ✓ |
| No — expiry column only | Smaller migration; add later if needed. | |

**User's choice:** Yes — add entry_eval_leased_by.

---

## Distinctive worker IDs (folded in during "explore more")

User raised: eval_jobs.leased_by currently always reads "remote-worker"; wants distinctive IDs (random, < 10 chars) so workers are distinguishable. Folded as in-scope because it makes the new entry_eval_leased_by column (and existing leased_by) actually useful.

### ID generation

| Option | Description | Selected |
|--------|-------------|----------|
| Random per process, optional --worker-id override | 8-char base36 default; operator override for named boxes, validated < 10 chars. | ✓ |
| Always random, no override | Opaque IDs only. | |
| Required --worker-id, no random fallback | Breaks zero-config rollout. | |

### ID transport

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP header (X-Worker-Id) | Sent with operator-token header; absent → "remote-worker" default. | ✓ |
| Request body field | Adds a body to /lease (currently bodyless). | |

**User's choice:** Random per process + optional --worker-id override; transmitted via X-Worker-Id header. Used for both eval_jobs.leased_by (replacing the _WORKER_ID_REMOTE constant) and the new entry_eval_leased_by.

---

## Claude's Discretion

- Exact server-side lease-claim SQL shape (mirror the remote endpoint's SKIP LOCKED LIFO claim).
- Module placement of the tuning constants; exact entry-ply lease TTL value (short, < 120s).
- Exact X-Worker-Id header name; base36 length/charset for the random worker ID.
- Migration index strategy for the new lease columns (reuse/extend ix_games_evals_pending where it helps).

## Deferred Ideas

- Backlog-gate threshold tuning (300/50/TTL re-measured against real server-pool throughput once live) — not a v1 blocker.
- macOS background-scheduling caveat (SEED-048) unchanged — no v1 action.
