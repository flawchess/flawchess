# Phase 149: Retire & Prune - Research

**Researched:** 2026-07-04
**Domain:** Backend deletion (dead protocol + dead code) + 2 durability migrations, FastAPI/SQLAlchemy async, Postgres partial unique indexes
**Confidence:** HIGH (all CONTEXT.md breadcrumbs verified against live code this session; a few real drifts found and documented below)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Worker Heartbeats (PRUNE-06) — DISCUSSED (deep-dived with the user):**
- **D-01 — Write cadence:** Upsert on every live submit (entry-submit, flaw-blob-submit, atomic-submit). No throttle.
- **D-02 — Counts:** Accumulate cumulative `submit_count` and `evals_submitted` (sum of `len(evals)` per submit).
- **D-03 — Version columns:** Store both `sf_version` (string, updated on every submit) and `worker_schema_version` (int, nullable — only the atomic lane sends it; leave NULL / don't overwrite when the lane doesn't provide it).
- **D-04 — Trigger events:** Submits only. Do not upsert on lease endpoints.
- **D-05 — Table shape (guidance):** `worker_heartbeats(worker_id PK, last_ip NULLABLE, sf_version, worker_schema_version NULLABLE, last_seen, submit_count, evals_submitted)`. `worker_id` matches the advisory `X-Worker-Id` identity (VARCHAR(16), see `worker_id_label`). Upsert via `INSERT ... ON CONFLICT (worker_id) DO UPDATE` (counts `= existing + delta`, `last_seen = now()`, `last_ip`/versions overwritten with latest). Planner/researcher decide exact column types and whether to funnel the three submit handlers through one shared helper.
- **D-06 — Worker IP (`last_ip`):** Store as `last_ip TEXT NULL`, populated from `request.client.host` in the same submit upsert. Most trustworthy fleet-identity signal (disambiguates spoofed/shared worker_id). Free in prod (`--proxy-headers --forwarded-allow-ips='*'`). Nullable because `request.client` can be `None` in tests. Store only the latest IP (no history). Add a one-line column comment noting these are operator-owned worker machines, negligible GDPR surface. Beyond the literal R15 enumeration `(worker_id, version, last_seen, counts)` — added deliberately (user-approved 2026-07-04).

**Claude's Discretion — locked-by-requirements, capture sensible defaults (NOT deep-discussed):**
- **D-07 — PRUNE-03 "unknown" result flow:** `GameResult` is `Literal["1-0","0-1","1/2-1/2"]` — no "unknown" member. Do NOT widen `GameResult`. Have `_normalize_chesscom_result` signal "unknown" out-of-band and let `normalize_chesscom_game` skip the game (return `None`) rather than store a fabricated draw. Emit `sentry_sdk.capture_message`/`capture_exception` with `white_result`/`black_result` in `set_context` (never in the message string). Confirm downstream callers tolerate the extra `None` skip. Planner may instead choose to persist the game with a nullable/unknown result if skipping loses a game the user played — flag the trade in the plan.
- **D-08 — PRUNE-05 durable import guard:** Add a partial unique index `(user_id, platform) WHERE status IN ('pending','in_progress')` and create the `import_jobs` row in the request handler (`app/routers/imports.py::start_import`) before `asyncio.create_task`. On `IntegrityError` from the index, return the existing active job with HTTP 200 (preserve the current dedup contract), not a 409. The in-memory `find_active_job` fast-path may stay as a cheap pre-check but is no longer the guarantee.
- **D-09 — PRUNE-01/02 deletion scope:** `tests/test_eval_worker_endpoints.py` covers both dead Gen-1 `/lease`+`/submit` and the LIVE `/entry-lease`+`/entry-submit` lanes plus `_claim_entry_eval_games` helpers. Surgical removal only — delete the Gen-1 tests, KEEP every entry-lane/atomic/flaw-blob test. Do not delete the whole file. For tier-2: remove the lane logic but keep the DB column. `/flaw-blob-*` is untouched.
- **D-10 — PRUNE-04:** `worker_schema_version` already arrives in `AtomicSubmitRequest`. Telemetry recording only (log/tag), no worker change, no rejection gate.

