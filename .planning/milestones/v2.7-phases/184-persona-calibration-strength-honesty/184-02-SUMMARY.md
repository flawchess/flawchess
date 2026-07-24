---
phase: 184-persona-calibration-strength-honesty
plan: 02
subsystem: infra
tags: [python, stdlib, calibration, bradley-terry, pava, codegen, ci, bash]

requires:
  - phase: 184-01
    provides: The harness style seam (`playGame`/`selectBotMoveOnce` optional `style`) and the PersonaId-keyed `calibration-persona-cell-schedule.mjs` (`ALL_PERSONA_CELLS`, `retargetedBotEloFor`, `personaCellKey`)
  - phase: 181-strength-lookup-curves (v2.6)
    provides: "`fit_bot_cell_rating`/`fit_all_bot_cells` (calibration_anchor_fit.py) and `isotonic_fit`/codegen `--check` pattern (gen_bot_strength_curves.py), reused verbatim"
provides:
  - scripts/calibration_persona_fit.py — PersonaId-keyed twice-per-cell (vs-Maia/vs-SF) rating fit + approx_blitz conversion, with --bootstrap and --self-test modes
  - scripts/gen_persona_calibration.py — per-style-column PAVA pooling (sorted by rung) + D-07 post-pool 1800 ceiling + D-03 round-50, emitting personaCalibration.ts with a --check drift gate
  - A minimal, backward-compatible style-override seam on scripts/calibration-harness.mjs (CALIBRATION_HARNESS_STYLE env var) so bin/preset-supervisor.sh can drive a real styled persona sweep unmodified
  - bin/run_persona_calibration_sweep.sh — the operator runbook (preflight, 24 supervised per-persona launches in batches, combine, fit, regenerate)
  - A committed, bootstrap-derived (retargeting-only) frontend/src/generated/personaCalibration.ts unblocking Plan 03/CI before the real overnight sweep runs
affects: [184-03-registry-and-bots-page, 184-04-persona-calibration-sweep-execution]

tech-stack:
  added: []
  patterns:
    - "Env-var-driven optional CLI override (CALIBRATION_HARNESS_STYLE) threaded through an existing multi-layer call chain, preserving byte-identical behavior when unset — extends Plan 01's STYLE-05 absent-style invariant to the CLI grid-loop path"
    - "Bootstrap/placeholder generated-artifact mode: a Node subprocess dump of the JS source of truth (ALL_PERSONA_CELLS) feeds the Python fit script, so no persona identity/blend mapping is ever duplicated or hardcoded in Python"
    - "PAVA pooling sorted by RUNG, not bot_elo — the isotonic_fit function is reused verbatim from gen_bot_strength_curves.py, but the caller sorts on a different axis because multiple personas can collide on bot_elo post-retargeting"
    - "24-persona overnight sweep as 24 independent single-cell harness invocations (one per --out-dir) through an UNCHANGED generic supervisor script, rather than a new persona-keyed CLI grid mode inside the harness"

key-files:
  created:
    - scripts/calibration_persona_fit.py
    - scripts/gen_persona_calibration.py
    - bin/run_persona_calibration_sweep.sh
  modified:
    - scripts/calibration-harness.mjs
    - .github/workflows/ci.yml
    - frontend/knip.json
    - reports/data/persona-calibration.json (generated)
    - reports/data/persona-calibration-cells.tsv (generated placeholder)
    - frontend/src/generated/personaCalibration.ts (generated)

