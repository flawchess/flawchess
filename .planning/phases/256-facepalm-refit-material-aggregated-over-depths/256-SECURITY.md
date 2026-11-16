---
phase: "256"
slug: "facepalm-refit-material-aggregated-over-depths"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-16"
---

# Phase 256 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register authored at plan time (every PLAN carries a `<threat_model>`); verified at ASVS level 1
> (grep depth) against the merged phase branch. No SUMMARY raised a threat flag.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| model constants -> SQL score expression | `facepalm_material` / `facepalm_score` SQL builders used by library and drill readers | model constants and weights only, no user input |
| committed TSV / labels -> fit script | `fit_facepalm.py` reads `--features` and `--labels` | committed report files, game ids and plies |
| operator box -> prod DB (tunnel) | read-only features pull and calibration sample (plan 07) | read-only game and flaw facts |
| owner decision -> shipped selection | material input and `FACEPALM_SCORE_MIN` decide what the drill serves | constants in `blunder_check_rules.py` |
| blind set-8 key (gitignored) -> repo | `temp/blunder-check/set8-key-2026-11-16.json` must never be committed | label key |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-256-01 | Tampering | `facepalm_material` SQL builders | low | mitigate | Only constants and weights enter the expression as SQLAlchemy literals; `app/services/facepalm_material.py` has no user-input path | closed |
| T-256-02 | Tampering | Python / SQL twin drift | medium | mitigate | Decaying-mean models in the parity grid and the stored-facts test; `test_new_twin_reproduces_phase_250_score` present and green | closed |
| T-256-03 | Denial of service | heavier score expression in reader queries | low | mitigate | Unrolled scalar CASE, no `unnest`, no subquery (module docstring; asserted by T-256-07's test) | closed |
| T-256-04 | Tampering | stale calibration cache under an aggregate model | medium | mitigate | `CACHE_VERSION: int = 4` in `scripts/blunder_check/sample.py`; `test_cache_version_3_is_refused` | closed |
| T-256-05 | Tampering | WR-01 pure-miss branch | medium | mitigate | `_pure_miss_term` / `_pure_miss_sql` return None / NULL; revert run failed 5 tests (256-03-SUMMARY) | closed |
| T-256-06 | Tampering | first_stable / gate drift between twins | medium | mitigate | `test_sql_twin_parity_aggregate_inputs` (6,144-row grid) | closed |
| T-256-07 | Denial of service | aggregate expressions in reader queries | low | mitigate | `test_aggregate_expression_is_one_scalar_expression` | closed |
| T-256-08 | Tampering | features TSV parsing | low | mitigate | `load_features` raises `FitError` on a foreign file or missing column; committed files only | closed |
| T-256-09 | Tampering | fit rows differ from what the shipped twin scores (WR-03, D-05) | medium | mitigate | `_spec_exclusion`; WR-03 and D-05 revert runs fail (256-04-SUMMARY) | closed |
| T-256-10 | Repudiation | which input and gate produced the constants | low | mitigate | Constants block and `_EXACT_FIELDS` carry `FACEPALM_MATERIAL_INPUT` and `FACEPALM_LOSS_GATE` | closed |
| T-256-11 | Information disclosure | owner section copies label comments and links | low | accept | See Accepted Risks Log | closed |
| T-256-12 | Information disclosure | blind set-8 key | medium | mitigate | `temp/` ignored by `.gitignore:5`; `git ls-files temp` is empty; no phase commit touches `temp/` | closed |
| T-256-13 | Tampering | set 8 leaking into the hold-out | medium | mitigate | `test_set_eight_holdout_runs_the_pipeline_on_sets_one_to_seven`; mutation-proved (256-06-SUMMARY) | closed |
| T-256-14 | Tampering | features pull and calibration writing to prod | high | mitigate | Both scripts use `make_readonly_engine`; no UPDATE pass in this phase | closed |
| T-256-15 | Denial of service | prod connections during the pull and calibration | medium | mitigate | 13 connections before launch, one script at a time, one read-only connection each (256-07-SUMMARY) | closed |
| T-256-16 | Tampering | refit run on unfinished labels | high | mitigate | D-01 check printed "60 set-8 rows, 0 unlabelled"; cell-wise comparison "290 rows compared, 0 unexpected cell changes" | closed |
| T-256-17 | Information disclosure | set-8 key and prod cache | medium | mitigate | Both stay in gitignored `temp/`; never read, never force-added | closed |
| T-256-18 | Repudiation | provenance of the chosen input and cut | low | mitigate | Owner reply, report paths and exact fit command in 256-07-SUMMARY; reports committed (`a869c5940`) | closed |
| T-256-19 | Tampering | hand-pasted or hand-tuned constants | medium | mitigate | `test_shipped_constants_reproduce_from_the_refit_features` runs `--check-constants` on the committed TSV every suite run | closed |
| T-256-20 | Tampering | Window 14 selected for the drill after the refit | low | mitigate | `window_14` tests in `tests/services/test_facepalm_score.py` read the 2026-11-16 TSV | closed |
| T-256-21 | Repudiation | why the cut and input are what they are | low | mitigate | Provenance comments in `blunder_check_rules.py` name `facepalm-fit-2026-11-16.md` and the command | closed |
| T-256-22 | Tampering | depth-3 values drift when the loader moves to arrays | medium | mitigate | `test_depth_3_fit_reproduces_the_2026_11_15_constants`; `--check-constants` on the 2026-11-15 table | closed |
| T-256-23 | Repudiation | which rule chose the material input | low | mitigate | Comparison section prints every input and the deciding reason | closed |
| T-256-24 | Tampering | constants block from a different input than the chosen one | medium | mitigate | `test_constants_block_is_the_chosen_input_final` | closed |
| T-256-SC | Tampering | npm/pip/cargo installs | high | accept | See Accepted Risks Log; `pyproject.toml`, `uv.lock` and the frontend manifests are unchanged across the phase | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-256-01 | T-256-11 | The labels TSV with the same links and comments is already committed; game ids and plies only, no usernames | plan 256-06 threat model | 2026-11-16 |
| AR-256-02 | T-256-SC | No plan installs a package; dependency manifests and lockfiles are unchanged over the phase diff | plans 256-01 to 256-08 threat models | 2026-11-16 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-16 | 25 | 25 | 0 | execute-phase orchestrator (L1 grep depth, plan-time register) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
