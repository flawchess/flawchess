# FlawChess Codebase Review — 2026-07-02

**Scope:** backend architecture, data schema and DB design, game import and remote-worker pipeline, DB query efficiency, statistical analysis correctness, tactic tagging (precision/recall), plus a superficial frontend pass and a production slow-query analysis.

**Method:** seven parallel review passes over the codebase (each with file:line-verified evidence), a full prod DB report (`reports/db-stats/db-report-prod-2026-07-02.md`), a fresh tactic-tagger precision/recall run (`reports/tactic-tagger/tactic-tagger-2026-07-02.md`), and independent spot-verification of the top-severity claims at source. Findings marked PLAUSIBLE were not fully confirmed; everything else was verified against the actual code or prod data.

**Overall assessment:** the codebase is in good shape for its age and scale. The hard invariants hold: no `asyncio.gather` on shared sessions anywhere, lease claiming uses `FOR UPDATE SKIP LOCKED` correctly, ply-parity/sign-convention/Wilson math all verified correct, both prod data-integrity checks PASS, admin/impersonation auth is solid, cache hit ratio is 99.86%. The issues below are real but concentrated: one auth gap, two silent-data-loss modes in the eval pipeline, a migration-tooling trap, production-only tactic-tagging defects, and a family of per-request `game_positions` aggregations that will not survive 10× data growth.

---

## Ranked recommendations

Ranked by (user-visible correctness / data-loss / security risk) × likelihood × leverage. Effort estimates are rough.

| # | Recommendation | Area | Severity | Effort |
|---|---|---|---|---|
| 1 | Authenticate `GET /api/imports/{job_id}` and sanitize its `error` field | Security | High | Trivial |
| 2 | Add the WR-05-style circuit breaker to the entry-ply eval drain | Pipeline | High | Small |
| 3 | Add `ix_game_flaws_blob_backfill` to the Alembic autogenerate ignorelist; restore 4 missing dev indexes; add an index-existence assertion | Schema/ops | High | Trivial |
| 4 | Fix the two production-only tactic-tagging defects: `has_forced_mate` no-op and `fen_map` losing ep/castling state | Tactics | High | Small |
| 5 | Kill the per-request `game_positions` aggregation family: share the endgame span computation (7× redundant scans), add missing `user_id` predicates in `canonical_slice_sql` and `phase_entry_subq` | Performance | High | Medium |
| 6 | Scope `/entry-submit` completion stamping to the actual leased batch | Pipeline | Medium-High | Small |
| 7 | Stream (or at least promptly release) chess.com archive JSON during import | Pipeline / OOM | Medium-High | Small-Medium |
| 8 | Move CPU-bound chess work (PGN parse, Zobrist, replay, classification) off the event loop | Latency | Medium | Medium |
| 9 | Fail closed on default `SECRET_KEY` in non-dev; add a minimum password policy | Security | Medium | Trivial |
| 10 | Statistical fixes: quintile-test covariance, `to_date` honored everywhere, entry-eval outlier trim, mid-rank percentile ties | Stats | Medium | Small each |
| 11 | Bound-validate remote-worker submissions (eval_cp/eval_mate ranges, pv/best_move lengths) | Pipeline | Medium | Trivial |
| 12 | Schema hardening batch: composite FK on `game_flaws`, `JSONB(none_as_null=True)` on PV blobs, CHECK constraints, `import_jobs` active-unique index, drop 2 dead `games` indexes | Schema | Medium | Small-Medium |
| 13 | Restructure the tier-4 drain pollers before data grows further (dominant DB load in prod) | DB ops | Medium | Medium |
| 14 | Tactic recall improvements: trapped-piece empty-escape fix, multi-label-aware recall goals, dispatch hygiene | Tactics | Medium | Small each |
| 15 | Frontend: lazy-load authenticated pages / split the 1.5 MB main chunk; add `isError` to the Home profile query | Frontend | Medium | Small |

Everything below expands these with evidence, plus the lower-priority findings.

---

## 1. Security and API surface

### 1.1 `GET /api/imports/{job_id}` is unauthenticated (High) — VERIFIED

`app/routers/imports.py:333` is the only route in the file without `Depends(current_active_user)`, and the DB fallback (`get_import_job`) has no user scoping either. Anyone holding a job_id can poll another user's import status (platform, platform username, progress, error). The `error` field is `str(exc)` (`app/services/import_service.py:619`), so raw exception text (DB errors, httpx URLs) leaks to unauthenticated clients. job_id is a UUIDv4 so it isn't guessable — that's the only mitigation.

**Fix:** add `current_active_user` + `job.user_id == user.id` check (404 otherwise, matching the IDOR pattern used everywhere else); map `job.error` to a sanitized message.

### 1.2 No fail-closed guard on default `SECRET_KEY` (High, latent)

