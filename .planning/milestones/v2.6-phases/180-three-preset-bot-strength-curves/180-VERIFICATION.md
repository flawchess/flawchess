---
phase: 180-three-preset-bot-strength-curves
verified: 2026-07-19T21:20:00Z
status: passed
score: 19/19 must-haves verified (phase-completion boundary, D-01)
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "The operator ~1,440-game sweep runs three per-preset non-uniform grids (D-03/D-04) at 24-30 games/(cell,anchor)"
    addressed_in: "Phase 180 Task 3 (folded-in HUMAN-UAT, off interactive critical path per D-01)"
    evidence: "180-04-PLAN.md truth + CONTEXT D-01: phase COMPLETES at the pilot; the sweep + reports/data/bot-curves-internal-scale.json + findings note are an operator-run HUMAN-UAT step, deferred by design (operator chose 'defer' 2026-07-19)"
  - truth: "The findings note mirrors the 173 note and bakes in interpretation caveats (Deep is a ceiling; sf0/maia700 outliers; G_preset subtracted)"
    addressed_in: "Phase 180 Task 3 (deferred operator step)"
    evidence: "180-04-PLAN.md; produced when the operator runs the sweep, not a phase-completion blocker (D-01)"
---

# Phase 180: Three-preset bot strength curves Verification Report

**Phase Goal:** Deliver the harness + measurement machinery + a validated real-engine pilot for measuring the bot's strength as a function of `bot_elo` at three blend presets on the Phase-173 internal anchor scale, plus the cross-family style-inflation gap `G_preset`. Per decision D-01, the phase COMPLETES at the Plan 04 Task 2 pilot; the full operator sweep is a folded-in HUMAN-UAT step, off the critical path.
**Verified:** 2026-07-19
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Completion Boundary (D-01)

Verified against the operator-approved completion boundary: the machinery (Plans 01-03) plus the real-engine pilot (Plan 04 Task 2). The ~18-22h operator sweep (Task 3) and its two artifacts (`reports/data/bot-curves-internal-scale.json`, the findings note) are DEFERRED by design and are correctly ABSENT — not counted as gaps, per D-01 and the verification framing.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 01-1 | `internalRatingFor` fail-loud on any non-Phase-173 anchor token | ✓ VERIFIED | `calibration-bot-cell-schedule.mjs:66-75` throws on undefined lookup; check.mjs PASS line 1 |
| 01-2 | `pickLocateAnchors` returns weakest+strongest by INTERNAL_RATING (not nominal) | ✓ VERIFIED | lines 84-87 sort on `internalRatingFor`; check.mjs "returns sf0+sf10" PASS |
| 01-3 | `selectMeasureBracket` nearest-to-estimate with >=2 Maia + >=2 SF cross-family floor | ✓ VERIFIED | lines 149-180 `ensureFamilyMinimum`; check.mjs "cross-family floor" PASS |
| 01-4 | Beyond-ladder cell flagged `beyond_ladder=true`, never thrown | ✓ VERIFIED | `bracketBeyondLadder` lines 190-195 returns bool; check.mjs PASS |
| 01-5 | Engine-free `.check.mjs` exits 0 with fabricated providers | ✓ VERIFIED | Re-ran this session: 6 PASS lines, exit 0 |
| 02-1 | `fit_bot_cell_rating` single-param MLE, anchors held fixed | ✓ VERIFIED | `calibration_anchor_fit.py:455-498` iterates one `strength`, anchors from `fixed_ratings` |
| 02-2 | Each cell fit TWICE (vs-Maia, vs-SF) vs same fixed ratings | ✓ VERIFIED | lines 650-651 two `fit_bot_cell_rating` calls, same `fixed_ratings` dict |
| 02-3 | `G_preset = rating_vs_maia - rating_vs_sf` direct output + per-preset combined | ✓ VERIFIED | line 660 per-cell; `combine_preset_g_preset` line 669; pilot JSON `per_preset` block |
| 02-4 | bot-curves JSON mirrors internal-scale shape + caveat header | ✓ VERIFIED | `bot-curves-pilot.json` carries rating_vs_maia/sf, g_preset, CIs, beyond_ladder, `_caveat` INTERNAL-SCALE header |
| 02-5 | pytest recovers synthetic ground-truth + asserts validation throws | ✓ VERIFIED | `test_fit_bot_cell_rating_synthetic_ground_truth`, `_rejects_bad_input`, `test_g_preset_sign` — 3 passed this session |
| 03-1 | Harness windows/brackets by INTERNAL_RATING via `internalRatingFor` (fixes clamp bug) | ✓ VERIFIED | harness imports lines 83-89; used at 837, 1527 |
| 03-2 | `DEFAULT_ANCHOR_TOKENS` = 10 labels, both families fire | ✓ VERIFIED | lines 183-193 (maia700..2300 + sf0..10); raw ledger shows both families |
| 03-3 | Locate pass (~8 games/2 anchors) then measure vs bracketing anchors | ✓ VERIFIED | `pickLocateAnchors` line 1312, `selectMeasureBracket` line 1527; ledger has locate+measure passes |
| 03-4 | Beyond-ladder cell emits row, warn-and-proceed | ✓ VERIFIED | line 1528 `bracketBeyondLadder`; pilot blend-0 cell shows `beyond_ladder=true` |
| 03-5 | `--resume` replays raw per-game ledger; byte-identical continuation | ✓ VERIFIED | raw ledger TSV present; pilot acceptance: SHA256 unchanged, empty diff (operator-verified) |
| 03-6 | Near-free metric columns populate; fabricated `.check.mjs` proves onPly | ✓ VERIFIED | ledger has cp_loss_sum/blunder_count/sf_agree/maia_agree cols; check.mjs 6 PASS lines, exit 0 |
| 04-1 | Full engine-free logic layer green before any real engine | ✓ VERIFIED | Re-ran all 3 gate commands this session — all exit 0 |
| 04-2 | Real-engine pilot: sane non-clamped ratings, INTERNAL_RATING windowing, both families, byte-identical resume | ✓ VERIFIED (HUMAN-UAT, operator-approved 2026-07-19) | Committed pilot artifacts (88 games); both families in ledger; operator sign-off recorded in SUMMARY |
| 04-3 | Phase COMPLETES at pilot; sweep is folded-in operator HUMAN-UAT | ✓ VERIFIED | D-01 boundary; operator chose "defer" 2026-07-19; ROADMAP row marks 4/4 complete at pilot |