key-decisions:
  - "persona-calibration.json wraps the 24 PersonaId entries under a `personas` key (plus a top-level `_caveat`) rather than a bare Record — keeps the internal-scale caveat alongside the data without polluting the exhaustive persona map"
  - "Each persona-calibration.json entry carries no `style` field (matches the plan's literal field list); style is derived by both Python scripts from the PersonaId key itself (`'attacker-1200'.split('-')[0]`) — personaId is already the single source of truth for style per Plan 01's schedule module"
  - "Deviation (Rule 2 — missing critical functionality): added a CALIBRATION_HARNESS_STYLE env-var seam to calibration-harness.mjs, threaded through runCell/locateCellPass/measureCellPass into the existing (Plan 01) playCellAnchorGames `style` param. Without this, the runbook could invoke bin/preset-supervisor.sh but no BotStyleParams bundle would ever reach selectBotMove — defeating CAL-04 entirely. bin/preset-supervisor.sh itself stays byte-for-byte unmodified (its generic `<name> <blend> <elo-csv>` interface is reused as-is); the env var is inherited by its nohup'd child. Verified: the pre-184 unstyled grid path still runs correctly after this change (real-engine smoke run, 1 locate-anchor sweep) and resolveStyleFromEnv() throws fail-loud on an unrecognized style name rather than silently defaulting"
  - "The persona overnight sweep is designed as 24 INDEPENDENT single-cell harness invocations (one --out-dir per persona), not a new persona-keyed grid mode inside main() — this sidesteps Pitfall 1 (botElo/blend collisions) entirely, since each persona's ledger/store is its own process, with no shared accumulator to collide in"
  - "Combine step (bash+awk) extracts the fit script's 10 required columns by COLUMN NAME (not position) from each persona's own harness-emitted -cells.tsv, so a future harness schema reorder can't silently corrupt the combined aggregate"
  - "Added frontend/src/generated/personaCalibration.ts to knip.json's ignore list (Rule 3 — blocking issue), mirroring the existing botStrengthCurves.ts/endgameZones.ts precedent for a generated file shipped ahead of its consumer (Plan 03)"
  - "requirements-completed left empty: CAL-04/CAL-05 are shared across Plans 02/03/04 (frontmatter). This plan delivers the fit+codegen+runbook pipeline and a bootstrap-derived committed artifact, not a real measurement (labels are provisional, approx_blitz=rung) or the UI-facing honesty surfaces — marking either requirement complete here would be a partial-delivery false-positive"

patterns-established:
  - "Twice-per-cell fit (vs-Maia-only, vs-SF-only), never merging families before fitting — the SAME discipline as fit_all_bot_cells, now applied at persona granularity"
  - "Post-pool ceiling clamp: cap AFTER PAVA pooling (never before), verified via a synthetic monotonicity-violation fixture that a pre-clamp order would produce a different (wrong) result"

requirements-completed: []

coverage:
  - id: D1
    description: "calibration_persona_fit.py fits each persona TWICE (vs-Maia-family, vs-SF-family) reusing fit_bot_cell_rating unmodified, converts via the pooled g_preset_combined + BLITZ_OFFSET_C read at run time (no hardcoded literals), and fails loud on <24 personas, a header/schema mismatch, or an unrecognized blend"
    requirement: "CAL-04"
    verification:
      - kind: unit
        ref: "uv run python scripts/calibration_persona_fit.py --self-test (fixture fit assertion + 24-count fail-loud guard + unknown-blend fail-loud guard) — exit 0"
        status: pass
      - kind: other
        ref: "uv run python scripts/calibration_persona_fit.py --bootstrap — writes a 24-entry persona-calibration.json + header-only persona-calibration-cells.tsv from the real ALL_PERSONA_CELLS registry via a Node subprocess dump"
        status: pass
    human_judgment: false
  - id: D2
    description: "gen_persona_calibration.py PAVA-pools per style column (sorted by rung), applies the D-07 1800 ceiling AFTER pooling, rounds to nearest 50 (D-03), and emits a complete Record<PersonaId, {botElo,label}> with a working --check drift gate"
    requirement: "CAL-05"
    verification:
      - kind: unit
        ref: "uv run python scripts/gen_persona_calibration.py && uv run python scripts/gen_persona_calibration.py --check && git diff --exit-code frontend/src/generated/personaCalibration.ts reports/data/persona-calibration.json — exit 0, no drift"
        status: pass
      - kind: other
        ref: "Manual synthetic-fixture test in-session: a deliberately non-monotone (rung, approx_blitz) series pools to a shared ~1800 label across the violating rungs with no inversion, confirming clamp-after-pool ordering"
        status: pass
      - kind: other
        ref: "Manual drift spot-check: hand-appended a comment to the committed personaCalibration.ts, confirmed --check exits 1 with a DRIFT: message, then reverted and confirmed exit 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "bin/run_persona_calibration_sweep.sh is a syntactically valid, executable operator runbook that launches every persona through the unmodified bin/preset-supervisor.sh (never the bare harness driver), and .github/workflows/ci.yml gains a valid Persona calibration drift check step"
    requirement: "CAL-04"
    verification:
      - kind: unit
        ref: "bash -n bin/run_persona_calibration_sweep.sh && python3 -c \"import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))\" — both exit 0"
        status: pass
      - kind: other
        ref: "Manual round-trip test: a synthetic 24-persona x 4-anchor TSV (matching the harness's real column schema) fed through calibration_persona_fit.py --input then gen_persona_calibration.py, producing 24 valid entries end to end"
        status: pass
    human_judgment: false
  - id: D4
    description: "The full frontend build/lint/knip/test gate stays green with the new generated file and the knip.json ignore addition"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b --force (clean), npm run knip (clean), npm run lint (only pre-existing unrelated coverage/ warnings), npm test -- --run src/lib/personas src/components/bots (126 passed)"
        status: pass
    human_judgment: false

