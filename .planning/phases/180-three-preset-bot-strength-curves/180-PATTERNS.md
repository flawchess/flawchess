# Phase 180: Three-preset bot strength curves - Pattern Map

**Mapped:** 2026-07-19
**Files analyzed:** 6 (2 modified, 3-4 new, 1 test extension)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/calibration-harness.mjs` (MODIFY: `internalRatingFor` swap, `DEFAULT_ANCHOR_TOKENS`, two-pass wiring, near-free metric columns) | CLI orchestrator / controller | batch (game-loop, CLI) | itself (prior D-15 windowing code in the same file) + `scripts/calibration-anchor-ladder.mjs` (two-pass orchestration shape) | exact (self) / role-match (orchestration) |
| `scripts/lib/calibration-bot-cell-schedule.mjs` (NEW: locate/bracket pure logic) | utility / pure-logic scheduler | transform (batch) | `scripts/lib/calibration-anchor-schedule.mjs` | role-match (same author, adjacent problem — a hub-and-spoke bracket vs a graph) |
| `scripts/lib/calibration-bot-cell-schedule.check.mjs` (NEW: unit checks) | test | request-response (assert-only) | `scripts/lib/calibration-anchor-schedule.check.mjs` | exact |
| `scripts/calibration_anchor_fit.py` (EXTEND: `fit_bot_cell_rating`, `G_preset`, bot-curves JSON writer) | service / fitter (batch, CLI) | transform (MLE fit) + file-I/O | itself — `fit_bradley_terry` (lines 156-194) is the direct specialization target | exact (self-extension) |
| `tests/scripts/test_calibration_anchor_fit.py` (EXTEND or sibling: `fit_bot_cell_rating` coverage) | test | request-response (pytest, synthetic fixtures) | itself (existing precedent, per RESEARCH.md "173-03's RED-first pattern") | exact |
| `--resume` two-pass integrity (in `calibration-harness.mjs`, `loadPriorSweep`/`cellKey`) | utility (durability/replay) | event-driven / file-I/O (ledger replay) | `scripts/calibration-anchor-ladder.mjs` (pair-keyed raw-ledger resume, per its own header comment) | role-match — genuinely different resume granularity, adapt don't copy verbatim |

## Pattern Assignments

### `scripts/lib/calibration-bot-cell-schedule.mjs` (utility, pure-logic transform)

**Analog:** `scripts/lib/calibration-anchor-schedule.mjs` (262 lines, full file read)

**Module header / docstring pattern** (lines 1-31): document the D-number(s) being satisfied, state
explicitly what does NOT port and why (this file's own "graph-shaped primitives don't fit a
hub-and-spoke bot-cell" caveat should follow the same disclosure style), and cite the specific
prior incident that motivated the design (this file cites the 2026-07-15 seed-101 run by date).

**Imports pattern** (line 32):
```javascript
import { anchorRatingFor } from './calibration-anchors.mjs';
```
For the new module, this becomes `internalRatingFor` (imported from `calibration-harness.mjs` once
that export exists there, per RESEARCH.md Pattern 3) or directly from
`calibration-internal-scale.mjs`'s `INTERNAL_RATING` table — do not reintroduce `anchorRatingFor`
(nominal scale) into the new bot-cell module; that would reintroduce the exact bug this phase fixes.

**Directly-reusable primitives to import verbatim, not reimplement** (lines 34-44, 174-179):
```javascript
export const INFORMATIVE_BAND_LOW = 0.2;
export const INFORMATIVE_BAND_HIGH = 0.8;
export function scoreInInformativeBand(score) {
  return score >= INFORMATIVE_BAND_LOW && score <= INFORMATIVE_BAND_HIGH;
}
// ...
export function bandDistance(score) {
  if (score < INFORMATIVE_BAND_LOW) return INFORMATIVE_BAND_LOW - score;
  if (score > INFORMATIVE_BAND_HIGH) return score - INFORMATIVE_BAND_HIGH;
  return 0;
}
```
The new module should `import { scoreInInformativeBand, bandDistance } from './calibration-anchor-schedule.mjs'` rather than duplicating these — RESEARCH.md Pattern 3 confirms this is the intended
reuse boundary.

**Named-constant pattern** (lines 37-39, 67, 133): every tunable is an exported, doc-commented
`const` (`INFORMATIVE_BAND_LOW`, `NEAREST_MAIA_RUNGS_PER_SF_ANCHOR`, `MIN_CROSS_FAMILY_EDGES`) —
mirrors CLAUDE.md's "No magic numbers" rule. The new module's `bracketSize` default (4, per
RESEARCH.md's `selectMeasureBracket(anchorSpecs, estimate, bracketSize = 4)`) and any locate-pass
game-count constant must follow this same named-export convention (e.g.
`export const DEFAULT_BRACKET_SIZE = 4;`, `export const LOCATE_PASS_GAMES = 8;`).

**Core transform pattern to adapt (NOT copy verbatim — different topology)** (lines 64-128,
"buildCandidateGraph"): shows the shape of "pure function over anchor specs → array of
selections", sorted-then-sliced logic (`initialCrossFamilyPairs`, lines 89-101) is the closest
structural precedent for the new module's `selectMeasureBracket` (sort by `|rating - estimate|`,
slice to bracket size, then force-include enough of each family):
```javascript
function initialCrossFamilyPairs(sfAnchors, maiaAnchors) {
  const pairs = [];
  for (const sf of sfAnchors) {
    const sfElo = anchorRatingFor(sf);
    const nearest = [...maiaAnchors]
      .sort((a, b) => Math.abs(anchorRatingFor(a) - sfElo) - Math.abs(anchorRatingFor(b) - sfElo))
      .slice(0, NEAREST_MAIA_RUNGS_PER_SF_ANCHOR);
    for (const maia of nearest) pairs.push(canonicalPair(sf.label, maia.label));
  }
  return pairs;
}
```

**Fail-loud vs warn-and-proceed distinction** (lines 141-170 vs RESEARCH.md's anti-pattern note):
`checkConnectivity` throws (`Error` with a matched substring like `/disconnected/` or
`/cross-family/`, tested via `assert.throws(..., /pattern/, msg)`) — this throw-on-invariant-
violation style should be copied for genuinely fatal bot-cell conditions (e.g. zero anchors
available at all), but per RESEARCH.md's explicit anti-pattern warning, a cell whose true strength
sits beyond the ladder edges is NOT fatal — return a `beyond_ladder: true` flag instead of throwing
(mirrors the existing `SKIP_REASON_*`/row-not-silently-absent pattern in `calibration-harness.mjs`
lines 903-907, 949).

---

### `scripts/lib/calibration-bot-cell-schedule.check.mjs` (test, request-response/assert-only)

**Analog:** `scripts/lib/calibration-anchor-schedule.check.mjs` (147 lines, full file read)

**Header / run-command comment pattern** (lines 1-9):
```javascript
#!/usr/bin/env node
/**
 * <name>.check.mjs — pure-logic assertion for <what>. No engines/network —
 * mirrors `calibration-elo.check.mjs`'s canned-fixture assertion style.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/<name>.check.mjs
 */
