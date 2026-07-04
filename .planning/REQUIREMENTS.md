# Requirements: v1.31 Pipeline Consolidation

**Milestone goal:** Retire the dead Gen-1 eval protocol and unify the copy-pasted eval write path so new pipeline work threads through one code path instead of 3+, removing the seams that generated FLAWCHESS-8D and the Phase 146/147 ungated-tag bugs. Server-side only — no worker protocol change, no fleet redeploy.

**Source:** SEED-080 (Tier-A/B recommendations of `reports/pipeline-review-2026-07-04.md`). R-numbers below reference that review's recommendation list.

**Scope note:** These are engineering-correctness/consolidation requirements, not user-facing capabilities, so they are phrased as observable code/behavior guarantees rather than "User can X". The milestone's user-visible contract is *no behavior change* — the pipeline produces identical eval/flaw/tag results through a smaller, single-path implementation.

---

## v1.31 Requirements

### Correctness fixes — Phase 148 (already shipped)

Five silent-data-loss / production-only-correctness defects from the 2026-07-02 code review. SEED-080's hard prerequisite (edits the same files as Phase 1/2); grouped into this milestone retroactively. All validated and shipped.

- [x] **CORR-01**: A deep forced mate is tagged — a truncated forced-mate PV (`has_forced_mate` set, PV capped before `is_checkmate()`) tags generic `mate` instead of the pre-fix no-op that dropped the tag entirely
- [x] **CORR-02**: Tactic PV replay preserves en-passant/castling state — the detector's `fen_map` carries full board FEN internally so ep/castling positions parse and replay correctly, while the persisted `game_flaws.fen` stays piece-placement-only (API contract unchanged)
- [x] **CORR-03**: The entry-ply eval drain does not stamp `evals_completed_at` on an all-fail (dead-pool) tick — an added circuit breaker withholds the completion marker when every eval in the tick fails
- [x] **CORR-04**: The endgame quintile significance test corrects for overlapping cohorts — no false "significant" verdicts from treating overlapping quintile cohorts as independent
- [x] **CORR-05**: A single malformed platform game no longer aborts the whole import — per-game normalization is guarded so one bad game is skipped, not fatal
- [x] **CORR-06**: The entry-submit endpoint enforces a batch-scoping minimum guard so a sparse/partial submit cannot silently under-scope its target set

### Phase 1 — Retire & Prune

Independent low-risk deletions + two small migrations. Shrink the surface before refactoring so Phase 2 consolidates 2 copies rather than 3.

- [ ] **PRUNE-01** (R2): The dead Gen-1 protocol is deleted — `/lease` + `/submit` endpoints + `_apply_submit` (`eval_remote.py`), the worker `_handle_full_ply_response` handler (`remote_eval_worker.py`), and the associated `test_eval_worker_endpoints.py` tests are removed; `/flaw-blob-*` is retained (tier-4 backfill actively draining). Prod traffic confirmed zero legacy hits before deletion.
- [ ] **PRUNE-02** (R12): Dead weight is removed — tier-2 lane code (the DB column is kept), `hashes_for_game` (`zobrist.py`), the `chesscom_to_lichess` future-use tables, and the caller-less `Game.needs_engine_full_evals` hybrid
- [ ] **PRUNE-03** (R13): `_normalize_chesscom_result`'s silent-draw fallback is replaced with an explicit "unknown" result + a Sentry capture, so a malformed/unknown result is surfaced rather than silently scored as a draw
- [ ] **PRUNE-04** (R11): `worker_schema_version` is recorded on submits as telemetry (log/tag only — no 426 rejection gate yet), giving fleet-version visibility
- [ ] **PRUNE-05** (R8): The import-job guard is durable — the `import_jobs` row is created in the request handler and a partial unique index on `(user_id, platform) WHERE status IN ('pending','in_progress')` prevents concurrent duplicate imports at the DB level
- [ ] **PRUNE-06** (R15): A `worker_heartbeats` table (worker_id, version, last_seen, counts) is populated server-side from the existing `X-Worker-Id` / submit fields — no worker-side change

### Phase 2 — Consolidate Write Path

Dependency chain, in order. R1/R4 first shrink R3 and R7.

- [ ] **WRITE-01** (R1): The Path A/B/C completion decision + guarded `eval_jobs` stamp is extracted into one `apply_completion_decision()`, replacing the 3 verbatim copies (`eval_drain.py`, `eval_remote.py` ×2)
- [ ] **WRITE-02** (R4): The classify preamble is unified — positions loaded + in-memory post-move overlay applied + classify run once per tick, replacing the 4 repeated sites (`_flaw_engine_plies`, `_missing_flaw_pv_targets`, `_build_flaw_multipv2_blobs`, `_derive_atomic_sentinel_lines`)
- [ ] **WRITE-03** (R3): `_classify_and_fill_oracle` replaces delete-then-insert with a per-ply diff/upsert, and `_snapshot_preserved_flaw_blobs` / `_restore_preserved_flaw_blobs` are deleted; an old-vs-new equivalence test across the incremental-retry scenarios proves identical output
- [ ] **WRITE-04** (R7): Shared submit/tick orchestration is extracted into `app/services/eval_apply.py`, `eval_drain.py` is split (entry lane / full lane / shared write path), and the router no longer imports private drain helpers
- [ ] **WRITE-05** (R5): `EnginePool` exposes one generic acquire/analyse/restart method, replacing the 3 near-identical copies (ride-along on Phase 2)
- [ ] **WRITE-06** (R6): The tier-3 / tier-4 Efraimidis–Spirakis lottery is parameterized into a single shared implementation (ride-along on Phase 2)

---

## Future Requirements (deferred)

- **R14** — tier-3 lease (double-claim hardening). Owned by SEED-072, deferred to a later milestone.
- **SEED-078** — full eval-result streaming. Separate trigger, out of this milestone.
- **SEED-077** — deferred, separate trigger.
- **R9** — entry-drain all-fail circuit breaker. Already delivered in Phase 148 (CORR-03), so not a Phase 1/2 item.

## Out of Scope (explicit exclusions)

- **Merging the entry lane and full lane** — review §7 "not recommended"; the two lanes have genuinely different latency/priority contracts.
- **Changing the post-move eval convention** — load-bearing across every source; a rewrite reopens the SEED-044 off-by-one risk for no consolidation gain.
- **Queue/broker rewrite** — the SKIP-LOCKED tiered queue is sound; replacing it is a different, larger project.
- **Any worker protocol change / fleet redeploy** — the whole milestone is server-side by design; the fleet is confirmed on atomic-lease/submit.
- **Client-facing behavior change** — the pipeline's eval/flaw/tag outputs must be byte-identical through the consolidated path.

---

## Traceability

*(Filled by the roadmapper — maps each REQ-ID to its phase.)*
