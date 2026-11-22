---
phase: "259"
slug: "facepalm-first-principles-refit"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-22"
---

# Phase 259 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| stored engine lines -> line replay | `game_positions.pv` tokens come from worker-supplied analysis (untrusted strings) | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| operator box -> prod DB (read-only) | the features pull reads prod lines and games | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| committed reports -> repository | review and features output land in git | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| operator box -> prod DB (tunnel, read-only) | the features pull | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| eval apply lanes -> post-commit hook -> game_flaws | worker-supplied lines become stored inputs | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| migration -> prod game_flaws at container start | schema change on a ~7.8M-row table | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| operator CLI -> prod DB | mode and cutoff become SQL predicates; shard processes open connections | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| migration -> prod game_flaws / games at container start | additive schema change | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| operator box -> prod DB (tunnel) | multi-hour batched UPDATE passes | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| shared checkout -> running passes | branch switches in MAIN while passes run | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| committed features TSV -> fit -> constants pasted into the app | fitted values reach every user's score | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| operator box -> prod DB (read-only) | the calibration sampler and miss-label sampler read prod | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| user request -> library / drill queries -> facepalm_expr | the score expression runs inside user-scoped queries | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| migration -> prod game_flaws at container start | index DDL | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| operator script -> prod DB | a write connection running CREATE INDEX CONCURRENTLY | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| operator box -> prod DB (tunnel) | a write session building an index; read-only pulls and calibration | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| fit output -> app constants | fitted values reach every user's score | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| release -> every user's library and drill | scores change for every user | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| operator box -> prod DB (read-only) | EXPLAIN ANALYZE on the largest account | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| eval apply lanes -> post-commit hook -> game_flaws | the hook's write set changes | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| migration -> prod game_flaws at container start | destructive schema change | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |
| operator scripts -> prod during the deploy | old code reading dropped columns | game ids, plies, engine lines, Maia probabilities, schema changes; no credentials or personal data |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-259-01 | Tampering | quiet_line_facts / quiet_best_line_facts on malformed or illegal UCI tokens (plan 01) | medium | mitigate | the same `_parse_move` + `legal_moves` guards as line_facts (T-250-01); null facts, never raises; `test_quiet_unusable_input_gives_null_facts` | closed |
| T-259-02 | Tampering | the live 9-slot arrays changing before the switch (half-converted scores, D-11) (plan 01) | high | mitigate | line_facts / best_line_facts / _facts_after_first_move untouched; `_net_loss` keeps its stop rule; the existing old-rule tests run unchanged (acceptance runs them with `-k "not quiet"`) | closed |
| T-259-03 | Tampering | features pull writing to prod (plan 02) | high | mitigate | `make_readonly_engine` (default_transaction_read_only on); `test_builder_has_no_write_path` stays; the review tool imports no database code (acceptance grep) | closed |
| T-259-04 | Information disclosure | committed review report and TSV (plan 02) | low | mitigate | game ids, plies and analysis links only, no usernames (precedent of the committed features TSVs) | closed |
| T-259-05 | Denial of service | prod DB during the pull beside another operator job (plan 03) | medium | mitigate | one read-only connection, `pgrep` check before the run, strictly one operator run at a time (D-11) | closed |
| T-259-06 | Tampering | building the recompute before the owner confirmed the rule (D-09) (plan 03) | high | mitigate | blocking decision here; plan 04 Task 1 carries a precondition on this SUMMARY's "confirm" option | closed |
| T-259-07 | Tampering | line mode overwriting maia_best_reply_prob with NULL (Pitfall 4) (plan 04) | high | mitigate | FACEPALM_REPLY_COLUMNS outside FACEPALM_COLUMNS; `test_line_mode_rows_never_carry_the_reply_prob` and `test_line_mode_preserves_a_stored_reply_prob` | closed |
| T-259-08 | Tampering | a reply probability or scalars from a since-repaired line written over the repaired one (plan 04) | medium | mitigate | refutation_pv and best_pv are already in the fingerprint; write_game_maia_scores re-checks it under the advisory lock (unchanged) | closed |
| T-259-09 | Denial of service | the migration rewriting or scanning game_flaws at container start (plan 04) | high | mitigate | nullable ADD COLUMN without default and NOT VALID CHECKs only (catalog changes); no index in this release | closed |
| T-259-10 | Tampering | SQL built from the mode / cutoff (plan 05) | high | mitigate | the mode picks a constant clause (`_REPLY_PENDING_CLAUSE`), never CLI text; the cutoff stays a bound parameter | closed |
| T-259-11 | Denial of service | prod connections during the reply pass (plan 05) | high | mitigate | one connection per shard, 12 workers documented as the ceiling, `--throttle-ms`; run strictly alone (plan 06 run book) | closed |
| T-259-12 | Tampering | reply mode overwriting other columns or stamps (plan 05) | medium | mitigate | the row carries PK plus FACEPALM_REPLY_COLUMNS only; the tracer test asserts every other column and stamp is unchanged | closed |
| T-259-13 | Denial of service | prod DB during the line and reply passes (WAL, locks, connections) (plan 06) | high | mitigate | 4 and 12 shards with `--throttle-ms 50`, one transaction per batch, S1 recorded before each launch, map rule 6 (one operator run at a time, operator connections under about 25); SIGTERM stops after a batch; resume by cutoff / stamp | closed |
| T-259-14 | Tampering | commits on the wrong branch after the R1 merge, or a running pass picking up code from a branch switch (plan 06) | high | mitigate | branch and checkout map: one committing checkout, cycles opened and closed by the orchestrator with idempotent checks, executors one at a time with a branch precondition, passes only from the detached PRODWT | closed |
| T-259-15 | Tampering | R1 moving live scores (not behaviour-neutral) (plan 06) | medium | mitigate | plan 04's test pins that the score expressions read no new column; the line pass rewrites the arrays with the unchanged old rule from today's lines (consistent with what the hook writes) | closed |
| T-259-16 | Tampering | constants that cannot be reproduced from the committed table (plan 07) | high | mitigate | `--check-constants` over the six names with a tolerance; seeded, deterministic CV; byte-identical report test | closed |
| T-259-17 | Repudiation | a shape chosen by AUC against the owner's D-01 principle (plan 07) | medium | mitigate | the shape is fixed in code; the alternatives section is printed only; `test_alternatives_section_is_information_only` pins that the constants stay the chosen fit | closed |
| T-259-18 | Tampering | calibration or miss-label runs writing to prod (plan 08) | high | mitigate | both keep `make_readonly_engine` (read-only transactions, unchanged); no write path added | closed |
| T-259-19 | Tampering | a stale calibration cache scored with the new fields missing (plan 08) | low | mitigate | CACHE_VERSION 5: an older cache is refused, as today | closed |
| T-259-20 | Elevation of privilege | readers losing their user scoping (V4) when the column map changes (plan 09) | high | mitigate | only `_game_flaw_columns` and the twin change; reader predicates (`GameFlaw.user_id == user_id`, `player_only_gate`) are untouched and their tests run in the full suite | closed |
| T-259-21 | Tampering | SQL and Python twins drifting apart (chip and filter disagree, 253 D-10) (plan 09) | high | mitigate | parity grid over every branch at both lambda bounds, type grid, fit-vs-twin parity on the plan 03 table | closed |
| T-259-22 | Tampering | a NULL loss falling to the ELSE branch of the key-move CASE (Pitfall 6) (plan 09) | medium | mitigate | explicit first branch `played_prob IS NULL OR loss IS NULL -> NULL`; grid rows with NULL in each input | closed |
| T-259-23 | Denial of service | an INVALID or drifted index after a failed CIC still costing writes, accepted by IF NOT EXISTS (Pitfall 5) (plan 10) | high | mitigate | check_index verifies indisvalid and the exact definition; `--drop-invalid` drops it concurrently; tests pin migration SQL == ORM and test-DB definition == EXPECTED_INDEXDEF | closed |
| T-259-24 | Denial of service | the migration building a 4.7M-row index under a lock at container start (plan 10) | high | mitigate | CONCURRENTLY IF NOT EXISTS in autocommit_block (a no-op on prod after the operator build); the plan 12 deploy is gated on `--check-only` exit 0 | closed |
| T-259-25 | Information disclosure | the operator script printing the prod URL (plan 10) | medium | mitigate | the URL comes from db_url_for_target and is never printed (only settings and counts) | closed |
| T-259-26 | Tampering | switching before the backfill is complete (chips vanish, drill pool drops, Pitfall 7) (plan 11) | high | mitigate | readiness gate here (pending counts 0, residues, coverage delta within 1%) and re-checked by plan 12 right before the deploy | closed |
| T-259-27 | Denial of service | the index build waiting on long transactions or running beside another job (plan 11) | high | mitigate | map rule 6 (no other operator process, S1 recorded), `statement_timeout = 0` only in the build session, detached with Monitor, invalid-index recovery path | closed |
| T-259-28 | Tampering | candidate constants committed by accident during the calibration (plan 11) | medium | mitigate | `git restore` plus the `git diff --quiet` acceptance check before any commit | closed |
| T-259-29 | Tampering | deploying with readiness regressed since plan 11 (plan 12) | high | mitigate | readiness and index check re-run in Task 2 step 1, immediately before the go-ahead and the deploy | closed |
| T-259-30 | Tampering | frontend 70% cutoff drifting from FACEPALM_STATS_MIN (Pitfall 9) (plan 12) | medium | mitigate | conditional frontend change in Task 1 with its tests; test_facepalm_stats_min_is_the_high_preset_cut updated with it | closed |
| T-259-31 | Denial of service | EXPLAIN ANALYZE load on prod (plan 12) | low | accept | SELECT-only, one read-only connection, one account, a handful of runs; the readers already run these statements for that user | closed |
| T-259-32 | Tampering | a reader of the arrays left when plan 15 drops them (plan 13) | high | mitigate | the grep gates of Tasks 1 to 3 (app, scripts, tests, comments excluded) plus the full suite; plan 14 adds the model-level gate | closed |
| T-259-33 | Tampering | arrays going stale on rows written after this release while still present (plan 13) | low | accept | the score has not read them since plan 12; a rollback below plan 12 would need a line pass anyway (D-05); the drop follows in the same release cycle | closed |
| T-259-34 | Tampering | mate plies changing when they come from the quiet facts (plan 13) | medium | mitigate | the same step replay feeds both rules; the tracer test compares them with the plan 04 values | closed |
| T-259-35 | Tampering | irreversible loss of the array values (plan 14) | high | mitigate | shipped only behind plan 15's blocking one-way decision with the no-reader evidence; the downgrade re-adds the columns and CHECKs; the values are derivable by a line pass with the shipped rule from git history | closed |
| T-259-36 | Denial of service | a long lock on game_flaws while dropping a 741 MB index (plan 14) | medium | mitigate | DROP INDEX CONCURRENTLY IF EXISTS in an autocommit block first; the column drops are catalog-only | closed |
| T-259-37 | Tampering | irreversible loss of the array values on prod (plan 15) | high | mitigate | blocking one-way decision (Task 2) with the no-reader and coverage evidence; downgrade re-adds the columns empty; values derivable by a line pass with the shipped rule from git history | closed |
| T-259-38 | Denial of service | an operator script selecting a dropped column during the swap (Pitfall 8) (plan 15) | high | mitigate | pgrep check before the deploy; the hook never raises (Sentry capture), so a failure cannot break an eval lane | closed |
| T-259-SC | Tampering | npm/pip/cargo installs (plan 01) | high | accept | this plan installs no package | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