import assert from 'node:assert/strict';
import { ... } from './<name>.mjs';
```

**Fixture-builder helper pattern** (lines 33-51): small factory functions building canned anchor
specs, reused across assertions:
```javascript
function maiaSpec(rungElo) { return { kind: 'maia', label: `maia${rungElo}`, rungElo }; }
function sfSpec(skillLevel) { return { kind: 'sf', label: `sf${skillLevel}`, skillLevel }; }
const TEN_ANCHOR_SET = [maiaSpec(700), maiaSpec(1100), ..., sfSpec(10)];
```
The new check file should build an analogous `TEN_ANCHOR_SET` fixture (or import one shared
constant) plus 1-2 fabricated bot-cell probe results, matching D-02(a)'s "fabricated providers, no
real engines" requirement.

**One-assertion-block-per-function, `console.log('PASS: ...')` after each block** (lines 22-29,
53-73, 75-99, 101-110, 112-144): each exported function gets its own titled block ending in a
`console.log('PASS: <fn> — <what was proven>')`; the file ends with a final summary line +
`process.exit(0)` (line 146-147). Copy this structure exactly for the new file — it is the
project's convention for `.mjs` logic tests, not vitest.

**Assertion style for thrown errors** (lines 83-93):
```javascript
assert.throws(
  () => checkConnectivity([maiaPair, sfPair], CONN_ANCHORS),
  /disconnected/,
  'a maia-only + sf-only graph with ZERO cross links must throw (disconnected)',
);
```

**Boundary-inclusive numeric assertions** (lines 24-28): test both band edges (0.2/0.8 inclusive)
and both outside points explicitly — the new file's `scoreInInformativeBand`-adjacent tests (if
any bot-cell-specific band logic is added) should follow this same boundary-testing discipline.

---

### `scripts/calibration_anchor_fit.py` — `fit_bot_cell_rating` (service/fitter, extend in place)

**Analog:** itself — `fit_bradley_terry` (lines 156-194) and its supporting helpers
(`_clamp_win_counts` lines 124-153, `build_win_counts` lines 101-121), full read of lines 101-200.

**Function signature / docstring convention** (lines 156-173): explicit param types, a docstring
explaining the math source (cites Hunter 2004 / RESEARCH.md pattern name), and an explicit warning
about what NOT to seed from (folklore `SF_SKILL_ELO`) — the new `fit_bot_cell_rating` docstring
should analogously warn against seeding `strength` from anything but the neutral `1.0` init:
```python
def fit_bradley_terry(
    win_counts: dict[tuple[str, str], float],
    anchors: Sequence[str],
    tol: float = DEFAULT_FIT_TOL,
    max_iter: int = DEFAULT_FIT_MAX_ITER,
) -> dict[str, float]:
    """Zermelo/MM joint MLE fit (RESEARCH.md Pattern 2, Hunter 2004).
    ...
    Neutral symmetric initialization strength[a] = 1.0 for every anchor
    (Pitfall 3 — never seed from folklore SF_SKILL_ELO).
    ...
    """