duration: ~45min
completed: 2026-07-22
status: complete
---

# Phase 184 Plan 02: Persona Calibration Sweep Pipeline Summary

**Built the Python fit + PAVA-pooling codegen pipeline that turns persona-cell sweep data into calibrated per-persona ELO labels, an operator runbook + CI drift gate for the eventual overnight sweep, and a committed bootstrap-derived `personaCalibration.ts` (labels currently equal rung) so Plan 03 and CI are unblocked ahead of the real measurement.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-22
- **Tasks:** 3
- **Files modified:** 8 (3 created, 5 modified, plus the knip.json follow-up fix)

## Accomplishments
- `scripts/calibration_persona_fit.py`: fits each of the 24 personas TWICE (vs-Maia-family, vs-SF-family) via `fit_bot_cell_rating` reused unmodified from `calibration_anchor_fit.py`, converts to `approx_blitz` via `g_preset_combined` + `BLITZ_OFFSET_C` read at run time from their canonical sources (never hardcoded), and fails loud on a <24-persona input, a schema mismatch, or an unrecognized blend. `--bootstrap` writes a real-registry-derived, retargeting-only placeholder (approx_blitz = rung); `--self-test` runs a fixture assertion.
- `scripts/gen_persona_calibration.py`: groups by style column (derived from the PersonaId itself, never a separate field), runs `gen_bot_strength_curves.py`'s `isotonic_fit` PAVA verbatim per style (sorted by rung, not bot_elo — personas can collide on the latter post-retargeting), applies the D-07 1800 ceiling strictly AFTER pooling, then D-03 rounds to nearest 50. Emits `frontend/src/generated/personaCalibration.ts` (`Record<PersonaId, {botElo, label}>`) with a `--check` drift gate mirroring the Bot-strength-curves precedent exactly.
- `bin/run_persona_calibration_sweep.sh`: the operator runbook — preflights core footprint, reads the 24 `ALL_PERSONA_CELLS` tuples straight from the JS source of truth, launches each persona through the UNMODIFIED `bin/preset-supervisor.sh` in batches of `--parallel`, combines the 24 per-persona `-cells.tsv` aggregates into a `persona_id`-keyed `persona-calibration-cells.tsv`, then invokes the fit + codegen scripts.
- `.github/workflows/ci.yml`: new "Persona calibration drift check" step immediately after the Bot strength curves step.
- Deviation: added a minimal `CALIBRATION_HARNESS_STYLE` env-var seam to `scripts/calibration-harness.mjs` so the runbook's per-persona invocations actually carry a real style bundle into `selectBotMove` — see Decisions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Persona rating fit script (twice-per-cell + retargeting + bootstrap)** - `47f0bad3` (feat)
2. **Task 2: Codegen script (PAVA per style column, 1800 clamp, round-50) + bootstrap generated file** - `8e978073` (feat)
3. **Task 3: Operator runbook script + CI drift-check step** - `9d795b80` (feat, includes the calibration-harness.mjs style-seam deviation)
4. **Follow-up fix: knip-ignore the new generated file** - `382e6e89` (fix)

## Files Created/Modified
- `scripts/calibration_persona_fit.py` - PersonaId-keyed twice-per-family fit, `--bootstrap`/`--self-test` modes
- `scripts/gen_persona_calibration.py` - per-style PAVA pooling + 1800 clamp + round-50 codegen, `--check` drift mode
- `bin/run_persona_calibration_sweep.sh` - operator runbook (preflight, batched supervised launches, combine, fit, regenerate)
- `scripts/calibration-harness.mjs` - added `resolveStyleFromEnv()`/`CALIBRATION_HARNESS_STYLE_ENV`, threaded `style` through `runCell`/`locateCellPass`/`measureCellPass`
- `.github/workflows/ci.yml` - new Persona calibration drift check step
- `frontend/knip.json` - ignore the new generated file (ahead-of-consumer precedent)
- `reports/data/persona-calibration.json`, `reports/data/persona-calibration-cells.tsv`, `frontend/src/generated/personaCalibration.ts` - bootstrap-derived generated artifacts

