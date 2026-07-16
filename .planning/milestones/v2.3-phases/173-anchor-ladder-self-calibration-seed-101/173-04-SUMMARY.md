---
phase: 173-anchor-ladder-self-calibration-seed-101
plan: 04
subsystem: infra
tags: [calibration, bradley-terry, elo, stockfish, maia, self-play, research-tooling]

# Dependency graph
requires:
  - phase: 173-02
    provides: anchor-vs-anchor orchestrator (two-pass probe/measure scheduler, connectivity guard, two-tier TSV, --resume)
  - phase: 173-03
    provides: calibration_anchor_fit.py (stdlib Bradley-Terry/Zermelo fit + bootstrap CIs + residuals + D-13 caveat)
provides:
  - Real anchor-vs-anchor sweep result (456 games, seed 1) committed as raw + per-pair TSVs
  - Fitted internal rating scale for all 10 anchors (maia700-2300, sf0/3/5/8/10), Node-importable
  - Explicit Maia-3 ladder compression verdict (~2.8x overall, non-uniform, worst at the top)
  - Closure of 168-RESEARCH.md Open Question 2 (SF Skill Level -> Elo folklore) for relative work
affects: [SEED-102, 168-RESEARCH]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Band-relaxing connectivity rescue (rescueConnectivity/bandDistance) as the D-04 re-target fallback when the nearest weaker anchor doesn't exist"

key-files:
  created:
    - scripts/lib/calibration-internal-scale.mjs
    - reports/data/anchor-ladder-internal-scale.json
    - reports/data/anchor-ladder-2026-07-15T20-28-27-398Z.tsv
    - reports/data/anchor-ladder-2026-07-15T20-28-27-398Z-pairs.tsv
    - .planning/notes/2026-07-15-anchor-ladder-self-calibration-findings.md
  modified:
    - scripts/lib/calibration-anchor-schedule.mjs (committed as part of checkpoint recovery, prior to this continuation)

key-decisions:
  - "Band-relaxing connectivity rescue (commit a2f96e81, user-approved during checkpoint recovery) fixes the D-04 dead-end when a pair's only informative link has no weaker same-family anchor to re-target to"
  - "Compression verdict computed both over the full ladder (700-2300, ~2.8x) and over the Maia-1-comparable sub-range (1100-1900, ~3.2x) to directly cross-check against the independently-measured Maia-1 real-lichess figure (~3.3x)"

patterns-established:
  - "Findings note numbered-findings structure (mirroring 2026-07-13-bot-calibration-findings.md) reused for a second SEED in the same phase family"

requirements-completed: [D-11, D-12, D-13]

coverage:
  - id: D1
    description: "Real anchor-vs-anchor sweep executed and committed (raw + per-pair TSVs, 456 games, seed 1)"
    requirement: "D-11"
    verification:
      - kind: manual_procedural
        ref: "Task 1 checkpoint:human-verify — user ran the sweep and confirmed the completed ledger filename"
        status: pass
    human_judgment: true
    rationale: "Multi-hour real sweep on Adrian's own machine — inherently a human-run/human-confirmed checkpoint, not automatable."
  - id: D2
    description: "Internal rating scale fit and emitted as calibration-internal-scale.mjs + JSON sibling, maia1500 pinned, all 10 anchors numeric, D-13 caveat carried"
    requirement: "D-12"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs -e \"import('./scripts/lib/calibration-internal-scale.mjs')...\" -> SCALE-OK"
        status: pass
    human_judgment: false
  - id: D3
    description: "Findings note states the Maia-3 compression verdict, per-anchor ratings + CIs, cross-family residuals, and closes 168-RESEARCH.md Open Question 2"
    requirement: "D-12"
    verification:
      - kind: other
        ref: "grep -qi 'compress'/'NOT human ELO'/'Open Question 2' .planning/notes/2026-07-15-anchor-ladder-self-calibration-findings.md -> NOTE-OK"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-16
status: complete
---

# Phase 173 Plan 04: Anchor Ladder Self-Calibration — Fit + Findings Summary

**Fitted the real 456-game anchor-vs-anchor sweep into an internal rating scale (Bradley-Terry/Zermelo, maia1500 pinned to 1500) and confirmed the Maia-3 argmax ladder is compressed ~2.8x overall — non-uniformly, worst at the top — closing 168-RESEARCH Open Question 2 for relative work.**

## Performance

