---
phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti
verified: 2026-09-13T00:00:00Z
status: human_needed
score: 12/14 must-haves verified
covered_files: [".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-01-PLAN.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-01-SUMMARY.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-02-PLAN.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-02-SUMMARY.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-03-PLAN.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-03-SUMMARY.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-04-PLAN.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-04-SUMMARY.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-05-PLAN.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-05-SUMMARY.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-06-PLAN.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-06-SUMMARY.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-07-PLAN.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-07-SUMMARY.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-08-PLAN.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-08-SUMMARY.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-CONTEXT.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-D13-SPOTCHECK.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-DISCUSSION-LOG.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-PATTERNS.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-RESEARCH.md", ".planning/phases/221-tactic-tagger-real-game-precision-winning-floor-predicate-ti/221-VALIDATION.md", "CHANGELOG.md", "app/repositories/library_repository.py", "app/services/flaws_service.py", "app/services/forcing_line_gate.py", "app/services/tactic_detector.py", "fixtures/tagger/realgame_tags.csv", "frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx", "frontend/src/lib/tacticComparisonMeta.ts", "frontend/src/lib/tacticMotifDefinitions.ts", "frontend/src/lib/theme.ts", "reports/retag/retag-2026-09-12.md", "reports/retag/retag-2026-09-13.md", "reports/tactic-tagger/tactic-tagger-2026-09-12.md", "scripts/research/dev_probe.py", "scripts/research/oracle_compare.py", "scripts/research/sample_realgame_tags.py", "scripts/retag_flaws.py", "scripts/tactic_tagger_report.py", "tests/scripts/tagger/conftest.py", "tests/scripts/tagger/precision_floors.py", "tests/scripts/tagger/test_detector_precision.py", "tests/scripts/test_ab_validate_gate.py", "tests/scripts/test_retag_flaws.py", "tests/services/test_flaws_service.py", "tests/services/test_forcing_line_gate.py", "tests/services/test_tactic_comparison_service.py", "tests/services/test_tactic_detector.py"]
covered_digest: "v1:sha256:65dfee4c9b6f17fe04cce0d5fa704012234dff19badf1cd120d1cee31f354710"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Sacrifice real-game real-share (SC2): decide whether 0.385 (measured, floor 0.33) is acceptable to ship against the ROADMAP's literal '>= 0.8 or suppressed' bar for sacrifice."
    expected: "An explicit accept/reject decision on record. If accepted, add a VERIFICATION.md override entry naming why 0.385 is acceptable (D-01's winning floor independently eliminates losing-line sacrifices; no board-derivable rule separates a compensated sacrifice from a delayed recapture; see 221-08-SUMMARY.md and 221-D13-SPOTCHECK.md)."
    why_human: "This is a product/precision-bar acceptability judgment on a number the code correctly and honestly reports, not a code defect — the phase's own plan-05/06/07 SUMMARYs already flag it with human_judgment: true and ask for this exact decision."
  - test: "TAGFIX-09 acceptance claim 5: allowed-sacrifice count fell 6.9x (58,863 -> 8,568), short of the ROADMAP's predicted ~10x. Decide whether to accept the shortfall or pull the named lever (lower SACRIFICE_CLEARANCE_MAX_DEPTH, currently 4)."
    expected: "An explicit accept/reject decision. Losing-line share for sacrifice fell 77.9% -> 0.4% (allowed) and 32.8% -> 0.0% (missed) regardless of the count shortfall, which is the phase's primary safety goal."
    why_human: "The shortfall's cause (D-05's retirement in plan 08, an operator-made decision) is fully documented in 221-07-SUMMARY.md Task 2 / Claim 5; whether 6.9x is 'the predicted order of magnitude' is a judgment call, not a programmatically checkable fact."
  - test: "Open a game with a former sacrifice or clearance tag on flawchess.com; confirm remaining tactic chips read as real tactics and the Library tactic grid renders without a clearance family/filter chip."
    expected: "No clearance chip anywhere in the UI; surviving sacrifice/other tactic chips on real games read as genuine tactics, not artifacts of the retag."
    why_human: "Visual/UX confirmation on the live site — the plan's own <human-check>, left to the operator per 221-07-SUMMARY.md's 'Operator human-check (open)' section; the operator indicated they would cross-check this independently."
---

# Phase 221: Tactic-Tagger Real-Game Precision — Winning Floor, Predicate Tightening & Port Fixes (SEED-165) Verification Report

