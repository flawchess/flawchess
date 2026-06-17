---
phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - alembic/versions/20260616_120000_phase_123_entry_eval_lease.py
  - app/models/game.py
  - app/services/eval_drain.py
  - tests/test_eval_worker_endpoints.py
autonomous: true
requirements: ["SEED-051-D-1", "SEED-051-D-3", "SEED-051-D-9", "D-01", "D-03", "D-04", "D-09"]
nyquist_compliant: true

must_haves:
  truths:
    - "A new big-import game can be atomically leased by exactly one claimer (server or remote); a second concurrent claim returns a disjoint set (no double-lease)"
    - "The in-process server drain (_pick_pending_game_ids) claims through the lease column and sets the lease when it picks (D-01) — server and remote workers strictly partition the same import"
    - "A crashed/stale lease (entry_eval_lease_expiry < now()) is reclaimable by the next claimer (TTL reclaim)"
    - "The migration adds two nullable columns to games with no data loss and no backfill (NULL = unclaimed is correct)"
  artifacts:
    - path: "alembic/versions/20260616_120000_phase_123_entry_eval_lease.py"
      provides: "Migration adding entry_eval_lease_expiry + entry_eval_leased_by VARCHAR(16) to games"
      contains: "entry_eval_lease_expiry"
    - path: "app/models/game.py"
      provides: "entry_eval_lease_expiry + entry_eval_leased_by mapped_columns"
      contains: "entry_eval_leased_by"
    - path: "app/services/eval_drain.py"
      provides: "Shared _claim_entry_eval_games SKIP-LOCKED LIFO helper + entry-ply constants + D-01 server lease"
      contains: "_claim_entry_eval_games"
  key_links:
    - from: "app/services/eval_drain.py::_pick_pending_game_ids"
      to: "app/services/eval_drain.py::_claim_entry_eval_games"
      via: "server-side lease claim (D-01)"
      pattern: "_claim_entry_eval_games"
    - from: "app/services/eval_drain.py::_claim_entry_eval_games"
      to: "games.entry_eval_lease_expiry"
      via: "UPDATE ... FOR UPDATE SKIP LOCKED RETURNING id"
      pattern: "FOR UPDATE SKIP LOCKED"
---

<objective>
Lay the entry-ply lease foundation: the migration + model columns, the single canonical SKIP-LOCKED LIFO claim helper over `games`, the named tuning constants (D-03/D-04), and the D-01 server-side lease in `_pick_pending_game_ids`. Also make the test fixture able to insert pending (un-evaluated) games.

Purpose: Everything downstream (the `/entry-lease` + `/entry-submit` endpoints in Plan 02, the worker ladder in Plan 03) depends on the lease columns existing and on the shared claim helper. D-01 closes the last source of wasted depth-15 CPU by making the server pool partition the same import as remote workers (neither double-evaluates a game).

Output: New `games` lease columns, the `_claim_entry_eval_games` helper, `ENTRY_LEASE_*` constants, a lease-claiming `_pick_pending_game_ids`, and an `evals_completed_at` kwarg on the test fixture.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

@.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-CONTEXT.md
@.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-RESEARCH.md
@.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-PATTERNS.md

# Read these source files first for exact analog shapes:
@app/services/eval_queue_service.py
@app/services/eval_drain.py
@app/models/game.py
@tests/test_eval_worker_endpoints.py
@alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py
</context>

## Artifacts this phase produces (Plan 01 subset)

- `games.entry_eval_lease_expiry` (DateTime tz, nullable) — new column
- `games.entry_eval_leased_by` (`String(16)` / VARCHAR(16), nullable) — new column, D-09 (NOT Text)
- `ENTRY_LEASE_TTL_SECONDS` (int, ~20) — new module-level constant (D-03/D-04)
- `ENTRY_LEASE_BATCH_SIZE` (int, 50) — new module-level constant (D-03)
- `ENTRY_LEASE_BACKLOG_THRESHOLD` (int, 300) — new module-level constant (D-03)
- `_claim_entry_eval_games(session, worker_id, batch_size, ttl_seconds)` — new shared SKIP-LOCKED LIFO claim helper
- `_pick_pending_game_ids` — now a lease claim (D-01)
- `_insert_game(..., evals_completed_at=...)` — new test-fixture kwarg

<tasks>

