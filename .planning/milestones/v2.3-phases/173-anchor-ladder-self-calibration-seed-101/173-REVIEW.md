---
phase: 173-anchor-ladder-self-calibration-seed-101
reviewed: 2026-07-16T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - scripts/calibration_anchor_fit.py
  - scripts/calibration-anchor-ladder.mjs
  - scripts/calibration-harness.mjs
  - scripts/lib/calibration-anchor-schedule.check.mjs
  - scripts/lib/calibration-anchor-schedule.mjs
  - scripts/lib/calibration-anchors.check.mjs
  - scripts/lib/calibration-anchors.mjs
  - scripts/lib/calibration-game-loop.check.mjs
  - scripts/lib/calibration-game-loop.mjs
  - scripts/lib/calibration-internal-scale.mjs
  - tests/scripts/test_calibration_anchor_fit.py
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 173: Code Review Report

**Reviewed:** 2026-07-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the anchor-ladder self-calibration harness: the Node probe/measure orchestrator
(`calibration-anchor-ladder.mjs` + `scripts/lib/calibration-anchor-schedule.mjs`), the extracted
mover-agnostic game loop (`calibration-game-loop.mjs`), the anchor rating tables
(`calibration-anchors.mjs`), and the stdlib-only Python Bradley-Terry fit
(`calibration_anchor_fit.py`) with its pytest suite. The extraction of `playTwoMoverGame` out of
`calibration-harness.mjs` is a clean, behavior-preserving refactor (git history shows it proven
byte-identical against the pre-existing determinism check). The Node-side D-04 connectivity guard
(`calibration-anchor-schedule.mjs::checkConnectivity`), which always receives de-duplicated
canonical pairs, is correct.

The one BLOCKER is in the Python fit script's own "belt-and-suspenders" re-check of the same D-04
invariant: it is fed un-canonicalized, directional pairs straight from the raw per-game TSV, which
silently defeats the ">= 2 cross-family links" guard — the exact non-identifiability failure mode
the check exists to prevent can pass undetected. Three further WARNINGs cover a magic-number
duplication of the informative-band bounds, a materially weaker `--resume` validation path in the
anchor-ladder script versus its sibling `calibration-harness.mjs`, and a missing parent-directory
creation before writing the fit script's output artifacts.

## Critical Issues

### CR-01: D-04 defensive connectivity re-check can be satisfied by a single real cross-family pairing

**File:** `scripts/calibration_anchor_fit.py:433-438`

**Issue:** `main()` builds the `pairs` argument for the belt-and-suspenders `check_connectivity`
call directly from the raw per-game rows, without canonicalizing the unordered anchor pair:

```python
anchors = sorted({g["anchor_white"] for g in games} | {g["anchor_black"] for g in games})
pairs = {(g["anchor_white"], g["anchor_black"]) for g in games}
...
check_connectivity(pairs, anchors)
```

`check_connectivity` (lines 215-251) counts cross-family edges as
`len([(a, b) for a, b in pairs if _is_maia(a) != _is_maia(b)])` and requires `>= 2`. Because a
`pairs` element is `(anchor_white, anchor_black)` taken verbatim from each game row, and colors
alternate every game (`aIsWhite = idx % 2 === 0` in `calibration-anchor-ladder.mjs`), any single
real cross-family pairing measured over its full `--games-per-measure` budget (default 24) will
contribute BOTH `("maia1500", "sf5")` and `("sf5", "maia1500")` to the set — two entries for one
actual bridge. The check then reports 2 cross-family "links" and passes, even though the fit is
statistically non-identifiable with only one true bridge (the exact scenario the docstring says
this guard exists to catch: "a disconnected or under-cross-linked graph makes the fit numerically
'converge' to a combined table whose maia/SF offset is arbitrary, not measured"). The Node-side
scheduler's own `checkConnectivity` (`calibration-anchor-schedule.mjs`) is NOT affected — it is
always called with de-duplicated canonical pairs from `kept`/`rescue.kept` — but this Python
re-check is the ONLY guard exercised when the script is run standalone against a hand-merged or
externally-produced TSV, which is exactly the case this defensive check is meant to cover.

`tests/scripts/test_calibration_anchor_fit.py::test_connectivity` does not catch this: it builds
`pairs` as hand-written single-direction Python sets (e.g.
`{("maia1500", "maia1900"), ("sf5", "sf8"), ("maia1500", "sf5")}`), which never exercises the
duplicate-both-directions shape that real per-game data produces.

**Fix:** Canonicalize before counting/passing to `check_connectivity`, e.g.:
```python
pairs = {tuple(sorted((g["anchor_white"], g["anchor_black"]))) for g in games}
```
and add a regression test to `test_connectivity` using a set built the same way `main()` builds it
(both `(a, b)` and `(b, a)` present for a single real pairing) to prove the guard still requires
two genuinely distinct anchor pairings.

## Warnings

### WR-01: Informative-band bounds hardcoded instead of reused, risking silent drift

**File:** `scripts/calibration-anchor-ladder.mjs:502`

**Issue:** `pairsAggregateRows` recomputes the D-01 informative-band membership with magic
literals:
```js
informative: scoreA >= 0.2 && scoreA <= 0.8,
```
`scripts/lib/calibration-anchor-schedule.mjs` already exports `INFORMATIVE_BAND_LOW`/
`INFORMATIVE_BAND_HIGH` and the `scoreInInformativeBand(score)` helper that is the single source
of truth for this gate elsewhere in the same file (`selectMeasurePairs`). `calibration-anchor-ladder.mjs`
already imports several other symbols from that module, so nothing prevents reuse here. If the band
is ever tuned, this diagnostic column in the `-pairs.tsv` artifact will silently disagree with the
actual probe→measure gating decision. Violates the project's "no magic numbers" rule (CLAUDE.md
Coding Guidelines).