## Decisions Made
See `key-decisions` in frontmatter for the full list, notably:
- The persona overnight sweep runs as 24 independent single-cell harness invocations (one `--out-dir` per persona) through the unmodified `preset-supervisor.sh`, rather than a new persona-keyed grid mode inside the harness — sidesteps the botElo/blend collision problem structurally.
- `persona-calibration.json` wraps entries under a `personas` key; style is derived from the PersonaId string, never duplicated as a separate field.
- `requirements-completed` left empty — CAL-04/CAL-05 are jointly delivered across Plans 02/03/04; this plan ships the pipeline and a provisional bootstrap artifact, not the real measurement or UI honesty surfaces.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added a style-override seam to calibration-harness.mjs**
- **Found during:** Task 3 (writing the operator runbook)
- **Issue:** No plan in this phase (01, 02, 03, or 04) modifies `calibration-harness.mjs`'s CLI/grid-loop to actually thread a `BotStyleParams` bundle into a real sweep run — Plan 01 only added the `style` parameter to `playGame`/`selectBotMoveOnce` and `playCellAnchorGames` (forwarded but always `undefined`). Without a way to set `style` on an actual CLI invocation, `bin/run_persona_calibration_sweep.sh` could launch `bin/preset-supervisor.sh` all day and never measure a single styled game — CAL-04's entire point (a per-persona style-induced offset) would be silently unmeasurable.
- **Fix:** Added `resolveStyleFromEnv()` reading an optional `CALIBRATION_HARNESS_STYLE` env var (fail-loud on an unrecognized name, `undefined` when unset), threaded as `style` through `runCell` → `locateCellPass`/`measureCellPass` → the existing `playCellAnchorGames` parameter. `bin/preset-supervisor.sh` itself is untouched (its generic `<name> <blend> <elo-csv>` interface is reused as-is); the runbook exports the env var in a per-persona subshell before invoking it.
- **Files modified:** scripts/calibration-harness.mjs
- **Verification:** `node --check` (syntax), a standalone `resolveStyleFromEnv` unit check (unset → undefined, valid name → resolved bundle, invalid name → throws), and a real-engine smoke run of the existing unstyled 1-elo/1-blend/2-anchor grid path (no style env var set) confirming it still completes correctly after the change.
- **Committed in:** `9d795b80` (Task 3 commit)

**2. [Rule 3 - Blocking] knip-ignore the new generated file**
- **Found during:** post-Task-3 verification (`npm run knip`)
- **Issue:** `frontend/src/generated/personaCalibration.ts` is not consumed anywhere yet (Plan 03 wires it into `personaRegistry.ts`), so knip's CI-blocking dead-file check flagged it as unused — a real gate failure, not a false concern to defer.
- **Fix:** Added it to `knip.json`'s `ignore` list, mirroring the existing `botStrengthCurves.ts`/`endgameZones.ts` precedent for exactly this ahead-of-consumer situation.
- **Files modified:** frontend/knip.json
- **Verification:** `npm run knip` clean; `npm run lint` shows only pre-existing unrelated `coverage/` warnings.
- **Committed in:** `382e6e89`

---

**Total deviations:** 2 auto-fixed (1 missing critical functionality, 1 blocking CI gate)
**Impact on plan:** Both were necessary for the shipped pipeline to be genuinely functional/green, not scope creep — no new features beyond what CAL-04's runbook requires.

## Issues Encountered
None beyond the two deviations above.

## User Setup Required
None - no external service configuration required. (The actual overnight sweep execution is Plan 04's HUMAN-UAT-gated operator step.)

## Next Phase Readiness
- Plan 03 can now wire `personaCalibration.ts` into `personaRegistry.ts`/`PersonaCard.tsx`/`PersonaDetailSurface.tsx` — the generated file's shape (`Record<PersonaId, {botElo, label}>`) is final; only its VALUES will change once Plan 04 runs the real sweep.
- Plan 04 can launch `bin/run_persona_calibration_sweep.sh` directly — the runbook, the style seam, and the fit/codegen scripts are all fixture-verified end to end (synthetic 24-persona round-trip test) and ready for real engine data.
- No blockers. `--check` is green on the committed bootstrap artifacts; CI now gates persona-calibration drift the same way it gates bot-strength-curves drift.

---
*Phase: 184-persona-calibration-strength-honesty*
*Completed: 2026-07-22*

## Self-Check: PASSED