```

**Continuity-correction discipline to reuse, not reimplement** (lines 124-153): `_clamp_win_counts`
prevents ±infinity blowup on a lopsided (e.g. 8-0) pair score before the fixed-point iteration —
`fit_bot_cell_rating` MUST apply the equivalent clamp to `win_counts_vs_fixed`/`games_vs_fixed`
before its own iteration (RESEARCH.md's own sketch already calls this out: "Same continuity-
correction discipline as `_clamp_win_counts`"). Reuse `_clamp_win_counts` directly if its signature
generalizes to a 1-vs-N (not N-vs-N) win-count dict, otherwise mirror its epsilon-clamp formula
exactly:
```python
epsilon = 1.0 / (SCORE_CLAMP_EPSILON_DIVISOR * games)
clamped_score_i = min(1.0 - epsilon, max(epsilon, score_i))
```

**Fixed-point (Zermelo/MM) iteration shape** (lines 176-194) — the direct template for
`fit_bot_cell_rating`, specialized from N free anchors to 1 free bot-cell strength against N fixed
opponents (RESEARCH.md's own code sketch at research lines 493-521 already follows this shape
correctly — implement it as written there, importing `RATING_SCALE`, `DEFAULT_FIT_TOL`,
`DEFAULT_FIT_MAX_ITER` from module scope rather than re-declaring):
```python
strength = {a: 1.0 for a in anchors}
total_wins = {a: sum(win_counts.get((a, b), 0.0) for b in anchors if b != a) for a in anchors}
for _ in range(max_iter):
    new_strength: dict[str, float] = {}
    for i in anchors:
        denom = sum(
            (win_counts.get((i, j), 0.0) + win_counts.get((j, i), 0.0)) / (strength[i] + strength[j])
            for j in anchors if j != i and (win_counts.get((i, j), 0.0) + win_counts.get((j, i), 0.0)) > 0
        )
        new_strength[i] = total_wins[i] / denom if denom > 0 else strength[i]
    max_rel_change = max(abs(new_strength[a] - strength[a]) / strength[a] for a in anchors)
    strength = new_strength
    if max_rel_change < tol:
        break