### Claude's Discretion
Everything not covered by D-01…D-10 above is delegated: the user explicitly treated the remaining gray areas as locked by REQUIREMENTS/ROADMAP. The defaults captured in D-07…D-09 are guidance — flag (don't silently override) if research surfaces a reason to deviate. This RESEARCH.md surfaces three such reasons (see Pitfalls 1-3): (1) deleting `TestTier1Claiming` needs an atomic-lane test replacement first; (2) "tier-2 lane logic" has no deletable branch — only a dead constant + docstring narrative; (3) the `import_jobs` durable-row creation currently lives in `_bootstrap_import_job`, not `create_job` as D-08's breadcrumb assumed — the fix must move it, not just reorder around an existing call.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (Milestone-level deferrals already recorded in SEED-080: 426 version-rejection gate, R14 tier-3 lease, entry/full lane merge, SEED-078 streaming.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| PRUNE-01 | Delete the dead Gen-1 protocol (`/lease`+`/submit`+`_apply_submit`+worker `_handle_full_ply_response`+associated tests); `/flaw-blob-*` retained | Exact line numbers confirmed for all 4 deletion targets; mechanically-verified 28-test deletion list + 67-test keep list in Code Examples; Pitfall 1 (job_id/lichess-skip coverage gap) and Pitfall 4 (isolation-proof tests referencing the dead endpoint) identify the two correctness risks |
| PRUNE-02 | Remove dead weight: tier-2 lane code (DB column kept), `hashes_for_game`, `chesscom_to_lichess` future-use tables, caller-less `Game.needs_engine_full_evals` | Pitfall 2 corrects the tier-2 scope (no deletable branch exists); Code Examples correct the `chesscom_to_lichess` scope to Table-3-only (Tables 1/2 are live); `hashes_for_game`'s 18 dependent tests + `process_game_pgn` replacement path enumerated; `needs_engine_full_evals` confirmed zero real callers (only comments) |
| PRUNE-03 | Replace `_normalize_chesscom_result`'s silent-draw fallback with explicit "unknown" + Sentry capture | Confirmed exact fallback line (207), confirmed `GameResult` has no unknown member, confirmed the existing `if normalized is not None` skip channel in `chesscom_client.py` needs zero caller changes |
| PRUNE-04 | `worker_schema_version` recorded on submits as telemetry (log/tag only) | Confirmed already present on `AtomicSubmitRequest` (line 239), confirmed absent from `SubmitRequest`/`EntrySubmitRequest`/`FlawBlobSubmitRequest` (supports D-03's nullable-column design) |
| PRUNE-05 | Durable `import_jobs` row created in the request handler + partial unique index on `(user_id, platform) WHERE status IN ('pending','in_progress')` | Pitfall 3 is the key finding: the DB insert currently lives in `_bootstrap_import_job` (background task), not `create_job` (in-memory) as assumed — traced the exact call chain and the exact code that must move |
| PRUNE-06 | `worker_heartbeats` table populated server-side from existing submit fields, zero worker-side change | Confirmed `worker_id_label` truncation precedent (VARCHAR(16)), confirmed `request.client.host` availability precedent (`auth.py:294`, `deploy/entrypoint.sh` proxy-headers config), confirmed all 3 live submit handlers' exact line numbers for the upsert insertion point, provided a concrete `pg_insert(...).on_conflict_do_update(...)` code example matching D-01 through D-06 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Directives with direct bearing on this phase's plan tasks:

- **Never `asyncio.gather` on the same `AsyncSession`** — every new/edited handler (heartbeat upsert, import-job insert) must stay inside the existing read-phase/write-phase session split already used by `_apply_atomic_submit` etc.
- **Sentry: never embed variables in the message string** — PRUNE-03's unknown-result capture and any heartbeat-related logging must use `sentry_sdk.set_context()`/`set_tag()`, matching the existing pattern in `eval_remote.py`'s Path-C warning and `import_service.py`'s failure captures.
- **Sentry: skip trivial/expected exceptions** — the `IntegrityError` caught for the durable import-job guard (PRUNE-05) is an expected/routine condition (a race, not a bug) and must NOT be `capture_exception`'d, matching `guest_service.py`'s existing precedent of a silent rollback-and-continue.
- **DB design rules** — every new FK needs an explicit `ondelete` (worker_heartbeats has no FK — worker_id is a free-form external identity string, not a reference to an internal table); avoid native Postgres `ENUM`; `worker_heartbeats` is low-volume (one row per worker) so plain typed columns are fine, no lookup table needed.
- **`ty check` zero errors** — new `WorkerHeartbeat` model and any new repository functions need explicit return type annotations; use `Sequence[str]` not `list[str]` for covariant params if any are introduced (unlikely to apply here — no `Literal` list params in this phase's surface).
- **Comment bug fixes** — PRUNE-03/05 are both closing real gaps (silent-draw, TOCTOU race); each fix site should carry a comment explaining what broke and why, per the existing convention seen throughout `eval_remote.py`'s SEED-076/CR-01 comments.
- **`uv run pytest -n auto`** for the full local suite; CI stays serial. The pre-merge gate (ruff format + check --fix, ty check, pytest -n auto -x, frontend lint+test) applies once before squash-merging this phase's branch to `main` — this phase is backend-only, so the frontend leg of the gate is a no-op pass-through, not skippable.
- **Never deploy or reset the dev DB in a plan** — the two migrations must be verified via `uv run alembic upgrade head` against the existing dev DB (already running per `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`), never via `bin/reset_db.sh`.

## Summary

This phase is pure server-side surgery on `app/routers/eval_remote.py`, `app/services/zobrist.py`, `app/services/chesscom_to_lichess.py`, `app/models/game.py`, `app/services/normalization.py`, `app/routers/imports.py`, and `tests/test_eval_worker_endpoints.py`, plus two additive Alembic migrations (`import_jobs` partial unique index, new `worker_heartbeats` table). No new external packages are introduced — the Package Legitimacy Audit is N/A for this phase.

Every line-number breadcrumb in `149-CONTEXT.md` was checked against the current tree and confirmed accurate for the five files that carry canonical positions (`eval_remote.py` 330/529/553/746/853/1217/1643; `remote_eval_worker.py` 656-704; `normalization.py` 186; `schemas/normalization.py:13`; `schemas/eval_remote.py:239`; `imports.py::start_import` at line 47). Two breadcrumbs needed real correction, not just confirmation:

1. **PRUNE-02's "`chesscom_to_lichess` tables" is NOT the whole module.** `app/services/chesscom_to_lichess.py` is actively imported by `app/services/canonical_slice_sql.py` for live rating-conversion (`composed_chesscom_to_lichess_grid`, `convert_chesscom_to_lichess`). Deleting the module would break a shipped feature. Only **Table 3** (`LICHESS_BLITZ_INTRA_TC`) and its two dead lookup functions (`lookup_uscf_from_lichess_blitz`, `lookup_fide_from_lichess_blitz`) are genuinely unused — confirmed zero callers outside the module and its own test file, and the module's own docstring already says so ("no Phase 94.4 caller consumes it yet"). Tables 1/2 (`CHESSCOM_INTRA_TC`, `CHESSCOM_BLITZ_TO_LICHESS`) are load-bearing and must NOT be touched.
2. **PRUNE-05's durable `import_jobs` row is NOT currently created "via `create_job`."** `import_service.create_job()` is 100% in-memory (registers a `JobState` dict entry, no DB write). The actual DB `INSERT` happens later, inside the fire-and-forget `asyncio.create_task(run_import(job_id))` → `_bootstrap_import_job()` helper. This changes where the fix has to land: the row-creation call must be *moved out* of `_bootstrap_import_job` and *into* `start_import` (before `create_task`), not merely reordered relative to an existing in-handler call.

**Primary recommendation:** Treat PRUNE-01 (Gen-1 protocol deletion) as the highest-risk item purely because of the 5,457-line test file's lane-mixing — the URL-usage analysis below gives an exact, mechanically-verified split of which of the 95 test functions are pure Gen-1 (safe delete), which are pure live-lane (keep untouched), and which reference the doomed `/submit` endpoint as an isolation-proof fixture inside an otherwise-live test class (must delete the whole test function, not just the assertion). Two concrete **test coverage gaps** were found that the plan must close before deleting Gen-1's `TestTier1Claiming` class (see Pitfall 1).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Gen-1 `/lease`+`/submit` deletion | API / Backend | — | Router + worker script, no DB schema change |
| Dead code removal (zobrist, chesscom_to_lichess Table 3, `needs_engine_full_evals`) | API / Backend | — | Pure Python service-layer cleanup |
| Unknown-result normalization | API / Backend | Database | New skip path through existing `NormalizedGame | None` contract |
| `worker_schema_version` telemetry | API / Backend | Database | Already-arriving field just needs a landing column/log |
| Durable import-job guard | API / Backend | Database / Storage | New partial unique index enforced at Postgres level, closes an app-memory-only race |
| `worker_heartbeats` | API / Backend | Database / Storage | New low-volume table, upsert-on-submit, no consumer UI this phase |

No Browser/Client, Frontend-SSR, or CDN tier is touched — this is 100% server-side (per CONTEXT.md scope: "Server-side only. No worker protocol change, no fleet redeploy").

## Package Legitimacy Audit

**N/A — this phase installs no new external packages.** All work uses already-vendored dependencies (SQLAlchemy 2.x async, Alembic, FastAPI, Sentry SDK, python-chess). No `npm install` / `uv add` is expected in any plan for this phase.

## Standard Stack

No new libraries. Reused, already-in-repo primitives:

| Component | Where it lives | Reused for |
|-----------|---------------|------------|
| `sqlalchemy.dialects.postgresql.insert` (`ON CONFLICT DO UPDATE`) | already imported in `eval_queue_service.py` | `worker_heartbeats` upsert-by-PK (PRUNE-06) |
| `sqlalchemy.exc.IntegrityError` try/except-rollback pattern | `app/services/guest_service.py:163-180` | durable import-job guard race handling (PRUNE-05) |
| `sentry_sdk.set_context` + `capture_message`/`capture_exception` | used throughout `eval_remote.py`, `normalization.py` callers | PRUNE-03 unknown-result capture |
| Alembic partial-index pattern (`postgresql_where=sa.text(...)`) | `app/models/eval_jobs.py` (`uq_eval_jobs_game_active`, `ix_eval_jobs_pick`) | both new migrations |

**Installation:** none.

## Architecture Patterns

### System Architecture Diagram

```
                     BEFORE (3 write-path copies, this phase removes 1)
                     ─────────────────────────────────────────────────
Remote worker fleet (100% on atomic lane, confirmed 0 legacy hits/11.3h)
        │
        ├──[DEAD, PRUNE-01]──▶ POST /lease ──▶ POST /submit ──▶ _apply_submit() ──┐
        │                                                                         │
        ├──────────────────▶ POST /entry-lease ──▶ POST /entry-submit ───────────┤
        │                                                                         ├──▶ game_flaws / game_positions
        ├──────────────────▶ POST /atomic-lease ──▶ POST /atomic-submit          │      (Postgres)
        │                     ──▶ _apply_atomic_submit() ──────────────────────────┤
        │                                                                         │
        └──────────────────▶ POST /flaw-blob-lease ──▶ POST /flaw-blob-submit ──┘
                              ──▶ _apply_flaw_blob_submit()  [UNTOUCHED, D-04 isolated]

                     AFTER PRUNE-01 (2 copies remain; Phase 150 unifies further)
                     ────────────────────────────────────────────────────────────
Remote worker fleet
        │
        ├──▶ POST /entry-lease ──▶ POST /entry-submit ──▶ _apply_eval_results() (no shift)
        │
        ├──▶ POST /atomic-lease ──▶ POST /atomic-submit ──▶ _apply_atomic_submit()
        │        (also gains worker_heartbeats upsert + worker_schema_version log)
        │
        └──▶ POST /flaw-blob-lease ──▶ POST /flaw-blob-submit ──▶ _apply_flaw_blob_submit()
                 (also gains worker_heartbeats upsert)

Request path (PRUNE-05):
Browser ──▶ POST /imports (start_import) ──▶ [NEW] create_import_job() DB INSERT
              (before asyncio.create_task)      │ partial unique idx (user_id, platform)
                                                  ▼                  WHERE status IN (pending, in_progress)
                                            asyncio.create_task(run_import) ──▶ _bootstrap_import_job()
                                                                                 (drops its own INSERT;
                                                                                  keeps previous-job lookup)
```

### Recommended Project Structure

No new files/directories. Edits land in:
```
app/routers/eval_remote.py         # delete /lease, /submit, _apply_submit; add heartbeat upsert calls
app/routers/imports.py             # start_import: create DB job row before create_task, handle IntegrityError
app/services/import_service.py     # _bootstrap_import_job: drop its create_import_job call
app/repositories/import_job_repository.py  # (maybe) new create_import_job_or_get_existing helper
app/services/normalization.py      # _normalize_chesscom_result: unknown-result signal
app/services/zobrist.py            # delete hashes_for_game
app/services/chesscom_to_lichess.py  # delete LICHESS_BLITZ_INTRA_TC + 2 lookup fns + _LICHESS_BLITZ_KEYS
app/models/game.py                 # delete needs_engine_full_evals hybrid property
app/models/eval_jobs.py            # (optional) drop/annotate TIER_AUTO_WINDOW — see Pitfall 2
app/models/worker_heartbeat.py     # NEW model
app/repositories/worker_heartbeat_repository.py  # NEW: shared upsert helper (D-05)
scripts/remote_eval_worker.py      # delete _handle_full_ply_response
tests/test_eval_worker_endpoints.py  # surgical deletion (28 of 95 tests) — see Pitfall 1
tests/test_zobrist.py              # delete 18 hashes_for_game-specific tests
tests/test_seed_openings.py        # rewrite 2 hashes_for_game references to process_game_pgn
tests/services/test_chesscom_to_lichess.py  # delete LICHESS_BLITZ_INTRA_TC-only tests
alembic/versions/<new>_import_jobs_partial_unique_index.py   # NEW migration
alembic/versions/<new>_worker_heartbeats_table.py             # NEW migration
```

### Pattern 1: Read-phase / write-phase session split (already established, must be preserved)

**What:** Every submit handler opens a short read-only session, closes it, does CPU work, then opens exactly one write session for all UPDATEs + commit. Never `asyncio.gather` inside an open `AsyncSession` (CLAUDE.md hard rule, and explicitly re-affirmed in `_apply_submit`'s and `_apply_atomic_submit`'s docstrings).

**When to use:** Any new code touching `worker_heartbeats` upsert or `import_jobs` insert must fit into this shape — the heartbeat upsert is a single `INSERT ... ON CONFLICT` statement, safe to run inside the *existing* write session of each of the three live submit handlers (no new session needed).

**Example (existing precedent for the upsert-by-PK shape, from `eval_queue_service.py`):**
```python
# Source: app/services/eval_queue_service.py (pg_insert already imported there)
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(WorkerHeartbeat).values(
    worker_id=worker_id, last_ip=last_ip, sf_version=sf_version,
    worker_schema_version=worker_schema_version, last_seen=sa.func.now(),
    submit_count=1, evals_submitted=n_evals,
)
stmt = stmt.on_conflict_do_update(
    index_elements=["worker_id"],
    set_={
        "last_ip": stmt.excluded.last_ip,
        "sf_version": stmt.excluded.sf_version,
        # worker_schema_version: only overwrite when the new value is non-NULL
        # (D-03: entry/flaw-blob lanes never send it — must not clobber the
        # last known atomic-lane value with NULL).
        "worker_schema_version": sa.func.coalesce(
            stmt.excluded.worker_schema_version, WorkerHeartbeat.worker_schema_version
        ),
        "last_seen": stmt.excluded.last_seen,
        "submit_count": WorkerHeartbeat.submit_count + stmt.excluded.submit_count,
        "evals_submitted": WorkerHeartbeat.evals_submitted + stmt.excluded.evals_submitted,
    },
)
await write_session.execute(stmt)
```

### Pattern 2: IntegrityError-as-idempotency (existing precedent for PRUNE-05)

**What:** `app/services/guest_service.py:163-180` already handles a concurrent-insert race by wrapping the commit in `try/except IntegrityError: await session.rollback()` and treating the conflict as "already done, re-fetch."

**When to use:** `start_import`'s new durable guard. Recommended shape:
```python
# Source: app/services/guest_service.py (pattern), adapted for import_jobs
try:
    job_row = await import_job_repository.create_import_job(session, job_id=job_id, ...)
    await session.commit()
except IntegrityError:
    await session.rollback()
    existing_row = await import_job_repository.get_active_job_for_user_platform(
        session, user_id, request.platform
    )
    response.status_code = 200
    return ImportStartedResponse(job_id=existing_row.id, status=existing_row.status)
```
Note `get_active_job_for_user_platform` does not exist yet — the plan needs a new repository query (`WHERE user_id=... AND platform=... AND status IN ('pending','in_progress')`), mirroring the new partial unique index's predicate exactly (drift-prevention: keep the two predicates textually identical, per the existing convention documented in `eval_remote.py`'s D-5 backlog-probe comment: "the probe predicate MUST match the claim predicate... keeping the two predicates in lock-step prevents drift").

### Anti-Patterns to Avoid

- **Deleting the whole `chesscom_to_lichess.py` module.** Confirmed live caller in `canonical_slice_sql.py` for Tables 1/2. Only Table 3 + its 2 functions are dead.
- **Leaving `_bootstrap_import_job`'s `create_import_job` call in place after adding one in `start_import`.** Both would try to `INSERT` a row with the same fresh `job_id` (PK), the second becoming an accidental extra UPDATE or a benign duplicate-key issue only avoided because the ids differ — but leaving both is wasted work and a maintenance trap. Remove the DB insert from `_bootstrap_import_job`, keep only its `get_latest_for_user_platform` lookup.
- **Assuming `worker_schema_version` needs a gate.** PRUNE-04 and D-10 are explicit: telemetry/log/tag only, never a 426 rejection (that's an explicitly deferred, out-of-scope future item per REQUIREMENTS.md's Out of Scope list).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Upsert-by-PK with counter increment | Manual SELECT-then-UPDATE-or-INSERT | `pg_insert(...).on_conflict_do_update(...)` | Already the established pattern in `eval_queue_service.py`; race-free under concurrent submits from multiple workers |
| Duplicate-import race guard | Application-level locking / Redis lock | Postgres partial unique index + `IntegrityError` catch | DB-level guarantee survives process restarts and multi-worker deploys; app-memory `find_active_job` cannot |
| Worker liveness tracking | A new polling/heartbeat-ping background task | Passive upsert on every submit (D-01/D-04) | Zero new worker-side code, zero new schedule; "submits only" is the locked decision |

**Key insight:** every piece of this phase reuses an existing pattern already proven elsewhere in this codebase (upsert, IntegrityError-as-idempotency, read/write session split). There is no genuinely novel mechanism here — the risk is entirely in *surgical precision* (which lines to delete, which tests to keep), not in engineering a new pattern.

## Runtime State Inventory

This phase deletes two live HTTP endpoints (`/lease`, `/submit`) that a deployed worker fleet has, in the past, called directly. All 5 categories checked:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `eval_jobs` rows with `tier=2` — **none exist** (Phase 118 removed the only enqueue path that ever wrote `tier=2`; `TIER_AUTO_WINDOW` constant is defined but never referenced as an argument anywhere — confirmed via repo-wide grep). No data migration needed for PRUNE-02's tier-2 item. | None |
| Live service config | Remote worker fleet (`scripts/remote_eval_worker.py`, deployed on 2 machines per `project_worker_fleet_topology` memory — Adrian's local box + Hetzner lima/kilo) — **already upgraded**. CONTEXT.md cites a 2026-07-04 prod log grep: zero `/lease`+`/submit` hits over 11.3h vs 54k atomic-lease hits `[CITED: 149-CONTEXT.md D-domain, not independently re-verified this session — re-check prod access logs immediately before merging the deletion, since the fleet is operator-controlled and could theoretically be rolled back to an older worker script between now and execution]`. | Re-verify zero-legacy-traffic claim right before merging PRUNE-01 (cheap: `ssh flawchess "docker compose logs backend | grep -c '/eval/remote/submit '"` filtered to the last few hours), not just trust the context snapshot |
| OS-registered state | None — no systemd/pm2/Task Scheduler entries reference `/lease` or `/submit` by name; the worker script's own `_run_cycle` no longer calls `_handle_full_ply_response` (already unreachable per Phase 147 D-02/D-05, confirmed in the read code) | None |
| Secrets/env vars | None — `EVAL_OPERATOR_TOKEN`, `X-Worker-Id`, `EXPECTED_SF_VERSION` are shared across all lanes, untouched by this phase | None |
| Build artifacts | None — no compiled/installed artifacts reference the deleted endpoints | None |

## Common Pitfalls

### Pitfall 1: Deleting `TestTier1Claiming` removes the ONLY coverage of job_id/eval_jobs stamping — with no atomic-lane replacement yet in place

**What goes wrong:** `_apply_atomic_submit` (line 1609-1624 of `eval_remote.py`) contains the *identical* tier-1/tier-2 `eval_jobs` completion-stamping logic as the doomed `_apply_submit` (line 494-509) — same `WHERE status='leased'` idempotency guard, same late-submit-safety invariant. But **every existing `TestAtomicSubmitEndpoint` test passes `"job_id": None`** (verified: `grep -n '"job_id"' tests/test_eval_worker_endpoints.py` shows all 7 occurrences in that class are `None`). The 5 tests in `TestTier1Claiming` (`test_tier1_lease_returns_job_id`, `test_submit_with_job_id_stamps_eval_jobs`, `test_submit_without_job_id_does_not_touch_eval_jobs`, `test_late_submit_does_not_corrupt_eval_jobs`, `test_lichess_eval_game_claim_releases_lease`) are the *only* place this logic is exercised end-to-end today.

**Why it happens:** `TestTier1Claiming` was written against `/lease`+`/submit` before the atomic pair existed (Phase 121-era, predates Phase 147's atomic lane), and nobody back-filled an atomic-lane equivalent because the atomic lane wasn't the primary path yet at the time.

**How to avoid:** Before deleting `TestTier1Claiming`, add 2-3 new tests to `TestAtomicSubmitEndpoint` (and one to `TestAtomicLeaseEndpoint`) that exercise: (a) a real `job_id` on `/atomic-submit` stamps `eval_jobs.status='completed'`; (b) a late/stale `job_id` (already completed or re-leased) is a no-op, not a corruption; (c) `job_id=None` (tier-3 pick) never touches `eval_jobs`. Also port `test_lichess_eval_game_claim_releases_lease`'s scenario to `TestAtomicLeaseEndpoint` — that class currently has zero test of the `is_lichess_eval_game=True → release_job + 204` branch (lines 689-692 of `eval_remote.py`), even though the branch exists and is documented as "mirrors /lease."

**Warning signs:** If the plan's checklist just says "delete Gen-1 tests" without a corresponding "add atomic-lane job_id/lichess-skip tests" line item, this gap will ship silently — `pytest` will still pass (100% green) because the *deleted* tests, not a *failing* assertion, were the only thing exercising this path.

### Pitfall 2: `TIER_AUTO_WINDOW` / "tier-2 lane logic" has no branch to delete — the code's own docstring argues for keeping it

**What goes wrong:** PRUNE-02 (per REQUIREMENTS.md R12) frames "tier-2 lane code" as dead weight to remove (keeping only the DB column). But `_claim_queued_job` (the shared tier-1/tier-2 claim SQL in `eval_queue_service.py`) is tier-agnostic — it does `ORDER BY ej.tier ASC` and has never had an `if tier == 2` branch to delete. The only tier-2-specific artifact is the `TIER_AUTO_WINDOW: int = 2` constant in `app/models/eval_jobs.py`, which is referenced **nowhere** as an argument (confirmed via repo-wide grep: only its own definition and one docstring line in `eval_queue_service.py`). The `eval_queue_service.py` module docstring explicitly states: *"The tier-2 lane (constant, generic claim handling, eval_jobs.tier column) is intentionally retained for a future per-user 'analyze my games' vs 'help drain for everybody' mode."* — i.e. the code's own comments argue AGAINST removal, contradicting PRUNE-02's framing.

**Why it happens:** Phase 118 already did the substantive tier-2 removal (deleted `enqueue_tier2_window`, the only thing that ever wrote `tier=2` rows). What's left is just an unused constant plus forward-looking commentary — there's no "lane logic" left to delete in the sense of a deletable code branch.

**How to avoid:** The planner should resolve this drift explicitly (flag to user/CONTEXT amendment if needed) rather than hunting for a nonexistent branch. Two defensible options: (a) minimal — delete the `TIER_AUTO_WINDOW` constant and trim the "future mode" narrative from the two docstrings (lowest risk, satisfies the letter of "remove tier-2 lane code" since the constant IS the only tier-2-specific code); (b) do nothing beyond documentation cleanup, since Phase 150 (write-path consolidation) will touch `eval_queue_service.py` anyway and this is genuinely zero-cost either way. Do NOT spend time searching for an `if`/`elif` branch that isn't there.

### Pitfall 3: `import_jobs` durable-row creation must move OUT of the background task, not just get a new index

**What goes wrong:** Simply adding the partial unique index without moving the `INSERT` earlier accomplishes nothing — the race window is between the in-memory `find_active_job` check (synchronous, in `start_import`) and the DB row's actual creation (currently inside `_bootstrap_import_job`, which only runs after `asyncio.create_task` has scheduled the coroutine — i.e., strictly AFTER the HTTP response for the first request has already been sent). A second concurrent request in the same window sees an empty in-memory registry too (if it lands before the first task's event-loop turn) and would also pass, both eventually attempting the DB insert — the new index catches this only if the insert *itself* moves into the synchronous request-handler path before `create_task`.

**Why it happens:** `create_job()` (in-memory) and `create_import_job()` (DB) are separate functions with confusingly similar names; it's easy to assume "the DB row is created right after the in-memory check" (as CONTEXT.md's D-08 breadcrumb does) without tracing that `_bootstrap_import_job` — not `start_import` — is the actual DB call site.

**How to avoid:** The plan must include a task to (1) call `import_job_repository.create_import_job` from `start_import` (wrapped in try/except IntegrityError per Pattern 2 above), BEFORE `asyncio.create_task(...)`, and (2) remove the now-redundant `create_import_job` call from `_bootstrap_import_job`, keeping only its `get_latest_for_user_platform` lookup (needed for `previous_last_synced_at`).

**Warning signs:** A plan task that only adds the migration + index without touching `import_service.py`'s `_bootstrap_import_job` will pass all existing tests (the race is a timing issue, not something the current test suite exercises) while leaving the actual bug unfixed.

### Pitfall 4: `test_blob_lease_does_not_touch_submit` / `test_blob_submit_does_not_touch_apply_submit` reference the doomed `/submit` endpoint as their own test subject

**What goes wrong:** These two tests (inside `TestFlawBlobLeaseEndpoint` and `TestFlawBlobSubmitEndpoint` respectively — both otherwise KEEP classes) exist specifically to prove `/submit`'s behavior is byte-for-byte unchanged after adding flaw-blob endpoints (D-04 isolation invariant). Once `/submit` is deleted, these tests cannot run — POSTing to a route that returns 404 (unregistered) would make the test fail, not pass.

**Why it happens:** These are the only two "cross-lane" tests inside otherwise pure live-lane classes; the URL-usage scan (below) correctly flags them as containing `_SUBMIT_URL` even though their surrounding class is 100% live-lane.

**How to avoid:** Delete both test functions specifically (not their containing classes). Optionally (not required by PRUNE-01/02's must-haves) add a lightweight replacement asserting flaw-blob-lease/submit doesn't corrupt an in-flight `/atomic-submit`'s game — but this is a nice-to-have, not a gap the existing D-04 isolation contract strictly requires (the flaw-blob handlers are structurally isolated: separate functions, no shared write session, confirmed by reading `_apply_flaw_blob_submit`'s docstring: "Does NOT call `_apply_submit` or `_classify_and_fill_oracle`").

### Pitfall 5: Test file line numbers will shift after every deletion — do deletions bottom-up

**What goes wrong:** The exact line ranges below (e.g. `2645-2958`) are correct against the CURRENT file. Deleting the earlier ranges (e.g. 287-425) shifts every later line number down. A plan/executor working top-down with fixed line numbers will delete the wrong content on the second edit onward.

**How to avoid:** Either (a) delete from the bottom of the file upward, or (b) match on function name via `Edit` tool's `old_string` (unique docstring/signature text) rather than line-number ranges, or (c) re-run the line-boundary scan (see Code Examples below) after each deletion to get fresh numbers.

## Code Examples

### Verified test-file surgery map (PRUNE-01, `tests/test_eval_worker_endpoints.py`, 95 total collected tests)

Verified this session via a script that maps every top-level `async def test_` / `class Test` boundary to which of 8 URL constants (`_LEASE_URL`, `_SUBMIT_URL`, `_ENTRY_LEASE_URL`, `_ENTRY_SUBMIT_URL`, `_FLAW_BLOB_LEASE_URL`, `_FLAW_BLOB_SUBMIT_URL`, `_ATOMIC_LEASE_URL`, `_ATOMIC_SUBMIT_URL`) it references, using word-boundary regex (a naive substring match falsely flags `_ENTRY_LEASE_URL` as containing `_LEASE_URL` — corrected for). `[VERIFIED: pytest --collect-only shows exactly 95 tests, matching CONTEXT.md D-09's count]`

**DELETE (28 tests/methods — pure Gen-1 or Gen-1-dependent isolation proofs):**

| Lines (current) | Test(s) | Reason |
|---|---|---|
| 287-425 | `test_lease_requires_operator_token`, `test_lease_wrong_operator_token`, `test_lease_non_ascii_operator_token`, `test_lease_no_pending_games`, `test_lease_returns_positions` | `/lease` only |
| 426-726 | `test_submit_requires_operator_token`, `test_submit_wrong_operator_token`, `test_submit_sf_version_mismatch`, `test_submit_applies_post_move_shift`, `test_submit_stamps_full_evals_completed_at`, `test_submit_idempotent` | `/submit` only |
| 727-1093 | `class TestTier1Claiming` (5 methods) | `/lease`+`/submit` only — **see Pitfall 1: add atomic-lane replacement tests before deleting** |
| 1871-1979 | `test_scope_explicit_returns_only_tier1_2`, `test_scope_idle_skips_tier1_2`, `test_scope_absent_is_bundled` | `/lease?scope=` param, Gen-1-specific (the `scope` param concept lives on identically on `/atomic-lease`, already covered by `TestAtomicLeaseEndpoint`) |
| 2071-2195 | `test_worker_id_header_populates_leased_by_on_full_lease`, `test_worker_id_absent_falls_back_to_remote_worker_on_full_lease` | `/lease` only (entry-lease variants at 1980-2070 are KEEP) |
| 2196-2493 | `class TestMultipv2BlobsRemote` (2 methods) | `/submit`-only backward-compat-with-old-worker-payload tests, moot once `/submit` is gone |
| 2494-2644 | `test_submit_phase146_build_blob_not_called`, `test_submit_phase146_blobs_null_both_markers_stamped` | `/submit` only |
| 2645-2958 | `test_submit_suppresses_cp_flaw_tag_then_blob_submit_self_heals` | `/submit`+flaw-blob; atomic-lane equivalent already exists and explicitly says "Mirrors test_submit_suppresses..." (`test_atomic_submit_gates_tactic_tag_and_stamps_both_markers`, `test_atomic_submit_missing_blob_writes_null_tag`) |
| within `TestFlawBlobLeaseEndpoint` | `test_blob_lease_does_not_touch_submit` (~3328-3378) | References doomed `/submit` as isolation-proof subject — see Pitfall 4 |
| within `TestFlawBlobSubmitEndpoint` | `test_blob_submit_does_not_touch_apply_submit` (~4790-4837) | Same — see Pitfall 4 |

**KEEP unmodified (67 tests):** everything in `TestFlawBlobLeaseEndpoint` minus the one method above, everything in `TestFlawBlobSubmitEndpoint` minus the one method above, all of `TestAtomicLeaseEndpoint`, all of `TestAtomicSubmitEndpoint`, all of `TestBlobAssemblyHelper`, all entry-lease/entry-submit tests (1280-1870, 1980-2070), `test_lease_partition`/`test_lease_lifo`/`test_lease_reclaim`/`test_leased_by_set` (1094-1279 — these test `_claim_entry_eval_games` directly, misleadingly named but entry-lane, not Gen-1), and the 8 SEED-076 atomic-cache tests at 4996-5457.

### `hashes_for_game` deletion scope (PRUNE-02)

```
# Source: this session's grep of tests/test_zobrist.py
17 dedicated test_hashes_for_game_* functions (lines 163-325ish) — delete all
1 equivalence test at line 435 (test_hashes_for_game_wrapper_matches_process_game_pgn)
  — delete the function, but the SCENARIO it proves (hashes_for_game and
  process_game_pgn agree) has already served its purpose once process_game_pgn
  is the sole implementation; no replacement needed.
2 references in tests/test_seed_openings.py (lines 70-76) — REWRITE (not delete):
  this test verifies seed-opening hashes match import-time hash computation,
  which must keep working. Swap hashes_for_game(pgn) for
  process_game_pgn(pgn)["plies"][...]["full_hash"] (see process_game_pgn's
  GameProcessingResult TypedDict shape at zobrist.py:138-153).
```

### `chesscom_to_lichess.py` deletion scope (PRUNE-02) — corrected from CONTEXT.md

```python
# Source: app/services/chesscom_to_lichess.py (this session's read)
# DELETE (confirmed zero external callers via repo-wide grep):
LICHESS_BLITZ_INTRA_TC   # Table 3, line 178
_LICHESS_BLITZ_KEYS       # line 231, used only by the two functions below
lookup_uscf_from_lichess_blitz   # line 512
lookup_fide_from_lichess_blitz   # line 526

# KEEP — actively imported by app/services/canonical_slice_sql.py:
CHESSCOM_INTRA_TC            # Table 1
CHESSCOM_BLITZ_TO_LICHESS    # Table 2
convert_chesscom_to_lichess
composed_chesscom_to_lichess_grid
lookup_uscf_from_chesscom_blitz   # line 488 — different function, KEEP
lookup_fide_from_chesscom_blitz   # line 500 — different function, KEEP
```
Corresponding deletions needed in `tests/services/test_chesscom_to_lichess.py` (lines 33, 149, 159 reference `LICHESS_BLITZ_INTRA_TC` directly).

### PRUNE-03 unknown-result flow (verified skip channel)

```python
# Source: app/services/chesscom_client.py:325-341 (this session's read) — the
# EXISTING skip channel the D-07 fix must plug into. No caller change needed.
for game in games:
    try:
        normalized = normalize_chesscom_game(game, username, user_id)
    except Exception as exc:
        ...  # existing exception-based skip (Phase 148 CORR-05)
        continue
    if normalized is not None:
        yield normalized   # <-- an "unknown result -> return None" fix flows
                            #     through this SAME gate, zero caller change
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `/lease` + `/submit` (Gen-1, no blob-write atomicity) | `/atomic-lease` + `/atomic-submit` (evals + blobs + classify in one transaction) | Phase 147 SEED-074 Part B | Eliminates the ungated-tag window; this phase deletes the superseded Gen-1 pair now that the fleet has migrated |
| Triple-PGN-parse (`hashes_for_game` + others) | Single-walk `process_game_pgn` | Phase 79-era D-01/D-02 refactor (per its own docstring) | `hashes_for_game` became a pure-legacy wrapper kept alive only by its own tests |
| `enqueue_tier2_window` (auto-enqueue) | Tier-3 ES-weighted idle-backlog lottery covers the same need | Phase 118 | Tier-2's *enqueue path* is already gone; only a dead constant + docstring remain (Pitfall 2) |

**Deprecated/outdated:** Gen-1 `/lease`+`/submit` (this phase retires it); `TIER_AUTO_WINDOW` constant (candidate for removal, see Pitfall 2); `hashes_for_game` (superseded, unused in production).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Zero legacy `/lease`+`/submit` prod traffic over the last 11.3h (cited from CONTEXT.md's 2026-07-04 log grep, not independently re-run this session) | Runtime State Inventory | If a not-yet-upgraded worker resurfaces (e.g. a stale Docker image restarted on a remote box), deleting the endpoints would 404 that worker's every request. Mitigation: re-run the prod log grep immediately before merging, per the Runtime State Inventory action item. |
| A2 | Fleet has exactly 2 machines (local Swiss DSL box + Hetzner lima/kilo) and both are confirmed on the atomic script version | Runtime State Inventory | Sourced from `project_worker_fleet_topology` memory file, not re-verified via SSH this session |

## Open Questions

1. **Should `TIER_AUTO_WINDOW` actually be deleted, or just left with trimmed docstrings?**
   - What we know: it's a zero-cost, zero-callsite constant; the surrounding code's own comments argue for keeping the *concept* alive for a speculative future feature.
   - What's unclear: whether the user/PRUNE-02's intent was "remove the constant" (literal) or "there's nothing left to remove, it was already done in Phase 118" (the constant is incidental).
   - Recommendation: default to removing the constant + trimming the two docstrings (satisfies the letter of R12 with near-zero risk since it has no callers); flag to the user in the plan if they'd rather leave the speculative-future-mode commentary in place.

2. **Does the plan need a new `worker_id_full_lease` VARCHAR(16) truncation test for `worker_heartbeats.worker_id`?**
   - What we know: `worker_id_label` already truncates to 16 chars (line 538-545 of `eval_remote.py`) before it's used for `games.entry_eval_leased_by` (VARCHAR(16)) and `eval_jobs.leased_by` (VARCHAR(100)). Reusing it verbatim for `worker_heartbeats.worker_id` PK is safe by construction.
   - What's unclear: whether the new PK column should be `VARCHAR(16)` (matching the truncation) or `TEXT` (per CLAUDE.md's "low-volume domain columns as TEXT+CHECK" guidance — though this isn't really a domain/enum column, it's an identity string).
   - Recommendation: `VARCHAR(16)` to match the truncation guarantee exactly (a `TEXT` column with a 16-char-truncated value at write time is functionally identical but a fixed-width type documents the invariant at the schema level — align with the existing `entry_eval_leased_by` precedent, not the CLAUDE.md enum-avoidance rule which targets a different problem shape).

## Environment Availability

Skipped — no external tool/service dependency beyond the already-running dev Postgres (`docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`, required for the two new migrations to `alembic upgrade head` and for the full test suite).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (async via `pytest-asyncio`), per-run cloned DB template (see CLAUDE.md "Test isolation") |
| Config file | `pytest.ini` / `pyproject.toml` (existing, unchanged) |
| Quick run command | `uv run pytest tests/test_eval_worker_endpoints.py tests/test_zobrist.py tests/services/test_chesscom_to_lichess.py tests/test_import_service.py tests/services/test_eval_queue.py -n auto` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRUNE-01 | Gen-1 endpoints 404/gone; live lanes unaffected; job_id/eval_jobs stamping still covered on atomic lane | integration | `pytest tests/test_eval_worker_endpoints.py -x` | Partial — atomic job_id tests are a Wave 0 gap (Pitfall 1) |
| PRUNE-02 | `hashes_for_game`, dead tier-2 constant, `LICHESS_BLITZ_INTRA_TC`, `needs_engine_full_evals` removed with zero prod behavior change | unit | `pytest tests/test_zobrist.py tests/services/test_chesscom_to_lichess.py -x` | ✅ (after the deletions/rewrites above) |
| PRUNE-03 | Unknown chess.com result → skip + Sentry capture, not silent draw | unit | `pytest tests/services/test_normalization.py -x` (or wherever `_normalize_chesscom_result`/`normalize_chesscom_game` tests live — confirm exact file during planning) | ❌ Wave 0 — new test needed for the "unknown → None + capture_message" path |
| PRUNE-04 | `worker_schema_version` recorded (log/tag/heartbeat column) on every atomic submit | unit/integration | new assertion inside `TestAtomicSubmitEndpoint` | ❌ Wave 0 |
| PRUNE-05 | Concurrent duplicate import for (user, platform) rejected at DB level, existing-job 200 preserved | integration | new test in `tests/test_import_service.py` or a new `tests/routers/test_imports.py` simulating a race (two sequential `create_import_job` calls with the same user/platform before the first completes) | ❌ Wave 0 |
| PRUNE-06 | `worker_heartbeats` upserts on every live submit lane, counts accumulate, `last_ip` populated, idempotent | unit/integration | new `tests/test_worker_heartbeats.py` (or folded into `test_eval_worker_endpoints.py`) | ❌ Wave 0 — new table, no tests exist yet |

### Sampling Rate

- **Per task commit:** targeted file(s) above via `-n auto`
- **Per wave merge:** `uv run pytest -n auto -x` (full backend suite — required by CLAUDE.md pre-merge gate anyway)
- **Phase gate:** Full suite green before `/gsd-verify-work`, plus a manual prod-log re-check per Runtime State Inventory before the PRUNE-01 deletion actually ships

### Wave 0 Gaps

- [ ] Atomic-lane test additions for job_id stamping + lichess-eval-game-skip (Pitfall 1) — must land BEFORE or IN THE SAME task as `TestTier1Claiming` deletion, not after
- [ ] New unknown-result test for PRUNE-03 (locate/confirm exact normalization test file path during planning — `grep -rn "_normalize_chesscom_result\|normalize_chesscom_game" tests/` was not exhaustively enumerated this session; verify file name at plan time)
- [ ] New `worker_heartbeats` model + migration + repository + tests (net-new, no existing scaffolding)
- [ ] New durable-import-race test (net-new)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Operator-token auth (`X-Operator-Token`, `require_operator_token`) is unchanged by this phase |
| V3 Session Management | No | N/A |
| V4 Access Control | Yes | `get_import_status` IDOR pattern (404-never-403) must be preserved verbatim when `start_import` gains the new IntegrityError path — the "return existing job" response must still be scoped to the requesting user (it already is, since `find_active_job`/the new DB lookup are keyed by `user_id`) |
| V5 Input Validation | Yes | New `worker_heartbeats.last_ip` is populated from `request.client.host`, already the same trusted-proxy pattern used by `auth.py:294`'s guest rate-limiter (uvicorn `--proxy-headers --forwarded-allow-ips='*'`, confirmed in `deploy/entrypoint.sh:8-10`). No new validation surface — `request.client` can be `None` in tests, handle with `if request.client else None` |
| V6 Cryptography | No | N/A |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Race condition on duplicate import creation (TOCTOU) | Tampering / DoS (resource exhaustion via duplicate concurrent imports) | Postgres partial unique index (PRUNE-05) — the actual fix this phase ships |
| Spoofed `X-Worker-Id` polluting `worker_heartbeats` | Spoofing | Already accepted as advisory-only (T-123-03 precedent, D-06's own text: "worker_id is self-reported/advisory, whereas IP maps onto the real topology"). `last_ip` is the stated mitigation/cross-check, not a hard auth boundary — correctly scoped as observability, not security-critical, per CONTEXT.md's own framing ("operator-owned worker machines... negligible GDPR surface") |
| Foreign/tampered token on flaw-blob or atomic-submit blob_nodes | Tampering | Already implemented (T-145-09, T-147-02) — untouched by this phase |

## Sources

### Primary (HIGH confidence — verified against live code this session)
- `app/routers/eval_remote.py` (full file, 1676 lines) — all endpoint/handler line numbers, `worker_id_label`, D-04 isolation docstrings
- `scripts/remote_eval_worker.py` (full file, 1162 lines) — `_handle_full_ply_response` dead-code confirmation, D-06 ladder comment confirming it's unreachable
- `tests/test_eval_worker_endpoints.py` (structural scan of all 95 test boundaries + targeted reads of ~15 test bodies)
- `app/services/zobrist.py`, `app/services/chesscom_to_lichess.py`, `app/services/canonical_slice_sql.py`, `app/services/normalization.py`, `app/schemas/normalization.py`, `app/schemas/eval_remote.py`, `app/models/game.py`, `app/models/eval_jobs.py`, `app/services/eval_queue_service.py`, `app/routers/imports.py`, `app/models/import_job.py`, `app/services/import_service.py`, `app/repositories/import_job_repository.py`, `app/services/guest_service.py`, `app/routers/auth.py`, `deploy/entrypoint.sh` — read/grepped directly
- `alembic/versions/20260311_142537_9e234104d7f2_add_import_jobs_table.py` — existing migration style precedent

### Secondary (MEDIUM confidence)
- `.planning/phases/149-retire-prune/149-CONTEXT.md` — user-locked decisions D-01 through D-10, treated as authoritative for scope/design choices (not re-litigated), but breadcrumbs were independently verified rather than trusted blindly
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — milestone/requirement traceability

### Tertiary (LOW confidence)
- Prod worker-fleet zero-legacy-traffic claim (A1 in Assumptions Log) — cited from CONTEXT.md, not independently re-run against prod this session

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, all patterns already in repo with cited line numbers
- Architecture: HIGH — full read of the affected router/worker files this session
- Pitfalls: HIGH — Pitfalls 1, 3, 4 are mechanically verified via direct code reads (not inferred); Pitfall 2 is a genuine, documented contradiction found in the code's own comments

**Research date:** 2026-07-04
**Valid until:** 14 days (this phase touches a live-traffic worker fleet whose migration status is time-sensitive — re-verify the zero-legacy-traffic claim if planning/execution slips past a few days)
