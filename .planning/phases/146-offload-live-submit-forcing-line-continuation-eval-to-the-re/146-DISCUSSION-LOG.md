# Phase 146: Offload live-submit forcing-line continuation eval to the remote worker - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-01
**Phase:** 146-offload-live-submit-forcing-line-continuation-eval-to-the-re
**Areas discussed:** Live-game priority lane, NULL-blob tag display, Completion-marker / atomicity (submit payload)

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Live-game priority lane | Fresh game tier-4 priority | ✓ |
| NULL-blob tag display | Raw vs hidden tags in window | ✓ |
| Worker upgrade scope | Confirm fleet-worker tier-4 client in-scope | |
| Completion-marker / atomicity | Submit payload + D-07 relaxation | ✓ |

**Note:** "Worker upgrade scope" was not selected for discussion → accepted as in-scope by
default (captured as D-04). Scout independently confirmed it is load-bearing (no fleet worker
speaks the flaw-blob contract today), so CONTEXT.md locks it as mandatory regardless.

---

## Live-game priority lane

| Option | Description | Selected |
|--------|-------------|----------|
| Recency-order tier-4 | `ORDER BY full_evals_completed_at DESC`; fresh wins, corpus on tail; no new tier/column | ✓ |
| Dedicated tier-3.5 lane | Separate higher-priority lottery for recent games; clearer, more code | |
| Keep pure random tier-4 | No change; fresh tags gated "eventually" during rollout | |

**User's choice:** Recency-order tier-4 (D-01)
**Notes:** Claude flagged the worker-collision risk of a pure `DESC LIMIT 1` (all idle workers
grab the newest game) → planner adds a recency tie-break/jitter. Captured in D-01.

---

## NULL-blob tag display

| Option | Description | Selected |
|--------|-------------|----------|
| Show raw tags (current behavior) | Display stored raw tags; tier-4 silently denoises; zero read-path change | ✓ |
| Hide tags until blobs land | Suppress chips while blobs NULL; new read-path gating; fresh game looks empty | |

**User's choice:** Show raw tags (D-02)
**Notes:** With recency priority (D-01) the window is short, and this matches how every
un-blobbed game already behaves today.

---

## Completion-marker / atomicity (submit payload)

| Option | Description | Selected |
|--------|-------------|----------|
| Drop second-best from /submit | Worker stops sending per-ply second-best; honest contract; cleanest | ✓ |
| Keep sending it (server ignores) | No /submit change; dead fields on the wire; smaller diff | |

**User's choice:** Drop second-best from /submit (D-03)
**Notes:** Claude verified against the code that dropping is safe — `_build_flaw_blob_lease_positions`
reconstructs both lines from stored `game_positions.pv` only, with no dependence on per-ply submit
second-best, and no other consumer exists. Live submit still fills flaw PVs + stamps both
completion markers; only the continuation blobs are deferred. D-07 atomicity is intentionally
relaxed on the live path and self-heals via tier-4.

---

## Claude's Discretion

- Worker full-ply pass likely reducible to MultiPV-1 once second-best is dropped — flagged as
  research-confirm/optional, not locked.
- Recency tie-break/jitter form; worker tier-4 poll cadence/batch/back-pressure; dev-first
  end-to-end validation gate; whether to lower `HTTP_TIMEOUT_S` back from the 120s stopgap.

## Deferred Ideas

- async-ify server-side blob assembly (the rejected SEED-071 alternative).
- Worker MultiPV-2 → MultiPV-1 (optional optimization, possibly this phase).
- Lowering `HTTP_TIMEOUT_S` below 120s (gated on observed live-submit latency).
