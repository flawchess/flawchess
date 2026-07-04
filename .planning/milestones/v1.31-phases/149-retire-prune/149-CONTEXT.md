# Phase 149: Retire & Prune - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Shrink the eval-pipeline surface before Phase 150 refactors it: delete the dead Gen-1 eval protocol and other dead weight, and land two small durability migrations, so Phase 150 consolidates 2 copies of the write path instead of 3.

**Server-side only.** No worker protocol change, no fleet redeploy. Fleet is confirmed fully on atomic-lease/submit (2026-07-04 prod log grep: zero legacy `/lease`+`/submit` hits over 11.3h vs 54k atomic-lease hits).

In scope (PRUNE-01…06):
- PRUNE-01: delete Gen-1 `/lease` + `/submit` + `_apply_submit` + worker `_handle_full_ply_response` + associated Gen-1 tests. Keep `/flaw-blob-*` (tier-4 backfill actively draining).
- PRUNE-02: remove dead weight — tier-2 lane logic (keep DB column), `hashes_for_game`, `chesscom_to_lichess` tables, caller-less `Game.needs_engine_full_evals`.
- PRUNE-03: replace `_normalize_chesscom_result` silent-draw fallback with explicit "unknown" + Sentry capture.
- PRUNE-04: record `worker_schema_version` telemetry on submits (log/tag only, no 426 gate).
- PRUNE-05: durable import-job guard — create `import_jobs` row in the request handler + partial unique index.
- PRUNE-06: `worker_heartbeats` table populated server-side from existing submit fields.

Out of scope: anything Phase 150 owns (write-path consolidation), worker protocol changes, a 426 version-rejection gate, R14 tier-3 lease (deferred).
</domain>

<decisions>
## Implementation Decisions

### Worker Heartbeats (PRUNE-06) — DISCUSSED
The one area the user chose to deep-dive. Table exists purely for fleet liveness/version visibility; it closes a real observability blind spot (today worker identity lives ONLY in hourly-rotating access logs — no server-side registry — and that gap already caused one wrong "server-pool did it" diagnosis). It also makes the milestone's own "fleet fully migrated to atomic" safety claim a standing SQL query instead of a one-off log grep. No consumer (admin UI / alert) is built in this phase — this is raw telemetry for a future surface; accepted because the cost is ~nothing (zero worker change, one server-side upsert-by-PK).

- **D-01 — Write cadence:** Upsert on **every live submit** (entry-submit, flaw-blob-submit, atomic-submit). No throttle. ~7.5 single-row upserts/s by PK is trivial and keeps `last_seen` genuinely real-time (the point of a liveness signal).
- **D-02 — Counts:** Accumulate cumulative `submit_count` **and** `evals_submitted` (sum of `len(evals)` per submit). Both are free at write time and distinguish "many tiny games" from "grinding big ones".
- **D-03 — Version columns:** Store **both** `sf_version` (string, updated on every submit — every lane sends it) and `worker_schema_version` (int, **nullable** — only the atomic lane sends it; leave NULL / don't overwrite when the lane doesn't provide it).
- **D-04 — Trigger events:** **Submits only.** Leases carry no result telemetry and would ~double write volume; a worker that leases but never submits is not meaningfully "alive/productive". Do not upsert on lease endpoints.
- **D-05 — Table shape (guidance):** `worker_heartbeats(worker_id PK, last_ip NULLABLE, sf_version, worker_schema_version NULLABLE, last_seen, submit_count, evals_submitted)`. `worker_id` matches the advisory `X-Worker-Id` identity already used elsewhere (VARCHAR(16), see `worker_id_label` in `eval_remote.py`). Upsert via `INSERT … ON CONFLICT (worker_id) DO UPDATE` (counts `= existing + delta`, `last_seen = now()`, `last_ip`/versions overwritten with the latest). Planner/researcher decide exact column types and whether to funnel the three submit handlers through one shared helper.
- **D-06 — Worker IP (`last_ip`):** Store the source IP as `last_ip TEXT NULL`, populated from `request.client.host` in the same submit upsert. This is the **most trustworthy fleet-identity signal** — `worker_id` is self-reported/advisory, whereas IP maps onto the real topology (`194.191.211.24` = local box, Hetzner = minor workers) and disambiguates spoofed/shared IDs. **Free in prod:** uvicorn runs `--proxy-headers --forwarded-allow-ips='*'` (`deploy/entrypoint.sh:10`), so Caddy's `X-Forwarded-For` is trusted and `request.client.host` already resolves the true remote worker IP (same value `auth.py:294`'s guest rate-limiter relies on). Nullable because `request.client` can be `None` in tests. Store only the latest IP (no history). Add a one-line column comment noting these are operator-owned worker machines (local + Hetzner), not end-user IPs — negligible GDPR surface. **Scope note:** this column is beyond the literal R15 enumeration `(worker_id, version, last_seen, counts)` — added deliberately (user-approved 2026-07-04) because it directly serves R15's fleet-visibility intent at ~zero cost.