**Phase Goal:** Make the tactic-motif tags describe tactics the user could actually have used or avoided — gate fixes (winning floor, never-skip-on-None-cp), a sacrifice/clearance predicate decision, seven cook-port fixes, missed-orientation parity, a real-game gate, and an offline prod retag with a before/after report.
**Verified:** 2026-09-13
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | ROADMAP SC1 — CC0 fixture gate green; oracle shows 0 cook-only for deflection/fork/trapped-piece and 0 ours-only for discovered-attack; sacrifice/clearance divergences documented | ✓ VERIFIED | Ran `uv run pytest tests/scripts/tagger -q -s` live: 3 passed, all 26 CC0-validated motifs at/above floor. Oracle table reproduced in `221-06-SUMMARY.md` (`scripts/research/oracle_compare.py`): all four required-zero cells hold. Divergence blocks present and current in `tests/scripts/tagger/precision_floors.py` (sacrifice comment names plan 08's retirement; clearance names D-06/D-07). |
| 2a | ROADMAP SC2 (clearance leg) — clearance real-share >= 0.8 or suppressed | ✓ VERIFIED | `_TIER3_REGISTRY` (`app/services/tactic_detector.py`) has 7 entries, no `clearance` — confirmed by direct read. `FAMILY_TO_MOTIF_INTS` (`app/repositories/library_repository.py`) and the frontend `TacticFamily` union (`frontend/src/lib/tacticComparisonMeta.ts`) both exclude clearance; only doc-comments mention the string. `SUPPRESSED_MOTIFS` in `precision_floors.py` includes `"clearance"`. |
| 2b | ROADMAP SC2 (sacrifice leg) — sacrifice real-share >= 0.8 | ✗ NOT MET (see human_verification) | Live run of `tests/scripts/tagger` shows `sacrifice real_share=0.385` (13 surviving, 5 real) against `REALGAME_REAL_SHARE_FLOOR['sacrifice']=0.33` — the never-regress floor PASSES but the ROADMAP's literal 0.8 bar for "keep" does not. No suppression branch exists for sacrifice (only clearance has one). This is a business/precision-bar judgment already flagged by the phase's own plan-05/06/07 SUMMARYs (`human_judgment: true`) as needing an explicit accept/reject decision — not a missing/stub/unwired code defect. Routed to human_verification. |
| 3 | ROADMAP SC3 — dev retag delta within reason of the review's simulation; survivors read as real tactics | ✓ VERIFIED | `221-06-SUMMARY.md`: sacrifice -94.4% (band ~-90%), clearance fully cleared, tier-2 deviations beyond the -5% band explained (D-04's combined mate-derived reject applying phase-wide) and are not code defects; 4 survivor sacrifice lines spot-checked and read as real. |
| 4 | ROADMAP SC4 — prod retag done, TAGFIX-09 acceptance queries pasted into the summary | ✓ VERIFIED | `221-07-SUMMARY.md` contains the full SQL + before/after numbers. Independently confirmed: `git rev-parse origin/production` == `cb5f2d622...` == `ssh flawchess "git rev-parse HEAD"` (live check, this session). `reports/retag/retag-2026-09-13.md` exists on disk. PR #358 confirmed MERGED via `gh pr view 358` (baseRefName production, headRefName main, mergedAt 2026-09-12T22:56:15Z). |
| 5 | ROADMAP SC5 — no `bin/reset_db.sh`, no migration, no MultiPV re-eval, no change to `PV_CAP_PLIES` / `ONLY_MOVE_CP_GAP_THRESHOLD` / the dispatcher's depth-primary sort | ✓ VERIFIED | `git diff --stat 3ceab603a d139075e8 -- alembic/ app/models/` empty (this session); `git diff 3ceab603a d139075e8 -- app/` has no `PV_CAP_PLIES =` / `ONLY_MOVE_CP_GAP_THRESHOLD =` hunk; `_sort_key` / `detect_tactic_motif` in `tactic_detector.py` unchanged in that diff. |
| 6 | TAGFIX-01 — per-tier winning floor (0cp geometric / +200cp tier-3+move-type) at the firing node, derived from the tier registries, mate-exempt | ✓ VERIFIED | `FIRING_FLOOR_TIER3_CP=200`, `FIRING_FLOOR_GEOMETRIC_CP=0`, `_MOTIF_FLOOR_CP`, `floor_cp_for_motif` in `tactic_detector.py`; `_solver_eval_at_firing`/`_passes_winning_floor`/`passes_winning_floor_fallback` in `forcing_line_gate.py`. `tests/services/test_forcing_line_gate.py::TestWinningFloorAtFiring` (17 tests) passes live. |
| 7 | TAGFIX-02 — gate never skipped merely because `pre_flaw_eval_cp` is None; already-winning reject derived from `eval_mate` | ✓ VERIFIED | `_classify_tactic_gated` in `flaws_service.py`: gate-run condition is `pv_blob is not None and len(pv_blob) > 0` (no `pre_flaw_eval_cp` conjunct); `_is_already_winning` in `forcing_line_gate.py` branches on `pre_flaw_eval_mate` when cp is absent. Live run of `tests/services/test_flaws_service.py` (179 passed) covers `TestClassifyTacticGated`. |
| 8 | TAGFIX-03 — sacrifice predicate with depth cap; persistence rule (D-05) | ⚠ SUPERSEDED BY OPERATOR DECISION, not a gap | `SACRIFICE_CLEARANCE_MAX_DEPTH=4` depth cap present and enforced in `detect_sacrifice` (verified by reading the code). The boards[k+3] persistence rule was implemented in plan 05, then retired in gap-closure plan 08 after `221-D13-SPOTCHECK.md` (operator review) showed it dropping two confirmed-real sacrifices (rows 0064, 0133) with no board-derivable fix available. Per this verification's explicit task instructions, the D-05 absence is NOT flagged as a gap — it is a recorded, operator-reviewed, reasoned reversion, not a missed requirement. `TestSacrificeRealGameSpotCheckRegressions` (2 tests) pins the retirement live. |
| 9 | TAGFIX-04 — clearance strengthen-then-decide, all 8 branch touchpoints landed on one decision | ✓ VERIFIED | See truth 2a. Structural check reproduced live: `_TIER3_REGISTRY` excludes `CLEARANCE`; `_INT_TO_MOTIF[15]=='clearance'`; `detect_clearance` still callable; `'clearance' not in FAMILY_TO_MOTIF_INTS`. |
| 10 | TAGFIX-05 — seven fixture-verified cook-port fixes land, oracle-verified | ✓ VERIFIED | `221-02-SUMMARY.md` / `221-06-SUMMARY.md` oracle table: all four SC1 required-zero cells hold. `self-interference` confirmed absent from `_TIER3_REGISTRY` in the live read. |
| 11 | TAGFIX-06 — missed-orientation parity: move stack on the missed pass, intermezzo k=2 unblocked | ✓ VERIFIED | `_build_missed_board_with_stack` in `flaws_service.py`, wired into `_detect_tactic_for_flaw`'s missed branch (live read). Dev measurement in `221-04-SUMMARY.md`: missed intermezzo 15->55 (within 3x of allowed 64); prod acceptance query in `221-07-SUMMARY.md` shows missed intermezzo 2,957 vs allowed 4,611 (1.56x, within target). |
| 12 | TAGFIX-07 — real-game gate harness built, CI-asserted per motif | ✓ VERIFIED | `fixtures/tagger/realgame_tags.csv` (164 rows, confirmed via `wc -l`); `REALGAME_REAL_SHARE_FLOOR` + `_compute_realgame_metrics` in `precision_floors.py` / `test_detector_precision.py`; live run prints the per-motif real-share table and gates sacrifice/intermezzo/x-ray. (Whether the gated *values* clear a business bar is truth 2b, tracked separately.) |
| 13 | TAGFIX-08 — harness hygiene: `discoveredCheck` caveat documented; oracle/dev-probe scripts relocated under `scripts/research/`, AGPL-clone-absent guard | ✓ VERIFIED | `scripts/research/{sample_realgame_tags,oracle_compare,dev_probe}.py` exist; `reports/tactic-tagger/review-2026-09-12-scripts/` no longer exists (confirmed via `ls`, empty). |
| 14 | TAGFIX-09 — prod retag + acceptance queries; motif 14/15 gone; odd discovered-attack depths gone; missed intermezzo within 3x; allowed sacrifice down by predicted order of magnitude | ✓ VERIFIED with one recorded shortfall | Claims 1-4 and 6 in `221-07-SUMMARY.md` PASS (losing share <5%/<2%, motif 14 = 0/0, motif 15 = 0/0, odd discovered-attack depth = 0/0, missed intermezzo 1.56x). Claim 5 (allowed sacrifice down >=10x) measured 6.9x — recorded honestly as NOT MET with its cause (D-05 retirement) named; not silently passed. Routed to human_verification per this task's explicit instruction to report it, not hide it. |