- **Duration:** 25 min (this continuation session; Task 1's multi-hour sweep ran separately and is not included)
- **Started:** 2026-07-16T05:30:00Z (approx, continuation agent spawn)
- **Completed:** 2026-07-16T05:55:00Z (approx)
- **Tasks:** 3 (Task 1 completed prior to this continuation via checkpoint:human-verify; Tasks 2-3 executed this session)
- **Files modified:** 5 (2 new artifacts + 2 TSVs committed + 1 findings note)

## Accomplishments

- Ran `scripts/calibration_anchor_fit.py` against the completed raw ledger (`reports/data/anchor-ladder-2026-07-15T20-28-27-398Z.tsv`, 456 games), producing `scripts/lib/calibration-internal-scale.mjs` (`INTERNAL_RATING`, all 10 anchors, `maia1500 === 1500`) and `reports/data/anchor-ladder-internal-scale.json` (ratings + bootstrap CIs + per-pair residuals), both D-13-caveated
- Committed the raw ledger + per-pair aggregate TSVs alongside the fit artifacts (all four D-12 machine-readable artifacts now in git)
- Wrote `.planning/notes/2026-07-15-anchor-ladder-self-calibration-findings.md`: explicit compression verdict (Maia-3 ladder compresses ~2.8x full-range, ~3.2x on the Maia-1-comparable 1100-1900 sub-range — closely matching Maia-1's independently-measured ~3.3x), per-anchor ratings + CIs, SF Skill-Level spacing, cross-family residuals (style-confounding signal), and closes 168-RESEARCH.md Open Question 2

## Task Commits

Each task was committed atomically:

1. **Task 1: Execute the real anchor-vs-anchor sweep (checkpoint:human-verify)** - completed in a prior session; the mid-run connectivity fix landed as `a2f96e81` (`fix(173-04): band-relaxing connectivity rescue for D-04 re-target dead-end`)
2. **Task 2: Fit the internal scale + emit the two machine-readable artifacts** - `c6126878` (feat)
3. **Task 3: Write the findings note — spacing + compression verdict, close 168 OQ2** - `1c39d610` (docs)

**Plan metadata:** pending (this SUMMARY's own commit)

## Files Created/Modified

- `scripts/lib/calibration-internal-scale.mjs` - `export const INTERNAL_RATING` (all 10 anchors, `maia1500 === 1500`), D-13 docstring
- `reports/data/anchor-ladder-internal-scale.json` - ratings + bootstrap CIs + per-pair residuals (cross-family flagged), D-13-labeled
- `reports/data/anchor-ladder-2026-07-15T20-28-27-398Z.tsv` - raw per-game ledger (456 games, seed 1)
- `reports/data/anchor-ladder-2026-07-15T20-28-27-398Z-pairs.tsv` - per-pair aggregate (16 measured pairs)
- `.planning/notes/2026-07-15-anchor-ladder-self-calibration-findings.md` - findings note: compression verdict, ratings, residuals, OQ2 closure

## Decisions Made

- Used the exact ledger filename reported at the checkpoint (`anchor-ladder-2026-07-15T20-28-27-398Z.tsv`) as `--input` to the fit, per the checkpoint outcome's explicit instruction
- Computed the compression verdict two ways (full ladder + the Maia-1-comparable 1100-1900 sub-range) to make the cross-check against the independently-measured Maia-1 figure (2026-07-13 note) explicit and load-bearing in the findings note, not just implicit in the raw numbers

## Deviations from Plan

### Auto-fixed Issues (recorded here per checkpoint outcome; occurred before this continuation)

**1. [Rule 4 - Architectural, user-approved] Band-relaxing connectivity rescue for the D-04 re-target dead-end**
- **Found during:** Task 1 (the real sweep), after the probe pass completed
- **Issue:** The D-04 connectivity guard failed loud: `{maia700, sf0}` had informative links only to each other, and the scheduler's re-target logic had no weaker Maia rung to fall back to, so the run could not proceed to the measure pass.
- **Fix:** Added `rescueConnectivity`/`bandDistance` to `scripts/lib/calibration-anchor-schedule.mjs`, relaxing the re-target search by nominal-rating band distance instead of requiring a strictly-weaker same-family anchor; wired into `scripts/calibration-anchor-ladder.mjs`; extended the check fixture. User-approved before implementation (this was an architectural change to the scheduler, Rule 4 in the deviation-rules taxonomy, not auto-applied).
- **Files modified:** `scripts/lib/calibration-anchor-schedule.mjs`, `scripts/calibration-anchor-ladder.mjs`, its check fixture
- **Verification:** The resumed run rescued pair `maia700 vs sf5` (probe score 0.1875) and completed the measure pass with the connectivity guard satisfied (`>= 2` cross-family links).
- **Committed in:** `a2f96e81` (prior session, before this continuation's Task 2/3)

---

**Total deviations:** 1 auto-fixed (1 architectural/user-approved, Rule 4), landed before this continuation began.
**Impact on plan:** Necessary to complete the real sweep at all — without the rescue, the D-04 guard would have blocked the run indefinitely at the ladder's weakest, least-connected pair. No scope creep — the fix is scoped entirely to the scheduler's re-target logic.

## Issues Encountered

None this session. The fit ran cleanly on the first attempt (`check_connectivity` passed, no `RuntimeError`), and both verification gates (Task 2's node import assertion, Task 3's grep gate) passed on first try.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SEED-102 is unblocked: it can now pick per-cell anchors by internal rating (`scripts/lib/calibration-internal-scale.mjs`'s `INTERNAL_RATING`) instead of nominal Elo labels, directly fixing the 2026-07-12 run's `ANCHOR_ELO_WINDOW` clamping (the compressed axis made a 400-point window too narrow near the ladder's top).
- 168-RESEARCH.md Open Question 2 is closed for relative (internal-scale) work; SEED-103 still owns the absolute human-ELO correction — this plan produced internal spacing only (D-13), never a human-ELO claim.
- No blockers. Phase 173 (all 4 plans) is now fully executed.

---
*Phase: 173-anchor-ladder-self-calibration-seed-101*
*Completed: 2026-07-16*

## Self-Check: PASSED

All created files verified present on disk (calibration-internal-scale.mjs, anchor-ladder-internal-scale.json, both TSVs, findings note, this SUMMARY). All four referenced commit hashes (a2f96e81, c6126878, 1c39d610, 9c36f761) verified present in git log.