<task type="auto">
  <name>Task 1: Migration + model columns for the entry-ply lease</name>
  <files>alembic/versions/20260616_120000_phase_123_entry_eval_lease.py, app/models/game.py</files>
  <read_first>
    @alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py (nullable col + partial index on games; manual revision-ID style)
    @app/models/game.py (the evals_completed_at / full_evals_completed_at mapped_columns block + __table_args__ partial-index comment convention)
    PATTERNS.md "alembic/versions/<new>" and "app/models/game.py" sections (exact column shapes).
  </read_first>
  <action>
    Hand-write the migration file (this project does NOT autogenerate the scaffold — mirror the manual revision-ID style of the analog). Set `down_revision = "7d5a4aa09a47"` (verified current head via `uv run alembic heads`). In `upgrade()` add two nullable columns to `games`: `entry_eval_lease_expiry` as `sa.DateTime(timezone=True)`, and `entry_eval_leased_by` as `sa.String(16)` (per D-09 — VARCHAR(16), NOT Text). Add NO new index and NO backfill — NULL means unclaimed, which is the correct default (this is the one way this migration differs from the evals_completed_at analog, which DID backfill). In `downgrade()` drop the columns in reverse order. The existing `ix_games_evals_pending` partial index already backs both the LIFO `ORDER BY id DESC` claim and the D-5 OFFSET probe (RESEARCH Assumption A2), so no index work is needed.

    In `app/models/game.py` add the two matching `mapped_column`s in the same eval-marker block as `evals_completed_at`: `entry_eval_lease_expiry: Mapped[datetime.datetime | None]` and `entry_eval_leased_by: Mapped[str | None]` with `sa.String(16)`. Add a one-line comment citing Phase 123 SEED-051 D-3/D-9. Do NOT add a new `Index(...)` to `__table_args__` (follow the existing convention: partial indexes live in the migration, declared only as a comment in the model).
  </action>
  <verify>
    <automated>uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head && uv run ty check app/models/game.py</automated>
  </verify>
  <acceptance_criteria>
    `alembic upgrade head` then `downgrade -1` then `upgrade head` all succeed (round-trip clean). The two columns exist on `games`, both nullable, `entry_eval_leased_by` is `character varying(16)`. `ty check` is clean on the model. No new index added.
  </acceptance_criteria>
  <done>Migration round-trips cleanly; model has the two nullable mapped_columns; entry_eval_leased_by is VARCHAR(16).</done>
</task>