**Score:** 12/14 must-haves verified (2 routed to human judgment: SC2 sacrifice leg and TAGFIX-09 claim 5, both honestly self-reported shortfalls, not code defects)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `app/services/tactic_detector.py` | Winning-floor constants, sacrifice/clearance predicate changes, 7 port fixes, self-interference/clearance undispatchable | ✓ VERIFIED | Read directly; matches every plan claim. |
| `app/services/forcing_line_gate.py` | `_solver_eval_at_firing`, `_passes_winning_floor`, `passes_winning_floor_fallback`, widened `apply_forcing_line_filter` | ✓ VERIFIED | Read directly; signature widened with defaulted kwargs as claimed. |
| `app/services/flaws_service.py` | Gate always runs on non-empty blob; `_pre_flaw_eval_mate`, `_firing_floor_fallback_eval`, `_build_missed_board_with_stack` | ✓ VERIFIED | Read directly; docstring and logic match. |
| `scripts/retag_flaws.py` | Real per-page `fen_map` via `_recompute_fen_map`; 4-bucket delta report | ✓ VERIFIED | `_load_fen_maps_for_page`, `_bucket_motif_change`, `_process_page` all present. |
| `tests/scripts/tagger/precision_floors.py` | Final floors (sacrifice 0.33, clearance suppressed with a preserved history comment); no `PRECISION_FLOOR` value ever lowered | ✓ VERIFIED | Read directly; floors match 08-SUMMARY's claimed final values exactly. |
| `fixtures/tagger/realgame_tags.csv` | 164 rows, row 0134 relabelled `wrong` | ✓ VERIFIED | `wc -l` = 165 (164 data + header); row 0134 content matches the operator's corrected rationale verbatim. |
| `CHANGELOG.md` | `[Unreleased]` bullet, corrected to remove the retired D-05 "much stricter... recapture" claim | ✓ VERIFIED | Bullet present, wording matches 08-SUMMARY's correction exactly. |
| `frontend/src/lib/tacticComparisonMeta.ts` + `tacticMotifDefinitions.ts` + `theme.ts` | Clearance removed from `TacticFamily`, colors, icon, Advanced group, copy | ✓ VERIFIED | Only doc-comments reference "clearance"; no live code path. |
| `reports/retag/retag-2026-09-13.md` | Prod writing-run 4-bucket report | ✓ VERIFIED | File exists on disk. |
| `scripts/research/{sample_realgame_tags,oracle_compare,dev_probe}.py` | Relocated, lint/type-clean, AGPL-clone-absent guard | ✓ VERIFIED | Files exist at the claimed path; old `reports/.../review-2026-09-12-scripts/` location is empty. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `_classify_tactic_gated` (flaws_service.py) | `apply_forcing_line_filter` (forcing_line_gate.py) | `motif_int=`, `pre_flaw_eval_mate=` kwargs | ✓ WIRED | Both new kwargs threaded through at the one call site inside the gate-run branch; verified by reading the call. |
| `_classify_tactic_gated` | `passes_winning_floor_fallback` | blob-missing branch | ✓ WIRED | `elif motif is not None and pv_blob is None:` branch calls it with `_firing_floor_fallback_eval`'s output. |
| `apply_forcing_line_filter` | `floor_cp_for_motif` (tactic_detector.py) | `_passes_winning_floor` | ✓ WIRED | Cross-module import confirmed cycle-free per plan 04 (detector has no app-internal imports). |
| `scripts/retag_flaws.py::_load_fen_maps_for_page` | `flaws_service._recompute_fen_map` | direct import | ✓ WIRED | `from app.services.flaws_service import _classify_tactic_gated, _recompute_fen_map` present; `TestRetagLiveClassifyParity` (2 tests) proves SC4 parity live. |
| `tests/scripts/tagger/test_detector_precision.py` | `precision_floors.REALGAME_REAL_SHARE_FLOOR` | `test_realgame_real_share_floor` | ✓ WIRED | Live run prints the gated table; sacrifice/intermezzo/x-ray all check against the dict. |
| `library_repository.FAMILY_TO_MOTIF_INTS` | `frontend/src/lib/tacticComparisonMeta.ts` | manual parity (no automated cross-check) | ✓ WIRED (both sides independently confirmed clearance-free) | No shared codegen between these two; verified each side by direct read rather than a single source of truth. Pre-existing pattern, not a regression introduced by this phase. |

