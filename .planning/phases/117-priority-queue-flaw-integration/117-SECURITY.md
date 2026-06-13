---
phase: 117
slug: priority-queue-flaw-integration
status: secured
threats_open: 0
threats_closed: 13
asvs_level: 1
created: 2026-06-13
---

# SECURITY.md — FlawChess Phase 117 Security Audit

**Phase:** 117 — Priority Queue + Flaw Integration
**Plans Audited:** 117-01 (Schema), 117-02 (Queue Service), 117-03 (Drain Integration)
**ASVS Level:** 1 · **Block on:** high
**Audit Date:** 2026-06-13
**Auditor stance:** Adversarial — every mitigation assumed absent until grep-proven.
**Result:** SECURED — 13/13 threats CLOSED, 0 open.

---

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| admin client → tier-1 trigger | Superuser-authenticated enqueue; the ONLY enqueue path exposed in Phase 117 (user-facing trigger is Phase 118) |
| future external worker → lease/report | A browser/external worker would claim+report jobs; in v1 only the server EnginePool is a worker, but the lease contract defines the boundary |
| eval_jobs claim → Postgres | FOR UPDATE SKIP LOCKED atomic claim; parameterized SQL only |
| drain → engine gather | asyncio.gather over EnginePool workers OUTSIDE any AsyncSession (CLAUDE.md hard rule; structurally enforced) |
| migration → prod DB | DDL + a single backfill UPDATE on the ~558k-row games table; instant nullable adds, no table rewrite |
| eval_jobs.user_id / game_id → users/games | FK ON DELETE CASCADE — referential integrity DB-enforced |

---

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-117-01 | Denial of Service | accept | CLOSED | Migration backfill is `UPDATE games WHERE white_blunders IS NOT NULL AND lichess_evals_at IS NULL` (games ~558k rows, not 44M). No UPDATE on game_positions — only instant nullable `add_column` ops. `alembic/versions/20260613_120000_phase_117_queue_pv.py:156-161` |
| T-117-02 | Tampering (orphan rows) | mitigate | CLOSED | `ForeignKey("users.id", ondelete="CASCADE")` `app/models/eval_jobs.py:67`; `ForeignKey("games.id", ondelete="CASCADE")` `:71` |
| T-117-03 | Information Disclosure (new columns) | accept | CLOSED | best_move/pv/timestamps non-sensitive analysis outputs, no PII |
| T-117-04 | Elevation of Privilege (tier-1 trigger) | mitigate | CLOSED | `POST /admin/eval/enqueue-tier1/{game_id}` gated by `Annotated[User, Depends(current_superuser)]` `app/routers/admin.py:89` |
| T-117-05 | Denial of Service (unbounded fan-out) | mitigate | CLOSED | Superuser-only enqueue (T-117-04); partial unique index `uq_eval_jobs_game_active` prevents duplicate active jobs per game `app/models/eval_jobs.py:37-41` |
| T-117-06 | Info Disclosure / waste (guest games) | mitigate | CLOSED | Tier-1/2 CTE `AND u.is_guest = false` `eval_queue_service.py:134`; tier-3 `User.is_guest == False` `:205`; enqueue guest-guard incl. None-user case `if is_guest is None or is_guest: return False` `:334` |
| T-117-07 | Tampering / SQLi (SKIP LOCKED CTE) | mitigate | CLOSED | Named bind params `:worker_id` / `:ttl` `eval_queue_service.py:127-158`; bound dict `:158`; zero f-strings inside any `sa.text()` (grep confirmed) |
| T-117-08 | Tampering (future external worker) | accept | CLOSED | `leased_by` server-assigned (`"server-pool"`); no user-controlled worker identity in Phase 117; external-worker auth deferred to Phase 118+ |
| T-117-09 | Denial of Service (whole-pool fan-out) | mitigate | CLOSED | `asyncio.gather` `eval_drain.py:1188-1190` runs after `load_session` exits (`:1176`) and before `write_session` opens (`:1219`) — structurally outside any session |
| T-117-10 | Tampering (preserve/overwrite gate repointed) | mitigate | CLOSED | WR-02 gate `Game.lichess_evals_at.is_(None)` `eval_drain.py:213`; non-comment grep for `white_blunders.is_(None)` returns zero; `is_analyzed` from `lichess_evals_at IS NOT NULL` `eval_queue_service.py:170-172` |
| T-117-11 | Repudiation / partial write | mitigate | CLOSED | Single `write_session` `eval_drain.py:1219-1258`: apply evals + classify+oracle + both markers + job report + commit, all atomic; classify/oracle errors propagate (CR-01/WR-01 fixes) to abort before markers commit |
| T-117-12 | Information Disclosure (Sentry identifiers) | mitigate | CLOSED | game_id/user_id/ply via `set_context`/`set_tag` only; `capture_message` strings are static literals; zero f-string interpolation in capture calls (grep confirmed) |
| T-117-SC | Tampering (supply chain) | mitigate | CLOSED | `pyproject.toml` unchanged across Phase 117 (git log); all imports in-tree pre-117 |

---

## Unregistered Threat Flags from SUMMARY.md

None. 117-01 and 117-02 SUMMARYs explicitly record zero new threat flags; 117-03 introduced no new unregistered attack surface. No new network endpoints beyond the superuser-gated admin trigger.

---

## Accepted Risks Log

| Risk ID | Category | Rationale |
|---------|----------|-----------|
| T-117-01 | DoS (migration) | games ~558k rows; single-statement UPDATE safe; game_positions gets only instant nullable adds (no rewrite). No runtime row-count guard — deploy-time note only (RESEARCH A3). |
| T-117-03 | Info disclosure | New columns (best_move, pv, lichess_evals_at, full_pv_completed_at) are non-sensitive engine output; no PII. |
| T-117-08 | Tampering (future worker auth) | External-worker identity boundary is a Phase 118+ concern; in Phase 117 the only worker is the server engine pool with server-assigned identity. |

---

## Notes

- **T-117-06 depth:** the missing-user edge case in `enqueue_tier1_game` (`is_guest is None`) was the CR-01 review fix — a missing user short-circuits at `:334` before any FK insert.
- **T-117-11 subtlety:** the per-flaw PV write loop wraps individual PV UPDATEs in try/except (intentional — one oversized PV must not drop already-written flaws/oracle counts); a connection-class error still invalidates the session so the outer commit fails and completion markers are not recorded. Fault tolerance is bounded to application-level exceptions.
- **T-117-09 structural guarantee:** gather-outside-session is enforced by context-manager boundaries, not convention.

---

## Audit Trail

### Security Audit 2026-06-13
| Metric | Count |
|--------|-------|
| Threats in register | 13 |
| Closed | 13 |
| Open | 0 |
| ASVS level | 1 |
| Register origin | authored at plan time (verify-mitigations mode) |