<task type="auto">
  <name>Task 2: Shared SKIP-LOCKED LIFO claim helper + constants + D-01 server lease</name>
  <files>app/services/eval_drain.py, tests/test_eval_worker_endpoints.py</files>
  <read_first>
    @app/services/eval_queue_service.py (the `_claim_queued_job` SKIP-LOCKED CTE — the exact bound-param discipline + the `(:ttl || ' seconds')::interval` / `str(ttl_seconds)` TTL idiom; the `WORKER_ID_SERVER_POOL` constant; the claim+commit short-session discipline in `claim_eval_job`)
    @app/services/eval_drain.py (the current unlocked `_pick_pending_game_ids` SELECT and its short-session wrapper; `run_eval_drain` callers)
    PATTERNS.md "app/services/eval_drain.py" section (constants block + helper body + D-01 call-site rewrite) and "Shared Patterns → Bound-param SKIP-LOCKED claim" + "Short-session discipline".
    @tests/test_eval_worker_endpoints.py (the `_insert_game` fixture — it hardcodes `evals_completed_at=now()` with no override).
  </read_first>
  <action>
    In `app/services/eval_drain.py`, add a module-level constants block near where the entry-ply claim/drain logic lives: `ENTRY_LEASE_TTL_SECONDS: int = 20` (D-04 — short, well under the 120s full-ply `LEASE_TTL_SECONDS`; entry batches are seconds of work; RESEARCH Pitfall 3 sanctions 15-30s), `ENTRY_LEASE_BATCH_SIZE: int = 50` (D-5 starting knob), `ENTRY_LEASE_BACKLOG_THRESHOLD: int = 300` (D-5 starting knob; the probe in Plan 02 uses THRESHOLD-1 as OFFSET). Each constant gets an inline comment naming the decision and rationale (no magic numbers — CLAUDE.md).

    Add `async def _claim_entry_eval_games(session, worker_id: str, batch_size: int, ttl_seconds: int) -> list[int]`: a single `sa.text` `UPDATE games SET entry_eval_lease_expiry = now() + (:ttl || ' seconds')::interval, entry_eval_leased_by = :worker_id WHERE id IN (SELECT id FROM games WHERE evals_completed_at IS NULL AND (entry_eval_lease_expiry IS NULL OR entry_eval_lease_expiry < now()) ORDER BY id DESC LIMIT :batch FOR UPDATE SKIP LOCKED) RETURNING id`. Bind EVERY value as a `:param` (`ttl`, `worker_id`, `batch`) — NEVER f-string-interpolate (project Security rule; mirror `_claim_queued_job`). Bind `ttl` as `str(ttl_seconds)` (the verbatim `_claim_queued_job` TTL idiom). Return `[row[0] for row in result.all()]`. This is the ONE canonical claim — Plan 02's `/entry-lease` calls the same helper. Do NOT write a second copy.

    Rewrite `_pick_pending_game_ids` (D-01): replace its current unlocked `SELECT … ORDER BY id DESC LIMIT n` body with a call to `_claim_entry_eval_games(session, WORKER_ID_SERVER_POOL, limit, ENTRY_LEASE_TTL_SECONDS)`. Import `WORKER_ID_SERVER_POOL` from `eval_queue_service`. Keep the short-session wrapper and `commit()` the lease so it is durable before the engine drain work begins (mirror `claim_eval_job`'s commit-then-release discipline — never hold the lock across the gather; CLAUDE.md "never asyncio.gather on the same AsyncSession"). The lease ends naturally: `_mark_evals_completed` stamping `evals_completed_at = now()` makes the queue predicate stop matching (permanent release); a crashed server pick is reclaimed by the TTL. Use `Literal`/typed signatures; `ty check` must stay clean.

    In `tests/test_eval_worker_endpoints.py`, add an `evals_completed_at: datetime | None = <current default>` keyword to `_insert_game` (mirror the existing `full_evals_completed_at` kwarg) so entry-ply pending-queue tests can insert games with `evals_completed_at=None`. Preserve the existing default behavior (today's hardcoded `now()`) when the kwarg is not passed — un-changed callers must behave identically.
  </action>
  <verify>
    <automated>uv run pytest tests/test_eval_worker_endpoints.py -x && uv run ty check app/services/eval_drain.py</automated>
  </verify>
  <acceptance_criteria>
    `_claim_entry_eval_games` exists, binds all values as params (no f-string in the sa.text), uses `FOR UPDATE SKIP LOCKED` + `ORDER BY id DESC`. `_pick_pending_game_ids` calls it with `WORKER_ID_SERVER_POOL` and commits the lease. The three `ENTRY_LEASE_*` constants are module-level with rationale comments. `_insert_game` accepts `evals_completed_at` and defaults to today's behavior. The existing endpoint test file still passes (no regression on the un-changed fixture default). `ty check` clean.
  </acceptance_criteria>
  <done>Shared claim helper + constants exist; server drain leases through them (D-01); fixture supports pending games; existing tests green; ty clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Lease-partition + TTL-reclaim tests for the shared claim helper</name>
  <files>tests/test_eval_worker_endpoints.py</files>
  <read_first>
    @tests/test_eval_worker_endpoints.py (the `eval_worker_session_maker`, `eval_worker_test_user`, the now-extended `_insert_game(evals_completed_at=...)`, `_delete_games`, and `_patch_router_session` fixtures — reuse verbatim, no new conftest infra).
    PATTERNS.md "tests/test_eval_worker_endpoints.py" section (lease_partition test shape: two concurrent claims return disjoint id sets).
    VALIDATION.md task 123-02-02 row (SKIP-LOCKED LIFO claim partitions games; no double-lease).
  </read_first>
  <behavior>
    - lease_partition: insert > batch_size pending games (evals_completed_at=None). Two sequential `_claim_entry_eval_games` calls with DIFFERENT worker_ids each return a non-empty list; the two id sets are DISJOINT (no game leased twice). (Sequential calls suffice to assert the predicate excludes already-leased rows; the SKIP LOCKED behavior under true concurrency is a DB guarantee.)
    - lease_lifo: the first claim returns the highest ids (newest-import-first, ORDER BY id DESC).
    - lease_reclaim: a game whose `entry_eval_lease_expiry` is in the PAST (set it manually < now()) is re-claimable by a subsequent `_claim_entry_eval_games` call (TTL reclaim); a game with a FUTURE lease expiry is NOT returned.
    - leased_by_set: after a claim, the leased games' `entry_eval_leased_by` equals the worker_id passed.
  </behavior>
  <action>
    Add the above tests to `tests/test_eval_worker_endpoints.py`, reusing the existing fixtures. Use the extended `_insert_game(evals_completed_at=None)` to create pending games. Drive `_claim_entry_eval_games` directly against the test session-maker (it is a service-layer helper, no HTTP needed). For lease_reclaim/future-lease, set `entry_eval_lease_expiry` directly via an UPDATE on the test session before re-claiming. Clean up inserted games with `_delete_games` in teardown to keep the shared test user's rows isolated.
  </action>
  <verify>
    <automated>uv run pytest tests/test_eval_worker_endpoints.py -k "partition or reclaim or lifo or leased_by" -x</automated>
  </verify>
  <acceptance_criteria>
    Four tests pass: disjoint partition, LIFO ordering, past-lease reclaim + future-lease exclusion, and leased_by population. They run against the per-run test DB (migration auto-applied) with no new conftest infra.
  </acceptance_criteria>
  <done>Lease-claim correctness (partition, LIFO, TTL reclaim, leased_by) is covered by automated tests; all green.</done>
</task>

</tasks>

<verification>
- `uv run alembic upgrade head` / `downgrade -1` / `upgrade head` round-trips clean.
- `uv run pytest tests/test_eval_worker_endpoints.py -x` green (existing + new lease tests).
- `uv run ty check app/ tests/` clean.
- The shared claim binds all sa.text values as params (grep: no f-string `{...}` inside the `_claim_entry_eval_games` sa.text body).
</verification>

<success_criteria>
- Two nullable lease columns on `games` (entry_eval_leased_by is VARCHAR(16), not Text).
- One canonical `_claim_entry_eval_games` SKIP-LOCKED LIFO helper, called by `_pick_pending_game_ids` (D-01).
- Three named tuning constants (TTL ~20s, batch 50, threshold 300) with rationale comments.
- Lease partition + TTL reclaim + LIFO + leased_by covered by automated tests.
- No double-lease: server pool and (future) remote endpoint partition the same import.
</success_criteria>

<output>
Create `.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-01-SUMMARY.md` when done.
</output>