**Fix:**
```js
import { /* ...existing... */ scoreInInformativeBand } from './lib/calibration-anchor-schedule.mjs';
// ...
informative: scoreInInformativeBand(scoreA),
```

### WR-02: `--resume` validation in the anchor-ladder script is far weaker than its sibling harness

**File:** `scripts/calibration-anchor-ladder.mjs:573-579` (`validateResumeSeed`), called at line 632

**Issue:** The only resume-consistency check performed is on `--seed`:
```js
function validateResumeSeed(rows, seed) {
  for (const row of rows) {
    if (row.seed !== seed) {
      throw new Error(`--resume: prior seed=${row.seed} differs from current --seed=${seed} — refusing to resume a different experiment`);
    }
  }
}
```
`calibration-harness.mjs::loadPriorSweep` (same phase family) explicitly validates
`--games-per-cell`, `--seed`, the D-11 search budget, AND grid-membership before allowing a
resume, with the stated rationale "a changed experiment is a footgun, not a feature." This script
has no equivalent check against `--games-per-probe`, `--games-per-measure`, `--anchors`, or
`--stockfish-procs`. Concretely: resuming a prior ledger with a smaller `--games-per-probe`/
`--games-per-measure` than the original run silently truncates the effective per-pair budget —
`probePass`/`measurePass` just see `remaining <= 0` and skip, with no error — producing a
statistically different (and unflagged) experiment from what the operator intended. Likewise,
resuming with a changed `--anchors` list is never validated against the prior ledger's own anchor
set.

**Fix:** Add the equivalent WR-02-style guard used in `calibration-harness.mjs`: after
`readPriorLedgerRows`, assert the prior ledger's implied `games-per-probe`/`games-per-measure`
(derivable from the max `probeGames`/`measureGames` per pair, or by requiring `--games-per-probe`/
`--games-per-measure` to be passed explicitly and matched) and that `args.anchors` (as a set) is
unchanged from the resumed run's anchor set (union of `anchor_white`/`anchor_black` across
`priorRows`), throwing rather than silently continuing on any mismatch.

### WR-03: Fit-script output writer doesn't create the parent directory

**File:** `scripts/calibration_anchor_fit.py:345-374` (`_write_outputs`)

**Issue:** Every JS artifact writer in this phase family creates its output directory defensively
before writing (`fs.mkdirSync(path.dirname(filePath), { recursive: true })` — see
`openLedgerWriter`, `writePairsAggregateFile` in `calibration-anchor-ladder.mjs`, and
`openMainTsvWriter`/`emitEloSummary` in `calibration-harness.mjs`). `_write_outputs` has no
equivalent:
```python
Path(out_js).write_text("\n".join(js_lines) + "\n", encoding="utf-8")
...
Path(out_json).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```
If `--out-js`/`--out-json` points at a directory that doesn't yet exist (a real possibility since
this is a standalone tool the docstring shows being pointed at arbitrary `reports/data/...` paths),
this raises an unhandled `FileNotFoundError` with a raw traceback after the fit and bootstrap have
already run to completion (bootstrap alone can take a while at `--bootstrap-samples 500`), instead
of failing fast or succeeding.

**Fix:**
```python
Path(out_js).parent.mkdir(parents=True, exist_ok=True)
Path(out_js).write_text(...)
Path(out_json).parent.mkdir(parents=True, exist_ok=True)
Path(out_json).write_text(...)
```

## Info

### IN-01: Fractional `--seed` is silently truncated rather than rejected

**File:** `scripts/calibration-anchor-ladder.mjs:156-165`, `scripts/calibration-harness.mjs:281-290`

**Issue:** Both scripts validate `--seed` with:
```js
const parsed = Number.parseInt(raw, 10);
if (!Number.isInteger(parsed)) { throw ... }
```
`Number.parseInt('1.5', 10)` returns `1` (an integer), so `Number.isInteger(parsed)` is trivially
true and a typo'd `--seed 1.5` is silently accepted as `--seed 1` rather than rejected — the WR-02
"every value-consuming flag validates" discipline these scripts otherwise apply carefully doesn't
quite reach this case. Low impact (seed is only informational/reproducibility metadata, and the
mistake is easy to notice from the emitted TSV's own `seed` column), but worth a one-line tightening
(e.g. checking `raw` against `/^-?\d+$/` before parsing) since both copies of this helper share the
same gap.

---

_Reviewed: 2026-07-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

## Fix Log (2026-07-16)

| Finding | Status | Resolution |
|---------|--------|------------|
| CR-01 | fixed | Commit `0384b52a` — pairs canonicalized before the D-04 re-check; mutation-proven regression test added (`test_main_single_bridge_both_orientations_fails_connectivity`). |
| WR-01 | fixed | Commit `0384b52a` — `pairsAggregateRows` uses `scoreInInformativeBand`. |
| WR-02 | deferred | `--resume` param validation beyond `--seed` left as-is: the ladder run for this phase is complete; flag for SEED-102 if the harness is reused. |
| WR-03 | fixed | Commit `0384b52a` — `_write_outputs` creates parent dirs. |
| IN-01 | deferred | Fractional `--seed` truncation is cosmetic for a manual research CLI. |