Evidence per threat (file and line, test, SUMMARY or report reference) is in the auditor verdict of 2026-11-22: 39 of 39 closed at ASVS level 1, verified by static read and grep. Transitional mitigations that later plans removed on purpose (the old line functions, the D-09 review tool, the R1 neutrality test) were verified through git history.

### Owner-approved exceptions to "one operator run at a time"

| Plan | Step run beside the Phase 252 feeder | Threat | Outcome |
|---|---|---|---|
| 03 | read-only features pull | T-259-05 | drift 0 |
| 06 | reply pass (30 of 50 prod connections at the peak; line pass at 8 workers instead of 4) | T-259-13 | EXIT=0, 0 write or score failures |
| 11 | covering index build, features pull, calibration | T-259-27 | index valid in under 50 s |
| 12 | readiness re-check, JIT measurement | T-259-29, T-259-31 | clean |
| 15 | drop deploy | T-259-38 | feeder kept running, hook kept writing |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-259-01 | T-259-31 | Read-only EXPLAIN ANALYZE on one prod account over one connection; the readers already run these statements for that user | plan 12 threat model | 2026-11-22 |
| AR-259-02 | T-259-33 | The arrays were stale on rows written between the switch and the drop; moot since migration f3a7b9c1e259 dropped them | plan 13 threat model | 2026-11-22 |
| AR-259-03 | T-259-SC | No package was installed in any plan; the manifests changed only by one ruff extend-exclude line | every plan threat model | 2026-11-22 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-22 | 39 | 39 | 0 | gsd-security-auditor (ASVS 1, block_on high) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-22
