---
phase: "248"
slug: "blunder-check-refutation-stats-and-calibration-seed-261108-dk0"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-10"
---

# Phase 248 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| remote worker to server | worker-supplied best_move/pv at ply+1 feed the refutation UCI | untrusted move strings |
| scorer to DB | per-game write of the refutation pair and stamps | game_flaws / games rows |
| dev box to prod DB | backfill (9 shards) and the read-only report over the tunnel | prod game data |
| repository to readers | committed calibration report and spot-check | aggregates, public game links |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-248-01 | Tampering | _derive_refutation | medium | mitigate | `chess.Move.from_uci` under a ValueError guard plus `post.legal_moves` membership before inference (`app/services/maia_flaw_scoring.py:364-378`); tested | closed |
| T-248-02 | Tampering | write_game_maia_scores | high | mitigate | ascending `pg_advisory_xact_lock` per game plus in-lock fingerprint re-read with refutation_uci (`maia_flaw_scoring.py:118,556-583`); mutation proof (c) in 248-01-SUMMARY | closed |
| T-248-03 | Denial of service | live lanes extra inference | low | accept | see Accepted Risks | closed |
| T-248-04 | Tampering | scripts/blunder_check/metrics.py | medium | mitigate | boundary tests and mutation proofs (248-02-SUMMARY); 31 tests in test_blunder_check_metrics.py green | closed |
| T-248-05 | Tampering | backfill `--db` target | high | mitigate | `choices` + `required=True`, banner prints current_database/server only (`scripts/backfill_maia_flaws.py:554-619`) | closed |
| T-248-06 | Tampering | selector SQL | medium | mitigate | mode picks one of two constant predicates (`_STAMP_CLAUSE_BY_MODE`, line 176); other inputs bound | closed |
| T-248-07 | Tampering | partial/stale refutation writes | medium | mitigate | `require_unstamped` on the mode's own stamp, advisory locks, fingerprint re-read; mutation proofs (248-03-SUMMARY) | closed |
| T-248-08 | Tampering | report engine | high | mitigate | `default_transaction_read_only=on` via server_settings (`scripts/blunder_check/sample.py:89`); write-raises test | closed |
| T-248-09 | Denial of service | prod DB under report reads | medium | mitigate | `pool_size=1`, named statement_timeout, 2.5% sample (`sample.py:84-99`) | closed |
| T-248-10 | Information disclosure | committed report | medium | mitigate | aggregates only; grep of reports/blunder-check/ for user_id/username/email finds nothing | closed |
| T-248-11 | Information disclosure | spot-check content | medium | mitigate | public chess.com/lichess links, ratings and moves only; render test asserts no user id/email | closed |
| T-248-12 | Denial of service | dev CPU under Maia | low | accept | see Accepted Risks | closed |
| T-248-13 | Elevation of privilege | unapproved deploy / prod write | high | mitigate | owner answered `merge-and-deploy`; deploy via /deploy and bin/deploy.sh (release #469, 248-06-SUMMARY) | closed |
| T-248-14 | Denial of service | migration vs running 247 backfill | high | mitigate | 247-07 EXIT=0 and no backfill process before deploy (248-06-SUMMARY Task 1) | closed |
| T-248-15 | Denial of service | prod load during refutation backfill | high | mitigate | no overlap with other backfills, 9 shards, slice first, pg_stat_activity watched (21 of 50 early) (248-07-SUMMARY) | closed |
| T-248-16 | Tampering | partial writes after crash | medium | mitigate | one transaction per batch under locks plus fingerprint guard; catch-up reruns selected 0 games (248-07-SUMMARY) | closed |
| T-248-17 | Tampering | report run against prod | high | mitigate | read-only session, run after all backfills, pg_stat_activity 20 -> 21 during the run (248-08-SUMMARY) | closed |
| T-248-18 | Information disclosure | committed report and spot-check | medium | mitigate | aggregates and public links only; 7 windows read before commit (248-08-SUMMARY) | closed |
| T-248-SC | Tampering | npm/pip/cargo installs | low | accept | see Accepted Risks | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-248-01 | T-248-03 | inference runs in asyncio.to_thread after the commit with no session open, about 77-150 ms per user blunder | plan 248-01 threat model | 2026-11-09 |
| AR-248-02 | T-248-12 | one single-threaded ORT session on the dev box; sample size is a flag | plan 248-05 threat model | 2026-11-09 |
| AR-248-03 | T-248-SC | no packages installed in any plan of this phase | plans 248-01..08 threat models | 2026-11-09 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-10 | 19 | 19 | 0 | orchestrator (secure-phase, ASVS L1 grep-depth) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-10
