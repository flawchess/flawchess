---
phase: 149-retire-prune
audited: 2026-07-04
asvs_level: 1
block_on: high
threats_total: 14
threats_closed: 13
threats_open: 0
threats_open_nonblocking: 1
accepted_risks: 5
---

# Phase 149: Retire & Prune — Security Audit

**Audited:** 2026-07-04
**ASVS Level:** 1 (grep-level: mitigation present in the cited file/boundary)
**block_on:** high (only high/critical open threats block ship)

Verified against the shipped implementation, not documentation. Every threat below was
checked by grepping/reading the actual cited files and, for the four high-severity
`mitigate` threats, additionally confirmed by running the relevant test suites live.

## Threat Verification

| Threat ID | Category | Severity | Disposition | Status | Evidence |
|-----------|----------|----------|-------------|--------|----------|
| T-149-01-SP | Spoofing | low | accept | CLOSED | `app/models/worker_heartbeat.py:14-19` class docstring states worker_id is advisory/self-reported and "NEVER used for authz/ownership decisions (T-123-03)". Confirmed by reading every `worker_id` use site in `app/routers/eval_remote.py`: all live behind `require_operator_token` first; the one place `worker_id` gates behavior (`Game.entry_eval_leased_by == worker_id`, eval_remote.py:574) is lease-bookkeeping between already-authenticated fleet workers, not an access-control boundary, and is explicitly commented as "the same advisory worker identity" (line 567-568). |
| T-149-01-TA | Tampering | low | accept | CLOSED | `grep -rn "worker_schema_version" app/` shows it is only ever stored (repository upsert + coalesce) and read back in a docstring — never compared/gated. `grep -n "426"` returns nothing anywhere in `app/routers/eval_remote.py`. The pre-existing 422 `sf_version` gate (`EXPECTED_SF_VERSION`, D-5/T-123-07) predates Phase 149 and is a separate, authoritative Stockfish-binary check, not the telemetry field this threat concerns. |
| T-149-01-ID | Info Disclosure | low | accept | CLOSED | `app/models/worker_heartbeat.py:28-34` — `last_ip` column comment verbatim: "Operator-owned worker machine IP (local box + Hetzner), not an end-user IP — negligible GDPR surface (D-06)." |
| T-149-01-DoS | DoS | low | mitigate | CLOSED | `app/repositories/worker_heartbeat_repository.py:53-77` — single `pg_insert(...).on_conflict_do_update(index_elements=["worker_id"])`, one row per call, no batching/fan-out. No throttle exists but severity/volume (~7.5/s) makes this an accepted low-risk shape per the plan. |
| T-149-02-TA | Tampering | medium | mitigate | CLOSED | `app/services/normalization.py:189-218` — `_normalize_chesscom_result` no longer has a `return "1/2-1/2"` fallback (`grep -n "safe fallback"` → empty); unrecognized pairs return `None`. `normalize_chesscom_game` (lines 263-275) skips (`return None`) on the unknown signal, flowing through the pre-existing `if normalized is not None` gate in `chesscom_client.py` with zero caller change. |
| T-149-02-ID | Info Disclosure | low | mitigate | CLOSED | `normalization.py:270-274` — `sentry_sdk.set_context("chesscom_result", {"white_result": ..., "black_result": ...})` then a **constant** `capture_message("Unrecognized chess.com result combination")` — no f-string/interpolation of the result variables into the message. |
| T-149-03-DoS | DoS | low | mitigate | **OPEN (non-blocking)** | Declared mitigation is a procedural pre-merge action ("re-run the prod-log zero-legacy-traffic grep immediately before merging"), not a code artifact. `149-VERIFICATION.md`'s own "Human Verification Required" section states this grep was last run during the CONTEXT.md planning session and **was not re-run** at execution or verification time — it is explicitly deferred to the deploy step. Cannot be marked CLOSED on code evidence alone; low severity keeps it non-blocking under `block_on: high`. |
| T-149-03-RE | Coverage-loss | high | mitigate | CLOSED | `tests/test_eval_worker_endpoints.py` contains `test_atomic_submit_with_job_id_stamps_eval_jobs` (2784), `test_atomic_submit_late_job_id_is_noop` (2855), `test_atomic_submit_without_job_id_does_not_touch_eval_jobs` (2930), `test_atomic_lease_lichess_eval_game_releases_lease` (2024) — all four present and, per live run, passing (`uv run pytest tests/test_eval_worker_endpoints.py -q` → 68 passed). `TestTier1Claiming` is confirmed absent (`grep -c "class TestTier1Claiming"` → 0). |
| T-149-03-TA | Tampering | high | mitigate | CLOSED | All 6 live routes confirmed registered: `/atomic-lease`, `/entry-lease`, `/entry-submit`, `/flaw-blob-lease`, `/flaw-blob-submit`, `/atomic-submit` (grep on `@router.post`). All 5 KEEP test classes present: `TestFlawBlobLeaseEndpoint`, `TestAtomicLeaseEndpoint`, `TestAtomicSubmitEndpoint`, `TestBlobAssemblyHelper`, `TestFlawBlobSubmitEndpoint`. Gen-1 (`/lease`, `/submit`, `_apply_submit`) confirmed deleted (grep → 0 hits each). Full `test_eval_worker_endpoints.py` run: 68 passed. |
| T-149-04-TA | Tampering | high | mitigate | CLOSED | `app/services/chesscom_to_lichess.py` retains `CHESSCOM_INTRA_TC`, `CHESSCOM_BLITZ_TO_LICHESS`, `convert_chesscom_to_lichess`, `composed_chesscom_to_lichess_grid`; dead Table-3 surface (`LICHESS_BLITZ_INTRA_TC`, `_LICHESS_BLITZ_KEYS`, `lookup_uscf_from_lichess_blitz`, `lookup_fide_from_lichess_blitz`) confirmed absent repo-wide. `app/services/canonical_slice_sql.py` still imports `composed_chesscom_to_lichess_grid`/`convert_chesscom_to_lichess` and resolves under `uv run ty check` (zero errors, live-run confirmed). |
| T-149-04-TA2 | Tampering | high | mitigate | CLOSED | `app/models/eval_jobs.py:68` — `tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)` retained; the tier-agnostic `ORDER BY tier ASC`-style claim SQL comment intact. `TIER_AUTO_WINDOW` confirmed absent repo-wide (`grep -rn` → empty). `app/models/game.py`'s `needs_engine_full_evals`/`_needs_engine_full_evals_expression` confirmed absent, comment updated to reference the raw predicate instead of the deleted symbol. |
| T-149-05-DoS | DoS (IDOR-adjacent resource exhaustion) | high | mitigate | CLOSED | Migration `alembic/versions/20260704_123013_12d3df9c5373_import_jobs_partial_unique_index.py` creates `uq_import_jobs_user_platform_active` on `(user_id, platform) WHERE status IN ('pending', 'in_progress')`; `uv run alembic heads` → single head (`12d3df9c5373`). `app/routers/imports.py:99-136` moves the durable `create_import_job` + `commit()` into `start_import` before `asyncio.create_task`, with `_bootstrap_import_job` (`import_service.py`) confirmed no longer calling `create_import_job`. Live test run: `tests/test_imports_router.py tests/test_import_service.py` → 81 passed. |
| T-149-05-AC | Access Control (IDOR) | high | mitigate | CLOSED | `app/repositories/import_job_repository.py:133-165` — `get_active_job_for_user_platform` filters `ImportJob.user_id == user_id, ImportJob.platform == platform, ImportJob.status.in_(("pending","in_progress"))`; called from `imports.py:117-119` with the requesting `user_id` (extracted from the authenticated `user` dependency, not client input) — no cross-user leak path found. Docstring explicitly states "ASVS V4 / IDOR guard". |
| T-149-05-ID | Info Disclosure | low | accept | CLOSED | `imports.py:108-136` — the `except IntegrityError:` branch never calls `sentry_sdk.capture_exception`; capture only happens in the separate `if existing_row is None:` (invariant-violation) sub-branch and the unrelated `except Exception:` (CR-01) branch, both of which are genuine-bug paths, not the routine race. |

