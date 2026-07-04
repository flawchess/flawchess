---
id: SEED-080
status: dormant
planted: 2026-07-04
planted_during: v1.30 closed / planning next milestone
trigger_when: next /gsd-new-milestone (candidate milestone), after the 2026-07-03 correctness phase merges
scope: large (one milestone, two phases)
source: reports/pipeline-review-2026-07-04.md
---

# SEED-080: Pipeline consolidation milestone (retire Gen-1 protocol + unify the eval write path)

Two-phase milestone implementing the Tier-A/B recommendations of the 2026-07-04 pipeline
architecture review. All changes are server-side — **no worker protocol changes and no
fleet redeploy required** (fleet confirmed fully on atomic-lease/submit; prod backend log
grep 2026-07-04 showed **zero** legacy `/lease`+`/submit` hits over an 11.3h window vs
54k atomic-lease hits).

## Why This Matters

The eval pipeline's building blocks are shared, but the orchestration around them is
copy-pasted: the Path A/B/C completion decision exists 3× verbatim, `/lease` vs
`/atomic-lease` are ~95% identical, the classify preamble is repeated 4×, and
`eval_remote.py` imports ~20 private helpers from `eval_drain.py`. The delete-then-insert
flaw write forced the snapshot/restore compensation layer that produced FLAWCHESS-8D and
the Phase 146/147 ungated-tag bugs. Every new feature must be threaded through 3+ copies;
consolidation removes the seams that generated most recent production incidents.

## The two phases

**Phase 1 — Retire and prune** (shrink before refactoring; independent low-risk items):
- **R2**: delete Gen-1 `/lease` + `/submit` endpoints + `_apply_submit`
  (`eval_remote.py:330-521, 553-645`) + worker dead handler `_handle_full_ply_response`
  (`remote_eval_worker.py:656-704`) + associated tests in `test_eval_worker_endpoints.py`.
  Keep `/flaw-blob-*` (tier-4 backfill actively draining ~2.4k games/h as of 2026-07-04).
- **R12**: dead weight — tier-2 lane code (keep DB column), `hashes_for_game`
  (`zobrist.py:270`), `chesscom_to_lichess` future-use tables, caller-less
  `Game.needs_engine_full_evals` hybrid.
- **R13**: `_normalize_chesscom_result` silent-draw fallback → explicit unknown + Sentry.
- **R11**: `worker_schema_version` telemetry on submits (log/tag only; no 426 gate yet).
- **R8**: durable import-job guard — create `import_jobs` row in the request handler +
  partial unique index on `(user_id, platform) WHERE status IN ('pending','in_progress')`.
- **R15**: `worker_heartbeats` table (worker_id, version, last_seen, counts) updated
  server-side from existing `X-Worker-Id` / submit fields — no worker change.

**Phase 2 — Consolidate the write path** (dependency chain, in order):
- **R1**: extract Path A/B/C + guarded eval_jobs stamp into one
  `apply_completion_decision()` (3 copies: `eval_drain.py:2745-2794`,
  `eval_remote.py:457-509`, `eval_remote.py:1558-1614`).
- **R4**: unify the classify preamble (load positions + in-memory post-move overlay +
  classify once per tick; 4 sites: `_flaw_engine_plies`, `_missing_flaw_pv_targets`,
  `_build_flaw_multipv2_blobs`, `_derive_atomic_sentinel_lines`).
- **R3**: replace delete-then-insert in `_classify_and_fill_oracle` with per-ply
  diff/upsert; delete `_snapshot_preserved_flaw_blobs`/`_restore_preserved_flaw_blobs`.
  Needs an old-vs-new equivalence test across the incremental-retry scenarios.
- **R7**: extract shared submit/tick orchestration into `app/services/eval_apply.py`;
  split `eval_drain.py` (entry lane / full lane / shared write path); router stops
  importing private drain helpers.
- Ride-alongs: **R5** (EnginePool: one generic acquire/analyse/restart method replacing
  the 3 copies) and **R6** (parameterize the tier-3/tier-4 ES lottery).

## When to Surface

**Trigger:** next `/gsd-new-milestone`. Hard prerequisite: the pending correctness phase
(`.planning/todos/pending/2026-07-03-code-review-pipeline-tactic-correctness-phase.md`)
must merge first — it edits the same files (`eval_drain.py`, `eval_remote.py`), and its
item 2 covers the review's R9 (entry-drain circuit breaker), which is therefore NOT in
this seed. Phase 1 strictly before Phase 2 (consolidating 2 copies beats consolidating 3).

## Scope Estimate

**Large — one milestone, two phases.** Phase 1 is mostly deletions + two small migrations.
Phase 2 contains the one genuinely risky item (R3, authoritative write rewrite) and the
module restructure (R7); R1/R4 first make both smaller. Explicitly out of scope (per
review §7 "not recommended"): merging entry/full lanes, changing the post-move convention,
queue/broker rewrite, worker protocol changes, R14 tier-3 lease (deferred), full SEED-078
streaming.

## Breadcrumbs

- `reports/pipeline-review-2026-07-04.md` — full findings (D1-D8, F1-F8) + recommendations
- `app/routers/eval_remote.py`, `app/services/eval_drain.py`,
  `app/services/eval_queue_service.py`, `app/services/engine.py`,
  `scripts/remote_eval_worker.py`, `app/services/import_service.py`
- Prod traffic check 2026-07-04 (~20:37 03.07 → 07:58 04.07 UTC): atomic-lease 54,155 /
  entry-lease 27,077 / flaw-blob-lease 27,076 / flaw-blob-submit 27,043 / atomic-submit 1 /
  legacy lease+submit **0**
- Related seeds: SEED-072 (tier-3 double-claim, stays deferred = R14), SEED-077/078
  (deferred, separate triggers), closed SEED-074/075/076 (the bug history R3 addresses)

## Notes

Captured 2026-07-04 after the pipeline architecture review session; enrichment (trigger,
why, scope) filled at capture time from the review discussion.
