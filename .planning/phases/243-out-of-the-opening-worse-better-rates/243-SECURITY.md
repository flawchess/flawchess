---
phase: "243"
slug: "out-of-the-opening-worse-better-rates"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-31"
---

# Phase 243 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client -> `GET /api/openings/out-of-opening-stats` | Authenticated request; no parameters accepted | Session token in; the user's own aggregate rates/percentiles out |
| service -> SQL builders | Literal TC / metric ids and int constants interpolated; `user_id` bound | User id (bindparam only) |
| operator CLI -> benchmark DB | Regen and eval-source report scripts resolve a DB URL and run heavy SQL | Read-only cohort data |
| regen output -> committed TSV -> prod seed | `app/data/cohort_cdf.tsv` becomes the prod peer basis after deploy | Aggregate percentile cells (no per-user data) |
| Alembic migration -> prod tables | `b7e4c2a9f013` deletes rows on out-of-set metric labels | Percentile rows |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-243-01 | Tampering | `canonical_slice_sql.py` opening builders | high | mitigate | Only Literal ids and int constants interpolated; `user_id` via `CAST(:user_id AS int)` + `.bindparams()` (`canonical_slice_sql.py:1465`) | closed |
| T-243-02 | Information disclosure | `opening_out_repository.fetch_opening_out_counts` | medium | mitigate | Keyword-only `user_id` (`opening_out_repository.py:46`); single_user CTE scopes every row | closed |
| T-243-03 | Tampering / Repudiation | migration `b7e4c2a9f013` DELETE | medium | mitigate | Deletes only out-of-set labels, logs non-zero rowcount at WARNING (`b7e4c2a9f013...py:112-115`); owner prod `GROUP BY metric` pre-deploy check listed in 243-01/05 SUMMARY | closed |
| T-243-04 | Denial of service | MG-entry scan in the builder | low | mitigate | `gp.user_id = rc.user_id` drives the PK index scan; measured ~180 ms warm per TC (243-01) | closed |
| T-243-05 | Tampering | CDF regen / eval-source report DB target | medium | mitigate | `_assert_benchmark_db` requires `flawchess_benchmark` and `:5433` (`gen_global_percentile_cdf.py:191-246`); report uses `SET TRANSACTION READ ONLY` (`opening_out_eval_source_report.py:282`); `--metrics`/`--tcs` validated against Literals | closed |
| T-243-06 | Tampering (integrity) | `cohort_cdf.tsv` merge | high | mitigate | `merge_cells` replaces only selected metrics (`gen_global_percentile_cdf.py:699`); non-opening rows diffed byte-identical vs main before commit (243-02 Task 3) | closed |
| T-243-07 | Denial of service | ~10-minute regen | medium | mitigate | Regen ran inline from the orchestrator (setsid nohup + Monitor) after Task 1 was committed | closed |
| T-243-08 | Tampering | `_compute_and_upsert_opening_cells` | medium | mitigate | `user_id` via bindparams; upsert on the 4-column PK with `color=color` (`user_benchmark_percentiles_service.py:507`) | closed |
| T-243-09 | Denial of service | Stage B opening loop | medium | mitigate | One counts query per anchored TC; per-TC try/except with Sentry capture and `CancelledError` re-raise (`user_benchmark_percentiles_service.py:456-513`); existing semaphore unchanged | closed |
| T-243-10 | Information disclosure | `fetch_opening_out_rows` | low | mitigate | Keyword-only `user_id` (`user_benchmark_percentiles_repository.py:213`) | closed |
| T-243-11 | Spoofing | out-of-opening-stats route | high | mitigate | `current_active_user` dependency (`openings.py:76`); `test_requires_auth_returns_401` | closed |
| T-243-12 | Information disclosure | route + service | high | mitigate | Route declares only `session` and `user` (`openings.py:73-77`); `user_id` from `user.id`; router test sends extra params and asserts an identical body | closed |
| T-243-13 | Denial of service | on-read SQL | medium | mitigate | Sequential queries on one session, 4 TCs; frontend 5-minute stale time, gated on tier2 readiness | closed |
| T-243-14 | Information disclosure | popover testids / Umami | low | mitigate | Fixed literal testids, pinned in `analytics.test.ts:407-408` | closed |
| T-243-15 | Tampering (XSS) | `OutOfOpeningSection` / `OutOfOpeningPopover` | low | mitigate | React text nodes only; no `dangerouslySetInnerHTML` in the new components | closed |
| T-243-16 | Information disclosure | stale cache after delete-all | low | mitigate | `['outOfOpeningStats']` invalidated in `App.tsx:1031` and `Import.tsx:211,411` | closed |
| T-243-SC | Tampering | npm/pip/cargo installs | high | accept | No package installs in any plan of this phase | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-243-01 | T-243-SC | No dependency was added or upgraded in this phase (RESEARCH Package Legitimacy Audit: none), so there is no supply-chain surface to mitigate | plan-time threat model | 2026-10-31 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-31 | 17 | 17 | 0 | secure-phase orchestrator (ASVS L1 grep-depth, plan-time register) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-31