**Score:** 19/19 in-scope truths verified (0 present/behavior-unverified). 2 truths (Plan 04 truths 4 & 5) are the deferred operator sweep — out of the D-01 completion boundary, not gaps.

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Operator ~1,440-game three-preset sweep at 24-30 games/(cell,anchor) | Task 3 (HUMAN-UAT, off critical path) | D-01; operator "defer" 2026-07-19 |
| 2 | `reports/data/bot-curves-internal-scale.json` + findings note (mirrors 173) | Task 3 (deferred) | Produced when operator runs the sweep; not a completion blocker |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/lib/calibration-bot-cell-schedule.mjs` | Two-pass scheduler, fail-loud, cross-family floor | ✓ VERIFIED | 195 lines, substantive, wired into harness |
| `scripts/lib/calibration-bot-cell-schedule.check.mjs` | Engine-free assertions | ✓ VERIFIED | 119 lines, 6 PASS, exit 0 |
| `scripts/calibration_anchor_fit.py` | `fit_bot_cell_rating` MLE + g_preset + JSON | ✓ VERIFIED | 869 lines; single-param MLE + dual fits + combine + JSON emit |
| `tests/scripts/test_calibration_anchor_fit.py` | Recovery + validation tests | ✓ VERIFIED | 353 lines; 3 relevant tests pass |
| `scripts/calibration-harness.mjs` | Internal-scale two-pass loop + near-free + resume | ✓ VERIFIED | 1655 lines; imports schedule module, 10-anchor default |
| `scripts/lib/calibration-near-free-metrics.check.mjs` | Near-free metric assertions | ✓ VERIFIED | 88 lines, 6 PASS, exit 0 |
| `reports/data/calibration-harness-2026-07-19T16-41-26-964Z*.tsv` | Pilot ledger/cells/summary | ✓ VERIFIED | 3 TSVs present, both anchor families in raw ledger |
| `reports/data/bot-curves-pilot.json` | Pilot fit output | ✓ VERIFIED | Well-formed: ratings, CIs, g_preset, per-preset, caveat header |
| `reports/data/bot-curves-internal-scale.json` | Deferred sweep output | — DEFERRED | Correctly ABSENT (Task 3, off critical path) |

### Key Link Verification

| From | To | Via | Status |
|------|----|----|--------|
| `calibration-bot-cell-schedule.mjs` | `calibration-internal-scale.mjs` | `import { INTERNAL_RATING }` | ✓ WIRED (line 32) |
| `calibration-bot-cell-schedule.mjs` | `calibration-anchor-schedule.mjs` | `scoreInInformativeBand`/`bandDistance` | ✓ WIRED (line 33) |
| `calibration-harness.mjs` | `calibration-bot-cell-schedule.mjs` | imports internalRatingFor/pickLocateAnchors/locateEstimate/selectMeasureBracket/bracketBeyondLadder | ✓ WIRED (lines 83-89, used 1312/1527/1528) |
| Harness TSV | `calibration_anchor_fit.py` load path | both anchor families + near-free columns | ✓ WIRED (pilot ledger consumed by fitter → bot-curves-pilot.json) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Schedule logic | `calibration-bot-cell-schedule.check.mjs` | 6 PASS, exit 0 | ✓ PASS |
| Near-free metrics | `calibration-near-free-metrics.check.mjs` | 6 PASS, exit 0 | ✓ PASS |
| Fitter MLE + g_preset | `pytest -k "fit_bot_cell_rating or g_preset"` | 3 passed, 7 deselected | ✓ PASS |
| Real-engine pilot | (operator-run, not re-run) | operator-approved 2026-07-19 | ? SKIP (HUMAN-UAT done) |

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in any of the six modified files. No stubs or empty implementations. SUMMARY "Known Stubs: None" confirmed by scan.

### Gaps Summary

No gaps. Every must-have inside the D-01 completion boundary is verified in the codebase: the three source modules (scheduler, fitter extension, harness) are substantive, correctly wired, and their engine-free gates re-ran green this session. The real-engine pilot's committed artifacts (raw ledger with both anchor families, well-formed `bot-curves-pilot.json`) plus the recorded operator approval (2026-07-19) satisfy the D-02b HUMAN-UAT criterion. The three adjudicated pilot signals (`any_clamped` = benign shutout continuity clamp not the nominal-fallback bug; blend-0 `beyond_ladder` = low-N under-bracketing; Human `G_preset=+70` = within enormous 8-game CIs) are documented and operator-approved as benign/low-N.

The two deferred items (the operator sweep and `bot-curves-internal-scale.json` + findings note) are explicitly out of the completion boundary per D-01; their absence is by design, not a defect.

---

_Verified: 2026-07-19_
_Verifier: Claude (gsd-verifier)_