### Behavioral Spot-Checks / Test Runs

| Behavior | Command | Result | Status |
|---|---|---|---|
| Detector + gate unit suite | `uv run pytest tests/services/test_tactic_detector.py tests/services/test_forcing_line_gate.py -q` | 196 passed, 7 skipped | ✓ PASS |
| Tagger fixture + real-game gate | `uv run pytest tests/scripts/tagger -q -s` | 3 passed; sacrifice/intermezzo/x-ray real-share PASS against their floors | ✓ PASS |
| Retag parity + report-bucket tests | `uv run pytest tests/scripts/test_retag_flaws.py -q` | 12 passed | ✓ PASS |
| Flaws-service + tactic-comparison-service tests | `uv run pytest tests/services/test_flaws_service.py tests/services/test_tactic_comparison_service.py -q` | 179 passed | ✓ PASS |
| Prod deployment matches release commit | `git rev-parse origin/production` vs `ssh flawchess "git rev-parse HEAD"` | both `cb5f2d622b5390239adc284b9da1a1426f52a50b` | ✓ PASS |
| Release PR state | `gh pr view 358 --json state,mergedAt,baseRefName,headRefName` | MERGED, production<-main, 2026-09-12T22:56:15Z | ✓ PASS |

No frontend tests or prod-DB queries were run per this task's explicit constraints (dev-only pytest runs authorized; no `bin/reset_db.sh`; no writes/queries against prod beyond the read-only `git rev-parse` deploy-SHA check already logged in `221-07-SUMMARY.md`'s own evidence trail).

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| TAGFIX-01 | 04 | Solver-winning floor at firing node | ✓ SATISFIED | See truth 6. |
| TAGFIX-02 | 04 | Gate never skipped on None cp | ✓ SATISFIED | See truth 7. |
| TAGFIX-03 | 05, 08 | Sacrifice depth cap + persistence | ✓ SATISFIED (persistence superseded by operator decision, depth cap retained) | See truth 8. |
| TAGFIX-04 | 05, 06 | Clearance decision | ✓ SATISFIED | See truth 9. |
| TAGFIX-05 | 02, 06 | Seven port fixes | ✓ SATISFIED | See truth 10. |
| TAGFIX-06 | 04 | Missed-orientation parity | ✓ SATISFIED | See truth 11. |
| TAGFIX-07 | 01, 06 | Real-game gate | ✓ SATISFIED (harness); ? NEEDS HUMAN (sacrifice bar) | See truths 12, 2b. |
| TAGFIX-08 | 01 | Harness hygiene | ✓ SATISFIED | See truth 13. |
| TAGFIX-09 | 03, 06, 07 | Prod retag + acceptance | ✓ SATISFIED (5 of 6 acceptance claims); ? NEEDS HUMAN (claim 5) | See truth 14. |