## Code Review Fallout (149-REVIEW.md / 149-REVIEW-FIX.md)

The phase's own code review found and fixed one blocker (CR-01) and two warnings (WR-01, WR-02) that
materially affect two of the threats above; both fixes were independently re-verified in the live
code during this audit, not taken on the review report's word alone:

- **CR-01** (feeds T-149-05-DoS's durability guarantee): `start_import`'s `except Exception:` branch
  now discards the stuck in-memory job on any non-`IntegrityError` failure — confirmed present at
  `imports.py:137-151`.
- **WR-01** (feeds T-149-01-DoS / heartbeat robustness): heartbeat upsert now runs in its own
  `session.begin_nested()` savepoint with a swallow-and-Sentry-capture wrapper, so a heartbeat write
  failure can never abort a real eval submission — confirmed present at
  `worker_heartbeat_repository.py:78-83`.
- **WR-02** (dead-code hygiene, not a registered threat): `LeaseResponse`/`SubmitEval`/`SubmitRequest`/
  `SubmitResponse` schema classes deleted — informational only.

## Open — Non-blocking (severity below `block_on: high`)

| Threat ID | Category | Severity | Mitigation Expected | What's Missing |
|-----------|----------|----------|----------------------|-----------------|
| T-149-03-DoS | DoS | low | Pre-merge re-run of the prod-log zero-legacy-traffic grep for `/eval/remote/lease` and `/eval/remote/submit`, confirming no stale worker is still calling the now-deleted Gen-1 routes, immediately before this branch ships. | Not yet executed. `149-VERIFICATION.md`'s "Human Verification Required" section already flags this as outstanding and recommends `ssh flawchess "docker compose logs backend \| grep -c '/eval/remote/submit '"` (or equivalent) run right before `bin/deploy.sh`. Does not block phase completion (low severity, below the `high` block threshold) but should be run before this branch is promoted to `production`. |

*This item does NOT count toward `threats_open` in the frontmatter (0) — it is below the `block_on: high` threshold. It blocks nothing in this phase; it is a deploy-time checklist item for whoever ships the branch.*

## Unregistered Flags

None. Scanned all 5 SUMMARY files (`149-01` through `149-05`) for a `## Threat Flags` section — none present in any. No new attack surface was identified in the reviewed diff beyond what the 5 plans' threat models already registered; the code-review's own findings (CR-01/WR-01/WR-02/IN-01/IN-02) all map onto existing threat IDs or are pure dead-code hygiene with no security surface.

## Verification Method Notes (ASVS L1 + spot depth)

Per `asvs_level: 1`, the baseline bar is "mitigation present in the cited file." For the four
high-severity threats (T-149-03-RE, T-149-03-TA, T-149-04-TA, T-149-04-TA2, T-149-05-DoS,
T-149-05-AC) this audit went beyond grep-only and additionally ran the actual test suites live
(`tests/test_eval_worker_endpoints.py` — 68 passed; `tests/test_imports_router.py` +
`tests/test_import_service.py` — 81 passed; `uv run ty check` on the touched modules — zero
errors) rather than trusting the SUMMARY/VERIFICATION reports' claimed pass counts.

## Summary

**13/14 threats CLOSED. 1/14 OPEN but non-blocking** (low severity, below `block_on: high`).
**`threats_open` (blocking gate value): 0.** No high/critical severity threat has an absent
mitigation. Phase 149 is clear to ship on security grounds; the one open item
(T-149-03-DoS) is a deploy-time operational checklist step, not a code gap, and should be
completed before promoting this branch to `production`.

---
*Audited: 2026-07-04*
*Auditor: Claude (gsd-security-auditor)*
