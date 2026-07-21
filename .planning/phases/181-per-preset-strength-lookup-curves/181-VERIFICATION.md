---
phase: 181-per-preset-strength-lookup-curves
verified: 2026-07-21T20:30:00Z
status: passed
score: 13/13 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 181: Per-preset strength lookup curves Verification Report

**Phase Goal:** Turn the Phase-180 curves into the shipping strength artifact: fit each preset's
`internal_rating = f_preset(bot_elo)` curve (monotone fit over the ~5 measured points), convert
to approximate human blitz ELO via `internal − G_preset + C` (C = +40 ± 100 from literature,
shared named constant), invert into per-preset `target_blitz_elo → bot_elo` lookups (100-ELO
steps) with honest per-preset ranges, an approximate-ELO disclaimer, and 2–3 harness confirmation
cells per preset validating the inversion. Single source of truth for all labeled bot strength
claims (custom bot builder, preset cards, SEED-098 personas).
**Verified:** 2026-07-21
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running the generator writes both `reports/data/bot-strength-lookup.json` AND `frontend/src/generated/botStrengthCurves.ts` | ✓ VERIFIED | Ran `uv run python scripts/gen_bot_strength_curves.py`; both files written, contents inspected |
| 2 | `--check` exits 0 on match, exits 1 on drift | ✓ VERIFIED | Ran `--check` (exit 0); tampered `bot-strength-lookup.json` with `{"tampered": true}` and re-ran `--check` → exit 1 naming the stale path; restored file, confirmed clean again |
| 3 | Fit consumes all 5 cells per preset incl. Human's two `beyond_ladder` cells | ✓ VERIFIED | `bot-curves-internal-scale.json`'s `per_preset` shows `n_cells: 5.0` for all 3 blends; `compute_artifact` hard-fails (`ValueError`) if count != 5 (D-08 guard); `extrapolated_bot_elos: [700, 1100]` present in shipped JSON's `human` component |
| 4 | Inversion returns the LOWEST bot_elo reaching each target on plateaus (D-07) | ✓ VERIFIED | Mutation test: reverted `approx_blitz_points`'s `x_lo` to `x_hi` → `test_inversion_lowest_bot_elo_wins` fails (`assert 1400 == 1200`); reverted, test passes again — genuinely tested, not symbol-present |
| 5 | Offset uses `rating_vs_maia` minus pooled `g_preset_combined` plus C, never per-cell `g_preset`/`rating_vs_sf` (D-01) | ✓ VERIFIED | `test_offset_uses_pooled_g_not_per_cell_or_vs_sf` asserts the pooled-G result and asserts it differs from the per-cell-G result; code reads `per_preset[...]["g_preset_combined"]`, fits on `rating_vs_maia` only |
| 6 | Lookup JSON stores components (fit_points, g_preset_combined, c_offset, band, extrapolated_bot_elos) separately from derived (range, lookup), plus a disclaimer (D-02) | ✓ VERIFIED | `reports/data/bot-strength-lookup.json` inspected: top-level `components`/`derived`/`disclaimer` keys, all 3 presets under each |
| 7 | Generated TS exports the lookup Record, per-preset ranges, per-preset bands, and disclaimer (D-06) | ✓ VERIFIED | `botStrengthCurves.ts` exports `BotStrengthPreset`, `APPROX_ELO_DISCLAIMER`, `BOT_STRENGTH_LOOKUP`, `BOT_STRENGTH_RANGES`, `BOT_STRENGTH_BANDS`; `npx tsc -b` passes clean |
| 8 | knip ignores the new generated TS; CI drift-checks both emitted artifacts | ✓ VERIFIED | `frontend/knip.json`'s `ignore` array contains `"src/generated/botStrengthCurves.ts"`; `npm run knip` clean; `.github/workflows/ci.yml` has a "Bot strength curves drift check" step running the generator + `git diff --exit-code` on both paths |
| 9 | Ranges round inward (floor up, ceiling down, D-10); Deep's ceiling is honest, well below the seed's hoped ~2600 | ✓ VERIFIED | Deep `derived.deep.range = {floor: 1600, ceiling: 1800}` — ceiling 1800 < 1900 (acceptance-criteria sanity check); `test_deep_range_ceiling_below_1900` passes; matches Deep's raw plateau (2064–2118 internal at bot_elo 2300/2600, pooled to ≈2091) minus pooled G (247.18) plus C (40) |
| 10 | Prediction file holds 2–3 off-grid cells per preset (predicted bot_elo NOT any of the 5 measured grid values) — D-11/D-12 | ✓ VERIFIED | `bot-strength-confirmation-predictions.json`: 3 human rows (bot_elo 1083/1588/1741), 2 light rows (1781/1820), 2 deep rows (1298/1442) — none of these 7 values match the 15 measured grid bot_elo values (700/1100/1300/1500/1700/1900/2300/2600); `test_predicted_bot_elo_not_on_measured_grid` passes |
| 11 | Each prediction row carries `target_blitz_elo`, `blend`, `predicted_bot_elo`, `predicted_internal`, and a 95% CI band via the locked interpolation rule (D-13) | ✓ VERIFIED | All 7 rows inspected — every field present; mutation test: swapped `_pooled_ci` for a plain two-bound average → `test_plateau_ci_is_inverse_variance_pooled_not_lerp` fails (`assert 0.0 > 1e-06`), restored, passes — genuinely tested |
| 12 | Each row includes the exact operator harness + fit commands (self-documenting runbook) | ✓ VERIFIED | Every row has `harness_cmd` (calibration-harness.mjs invocation with the row's own predicted bot_elo/blend) and `fit_cmd` (calibration_anchor_fit.py); `test_row_has_runbook_commands` passes |
| 13 | Confirmation generator imports fit/invert functions from Plan 01 rather than re-implementing them, and does not modify that file | ✓ VERIFIED | `gen_bot_strength_confirmation_cells.py` imports `isotonic_fit`, `approx_blitz_points`, `load_internal_scale`, `compute_artifact`, `PRESETS`, `BLITZ_OFFSET_C`, `GRID_STEP`, `_Block`, `_INPUT` from `scripts.gen_bot_strength_curves`; `grep -n "def isotonic_fit"` on the confirmation script returns nothing; `git log` shows Plan 02 commits never touch `gen_bot_strength_curves.py` |
| 14 | Findings note documents measured-curve realities, the `beyond_ladder` mechanism resolution, the narrow overlap zone, and a HUMAN-UAT confirmation-run placeholder | ✓ VERIFIED | `.planning/notes/2026-07-21-bot-strength-lookup-findings.md` covers all four: Light non-monotone dip, Deep 2600 dip/plateau, Human ~1474 ceiling; resolves `beyond_ladder` as the `sf0≈1069.33` anchor-floor mechanism (not Maia-3's 1100–2000 band) with explicit "must not fix the wrong thing" language; documents the 1500–1800 overlap zone; ends with a clearly-marked "Confirmation run (HUMAN-UAT — to be filled)" section with the D-13 pass criterion and D-14 refit-on-failure protocol |

**Score:** 14/14 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/gen_bot_strength_curves.py` | PAVA fit + offset + inversion + JSON/TS emitter | ✓ VERIFIED | Exists, substantive (333 lines), wired into CI, `ruff`/`ty` clean |
| `reports/data/bot-strength-lookup.json` | components+derived shipping artifact | ✓ VERIFIED | Committed, matches a fresh render (`--check` exit 0) |
| `frontend/src/generated/botStrengthCurves.ts` | generated TS mirror | ✓ VERIFIED | Committed, type-checks (`tsc -b`), knip-clean, matches a fresh render |
| `tests/scripts/test_gen_bot_strength_curves.py` | unit tests | ✓ VERIFIED | 13 tests, all pass; D-07 invariant mutation-kill confirmed |
| `scripts/gen_bot_strength_confirmation_cells.py` | sibling off-grid prediction generator | ✓ VERIFIED | Imports Plan 01's functions, no re-implementation, `ruff`/`ty` clean |
| `reports/data/bot-strength-confirmation-predictions.json` | 2–3 off-grid cells/preset | ✓ VERIFIED | 7 rows (3/2/2), all off-grid, `--check` exit 0 |
| `tests/scripts/test_gen_bot_strength_confirmation_cells.py` | unit tests | ✓ VERIFIED | 5 tests, all pass; D-13 rule mutation-kill confirmed |
| `.planning/notes/2026-07-21-bot-strength-lookup-findings.md` | human-readable findings note | ✓ VERIFIED | Exists, covers all required sections including HUMAN-UAT placeholder |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `gen_bot_strength_curves.py` | `bot-curves-internal-scale.json` | `load_internal_scale()` fail-loud read | ✓ WIRED | Raises `ValueError` naming missing `cells`/`per_preset` — verified by reading the source and by `test_loader_fails_loud_on_missing_cells` |
| `frontend/knip.json` | `botStrengthCurves.ts` | `ignore` array entry | ✓ WIRED | Present alongside the `endgameZones.ts` precedent |
| `.github/workflows/ci.yml` | `gen_bot_strength_curves.py` + its 2 artifacts | "Bot strength curves drift check" step | ✓ WIRED | Step present, runs generator then `git diff --exit-code` on both paths; confirmed locally clean |
| `gen_bot_strength_confirmation_cells.py` | `gen_bot_strength_curves.py` | Python import (`from scripts.gen_bot_strength_curves import ...`) | ✓ WIRED | Import list confirmed; no re-implemented `isotonic_fit`/`invert_lookup`/`load_internal_scale` in the sibling file |

### Behavioral Spot-Checks (Mutation-Proofs)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| D-07 lowest-bot_elo-wins tie-break is genuinely tested | Reverted `x_lo`→`x_hi` in `approx_blitz_points`, ran `test_inversion_lowest_bot_elo_wins` | Failed (`1400 == 1200` assertion error) as predicted, then restored + passed | ✓ PASS |
| D-13 inverse-variance-pooled CI rule is genuinely tested | Reverted `_pooled_ci` to a plain two-bound average, ran `test_plateau_ci_is_inverse_variance_pooled_not_lerp` | Failed (`0.0 > 1e-06`) as predicted, then restored + passed | ✓ PASS |
| `--check` drift detection actually detects drift | Tampered `bot-strength-lookup.json` with `{"tampered": true}`, ran `--check` | Exit 1, named the stale path; restored, `--check` exit 0 again | ✓ PASS |
| Full test suite for both scripts | `uv run pytest tests/scripts/test_gen_bot_strength_curves.py tests/scripts/test_gen_bot_strength_confirmation_cells.py -q` | 18 passed | ✓ PASS |
| Frontend type-check + knip | `npx tsc -b && npm run knip` | Both clean, no output | ✓ PASS |
| Backend lint/type-check | `ruff check` + `ty check scripts/ tests/` | Clean on all 4 phase files (4 pre-existing, unrelated ty diagnostics in `scripts/seed_openings.py` confirmed out of scope) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SEED-104 | 181-01, 181-02 | Per-preset strength lookup curves: offset model, honest ranges, disclaimer, confirmation-cell protocol | ✓ SATISFIED | Both plans' `requirements-completed`/`coverage` sections trace to SEED-104; all method steps from the seed (fit → offset → invert → validate) are implemented; the seed's own "validate" step (§Method 4) explicitly calls for running confirmation cells in the harness — Plan 02 delivers the machine-readable prediction file per the accepted D-11 split-delivery pattern (mirrors Phase 180's precedent), with the actual game-play run scoped as operator HUMAN-UAT, not silently dropped |

No orphaned requirements — `.planning/REQUIREMENTS.md` has no formal IDs mapped to Phase 181 (confirmed via grep); the phase traces to SEED-104 by design, per the task's own framing.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any of the 4 Python files or 2 test files | — | None |

The one "placeholder" hit (findings note §5, "Confirmation run (HUMAN-UAT — to be filled)") is an intentional, clearly-labeled deferred section per the phase's own D-11 split-delivery design (documented in `181-CONTEXT.md`), not an unresolved debt marker — same pattern Phase 180 used and that was accepted.

### Code Review Findings (informational — not phase must-haves)

A code review (`181-REVIEW.md`) ran after both plans landed: 0 critical, 3 warnings, 2 info, no blockers. None of the 5 findings were subsequently fixed (confirmed by grep — no follow-up commit). All are scoped explicitly as "process/robustness gaps... none reproduce against the currently committed data":

- **WR-01** (most notable): `reports/data/bot-strength-confirmation-predictions.json` has no CI drift-check, unlike its two Plan 01 siblings. This was never a Plan 02 must-have (only Plan 01's must-haves required a CI drift step), so it is not a gap against this phase's declared scope — but it is a real latent risk: if `gen_bot_strength_curves.py`'s shared fit functions change later without regenerating the predictions file, CI would stay green while the operator confirmation run works from stale predicted `bot_elo`/CI values.
- **WR-02**/**WR-03**: unguarded zero-width-range edge cases in `select_confirmation_targets`/`invert_lookup` that would surface as unhelpful generic crashes rather than named fail-loud errors, dormant against current data.
- **IN-01**/**IN-02**: minor JSON type inconsistency (`bot_elo` float vs int) and a test-file import-placement style nit.

None of these affect the phase's must-haves or the shipped artifact's current correctness — they are recorded here for visibility, not as blocking gaps.

### Human Verification Required

None required to pass this phase. One item is worth flagging to the human as **forward-looking action, not a phase-181 gap**:

1. **Overnight confirmation game-play run (D-11 split delivery)**
   **What:** Run each of the 7 rows' `harness_cmd` + `fit_cmd` from `reports/data/bot-strength-confirmation-predictions.json`, compare each measured `rating_vs_maia` against its recorded `[ci95_lo, ci95_hi]`, and fill in the findings note's "Confirmation run" placeholder with pass/fail.
   **Why deferred, not a gap:** This is the identical split-delivery pattern Phase 180 used (D-01 precedent), explicitly locked in `181-CONTEXT.md` D-11, and the phase's own `must_haves` only require the machine-readable prediction file + runbook (verified above) — not the game-play run itself. Both SUMMARY.md files and the findings note are explicit and consistent that this is operator-run HUMAN-UAT outside session scope, not a silently-skipped step.
   **Recommended follow-up:** consider adding the WR-01 CI drift-check for the confirmation-predictions file in a small follow-up task, since a stale prediction file silently defeats its own purpose.

### Gaps Summary

None. All 14 observable truths across both plans are verified against the actual codebase (not SUMMARY.md claims): both generators run, emit correct, deterministic, drift-checked artifacts; the D-01 offset math, D-07 lowest-wins inversion, D-08 all-cells-retained guard, D-10 inward rounding, and D-13 interpolated-CI rule are all mutation-tested (not just symbol-present); the shipped Deep ceiling (1800 approx-blitz) is honestly below the seed's hoped ~2600, matching the phase goal's own stated finding; the findings note resolves the `beyond_ladder` mechanism correctly; and no consumer wiring was expected or attempted (explicitly out of scope per D-04/`181-CONTEXT.md`).

---

_Verified: 2026-07-21_
_Verifier: Claude (gsd-verifier)_