### Claude's Discretion — locked-by-requirements, capture sensible defaults (NOT deep-discussed)
The user explicitly treated the remaining gray areas as locked by REQUIREMENTS/ROADMAP and delegated the details. Capture these as researcher/planner guidance, not re-litigated decisions — but flag if research surfaces a reason to deviate:

- **D-07 — PRUNE-03 "unknown" result flow:** `GameResult` is `Literal["1-0","0-1","1/2-1/2"]` (`app/schemas/normalization.py:13`) — it has no "unknown" member. Recommended default: **do NOT widen `GameResult`.** Have `_normalize_chesscom_result` signal "unknown" out-of-band and let `normalize_chesscom_game` **skip the game** (return `None`, same as it already does for non-standard variants) rather than store a fabricated draw. Emit a `sentry_sdk.capture_message`/`capture_exception` with `white_result`/`black_result` in `set_context` (never in the message string — grouping rule). Confirm downstream callers tolerate the extra `None` skip. Planner may instead choose to persist the game with a nullable/`unknown` result if skipping loses a game the user played — flag the trade in RESEARCH.md.
- **D-08 — PRUNE-05 durable import guard:** Add a partial unique index `(user_id, platform) WHERE status IN ('pending','in_progress')` and create the `import_jobs` row **in the request handler** (`app/routers/imports.py::start_import`) before `asyncio.create_task`, so the DB — not the in-memory `find_active_job` registry — is the source of truth for concurrency. Recommended default: on `IntegrityError` from the index, **return the existing active job with HTTP 200** (preserve the current dedup contract at `imports.py:67-73`, which already returns existing-job-200), not a 409. The in-memory `find_active_job` fast-path may **stay as a cheap pre-check** but is no longer the guarantee. `import_jobs` model already exists (`app/models/import_job.py`); currently rows appear to be created via `create_job` AFTER the in-memory check — the migration moves the durable guarantee to the DB.
- **D-09 — PRUNE-01/02 deletion scope:** `tests/test_eval_worker_endpoints.py` (95 test fns) covers **both** the dead Gen-1 `/lease`+`/submit` **and the LIVE** `/entry-lease`+`/entry-submit` lanes plus `_claim_entry_eval_games` helpers. **Surgical removal only** — delete the Gen-1 `/lease`+`/submit` tests, KEEP every entry-lane / atomic / flaw-blob test. Do not delete the whole file. For tier-2: remove the lane *logic* but keep the DB column (per PRUNE-02). `/flaw-blob-*` is untouched.
- **D-10 — PRUNE-04:** `worker_schema_version` already arrives in `AtomicSubmitRequest` (`app/schemas/eval_remote.py:239`). This is telemetry recording only (log/tag), no worker change, no rejection gate. Naturally overlaps D-03 (the heartbeat table is one place it lands); also acceptable as a Sentry tag / structured log on the submit path.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone source & review
- `reports/reviews/pipeline-review-fable-2026-07-04.md` — the full pipeline architecture review (D1-D8, F1-F8 + Tier-A/B recommendations) that this whole milestone implements. **NOTE the path drift:** SEED-080 and ROADMAP.md cite `reports/pipeline-review-2026-07-04.md`, but the file actually lives at `reports/reviews/pipeline-review-fable-2026-07-04.md`. Use the real path.
- `.planning/seeds/SEED-080-pipeline-consolidation-milestone.md` — maps each PRUNE requirement to a review recommendation (R2/R12/R13/R11/R8/R15) with exact line-number breadcrumbs.
- `.planning/REQUIREMENTS.md` (PRUNE-01…06, lines 28-33) — the locked requirement text.
- `.planning/ROADMAP.md` §"Phase 149: Retire & Prune" (lines 138-149) — goal + 5 success criteria.