`app/core/config.py:26` defaults `SECRET_KEY` to `"change-me-in-production"` while `ENVIRONMENT` defaults to `"production"` (config.py:37). Every JWT surface signs with this key: auth/guest/impersonation strategies (`app/users.py:107,114,190,236`), OAuth state JWTs, password-reset secrets. Nothing asserts the key was changed. A prod `.env` that omits `SECRET_KEY` silently runs with a publicly known key — anyone could forge tokens for any user, including impersonation tokens. Prod is presumably configured correctly today; the gap is latent and cheap to close.

**Fix:** raise at startup if `ENVIRONMENT != "development"` and the key is the default (mirroring the existing D-22 deploy-blocker pattern in `get_insights_agent()`).

### 1.3 No password policy (Medium)

FastAPI-Users' default `validate_password` is a no-op and `UserManager` (`app/users.py:63-90`) doesn't override it; `/auth/register` and `/auth/guest/promote/email` accept a 1-character (even empty) password. **Fix:** override `validate_password` (min length, reject password == email).

### 1.4 Guest JWT lifetime says 30 days, is 365 (Medium)

`app/users.py:110`: `_GUEST_JWT_LIFETIME_SECONDS = 31536000  # 365 days`, while the docstrings in `auth.py:293,308` and `guest_service.py:5,35` promise 30-day tokens. No server-side revocation exists. Pick one number and align docs/code.

### 1.5 Lower-priority security/robustness items

- **Guest promotion TOCTOU** (`app/services/guest_service.py:176-181`): `IntegrityError` from an email-uniqueness race is swallowed as "idempotent"; the user stays a guest yet the flow redirects with `#promoted=1`. Re-check `updated.is_guest` after rollback.
- **`--forwarded-allow-ips='*'`** (`deploy/entrypoint.sh:10`): safe only because backend:8000 isn't published and Caddy strips untrusted XFF. Pin to the Caddy subnet so the guest-creation rate-limit key can't ever become spoofable.
- **Sentry spam from malformed OAuth `state`** (`app/routers/auth.py:199,396`): unauthenticated clients can burn Sentry quota; also `detail=f"OAuth error: {error}"` reflects user input. Log at debug, use a static detail.
- **IP rate limiter never evicts keys** (`app/core/ip_rate_limiter.py:27-41`): unbounded dict growth under IP spray. Delete empty keys.
- **Duplicate-import race** (`app/routers/imports.py:68-85`): the in-memory active-job check crosses two `await`s before the job is registered; two rapid POSTs launch two imports (games deduped by unique constraint, but double API load and racing counters). Register the job before the first `await` and add the DB backstop (see 4.4).

---

## 2. Import and remote-worker pipeline

### 2.1 Entry-ply drain has no all-fail circuit breaker (High) — VERIFIED