return {a: RATING_SCALE * math.log10(strength[a]) for a in anchors}
```

**Two independent fits, never averaged** (Pitfall 3 in RESEARCH.md): call `fit_bot_cell_rating`
TWICE per cell (once on `win_counts`/`games` restricted to `maia*` rows, once restricted to `sf*`
rows), each against the FULL `INTERNAL_RATING` fixed-rating dict (not two different subsets of
`fixed_ratings` — only the observed win/game counts differ between the two calls). `G_preset =
rating_vs_maia - rating_vs_sf` is computed directly from the two returned floats, per cell.

**Output/write pattern to mirror** (see `_write_outputs`, line 345, and
`reports/data/anchor-ladder-internal-scale.json` shape per RESEARCH.md D-06): new bot-curves JSON
should carry the same per-entity shape (rating + CI + metadata) the existing anchor-ladder JSON
uses, plus the new `rating_vs_maia`/`rating_vs_sf`/`g_preset`/`beyond_ladder` fields — read
`_write_outputs` (around line 345) for the exact existing JSON envelope shape before adding new
top-level keys.

---

### `tests/scripts/test_calibration_anchor_fit.py` (test, pytest, extend or sibling)

**Analog:** itself (existing file, precedent already established per RESEARCH.md: "mirrors 173-03's
RED-first pattern"). Add a `test_fit_bot_cell_rating_synthetic_ground_truth` (or similar) using a
fabricated fixed-rating dict + synthetically-generated win/loss counts at a KNOWN true strength,
asserting the fit recovers that strength within a small tolerance — this is the existing file's own
established convention for `fit_bradley_terry`'s coverage; apply the same fixture-generation
approach to the new single-parameter function.

---

### `scripts/calibration-harness.mjs` — `internalRatingFor` swap (controller, request-response/batch)

**Analog:** itself. Three exact call sites to change, all currently calling `anchorRatingFor`
(nominal scale, the bug):

1. `partitionAnchorsByWindow` (lines 910-918) — `Math.abs(anchorRatingFor(anchorSpec) - botElo) <= ANCHOR_ELO_WINDOW` → swap `anchorRatingFor` for `internalRatingFor`. Per RESEARCH.md Open
   Question 1 (recommendation: supersede), this whole function's role is likely retired by the new
   two-pass bracket module rather than fixed in place — confirm with the plan before touching it.
2. `orderAnchorsForDynamicCutoff` (lines 939-947) — same swap, same "likely retired" caveat.
3. `summaryRowForCellGroup` (lines 667-676) — `anchorRating: anchorRatingFor(row.anchorSpec)` inside
   the advisory `combineAnchorEstimates` call; per Pitfall 3, this combined-estimate advisory print
   is NOT the final G_preset artifact and can keep using a single combined number for the live
   progress printout — just fix the axis it's combined on.

**`DEFAULT_ANCHOR_TOKENS` restriction pattern** (lines 152-169): replace the Maia-every-200-ELO
ladder + 3 SF skills with exactly the 10 measured labels:
```javascript
const DEFAULT_ANCHOR_TOKENS = [
  'maia700', 'maia1100', 'maia1500', 'maia1900', 'maia2300',
  'sf0', 'sf3', 'sf5', 'sf8', 'sf10',
];
```

**Fail-loud guard pattern to copy for `internalRatingFor` itself** (see RESEARCH.md Pattern 1's
full code, already written verbatim there) — throws with a descriptive message rather than falling
back, matching WR-02 discipline already used throughout this file (e.g. `requireFlagValue`,
`parsePositiveIntFlag` per CLAUDE.md V5 input-validation note).

---

### `--resume` two-pass integrity — raw-ledger-replay analog

**Analog:** `scripts/calibration-anchor-ladder.mjs` (689 lines total; targeted read recommended at
its own resume-related section before implementing, per RESEARCH.md Pitfall 5 — its header comment
states verbatim: "the resumable unit is ONE (anchor_a, anchor_b) pair's played games so far, NOT a
bot harness fixed grid cell"). The existing `calibration-harness.mjs` resume (`loadPriorSweep`,
lines 825-864; `cellKey`, line 752) validates a FIXED `--games-per-cell` per row (line 845:
`row.games !== args.gamesPerCell` throws) — this assumption breaks once cells have
variable-length two-pass game counts (locate + bracket-dependent measure). RESEARCH.md's own
recommendation (Open Question 2): follow the anchor-ladder's raw-ledger-replay pattern rather than
extending the fixed-count model. Read `calibration-anchor-ladder.mjs`'s resume logic directly
(grep for `resume`/`ledger` in that file) before implementing — not excerpted here since this
research flags it as a genuine open design fork requiring its own targeted read at plan time.

## Shared Patterns

### Fail-loud validation (WR-02 discipline)
**Source:** `scripts/lib/calibration-anchor-schedule.mjs` `checkConnectivity` (lines 141-170) +
`scripts/calibration-harness.mjs`'s existing CLI flag parsers (`requireFlagValue`,
`parsePositiveIntFlag`)
**Apply to:** `internalRatingFor` (throw on missing `INTERNAL_RATING` key — Pitfall 1), the new
bot-cell schedule module's genuinely-fatal conditions (zero anchors available), `fit_bot_cell_rating`'s input validation (non-empty games, `fixed_ratings` covers every referenced label — per
RESEARCH.md's STRIDE table, "Tampering" mitigation).
```javascript
throw new Error(`internalRatingFor: no measured INTERNAL_RATING for ${anchorSpec.label} — only the 10 Phase-173 anchors are usable`);
```

### Warn-and-flag, never throw, for "real but extreme" measurements
**Source:** RESEARCH.md's explicit anti-pattern section + `calibration-harness.mjs`'s existing
`SKIP_REASON_*` row-not-silently-absent convention (lines 903-907, 949)
**Apply to:** a bot cell whose true strength sits beyond `sf10`/below `sf0` — set `beyond_ladder: true` on the row/fit output, never throw (Pitfall 4).

### Named-constant discipline (no magic numbers)
**Source:** `scripts/lib/calibration-anchor-schedule.mjs` (`INFORMATIVE_BAND_LOW/HIGH`,
`MIN_CROSS_FAMILY_EDGES`, `NEAREST_MAIA_RUNGS_PER_SF_ANCHOR`) + `calibration-harness.mjs`
(`ANCHOR_ELO_WINDOW`, `DEFAULT_GAMES_PER_CELL`)
**Apply to:** any new tunable in the bot-cell schedule module (bracket size, locate-pass game
count) and in `fit_bot_cell_rating` (reuse existing `DEFAULT_FIT_TOL`/`DEFAULT_FIT_MAX_ITER`/
`RATING_SCALE` rather than re-declaring).

### `.check.mjs` fabricated-provider test structure
**Source:** `scripts/lib/calibration-anchor-schedule.check.mjs` (full file, see excerpts above)
**Apply to:** `calibration-bot-cell-schedule.check.mjs` (new) and any near-free-metrics check file
(`onPly` extension coverage) — same header/run-command comment, fixture-builder helpers,
one-block-per-function with `console.log('PASS: ...')`, `process.exit(0)` at the end.

### Two-independent-fits-never-averaged
**Source:** RESEARCH.md Pitfall 3, this phase's own D-06 requirement
**Apply to:** `fit_bot_cell_rating` call sites in the new fit-extension code — always call twice
(vs-Maia rows, vs-SF rows) against the same fixed `INTERNAL_RATING`, never merge win/game counts
across families before fitting.

## No Analog Found

None — every file in scope has a strong same-repo analog (this phase is explicitly an extension of
Phase 173's proven tooling, per RESEARCH.md's own framing: "every primitive this phase needs already
exists in this codebase").

## Metadata

**Analog search scope:** `scripts/`, `scripts/lib/`, `tests/scripts/` (no `app/`, `frontend/`, or
`.planning/` code surface — this phase touches no web-app tier)
**Files scanned directly (full or targeted read):** `scripts/calibration-harness.mjs` (targeted:
lines 140-180, 660-950, plus grep-located call sites across full 1270 lines),
`scripts/lib/calibration-anchor-schedule.mjs` (full, 262 lines),
`scripts/lib/calibration-anchor-schedule.check.mjs` (full, 147 lines),
`scripts/calibration_anchor_fit.py` (targeted: lines 60-200 plus grep of full 461-line structure),
`scripts/calibration-anchor-ladder.mjs` (structure only via `wc -l`/grep — flagged for a targeted
read at plan/implementation time on the resume-ledger section specifically)
**Pattern extraction date:** 2026-07-19
