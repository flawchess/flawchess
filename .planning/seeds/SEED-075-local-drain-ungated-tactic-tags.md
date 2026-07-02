---
id: SEED-075
status: dormant
planted: 2026-07-02
planted_during: v1.30 milestone close. While closing v1.30 the Phase 147 "no ungated tactic tag anywhere" strict-zero invariant was re-verified against prod and found still broken (and growing: ~9 on 2026-07-01 → 75 on 2026-07-02). Root-caused to the local in-process eval drain, which was never given the blobs_pending guard that the atomic upgraded-worker path got in Phase 147.
trigger_when: soon-ish — analytical-only, not rollback-class, but it grows during active analysis (in-process drain mints faster than tier-4 drains). One-line-ish backend fix, ideal for /gsd-quick in a fresh session.
scope: Trivial — backend, one call site. app/services/eval_drain.py:2642 `_classify_and_fill_oracle(...)` defaults `blobs_pending=False` on the local drain path; the fix is to pass the correct signal so a flaw with no assembled blob is either suppressed to NULL or written a `[]` D-06 sentinel. No DB schema change. No new endpoint. Mirror the atomic-worker path (app/routers/eval_remote.py:312,1254 already pass blobs_pending=True).
---

# SEED-075: Local eval drain re-mints ungated cp-based tactic tags (Phase 147 strict-zero gap)

## Why This Matters

Phase 147 (v1.30) established the invariant "no ungated cp-based tactic tag is ever
persisted" — go-forward suppression at the write site plus a corpus migration
(`eb341e836ee9`) that cleared the raw tags left on already-imported games. That invariant
does **not** hold at steady state in prod, because one producer was never converted.

**Verified on prod 2026-07-02 (during v1.30 close):**

```sql
SELECT
  count(*) FILTER (WHERE gf.allowed_tactic_motif IS NOT NULL AND gf.allowed_pv_lines IS NULL) AS allowed_ungated,
  count(*) FILTER (WHERE gf.missed_tactic_motif  IS NOT NULL AND gf.missed_pv_lines  IS NULL) AS missed_ungated
FROM game_flaws gf
JOIN game_positions gp
  ON gp.user_id = gf.user_id AND gp.game_id = gf.game_id AND gp.ply = gf.ply - 1
WHERE gp.eval_cp IS NOT NULL;
-- allowed_ungated = 44, missed_ungated = 31  (75 total; was ~9 on 2026-07-01 → growing)
```

These 75 are flaws where `eval_cp` was present (so the forcing-line gate *could* have run)
but the continuation blob is NULL and a raw motif was persisted anyway — the exact
invariant violation. (The much larger ~175K motif-with-NULL-blob total is almost entirely
mate-adjacent rows where `eval_cp IS NULL`, preserved by design and NOT part of this.)

Severity: 75 / 3.36M flaws (~0.04% of the 185K tagged flaws), analytical-only,
self-healing-eligible — **not rollback-class**. But it drifts upward during active analysis,
which is why it's worth a small fix rather than leaving it to tier-4 alone.

## Root Cause (code)

- `app/services/eval_drain.py:2642` — the local in-process drain calls
  `_classify_and_fill_oracle(write_session, game_id, engine_result_map, flaw_pv_blobs)`
  **without** `blobs_pending`, so it defaults to `False`.
- `app/services/flaws_service.py:583` — the suppression branch
  `if blobs_pending and motif is not None and pv_blob is None and pre_flaw_eval_cp is not None: return None`
  therefore never fires on this path. For a flaw whose blob wasn't assembled into the
  in-memory `flaw_pv_blobs`, the raw cp-based tag is persisted.
- `app/services/eval_drain.py:1411` — `_run_multipv2_pass` only updates flaws that ARE in
  `flaw_pv_blobs`; it writes **no `[]` sentinel** for absent ones, so the blob column stays
  NULL alongside the raw tag.
- Contrast: the atomic upgraded-worker path (`app/routers/eval_remote.py:312` and `:1254`)
  correctly passes `blobs_pending=True` and suppresses these — this is the Phase 147 behavior;
  it just never reached the in-process drain.

The default on `blobs_pending` is documented as intentional for the local drain
(`eval_drain.py:711-712`), on the assumption that the in-memory `flaw_pv_blobs` covers every
flaw. In practice some flaws are un-walkable / un-assembled and slip through NULL-blob + raw-tag.

## Self-Heal (why it doesn't just fix itself)

The tier-4 lottery predicate (`app/services/eval_queue_service.py::_claim_tier4_blob`) only
needs `full_evals_completed_at IS NOT NULL AND allowed_pv_lines IS NULL`, so these games stay
eligible even after `full_pv_completed_at` is stamped — they DO eventually get a real blob and
a gated retag. But it's a weighted-random lottery over the whole ~175K NULL-blob pool (mostly
mate-adjacent), so tail latency is tens of minutes and live production outpaces drainage during
active analysis → a persistent small, slowly-growing non-zero population.

## Fix Candidates (pick at plan/quick time)

1. **Pass the correct `blobs_pending` at `eval_drain.py:2642`.** Simplest. Setting it `True`
   suppresses the tag to NULL for any flaw whose blob wasn't assembled in this pass; tier-4
   later lands the real blob and the D-07 gated retag re-tags it. Confirm this doesn't
   suppress legitimately-blobbed flaws (it shouldn't — the branch requires `pv_blob is None`).
2. **Write a `[]` D-06 sentinel** in the local drain for flaws it can't assemble a blob for
   (mirror the tier-4 `sentinel_lines` path, `_build_flaw_blob_lease_positions` ~1431). This
   marks them un-gate-able-FINAL (raw tag accepted by design) instead of leaving them NULL and
   re-eligible. Changes semantics (accept vs suppress) — decide which is intended for genuinely
   un-walkable lines.

Option 1 aligns with Phase 147's intent ("never persist an ungated tag; suppress until the
blob lands"). Option 2 is closer to "these are legitimately un-gate-able, stop re-queuing them."
The two are not mutually exclusive (un-walkable → sentinel FINAL; merely-deferred → suppress).

## Verification

Re-run the prod query above (needs `bin/prod_db_tunnel.sh`); the go-forward count should stop
climbing and the existing 75 drain toward 0 via tier-4. Add a unit test asserting the local
drain classify path suppresses (or sentinels) a motif'd flaw with `eval_cp` present and no blob,
mirroring the existing atomic-submit test.

## Pointers

- `app/services/eval_drain.py` — `_classify_and_fill_oracle` (678), leak call site (2642),
  `_run_multipv2_pass` (1400), `_build_flaw_blob_lease_positions` sentinel_lines (1416/1431).
- `app/services/flaws_service.py` — `_classify_tactic_gated` (525), suppression branch (583).
- `app/routers/eval_remote.py` — correct `blobs_pending=True` sites (312, 1254).
- `app/services/eval_queue_service.py` — `_claim_tier4_blob` predicate (~558).
- Memory: `project_local_drain_ungated_tactic_tags` (root cause + prod evidence).
- Related: `project_asyncpg_jsonb_null_vs_sql_null` (JSONB null vs SQL NULL on pv_lines).