### Source files touched (breadcrumbs from SEED-080)
- `app/routers/eval_remote.py` — Gen-1 `/lease` (553), `/submit` (746), `_apply_submit` (330) to delete; live submit handlers (`entry-submit` 853, `flaw-blob-submit` 1217, `atomic-submit` 1643) to instrument for heartbeats; `worker_id_label` (529) advisory identity dep.
- `scripts/remote_eval_worker.py` — dead `_handle_full_ply_response` handler to delete (SEED-080 cites ~656-704).
- `tests/test_eval_worker_endpoints.py` — surgical Gen-1 test removal (see D-08).
- `app/services/normalization.py` — `_normalize_chesscom_result` (186) silent-draw fallback (PRUNE-03).
- `app/schemas/normalization.py:13` — `GameResult` literal (no "unknown" member).
- `app/routers/imports.py::start_import` (45) + `app/models/import_job.py` + `app/services/import_service.py` — durable import guard (PRUNE-05).
- `app/services/zobrist.py` (~270) — `hashes_for_game` to delete; `chesscom_to_lichess` tables + `Game.needs_engine_full_evals` (PRUNE-02).
- `app/schemas/eval_remote.py:239` — `worker_schema_version` already present on `AtomicSubmitRequest` (PRUNE-04).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `worker_id_label` dependency (`app/routers/eval_remote.py:529`) — already resolves the advisory `X-Worker-Id` identity (VARCHAR(16), truncated) used by `games.entry_eval_leased_by`. Reuse it verbatim as the `worker_heartbeats.worker_id` PK source; no new header parsing.
- `import_jobs` table / `ImportJob` model (`app/models/import_job.py`) already exists — PRUNE-05 is an index + a moved insert point, not a new table.
- Existing dedup contract in `imports.py:67-73` returns the existing active job with HTTP 200 — the durable guard should preserve that observable behavior.
- `normalize_chesscom_game` already returns `NormalizedGame | None` and skips non-standard variants via `None` — the "unknown result → skip" path (D-07) reuses that existing skip channel.

### Established Patterns
- Sentry: never embed variables in the message string — use `sentry_sdk.set_context(...)` / `set_tag(...)` (CLAUDE.md). Applies to both the PRUNE-03 unknown-result capture and any heartbeat/version telemetry.
- DB design rules (CLAUDE.md): FK + explicit `ondelete`; avoid native `ENUM`; low-volume domain columns as `TEXT`+`CHECK`. `worker_heartbeats` is low-volume (one row per worker) — plain columns are fine; `worker_id` is the natural PK.
- Migrations: `uv run alembic revision --autogenerate`; migrations run automatically on prod backend startup. Two migrations expected this phase (import partial unique index + worker_heartbeats table).

### Integration Points
- The three live submit handlers (`entry-submit`, `flaw-blob-submit`, `atomic-submit`) are where the heartbeat upsert hooks in — ideally one shared helper called from each so Phase 150's write-path consolidation inherits a single insertion point.
- Deleting Gen-1 `/lease`+`/submit` must leave `/flaw-blob-*` and all entry/atomic lanes untouched; the surgical test edit (D-09) is the main correctness risk of PRUNE-01.

</code_context>

<specifics>
## Specific Ideas

- User pushed back on building `worker_heartbeats` before accepting it — the justification (no server-side registry today + hourly log rotation that already caused a misdiagnosis + underwriting the "fleet fully on atomic" safety claim) is the reason it stays in scope. If a future reviewer questions the table's value, that is the answer, and the honest caveat is "no reader built yet."
- Everything else was explicitly delegated as locked-by-requirements; the defaults in D-06…D-09 are guidance, and the planner should flag (not silently override) if research surfaces a reason to deviate.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Milestone-level deferrals already recorded in SEED-080: 426 version-rejection gate, R14 tier-3 lease, entry/full lane merge, SEED-078 streaming.)

</deferred>

---

*Phase: 149-Retire-Prune*
*Context gathered: 2026-07-04*