No orphaned requirements: all TAGFIX-01..09 IDs defined in ROADMAP.md are claimed by at least one plan's frontmatter `requirements` field.

### Anti-Patterns Found

None. Grepped all touched `app/` and `scripts/` files for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` — zero hits. No stub returns, no hardcoded empty-data anti-patterns found in the reviewed code paths.

### Human Verification Required

See `human_verification` in the frontmatter (3 items): the sacrifice real-share/SC2 acceptance decision, the TAGFIX-09 claim-5 (6.9x vs 10x) acceptance decision, and the plan-07 `<human-check>` (flawchess.com visual confirmation) that the phase itself deferred to the operator.

### Gaps Summary

No code-level gaps were found: every claimed artifact exists, is substantive, and is wired exactly as the plan SUMMARYs describe; all locally-runnable tests (detector, gate, flaws-service, retag parity, tagger fixture + real-game harness — 390+ tests across the five commands run in this verification) pass; the single squash-merge to `main`/`production` and the prod server SHA were independently confirmed, not merely narrated.

Two numeric acceptance bars fall short of the phase's own aspirational targets, and both are already self-reported (not hidden) in the phase's own SUMMARYs with `human_judgment: true`:

1. **Sacrifice real-game real-share (0.385) is below the ROADMAP's literal 0.8 "keep" bar for SC2.** The phase resolved this via `D-01`'s winning floor doing the losing-line-elimination work instead of a real-share bar on sacrifice specifically — a reasoned, well-evidenced trade-off (`221-D13-SPOTCHECK.md`, `221-08-SUMMARY.md`), but the ROADMAP's literal wording is not met and there is no recorded override accepting the deviation yet.
2. **Allowed-sacrifice count fell 6.9x, short of the predicted ~10x (TAGFIX-09 claim 5).** Directly attributable to the same D-05 retirement, honestly reported with the remaining lever (`SACRIFICE_CLEARANCE_MAX_DEPTH`) named in `221-07-SUMMARY.md`.

Both are judgment calls on an already-transparent, already-measured record — not evidence of missing, stubbed, or unwired implementation. This phase is recommended for **human_needed** disposition: an explicit operator decision (accept as-is, or pull the depth-cap lever in a follow-up) closes it out, at which point a re-verification with a recorded override would move it to `passed`.

---

*Verified: 2026-09-13*
*Verifier: Claude (gsd-verifier)*