`app/services/eval_drain.py:2304-2308` marks every picked game `evals_completed_at = now()` regardless of eval success. `engine.evaluate()` returns `(None, None)` when the pool is dead (never started, broken binary, all workers failed — dead slots are re-queued by `_analyse`'s `finally` at `engine.py:494-495` and answer instantly). The full-ply drain explicitly guards this exact failure with the WR-05 circuit breaker (`eval_drain.py:2556-2570`); the entry drain doesn't. A dead pool therefore permanently stamps `_DRAIN_BATCH_SIZE` games per tick as "evaluated" with NULL evals at maximum loop speed — endgame analytics silently degrade and `resweep_holed_games` only re-arms *full*-eval holes, not entry holes. Side effect: `_apply_eval_results` (`eval_drain.py:1984-1994`) Sentry-captures per failed target, flooding Sentry during the same outage.

**Fix:** mirror WR-05: if all results in a non-empty batch are `(None, None)`, release the lease instead of marking complete, emit one aggregated Sentry event, sleep. Fix the `EnginePool` docstring (`engine.py:380-382`, claims dead slots are dropped; they aren't) in the same pass.

### 2.2 `/entry-submit` stamps completion for ALL games leased under the worker id (Medium-High)

`app/routers/eval_remote.py:746-813` selects `WHERE entry_eval_leased_by == worker_id AND evals_completed_at IS NULL` and marks the **full set** complete. If two workers share an id (operator runs a fixed `--worker-id`; legacy default `"remote-worker"`), or a fixed-id worker restarts mid-batch within the 20 s TTL, the first submit stamps the other batch's games complete with zero evals applied — silent, permanent entry-eval loss with no Sentry signal. The shipped worker generates random ids, so this is operator-error-triggered, but the blast radius is silent data loss.

**Fix:** return claimed `game_ids` from `/entry-lease` and stamp only the echoed/intersected set; at minimum add `entry_eval_lease_expiry > now()` to the guard.

### 2.3 chess.com archives fully buffered in memory (Medium-High, matches the OOM history)

`app/services/chesscom_client.py:314-324`: each monthly archive is materialized twice (raw response + parsed dict, both alive while the batch loop consumes it), up to `CHESSCOM_SEMAPHORE_LIMIT = 3` concurrent imports. A heavy bullet month is tens of MB of JSON × Python object overhead. Given the prod OOM history is import memory pressure and the backend has a 4 GB cap, this is the largest single allocation in the import path. Lichess correctly streams NDJSON; chess.com doesn't.

**Fix:** stream-parse (`ijson` over `aiter_bytes()`), or at minimum `del resp` after `.json()` and consume the games list destructively.

### 2.4 CPU-bound chess work blocks the event loop (Medium)

No `asyncio.to_thread`/executor exists anywhere in these paths:

- Import: `_collect_position_rows` (`import_service.py:908-946`) runs `process_game_pgn` (full PGN parse + 3 Zobrist hashes + classification per ply) for a 30-game batch synchronously — hundreds of ms to seconds of uninterrupted event-loop CPU, inside an open transaction.
- Worker endpoints: `/entry-lease` re-parses up to 50 PGNs (`eval_remote.py:686-700`); `/submit`/`/atomic-submit` run full replay + `classify_game_flaws` + `_derive_atomic_sentinel_lines` synchronously (`eval_remote.py:187-213, 1017-1052`).
- Interactive: `/suggestions` parses 10 PGNs (`position_bookmarks.py:96-111`); `/next-moves` replays one PGN per candidate (`openings_service.py:419-438`).

During an import, every API request (auth included) stalls behind these bursts. **Fix:** wrap the pure-CPU stages in `await asyncio.to_thread(...)`, keeping them outside open sessions (the import parse must move before the write session opens).

### 2.5 Worker-submitted evals are not range-validated (Medium)

`app/schemas/eval_remote.py:30-46`: `eval_cp`/`eval_mate` have no bounds, `pv`/`best_move` no `max_length`, `ply` no upper bound. The server clamps engine-path evals but applies worker values raw with `CAST(... AS smallint)` — an out-of-range value raises `DBAPIError` → 500 for the whole submit, and the worker's retry loop re-cycles the same game indefinitely (holes never resolve). Unbounded `pv` strings also mean one buggy worker can post multi-MB payloads. **Fix:** mirror the server-side clamps as Pydantic `Field` bounds at the trust boundary.

### 2.6 Full-ply `/submit`/`/atomic-submit` accept any game_id with zero lease validation (Medium)

Unlike `/entry-submit` (WR-02 filter), the full-ply paths trust `body.game_id` entirely (`eval_remote.py:216-382, 1100-1336`). A stale worker whose lease expired can interleave its delete-then-insert classification with the new claimant's (last-writer-wins evals; `ON CONFLICT DO NOTHING` can leave a mixed `game_flaws` set if classifications disagree). Robustness, not authz (all parties hold the operator token) — but the asymmetry with entry-submit is undocumented. **Fix:** require `eval_jobs.leased_by == X-Worker-Id AND status='leased'` for tier-1/2; consider a games-level lease for tier-3.

### 2.7 One malformed platform game object aborts the whole import (Medium)

`normalize_chesscom_game`/`normalize_lichess_game` are called unguarded per game (`chesscom_client.py:325-330`, `lichess_client.py:184-188`); a single `KeyError` fails the entire job. The CLAUDE.md per-game try/except rule is honored for PGN parsing but not normalization. **Fix:** per-game try/except + skip + one aggregated Sentry capture.

### 2.8 Lower-priority pipeline items

- **Fire-and-forget `asyncio.create_task` without saved references** (`imports.py:85`, `import_service.py:508,527`, `eval_drain.py:2331`): tasks hold only weak refs; a GC'd import task = job stuck in_progress until the 3 h reaper. Standard fix: module-level task set + done-callback (also enables clean shutdown cancellation).
- **Yield-gate counts aren't EXISTS probes** (`eval_drain.py:348-366`): `select(count()).limit(1)` counts the whole pending set per drain tick; use a real `LIMIT 1` existence probe.
- **`_jobs` registry never evicts terminal jobs** (`import_service.py:139`): unbounded process-lifetime growth.
- **Lichess retry restarts the NDJSON export from scratch** (`lichess_client.py:116-202`): correct but up to 3× wall time on large first imports; advance the cursor on retry.
- **Lichess-eval tier-1 jobs ping-pong** between worker lease and release (`eval_remote.py:460-463`), starving the worker's fall-through rungs on that poll cycle.
- **Unknown chess.com result combos default to draw** (`normalization.py:204-207`): a new result string would silently record decisive games as draws in WDL stats. Infer from the loser-side string and Sentry-capture unknowns.

---

## 3. DB query efficiency (with prod corroboration)

Prod baseline (see `reports/db-stats/db-report-prod-2026-07-02.md`): 12 GB, 686k games, 50M positions, cache hit 99.86%, no recurring app query above ~300 ms avg *at current scale*. The findings below are about aggregate load and headroom, and they compound: several purpose-built partial indexes are being defeated by missing predicates.

### 3.1 Endgame overview runs ~7 redundant GROUP BY scans of the user's endgame positions per request (High) — the top structural fix

Every repo function in the `GET /endgames/overview` path independently re-derives "which games have ≥6 endgame plies" from `game_positions` (`endgame_repository.py:43-66, 206-225, 363-382, 560-616, 656-756, 827-840`): entry rows (1), count (2), performance IN + NOT IN (3+4 — the subquery is embedded twice), buckets (5), timeline (6+7 — `.subquery()`, not a CTE, so it re-executes per statement), clock stats (8, with two `array_agg` per game). The insights path (`insights_service.py:160-183`) doubles this on cache miss (all-time + 3-month). The Phase 53 docstring claims the redundancy was eliminated; only entry-row sharing was done. For a heavy user each pass touches 10⁴–10⁵ index tuples, serially, on one pooled connection (pool 10+10, max_connections=30 shared with workers) — the same query family behind the earlier 135 s incident (quick-260617-pu4).

**Fix (in order of preference):** persist per-game endgame facts on `games` at import time (`endgame_entry_ply`, `endgame_entry_eval_cp/mate`, `endgame_ply_count`, per-class span info) so the dashboard never touches `game_positions`; or compute the span aggregation once per request and share it across all consumers. Also rewrite the two `Game.id.notin_(subq)` anti-joins as `NOT EXISTS` (`endgame_repository.py:596, 738`) — `NOT IN` can't be planned as an anti-join and this file already documents one planner meltdown from this shape.

### 3.2 `canonical_slice_sql` omits `user_id` — the partial covering index is unusable (High) — VERIFIED

The `game_positions` CTEs (`canonical_slice_sql.py:342-356, 611-618, 671-687, 759-770, 871-881, 937-947, 1016-1026`) filter `endgame_class IS NOT NULL AND game_id IN (SELECT id FROM recent_capped)` with **no `user_id` qualifier**. `ix_gp_user_endgame_game (user_id, game_id, endgame_class, ply) INCLUDE (eval_cp, eval_mate)` was built exactly for this predicate but needs the leading column; without it the planner falls back to per-game probes on `ix_game_positions_game_id` + heap-fetching every ply of every game (~240k heap rows per CTE). This runs ~50 times per user per Stage A/B percentile pass, triggered at import completion — competing with the import itself for buffers and connections.

**Fix:** one line per CTE — `JOIN recent_capped rc ON rc.id = gp.game_id AND rc.user_id = gp.user_id` (and a constant `gp.user_id = :user_id` bound on the single-user path). No index change needed.

### 3.3 `query_opening_phase_entry_metrics_batch` is a measured ~1.3 s query on hot paths (High)

`stats_repository.py:499-662` (own comment at :555 records "user 45 (39k games): CTE 1298ms"). `phase_entry_subq` has no `user_id` predicate (same disease as 3.2 — the PK `(user_id, game_id, ply)` would serve both the lookup and the `DISTINCT ON` ordering), and for shallow hashes the dedup set approaches the user's full game count. Called twice per most-played-openings request, once per explorer click, plus bookmarks and opening insights.

**Fix:** (a) immediate: add `user_id` to the subquery; (b) structural: persist `mg_entry_eval_cp/mate SMALLINT` on `games` at import (constant per game), deleting the `game_positions` stage entirely. Until then, consider serving the eval pillar lazily so explorer navigation isn't gated on it.

### 3.4 Opening Insights scans ply 0–16 × all games twice per request, uncached (High)

`openings_repository.py:653-694` groups over the user's whole opening region; the best index `ix_gp_user_full_hash_move_san` doesn't carry `ply` or `game_id`, so every ply≤28 entry heap-fetches (~3M tuples for a 100k-game user), twice (both colors), plus the H3.3 eval scans — on every filter change, no cache (unlike endgame LLM insights). **Fix:** replace the partial index with `(user_id, full_hash, move_san) INCLUDE (ply, game_id) WHERE ply <= 28` (also helps `query_next_moves`/`query_position_wdl_batch`), and cache results keyed on (user_id, filter hash, last_import_at).

### 3.5 Stats tab: same filtered-games set rebuilt ~6×, unbounded per-game comparison rows (Medium)

One Stats-tab load fires 3 endpoints that together evaluate the identical `apply_game_filters` subquery ~6 times and rescan the user's `game_flaws` ~4 times (`library_service.py:961-1099, 1311-1400, 1501-1595`). `fetch_flaw_comparison` returns one 32-column row per analyzed game (10⁴–10⁵ rows) so Python can compute mean+CI — computable in SQL as a single row (`avg`, `count`, `sum(x*x)`). **Fix:** one service call per page view sharing a `MATERIALIZED` CTE; push mean/CI into SQL.

### 3.6 Tier-4 drain pollers are the dominant prod DB load (Medium, from the DB report)

The two softmax-random selection queries consume ~45 min of DB time per 9 days (128 ms + 51 ms per call, every ~50 s), driving 60k buffer hits + 16k `game_flaws` probes per poll (EXPLAIN-verified: nested-loop semi join over all users × their games) and billions of probes on `uq_games_id_user_id` (~7k scans/s). Affordable today; O(users × games) per poll. **Fix when it matters:** maintain a small materialized pending-work set (or sample candidates before weighting) instead of weighting the full qualifying set per poll.

### 3.7 Lower-priority query items

- **COUNT(*) + OFFSET per page navigation** (`library_repository.py:1647`, `openings_repository.py:344`, `endgame_repository.py:507`): count once per filter change (or `count(*) OVER ()`); keyset pagination only if deep paging shows up in practice.
- **`ORDER BY played_at DESC NULLS LAST` defeats `ix_games_user_played_at`** (DESC = NULLS FIRST in PG; `game.py:60` vs the four archive queries): standardize on plain `.desc()` or add a matching index — EXPLAIN first.
- **N+1s:** bookmark suggestions (~40-50 round trips/request, `position_bookmark_repository.py:204-221`), per-bookmark time-series (`openings_service.py:302-318`) — batchable, low traffic.
- **`fetch_page_eval_positions` loads full ORM entities incl. `pv` TEXT** for every ply of every page game (`library_repository.py:1163-1190`): select only needed columns.

---

## 4. DB schema and migration safety

### 4.1 `ix_game_flaws_blob_backfill` will be dropped by the next autogenerate (High) — VERIFIED

The index (prod's most-scanned `game_flaws` index: 348M scans, backs every tier-4 idle poll) exists only in migration `20260630_220000_c3f5d1e8a092`, is not declared in `GameFlaw.__table_args__`, and is **absent from `_AUTOGEN_INDEX_IGNORELIST`** (`alembic/env.py:74-86` — verified: the list ends at `ix_games_needs_engine_full_evals`/`ix_eval_jobs_user_id`). The next `alembic revision --autogenerate` will emit `op.drop_index(...)`; if that slips through review, every idle poll seq-scans 3.36M rows. **Fix:** one line in the ignorelist (or declare it on the model — the env.py comment that "SQLAlchemy can't represent partial indexes in the ORM" is incorrect; the models already declare several).

### 4.2 Dev DB is missing four prod partial indexes despite being at Alembic head (Medium-High)

Dev lacks `ix_games_evals_pending`, `ix_games_full_evals_pending`, `ix_games_full_pv_pending`, `ix_games_needs_engine_full_evals` even though the migrations create them unconditionally and nothing drops them. The migration-only-index pattern has zero drift detection — the same silent drop in prod would surface only as slow queries. **Fix:** recreate on dev; add a 5-line startup or test assertion that the known migration-only index names exist in `pg_indexes`.

### 4.3 Schema hardening batch (Medium)

- **`game_flaws` composite FK:** replace the two independent FKs with `FOREIGN KEY (game_id, user_id) REFERENCES games(id, user_id) ON DELETE CASCADE` — the same SEED-041 §B1 treatment `game_positions` already got. Today nothing stops a flaw row claiming the wrong `user_id`, and every read path (and the scoped delete guard) trusts the denormalized column.
- **JSONB null landmine:** `allowed_pv_lines`/`missed_pv_lines` (`game_flaw.py:120-121`) lack `none_as_null=True`. Any future ORM write of Python `None` persists `null::jsonb`, which the backfill partial index, the tier-4 lottery, and `backfill_multipv.py` all skip via `IS NULL` — a permanently invisible, never-filled row. This exact class already bit the project (Phase 145). Declare `JSONB(none_as_null=True)` and consider a `jsonb_typeof(...) IS DISTINCT FROM 'null'` CHECK.
- **Zero CHECK constraints in the entire schema** (prod `pg_constraint` count = 0) despite CLAUDE.md rule 4 mandating them for enum-like columns. Start with `game_flaws.severity IN (1,2)`, `eval_jobs.status`, `games.platform`, added as `NOT VALID` + `VALIDATE` to avoid long locks.
- **`import_jobs` has no natural-key constraint:** add the partial unique index `(user_id, platform) WHERE status IN ('pending','in_progress')` (the `uq_eval_jobs_game_active` pattern) as the cross-process backstop for finding 1.5.
- **`benchmark_metric` native ENUM** (23 labels, 12 admittedly redundant, already one destructive reshape): migrate to `TEXT + CHECK` next time it's touched, per the project's own rule.

### 4.4 Dead/near-dead indexes (Medium, corroborated by prod stats)

- `ix_games_full_pv_pending` — 0 scans, 20 MB; no code path queries the predicate anymore (grep-verified). Drop CONCURRENTLY.
- `ix_games_full_evals_pending` — 1 scan, 18 MB; superseded by the user-leading indexes. Drop.
- `ix_gp_full_hash_opening` — 2 scans, 180 MB; its D-116-02 consumer was replaced by the `opening_position_eval` cache. Reconcile the stale coupling comments (`eval_drain.py:116`, `game_position.py:112-121`) first, then drop. All three tax every `games` update / position COPY.
- `ix_gp_user_white_hash`/`ix_gp_user_black_hash` (620 MB combined, 42 scans in 9 days) back the system-opening filter feature — keep, but this is a known cost.
- `opening_position_eval` has never been analyzed (stats 28× off: n_live_tup 59k vs 1.69M actual). Run `ANALYZE`; consider autovacuum tuning for insert-only tables.

### 4.5 Low schema items

`games.time_control_bucket` NULLs (383 rows) vanish from explicit all-bucket filters; `Game.positions` cascade lacks `passive_deletes=True`; `user_activity` surrogate PK + unique could be a natural composite PK; `game_positions` row alignment wastes ~6 bytes/row (~285 MB) — only worth fixing piggy-backed on a future table rewrite; eval-completion predicates duplicated as raw SQL strings across `eval_queue_service.py` while canonical hybrids exist on `Game` (drift risk).

---

## 5. Statistical correctness

The core machinery verified correct: ply parity/color attribution (single SQL source `is_opponent_expr`, consistent everywhere), eval sign conventions (white-perspective with uniform flip, mate branch priority identical in Python and SQL), Wilson utilities (formula, guards, two-sided p), draw handling (0.5 everywhere; conversion wins-only, recovery wins+draws), TC bucketing (single implementation, stored once), rating-at-game-time (never current rating), CDF direction (all 11 metrics higher-is-better), Endgame ELO timeline math. Findings:

### 5.1 Time-pressure quintile significance test is anti-conservative (High)

`endgame_service.py:2326-2328`: every eligible game contributes to *both* the user-quintile and opponent-quintile splits with exactly inverted outcomes (`:2228-2237`). When both players land in the same quintile (common in Q0 — mutual time trouble is correlated), the same games sit on both sides of `compute_score_difference_test`, which assumes independent cohorts, so the anti-correlated covariance term is dropped from the variance. Worked example: 100 fully-shared games with true SE 0.10 get reported SE 0.0707 — a delta of +0.14 reads z=1.98 (p≈0.048, "significant") when the true z is 1.4 (p≈0.16). The docstring's independence claim (`:2140-2143`) is wrong. **Fix:** track the shared-game count m per (tc, quintile) and add the `+2m·cov/(n_u·n_o)` term (or use a paired test for the overlap). Point estimates are unaffected.

### 5.2 `to_date` silently ignored by half the endgame overview (Medium)

`get_endgame_overview` (`endgame_service.py:3528-3545, 3647-3650`) and `get_endgame_timeline` (`:3225-3243`) fetch with `to_date=None` and Python-filter only the *lower* bound, while `bucket_rows`/`entry_rows` in the same response pass `to_date` to SQL. With a bounded date range, the documented invariant `sum(material_rows.games) == endgame_wdl.total` breaks and the overview disagrees with `/endgames/performance`. **Fix:** apply the upper bound in the same Python filters (rows `r[0] <= to_dt`, clocks `r[8] <= to_dt`).

### 5.3 Page-level entry-eval mean not outlier-trimmed (Medium)

`endgame_service.py:2962-2978` sums signed `eval_cp` with no `abs(...) < EVAL_OUTLIER_TRIM_CP` guard, while every sibling aggregate trims at 2000 and `compute_eval_confidence_bucket`'s contract assumes trimmed inputs. One +9000 cp adjudicated game among 50 entries shifts the reported mean from ~+0.5 to ~+2.35 pawns and distorts the CI. **Fix:** add the trim guard.

### 5.4 Percentile ties rank at the bottom of the plateau (Medium, PLAUSIBLE magnitude)

`global_percentile_cdf.py:162-176`: `bisect_left` + the plateau branch return the *lowest* percentile of a run of identical breakpoints. Rate metrics are quantized (conversion at the 30-game floor moves in 1/30 steps; `net_flag_rate` clusters at 0), so plateaus are wide — a median user can read "35th percentile" and land near the red band. **Fix:** mid-rank (Hazen) tie treatment: return the plateau's midpoint percentile.

### 5.5 Low statistical items

Wilson applied to means of continuous expected scores (conservative, mislabeled variance — accepted Phase 83 decision, noted only); zone boundary semantics contradict the ZoneSpec docstring at exact boundaries (`endgame_zones.py:150-157` vs `832-845`); per-bucket scores derived from rounded percentages (≤0.00075 error; the page-level fix from Phase 85.1 WR-01 wasn't applied to bucket rows; `_wdl_to_score` is dead code); opening-insights gate and classification use different WDL bases (documented D-04 decision — consistency observation); `derive_user_result` maps unknown results to "loss" (verify `SELECT count(*) FROM games WHERE result NOT IN (...)` is 0); flaw parity derived from list index rather than the stored `ply` (correct under the current invariant — add a cheap assertion to fail loud); `_is_unpunished` end-of-game branch also fires on missing-eval replies (`flaws_service.py:785-793`); NaN can theoretically reach a plain-JSON boundary (`insights_service.py:1045-1059`).

---

## 6. Tactic tagging (new feature — precision/recall)

Fresh report: `reports/tactic-tagger/tactic-tagger-2026-07-02.md` — numbers identical to 2026-06-23 (no regressions). Micro-averaged train precision **0.998** (18,534 TP / 46 FP): precision is essentially solved. Recall is the weak axis, and the FN breakdown changes what "improving recall" means: silent misses (detector returned nothing) are **zero for every motif except trapped-piece (45)**. Nearly all recall loss is "shadowed" — the puzzle carries multiple themes and single-winner dispatch returned a different but *also-correct* motif. Loosening detectors cannot recover that; it's zero-sum dispatch.

### 6.1 Production-only correctness defects (High — invisible to the fixture harness)

- **`has_forced_mate` is a no-op** (`tactic_detector.py:2462-2490`): the flag gates entry to the mate branch, but every mate detector re-checks `boards[-1].is_checkmate()` and bails. Empirically verified: truncated mate-in-2 PV + `has_forced_mate=True` → no tag. Production passes the flag for `eval_mate > 0` flaws, and with `PV_CAP_PLIES = 12`, mates-in-7+ always have truncated PVs — so deep mates **never tag as mate** in production, getting an incidental motif or nothing. Zero test coverage on the flag. **Fix:** fall back to generic `mate` when the flag is set but the truncated PV doesn't end in checkmate (skip geometry-dependent named subtypes).
- **Production boards lose en-passant and castling state** (`flaws_service.py:443-451`): `fen_map` stores `board_fen()` only. Verified consequences: a castling/ep flaw move fails `parse_san` → no tag; worse, a PV starting with an ep capture is pushed as a quiet pawn move **without removing the captured pawn**, silently corrupting the board for the whole line → bogus motif geometry. **Fix:** store `board.fen()` in the detector-internal `fen_map` (the replay already has it; keep `board_fen()` for Zobrist comparisons per the CLAUDE.md rule).

### 6.2 Precision/recall improvements, ranked

1. **Trapped-piece empty-escape-set fix** — the only positive-sum recall gain available: all 45 genuine silent FNs are cornered pieces with *zero* legal moves, rejected by the deliberate deviation at `tactic_detector.py:918-922`. Flipping to cook semantics ≈ recall 0.770 → ~0.83 with precision at 1.000 and headroom over the floor. Re-measure train+test before shipping.
2. **Discovered-attack depth breaks the forcing gate** (Medium): the detector returns an odd depth (WR-02, `:885-893`), but `forcing_line_gate.py:354-371` models solver nodes at even indices — the actual firing move is excluded from the only-move requirement, under-gating production discovered-attack tags. Cheapest fix: normalize `firing_depth` at the gate boundary (`flaws_service.py:579`).
3. **Make recall goals multi-label-aware**: fork FN = 908 with 0 silent / 0 wrong; the fork 0.60 and discovered-attack 0.30 recall goals are structurally unreachable by detector edits. Count "shadowed by another correct theme" as satisfied so `--check-goals` / the improvement loop doesn't churn on unreachable targets.
4. **Dispatch hygiene**: `self-interference` fires at `met >= 1` (confidence 50) and steals dispatch while being query-suppressed — the position silently loses its real chip. Require `met == 2` or drop it from Tier-3. `doubleBishopMate` *does* exist in the fixture data (4 rows), so it can be validated instead of suppressed (resolves OQ-2 in `motif_theme_map.py:23`); fix the boden file-side test for equal-file bishops while there.
5. **ep-aware capture predicates**: several anchors use `piece_at() is not None` and miss en-passant captures; `_move_was_capture` exists but only intermezzo uses it. Tiny principled gain.

Not recommended: chasing discovered-check's 33 FPs — several are geometrically genuine discovered checks that lichess labeled only `discoveredAttack` (label-noise ceiling, no separating feature found), and tightening trades against its already-low 0.337 recall.

---

## 7. Architecture and layering (Medium overall)

- **Connections held across external calls:** `generate_insights` holds the request's pooled connection through the LLM call, which has **no explicit timeout** (`insights_llm.py:2534-2540, 298-347`) — ~20 concurrent generations exhaust the 10+10 pool for the whole app. `google_callback_promote` similarly touches the DB before the Google token exchange (`auth.py:417-430`; the plain callback gets it right). Fix: release/scope sessions before external awaits; set a model-request timeout.
- **`eval_remote.py` is a 1,372-line router with business logic, raw SQL, and ~20 underscore-private imports** from eval_drain/eval_queue_service/flaws_service — breaches the routers-are-HTTP-only rule and makes any drain refactor break the router. Extract an `eval_remote_service.py`, promote the shared functions to public names.
- **Duplicated filter logic in `openings_repository.py:102-135, 175-200`** re-implements the full filter block inline, violating the single-source `apply_game_filters` rule — silent drift here skews openings WDL vs every other surface. Refactor to the shared util.
- **Known ungated-tactic-tag root cause:** `_classify_and_fill_oracle(..., blobs_pending: bool = False)` (`eval_drain.py:683`) — the defaulted safety flag is why the local drain re-mints raw cp tags (already tracked). Make it keyword-only with no default. Verified no siblings: both remote submit paths pass `True` explicitly.
- **Insights router reaches into private service members** and re-implements the Tier-1 cache lookup (`insights.py:218,232`); no per-user rate limit on the LLM failure path (`insights.py:91-162` — each failed retry pays a fresh LLM call).

Verified clean: admin/impersonation auth (superuser gates, per-request re-validation), operator-token `hmac.compare_digest` fail-closed, per-user IDOR guards on all data routers, CORS dev-only, lifespan shutdown ordering, Sentry `before_send` fingerprinting, `send_default_pii=False`.

---

## 8. Frontend (superficial pass, as requested)

1. **Single 1.5 MB main JS chunk** — only `AnalysisPage` is lazy; recharts + react-chessboard + chess.js + all authenticated pages ship to the public homepage (`App.tsx:42`, no `manualChunks`). Lazy-load the authenticated pages and/or split vendor chunks.
2. **Home profile query has no `isError` branch** (`Home.tsx:614-643`): on API failure an authenticated user is silently redirected to `/library/import` as if they had no games — exactly the fall-through the project rule forbids.
3. **Component size:** `Openings.tsx` (~665 logic LOC before the return), `Endgames.tsx`, `EvalChart.tsx`, `LibraryGameCard.tsx` all far exceed the project's own limits — extract data hooks when next touched.
4. Minor: hardcoded theme-relevant colors in `Home.tsx`/`MoveExplorer.tsx`; silent `gameCount` query failure in Openings; 471 KB dead `prerender-*.js` in dist assets.

Compliant spot-checks: global query error capture centralized correctly, Sentry tags on manual fetches, no `any`/`@ts-ignore` hotspots, filter store architecture clean, memoization where it matters.

---

## 9. Production DB health (summary; full report in `reports/db-stats/db-report-prod-2026-07-02.md`)

- 12 GB total; `game_positions` is 74% (8.9 GB, 4 GB indexes). Cache hit 99.86%; autovacuum healthy; dead-tuple ratios fine.
- **Sanity checks PASS**: flaw counts match lichess aggregates within 0.3%, zero null-count gaps; zero analyzed games invisible to the Flaws Timeline (both platforms).
- Dominant load = tier-4 drain pollers (finding 3.6). No recurring app query above ~300 ms avg. `games` shows regular full-table seq scans (~70k since June 23) not attributable to the EXPLAIN-verified poller — worth an `auto_explain` session.

---

## Suggested sequencing

1. **This week (small, high-leverage):** #1 auth on import status, #3 ignorelist line + dev index restore, #9 SECRET_KEY guard, #11 worker input bounds, `ANALYZE opening_position_eval`.
2. **Next milestone candidates:** #2 entry-drain circuit breaker, #4 tactic production fixes (has_forced_mate, fen_map), #6 entry-submit scoping, #7 chess.com streaming, #10 stats fixes, #12 schema hardening batch.
3. **Structural (plan as phases):** #5 endgame/openings per-request aggregation elimination (import-time per-game columns is the durable fix), #8 to_thread offloading, #13 tier-4 poller restructure, #14 tactic recall items, #15 frontend code-splitting.

Per the GSD process, none of this was implemented — recommended capture: items in (1) as a quick-task batch, (2)–(3) as seeds/phases for the next milestone planning pass.
