# Phase 180: Three-preset bot strength curves - Research

**Researched:** 2026-07-19
**Domain:** Offline calibration tooling (Node CLI harness + Python stdlib fitter) — no app/API/schema/UI surface
**Confidence:** HIGH (all code paths, TSV schemas, and measured anchor numbers read directly from the repo; grid-point recommendations are MEDIUM/flagged [ASSUMED] since blend=0.05 has never been measured)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Split delivery. The phase completes when the harness fixes land and are proven on a
  pilot. The full ~1,440-game (~18-22h) sweep, the fitted curves, `G_preset`, and the findings
  note are an **operator-run HUMAN-UAT step** folded in afterward — the overnight run does NOT sit
  on the phase's interactive critical path.
- **D-02:** Both layers required: (a) unit / `*.check.mjs` logic tests on the new internal-scale
  windowing + two-pass cell-selection using fabricated providers (no real engines, deterministic);
  AND (b) a small real-engine pilot of 1–2 real cells at low N confirming: sane ratings, correct
  anchor windowing on `INTERNAL_RATING`, both anchor families firing, and `--resume` integrity.
- **D-03:** **Per-preset, non-uniform grids** (locked shape): three separate rows, Human skewed to
  the low end, Light the middle, Deep the high end, overlapping in the middle, ~5 `bot_elo` points
  each. Each preset's honest slider range (SEED-104) drives its point placement.
- **D-04:** **Exact `bot_elo` point values are a planner/researcher output**, chosen after
  inspecting `INTERNAL_RATING` spacing and anchor bracketing — evidence-based placement, not
  guessed here. (Seed example {700,1100,1500,1900,2300} is illustrative only.)
- **D-05:** Games-per-(cell, anchor) on the measure pass is a **planner decision** — set from a
  precision target given the measured anchor spacing, within the seed's 24–30 band (24 → ±71/anchor
  → ~±35 combined; 30 → ~±64/anchor at ~25% more wall-clock). Applies to the operator sweep budget,
  not the pilot.
- **D-06:** **Extend `scripts/calibration_anchor_fit.py`** (the existing Bradley-Terry/Elo fitter)
  rather than reimplementing in JS. Hold the 10 anchors fixed at their `INTERNAL_RATING`, fit each
  bot cell's rating with **separate vs-Maia and vs-SF fits** so `G_preset = rating_vs_Maia −
  rating_vs_SF` is a direct output. Emit a bot-curves JSON mirroring
  `reports/data/anchor-ladder-internal-scale.json` (ratings + CIs), consistent method with 173,
  CIs for free.
- **D-07:** **Reuse the Phase-173 `scripts/lib/calibration-anchor-schedule.mjs`** probe→measure +
  connectivity/cross-family guard (informative [0.2, 0.8] band, `rescueConnectivity`/`bandDistance`
  rescue). Adapt as needed for bot-vs-anchor cells. Locate pass ≈ 8 games vs 2 widely-spaced
  anchors to place a cell, then measure vs the 3–4 anchors bracketing that estimate on
  `INTERNAL_RATING`.
- **Locked upstream (SEED-102):** Blend values `{0, 0.05, 0.5}` fixed. Human = one Maia policy
  call, no search, sample raw policy; Light/Deep = full MCTS, `tau = TAU_MAX·(1−blend)`,
  `TAU_MAX = 0.1`. Cross-family split is a first-class output. Also log near-free: Maia-agreement,
  SF-agreement, ACPL, blunder rate, draw rate, game length. Primary output is on the internal
  anchor scale, NOT human ELO.

### Claude's Discretion

- Exact `bot_elo` point values per preset (D-04), measure-pass games/cell (D-05), and the precise
  adaptation of the 173 schedule module to bot cells (D-07) are all planner/researcher calls.

### Deferred Ideas (OUT OF SCOPE)

- Absolute human-ELO pin `C` and the shipping lookup curves / honest per-preset slider ranges /
  preset cards — SEED-104, gated on this phase's outputs.
- Bot personas / play-style layer — SEED-098, downstream of calibrated presets.
</user_constraints>

<phase_requirements>
## Phase Requirements

No `.planning/REQUIREMENTS.md` exists in this project for this phase — it is backlog work sourced
directly from a seed (SEED-102), the same pattern Phase 173 used (its own `173-VALIDATION.md`
states verbatim: "No `REQUIREMENTS.md` entries map to this phase (SEED-101 backlog work); the
CONTEXT.md decisions D-01…D-13 are the phase's requirements"). Phase 180 follows the identical
pattern: CONTEXT.md's D-01…D-07 ARE the requirements this research and the downstream plan must
satisfy.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Split delivery: harness fixes + pilot in-phase, full sweep as HUMAN-UAT | Validation Architecture section; pilot design (Q6) |
| D-02 | Two-layer pilot: logic checks + small real-engine pilot | Q6 — pilot design, mirrors `calibration-anchor-schedule.check.mjs` + Phase 173's `checkpoint:human-verify` pattern |
| D-03 | Per-preset non-uniform grid shape, ~5 points, overlapping middle | Q1 — grid point recommendation |
| D-04 | Exact `bot_elo` points, evidence-based from `INTERNAL_RATING` spacing | Q1 — full anchor ladder table + recommended point sets |
| D-05 | Games/(cell,anchor), 24–30 band, ~±35 combined target | Q4 — SE arithmetic worked through |
| D-06 | Extend `calibration_anchor_fit.py`, pinned anchors, separate vs-Maia/vs-SF fits | Q5 — fit extension design + output shape |
| D-07 | Adapt `calibration-anchor-schedule.mjs` to bot-vs-anchor cells | Q3 — locate/measure adaptation, reusable vs non-reusable pieces |
</phase_requirements>

## Summary

This is a pure offline-tooling phase: fix a windowing bug in `scripts/calibration-harness.mjs`
(anchors are currently bracketed by nominal `bot_elo`, not the measured `INTERNAL_RATING` — the
exact bug that clamped every cell in the 2026-07-12 run), add a locate-then-measure two-pass
schedule for bot cells (adapting, not reusing verbatim, Phase 173's anchor-vs-anchor scheduler),
and extend `scripts/calibration_anchor_fit.py` to fit each bot cell's rating against the 10
already-measured anchors held fixed, producing `G_preset = rating_vs_Maia − rating_vs_SF` directly.
No new npm/pip packages, no app/API/schema/UI change — the entire surface is `scripts/` and
`scripts/lib/`.

The ten anchors (5 Maia argmax rungs, 5 Stockfish Skill Levels) span internal ratings 1069–1908 and
interleave rather than nest (`sf3≈maia1100`, `sf5≈maia1500`, `sf8` between `maia1900`/`maia2300`).
Because Human (blend 0) shares Maia's own policy family, its 5 grid points should land exactly on
the 5 measured Maia rungs (700/1100/1500/1900/2300) for maximum bracket tightness. Light and Deep
run full MCTS and are expected (per the 2026-07-12 clamped run's blend-0→0.5 "cliff", Finding 1 of
the 2026-07-13 note) to land well above their own nominal `bot_elo` on the internal scale — their
grid points should still be chosen on the `bot_elo` axis (mid-skew for Light, high-skew for Deep,
sharing {1100,1500,1900} for a direct equal-`bot_elo` style comparison), with the actual internal
placement discovered by the two-pass locate step, not predicted here.

The `D-06` fit does NOT require a new raw per-game ledger: the existing aggregated main-results TSV
(wins/draws/losses per anchor) is sufficient for a parametric bootstrap CI around a single pinned-
anchor MLE fit. `G_preset` "for free" (near-free metrics: Maia-agreement, SF-agreement, ACPL,
blunder rate) is NOT actually free today — draw rate and game length are already computed and just
need surfacing; ACPL/blunder-rate/SF-agreement can reuse the existing per-ply adjudication eval
call (zero extra engine calls); Maia-agreement needs one extra cheap policy forward-pass per bot
ply (not literally free, but cheap relative to a full MCTS move).

**Primary recommendation:** Fix `internalRatingFor` at the three call sites in
`calibration-harness.mjs` (windowing, dynamic-cutoff ordering, advisory-summary combination), swap
`DEFAULT_ANCHOR_TOKENS` to the exact 10 measured anchors, build a new pure-logic bot-cell locate
module (mirroring `calibration-anchor-schedule.mjs`'s separation of pure logic from orchestration),
extend `calibration_anchor_fit.py` with a `fit_bot_cell()` function that reads the harness's
existing aggregated TSV schema, and gate the pilot behind the same two-tier check-then-checkpoint
pattern Phase 173 already used successfully (`*.check.mjs` green → `checkpoint:human-verify` for
the real-engine slice).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Anchor windowing / bracket selection | CLI tooling (`scripts/calibration-harness.mjs`) | — | Pure Node logic over an already-loaded constant table; no app/API involvement |
| Two-pass locate→measure scheduling | CLI tooling (`scripts/lib/`) | — | Extends the existing pure-logic scheduler module pattern (173) |
| Game simulation (bot vs anchor) | CLI tooling, Node subprocess pool | External engine processes (Stockfish, ONNX Maia) | Headless harness spawns real engine subprocesses; no browser/worker involved |
| Rating fit (Bradley-Terry, pinned anchors) | CLI tooling (Python `scripts/`) | — | Stdlib-only per D-07 of Phase 173's own research (no numpy/scipy) |
| Artifact storage | Filesystem (`reports/data/`, `scripts/lib/*.mjs`) | Git (committed) | Same pattern as `anchor-ladder-internal-scale.json` / `calibration-internal-scale.mjs` |
| Shipping consumption of curves | N/A this phase | SEED-104 (future phase) | Explicitly out of scope — this phase only produces the measurement artifact |

No browser/API/database tier is touched at all in this phase — flagging this explicitly since the
template assumes a web-app phase by default; this one doesn't have one.

## Project Constraints (from CLAUDE.md)

- **GSD scope discipline**: "Do not add unplanned features, refactors, or improvements outside the
  current GSD phase scope." Directly relevant — the harness/schedule/fit files carry heavy prior
  Phase 168/168.5/173 investment; resist the urge to "clean up" unrelated code while touching them.
- **No sycophancy / disagree-and-commit** communication style applies to this doc's phrasing.
- **No magic numbers**: any new constant (locate-pass game count, bracket-size N, etc.) must be a
  named export, mirroring `DEFAULT_GAMES_PER_PROBE`/`MIN_CROSS_FAMILY_EDGES`-style constants
  already in this codebase.
- **Comment bug fixes**: the `internalRatingFor` swap is fixing a real, documented bug (2026-07-12
  clamped run) — the fix site needs a comment explaining what broke and why, per CLAUDE.md's
  "Comment bug fixes" rule (mirrors the existing style throughout `calibration-harness.mjs`, e.g.
  "Rule 1 bug fix" comments already present).
- **Function size limits** (nesting depth 3 soft/4 hard, logic LOC 100 soft/200 hard): the two-pass
  bot-cell adaptation should follow `calibration-anchor-ladder.mjs`'s existing decomposition
  (`probePass`/`scheduleGraph`/`measurePass` as separate functions) rather than inlining into
  `calibration-harness.mjs`'s already-large `main()`.
- **This project uses Python 3.13 + uv, Node ESM (`.mjs`)** — `calibration_anchor_fit.py`
  additions must stay stdlib-only (matches its own docstring: "stdlib only
  (`math`/`random`/`argparse`/`json`), no numpy/scipy").
- **httpx-only / no `requests`** — N/A, no HTTP calls in this phase.
- Sentry rules (`app/services`, `app/routers`) — N/A, this phase never touches `app/`.

## Standard Stack

No new libraries. This phase extends four existing files, adding zero new npm/pip dependencies.

### Core (existing, reused verbatim or extended)
| Library/Module | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `scripts/calibration-harness.mjs` | in-repo | bot-vs-anchor game loop, grid sweep, TSV emission | already proven, the file this phase fixes |
| `scripts/lib/calibration-anchor-schedule.mjs` | in-repo | probe→measure gate + connectivity guard (pure logic) | D-07: reuse/adapt, don't reimplement |
| `scripts/lib/calibration-internal-scale.mjs` | in-repo (GENERATED) | the `INTERNAL_RATING` lookup table | the ruler this phase must window against |
| `scripts/calibration_anchor_fit.py` | in-repo | Bradley-Terry/Elo MLE fit, bootstrap CI | D-06: extend for pinned-anchor single-parameter fit |
| Node stdlib (`node:assert/strict`, `node:fs`, `node:path`) | Node runtime | `.check.mjs` pure-logic tests | project convention, no vitest for scripts/ |
| Python stdlib (`math`, `random`, `argparse`, `json`) | Python 3.13 | fit + bootstrap | `calibration_anchor_fit.py`'s own D-07: no numpy/scipy |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Parametric bootstrap CI on aggregated WDL counts (recommended, Q5) | A new raw per-game ledger + nonparametric bootstrap over games (mirrors 173's `bootstrap_ci` exactly) | More faithful to 173's method, but requires a NEW artifact type the harness doesn't currently emit for bot cells (WR-01 durability at per-game granularity); the anchors are FIXED constants here (not being refit), so the cross-pair correlation that motivated 173's game-level resampling doesn't apply — the simpler aggregate approach is statistically adequate for this sub-problem |
| Reusing `combineAnchorEstimates`/`invertAnchorElo` (JS, closed-form Elo inversion) for the final G_preset | Reimplementing a proper single-parameter Bradley-Terry MLE in Python (recommended, D-06 explicit) | D-06 explicitly asks for the Python fit path so `G_preset` "falls out directly" from a real MLE, not an ad-hoc weighted average of independent inversions; the JS `combineAnchorEstimates` remains useful only for the harness's own live-progress advisory printout, not the final artifact |

**Installation:** none — no new packages.

## Package Legitimacy Audit

Not applicable — this phase introduces zero external packages (npm or PyPI). All work extends
existing in-repo `scripts/` and `scripts/lib/` modules.

**Packages removed due to [SLOP] verdict:** none (no packages evaluated — none introduced)
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ scripts/lib/calibration-internal-scale.mjs (GENERATED, Phase 173)   │
│   INTERNAL_RATING = { maia700: 1129.29, ..., sf10: 1907.93 }        │  ← the ruler
└───────────────────────────────┬───────────────────────────────────┘
                                 │ imported (NEW in this phase)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ scripts/calibration-harness.mjs                                     │
│                                                                       │
│  main() ─ for each (preset row, bot_elo point):                     │
│    ┌─────────────────────────────────────────────────────────┐     │
│    │ LOCATE pass (NEW, D-07 adaptation)                       │     │
│    │  play ~8 games vs 2 widely-spaced anchors                │     │
│    │  → invertAnchorElo() rough internal-rating estimate       │     │
│    └───────────────────────┬───────────────────────────────────┘     │
│                             ▼                                        │
│    ┌─────────────────────────────────────────────────────────┐     │
│    │ bracket selection (NEW pure-logic module)                │     │
│    │  pick 3-4 anchors nearest the locate estimate,            │     │
│    │  forcing >=2 Maia + >=2 SF where the ladder allows         │     │
│    └───────────────────────┬───────────────────────────────────┘     │
│                             ▼                                        │
│    ┌─────────────────────────────────────────────────────────┐     │
│    │ MEASURE pass (existing playCell, budget bumped to 24-30) │     │
│    │  reuses locate games as first N (never replays)          │     │
│    │  onPly hook (NEW) also captures: post-move eval           │     │
│    │  (reused from adjudication), SF bestmove (reused),        │     │
│    │  one extra Maia policy call (agreement rate)               │     │
│    └───────────────────────┬───────────────────────────────────┘     │
│                             ▼                                        │
│  writeRow() → calibration-harness-<ts>.tsv (per-cell aggregate,     │
│                now carries near-free metric columns too)             │
└───────────────────────────────┬───────────────────────────────────┘
                                 │ TSV (existing schema, extended)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ scripts/calibration_anchor_fit.py (EXTENDED, D-06)                  │
│   fit_bot_cell(cell_rows, fixed_ratings=INTERNAL_RATING)            │
│     → rating_vs_maia, rating_vs_sf (2 independent 1-param MLE fits) │
│     → G_preset = rating_vs_maia - rating_vs_sf                      │
│     → bootstrap CI via resampling WDL counts (parametric)           │
│   writes reports/data/bot-curves-internal-scale.json                │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    (out of scope this phase — SEED-104 consumes it)
```

### Recommended Project Structure

No new top-level directories. New/modified files, all within existing conventions:

```
scripts/
├── calibration-harness.mjs              # MODIFIED: internal-scale windowing, two-pass integration, near-free metric columns
├── calibration_anchor_fit.py            # MODIFIED: fit_bot_cell(), load_bot_cells(), new CLI mode/flags
└── lib/
    ├── calibration-internal-scale.mjs   # UNCHANGED (imported, not modified)
    ├── calibration-anchor-schedule.mjs  # UNCHANGED (imported, D-07 reuse — pure functions only)
    ├── calibration-bot-cell-schedule.mjs   # NEW: bot-cell-specific locate/bracket logic (pure, engine-free)
    ├── calibration-bot-cell-schedule.check.mjs  # NEW: D-02(a) logic-test layer, mirrors calibration-anchor-schedule.check.mjs
    └── calibration-anchors.mjs          # UNCHANGED (imported)
tests/scripts/
└── test_calibration_anchor_fit.py       # MODIFIED (or new sibling): fit_bot_cell() coverage, synthetic ground-truth fixture (mirrors 173-03's RED-first pattern)
```

### Pattern 1: `internalRatingFor` replacing `anchorRatingFor` at windowing/ordering/combining call sites

**What:** A new function that looks up `INTERNAL_RATING[anchorSpec.label]`, throwing (WR-02
fail-loud discipline, matching every other validation in this file) if the label is absent from
the table — this is the guard that also FORCES the anchor-token list restriction (Pattern 2 below),
since any token not in the Phase 173 10-anchor set has no measured `INTERNAL_RATING` entry.

**When to use:** Every place `calibration-harness.mjs` currently calls `anchorRatingFor(anchorSpec)`
to make a strength-relative decision about a bot cell (three call sites, verified by direct read):

1. `partitionAnchorsByWindow` (line ~910–918) — the static `ANCHOR_ELO_WINDOW` bracket, currently
   comparing `anchorRatingFor(anchorSpec)` against nominal `botElo`.
2. `orderAnchorsForDynamicCutoff` (line ~939–947) — sorts weaker/stronger anchors by
   `anchorRatingFor` around nominal `botElo` for the D-15 sweep-cutoff traversal.
3. `summaryRowForCellGroup` (line ~666–676) — the D-05 advisory per-cell Elo estimate, calling
   `anchorRatingFor(row.anchorSpec)` inside `combineAnchorEstimates`.

**Example:**
```javascript
// Source: scripts/lib/calibration-internal-scale.mjs (Phase 173) + this phase's fix
import { INTERNAL_RATING } from './lib/calibration-internal-scale.mjs';

/**
 * Bug fix (Phase 180, SEED-102 Finding 3 of the 2026-07-13 note): the harness
 * previously windowed/ordered/combined anchors by their NOMINAL rating
 * (anchorRatingFor), which is compressed ~2.8x relative to their measured
 * INTERNAL_RATING (Phase 173 Finding 2) — every 2026-07-12 cell clamped
 * because the informative anchors sat outside a window computed on the
 * wrong axis. Throws (fail-loud) if an anchor token has no measured
 * internal rating — this is what restricts DEFAULT_ANCHOR_TOKENS to
 * exactly the 10 Phase-173-measured anchors (Pattern 2).
 */
export function internalRatingFor(anchorSpec) {
  const rating = INTERNAL_RATING[anchorSpec.label];
  if (rating === undefined) {
    throw new Error(
      `internalRatingFor: no measured INTERNAL_RATING for ${anchorSpec.label} — ` +
        `only the 10 Phase-173 anchors are usable for internal-scale windowing`,
    );
  }
  return rating;
}
```

### Pattern 2: restricting the default anchor set to the 10 measured anchors

**What:** `DEFAULT_ANCHOR_TOKENS` currently builds a large Maia ladder every 200 nominal ELO
(`maia600, maia800, ... maia2600`, ~11 tokens) plus only `sf0, sf3, sf5` — none of the extra Maia
rungs (800/1300/1700/2100/2500/etc.) and neither `sf8` nor `sf10` have a measured
`INTERNAL_RATING` entry. "Both anchor families enabled" (CONTEXT.md in-scope item 3) does not
require new dispatch logic — `parseAnchorSpec` already generically parses any `sf<N>`/`maia<ELO>`
token — it requires swapping the DEFAULT token list (and, for the pilot, `--anchors` overrides) to
exactly the 10 measured labels.

**When to use:** `DEFAULT_ANCHOR_TOKENS` declaration (line ~162–169) and any CLI-default
documentation/usage comment referencing the old list.

**Example:**
```javascript
// Source: scripts/lib/calibration-internal-scale.mjs's own key set (Object.keys(INTERNAL_RATING))
const DEFAULT_ANCHOR_TOKENS = [
  'maia700', 'maia1100', 'maia1500', 'maia1900', 'maia2300',
  'sf0', 'sf3', 'sf5', 'sf8', 'sf10',
];
```

### Pattern 3: locate pass — two widely-spaced anchors, then bracket

**What:** Adapted from `calibration-anchor-ladder.mjs`'s probe→measure structure, but for a
BOT CELL vs a FIXED anchor pool (not anchor-vs-anchor). The bot cell is not a graph node — it has
no identifiability problem, so `checkConnectivity`/`buildCandidateGraph` (graph-shaped, anchor-vs-
anchor specific) do NOT port directly. What DOES port: `scoreInInformativeBand`, `bandDistance`,
and the general "cheap wide probe → informative-band-driven narrowing" shape.

**When to use:** Once per (preset, `bot_elo`) cell, before the measure pass.

**Example (pseudocode, this phase's new module):**
```javascript
// Source: adapted from scripts/lib/calibration-anchor-schedule.mjs's scoreInInformativeBand/bandDistance
// and scripts/calibration-anchor-ladder.mjs's probePass/measurePass shape (Phase 173, D-01/D-08)
import { scoreInInformativeBand, bandDistance } from './calibration-anchor-schedule.mjs';
import { internalRatingFor } from '../calibration-harness.mjs';

/** Picks 2 widely-spaced anchors (weakest + strongest available) for the locate pass. */
export function pickLocateAnchors(anchorSpecs) {
  const sorted = [...anchorSpecs].sort((a, b) => internalRatingFor(a) - internalRatingFor(b));
  return [sorted[0], sorted[sorted.length - 1]];
}

/** Rough internal-rating estimate from 2 locate-pass scores (invertAnchorElo, reused verbatim). */
export function locateEstimate(locateResults) {
  // locateResults: [{ anchorSpec, score, games }, ...] — reuses combineAnchorEstimates
  // from calibration-elo.mjs (imported by calibration-harness.mjs already).
}

/**
 * Selects the bracket for the measure pass: the N anchors nearest the locate
 * estimate, forcing at least 2 Maia + 2 SF where the ladder makes that
 * possible (generalizes calibration-anchor-schedule.mjs's
 * MIN_CROSS_FAMILY_EDGES spirit to a hub-and-spoke, not a graph edge count).
 */
export function selectMeasureBracket(anchorSpecs, estimate, bracketSize = 4) {
  // sort by |internalRatingFor(spec) - estimate|, but ensure >=2 of each family
  // survive the cut even if that means including a slightly-farther anchor —
  // mirrors D-04's cross-family requirement, applied per-cell instead of per-graph.
}
```

### Anti-Patterns to Avoid

- **Reusing `checkConnectivity`/`buildCandidateGraph`/`rescueConnectivity` verbatim for bot cells:**
  these are graph-connectivity primitives solving a DIFFERENT problem (are all 10 anchors
  mutually identifiable). A bot cell isn't a graph node with edges to other bot cells — it only
  ever compares against the fixed anchor pool. Importing these functions unchanged and trying to
  force-fit a "graph" of one bot cell + N anchors is over-engineering; only
  `scoreInInformativeBand`/`bandDistance` (scalar band-membership helpers) genuinely port.
- **A cell beyond the ladder's edge fail-loud like Phase 173's connectivity guard:** Phase 173's
  `checkConnectivity` throws because a disconnected inter-anchor graph makes the WHOLE SCALE
  non-identifiable (Pitfall 1, 173-RESEARCH.md). A single bot cell whose true strength sits above
  `sf10` (1907.93) or below `sf0` (1069.33) is not a broken scale — it's a real, if imprecise,
  measurement. Warn-and-proceed (flag the row, e.g. `beyond_ladder=true`), never throw.
- **Modifying `INTERNAL_RATING`/`calibration-internal-scale.mjs` in this phase:** it is
  `GENERATED — do not hand-edit` per its own docstring. This phase only imports/reads it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Elo↔score inversion for a rough locate estimate | A new closed-form inversion | `invertAnchorElo`/`combineAnchorEstimates` (`calibration-elo.mjs`, already imported by the harness) | Already handles the small-sample clamp (Pitfall 4) and Wilson-CI weighting |
| Score confidence intervals | A hand-rolled normal-approximation CI | `wilsonBounds` (`@/lib/scoreConfidence`, "Trust the established Wilson stat method" project convention — see MEMORY.md `feedback_wilson_chess_score`) | Already the canonical method across this codebase |
| Informative-band gating | A new threshold check | `scoreInInformativeBand`/`INFORMATIVE_BAND_LOW`/`INFORMATIVE_BAND_HIGH` (`calibration-anchor-schedule.mjs`) | Exact D-01 semantics already implemented and unit-tested |
| Bradley-Terry MLE fitting | A new fitting routine per bot cell from scratch | Extend `fit_bradley_terry`'s Zermelo/MM iteration pattern in `calibration_anchor_fit.py`, specialized to ONE free parameter against N fixed opponents (a strict simplification of the existing N-parameter joint fit) | Same convergence properties, same continuity-correction discipline (`_clamp_win_counts`), proven correct in Phase 173 |
| Move-eval-drop severity classification (blunder/mistake/inaccuracy) for the ACPL/blunder-rate near-free metric | A new threshold table | `BLUNDER_DROP`/`MISTAKE_DROP`/`INACCURACY_DROP` + `evalToExpectedScore` (`@/lib/liveFlaw` / `@/generated/flawThresholds`) | Already the canonical, generated-from-Python thresholds used everywhere else in the app |
| Bot's own best-move UCI comparison for anchor moves | Reimplementing argmax selection | `maiaArgmaxMove` (`calibration-anchors.mjs`) — already deterministic UCI-ascending-tiebreak argmax | Exact function this phase's "Maia-agreement rate" metric needs to call for comparison, not reimplement |

**Key insight:** every primitive this phase needs (band-gating, Elo inversion, Wilson CI,
Bradley-Terry MLE, move-severity classification, argmax selection) already exists in this codebase
from Phases 168/168.5/173/163. The actual net-new code is thin: an `internalRatingFor` swap, a
DEFAULT_ANCHOR_TOKENS restriction, a bot-cell-specific locate/bracket module (which itself mostly
composes the above), and a `fit_bot_cell()` Python function that reuses `fit_bradley_terry`'s
math with the free-parameter count reduced from 10 to 1.

## Common Pitfalls

### Pitfall 1: including an unmeasured anchor token silently degrades to nominal windowing
**What goes wrong:** If `internalRatingFor` (or the anchor-token restriction) is implemented as a
fallback (`INTERNAL_RATING[label] ?? anchorRatingFor(spec)`) rather than a fail-loud throw, a
mistakenly-included extra Maia rung (e.g. `maia1300`, present in the OLD `DEFAULT_ANCHOR_TOKENS`
but never measured by Phase 173) silently reintroduces the exact nominal-scale bug this phase
exists to fix, for that one anchor only — hard to notice in a 15-cell × 4-anchor sweep.
**Why it happens:** A "helpful" fallback feels safer than a throw, but it reintroduces the bug
invisibly instead of loudly.
**How to avoid:** `internalRatingFor` MUST throw (WR-02 discipline, matching every other guard in
this file) on a missing key — never fall back to `anchorRatingFor`.
**Warning signs:** A cell's row shows an anchor windowed/played that isn't one of the 10 Phase-173
labels.

### Pitfall 2: style-outlier anchors (`sf0`, `maia700`) skew a cell's bracket
**What goes wrong:** Per 2026-07-15 Finding 4, `sf0` and `maia700` both show large cross-family
residuals (every Maia rung underperforms its predicted score against `sf0`; `maia700` lost all 8
probe games to `sf3`, residual −0.206). A bot cell whose bracket leans heavily on either of these
two anchors inherits that style noise, not just wider CI.
**Why it happens:** They sit at the bottom of the ladder (weakest available in each family), so any
LOW `bot_elo` cell's bracket naturally includes them.
**How to avoid:** Flag any bot-cell row whose bracket includes `sf0` or `maia700` (mirrors the
skip_reason column pattern already in the TSV) so the findings note (the operator-run HUMAN-UAT
step) reads those cells with the Finding-4 caveat explicitly, per SEED-102's own caveat text.
**Warning signs:** A cell's fitted rating disagrees materially between its vs-Maia and vs-SF
sub-fits in a way that doesn't match the expected `G_preset ≈ 0` for Human.

### Pitfall 3: non-transitivity means `G_preset` is a real signal, not noise to average away
**What goes wrong:** Treating `rating_vs_Maia` and `rating_vs_SF` as two noisy estimates of "the
same true rating" and averaging them (as `combineAnchorEstimates`/the old D-05 advisory summary
does) throws away exactly the signal this phase exists to measure. `G_preset` MUST be reported per
preset as its own first-class number, not folded into a single "best estimate."
**Why it happens:** The existing advisory-summary code path (`emitEloSummary`) is the natural thing
to reach for, but it was built for a single-scalar-strength worldview (pre-Finding-4).
**How to avoid:** D-06's fit MUST run two independent single-parameter fits (vs-Maia-only rows,
vs-SF-only rows) per bot cell, never one combined fit. The bot-curves JSON output needs separate
`rating_vs_maia`/`rating_vs_sf` fields, not a single averaged `rating`.
**Warning signs:** The output JSON has only one rating number per cell.

### Pitfall 4: "Deep is a ceiling, not deeper" — don't misread the top cell's inflated rating
**What goes wrong:** Deep's highest `bot_elo` cell (2300 or 2600 nominal) is likely to measure an
internal rating ABOVE `sf10` (1907.93, the ladder's own ceiling) — extrapolation, wide/asymmetric
CI, bracket possibly all-below-no-anchor-above. Reading this as "Deep genuinely reaches near-2600
internal strength with tight confidence" overstates the measurement; reading it as "the same MCTS
depth as Light, just less noisy sampling, bumping into the top of what this specific anchor pool
can resolve" is the correct interpretation (per SEED-102's own explicit framing: "Deep is a
ceiling, not a different feel").
**Why it happens:** The anchor pool's ceiling (`sf10`) is fixed by Phase 173's own 10-anchor
choice; nothing in THIS phase re-measures a stronger anchor.
**How to avoid:** Flag any bot cell whose locate estimate exceeds `sf10`'s internal rating (or sits
below `sf0`'s) as `beyond_ladder=true` in the output, and have the findings note explicitly caveat
those cells' CIs as one-sided/extrapolated.
**Warning signs:** A cell's bracket has 0 anchors above (or below) it.

### Pitfall 5: `--resume` grid-order-prefix integrity under a NEW two-pass schedule
**What goes wrong:** The existing `--resume` contract (`loadPriorSweep`, `cellKey`) assumes each
grid cell is played via a SINGLE flat loop with a deterministic `gameIndex` fast-forward. If the
two-pass locate→measure adaptation changes how many games a cell consumes BEFORE its bracket is
even known (locate games vs measure games), a naive resume could either replay locate games
(breaking D-09 seeded determinism) or mis-count `gameIndex`, corrupting every subsequent cell's
opening/color/seed assignment for the REST of the sweep — this exact landmine already forced Phase
173's `calibration-anchor-ladder.mjs` to build pair-keyed resume logic distinct from the bot
harness's cell-keyed resume logic (see that file's own header comment, "the resumable unit is ONE
(anchor_a, anchor_b) pair's played games so far, NOT a bot harness fixed grid cell").
**Why it happens:** Two-pass locate makes a cell's total game count variable (bracket size differs
per cell), unlike the current fixed `--games-per-cell` assumption baked into `loadPriorSweep`'s
validation (`row.games !== args.gamesPerCell` throws).
**How to avoid:** Either (a) resume at the LOCATE-PASS granularity (mirroring
`calibration-anchor-ladder.mjs`'s per-pair resume, replaying the raw ledger rather than trusting
a fixed per-cell game count), or (b) keep the harness's existing cell-keyed resume model but make
the validated "expected games" a function of the cell's OWN discovered bracket size rather than a
single global `args.gamesPerCell` constant. This is a genuine open design fork — flagged in Open
Questions below, not resolved here.
**Warning signs:** `loadPriorSweep`'s `row.games !== args.gamesPerCell` guard throws on a
perfectly valid resume of a two-pass sweep, because different cells legitimately consumed
different total game counts.

### Pitfall 6: recurrence of the 2026-07-12 "any_clamped=true on every cell" failure mode
**What goes wrong:** All 9 cells in the 2026-07-12 run reported `any_clamped=true` — meaning every
combined ELO estimate was a bound, not a real measurement, because the informative stronger anchor
was pruned by the (nominal-axis) window.
**Why it happens:** Root cause is Pitfall 1/the core bug this phase fixes — but it's worth an
explicit acceptance test: after the fix, a real-engine pilot cell should NOT report
`any_clamped=true` for a well-chosen `bot_elo` point (one whose true internal rating sits inside
the 1069–1908 anchor range).
**How to avoid:** The D-02(b) real-engine pilot's "sane ratings" acceptance criterion should
explicitly check `any_clamped=false` (or the cell's win rate against its bracket sits in
[0.2, 0.8], not 0/1) as a regression guard against this exact prior failure.
**Warning signs:** `any_clamped=true` reappearing in the pilot's summary TSV.

## Code Examples

### `fit_bot_cell()` extension shape for `calibration_anchor_fit.py` (D-06)

```python
# Source: adapted from scripts/calibration_anchor_fit.py's existing fit_bradley_terry
# (Zermelo/MM iteration), specialized to ONE free parameter (the bot cell) against
# N FIXED opponents (the 10 Phase-173 anchors, held at their measured INTERNAL_RATING).
def fit_bot_cell_rating(
    win_counts_vs_fixed: dict[str, float],   # {anchor_label: bot's wins vs that anchor}
    games_vs_fixed: dict[str, float],        # {anchor_label: games played vs that anchor}
    fixed_ratings: dict[str, float],         # INTERNAL_RATING, held constant
    tol: float = DEFAULT_FIT_TOL,
    max_iter: int = DEFAULT_FIT_MAX_ITER,
) -> float:
    """Single-parameter MLE: iterate the bot's own strength only, anchors fixed.
    Same continuity-correction discipline as _clamp_win_counts (Pitfall 4 —
    a swept bracket must not blow up to +/-infinity)."""
    strength = 1.0  # neutral init, same convention as fit_bradley_terry
    for _ in range(max_iter):
        denom = sum(
            games_vs_fixed[a] / (strength + 10 ** (fixed_ratings[a] / RATING_SCALE))
            for a in games_vs_fixed
            if games_vs_fixed[a] > 0
        )
        total_wins = sum(win_counts_vs_fixed.values())
        new_strength = total_wins / denom if denom > 0 else strength
        if abs(new_strength - strength) / strength < tol:
            strength = new_strength
            break
        strength = new_strength
    return RATING_SCALE * math.log10(strength)
```

### `G_preset` computation per cell (D-06)

```python
# Source: this phase's extension — two independent fit_bot_cell_rating() calls,
# one per anchor family, holding the SAME 10-anchor INTERNAL_RATING fixed.
rating_vs_maia = fit_bot_cell_rating(wins_vs_maia, games_vs_maia, INTERNAL_RATING)
rating_vs_sf = fit_bot_cell_rating(wins_vs_sf, games_vs_sf, INTERNAL_RATING)
g_preset_cell = rating_vs_maia - rating_vs_sf
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Window/order/combine anchors by nominal `bot_elo`-vs-`anchorRatingFor` (nominal Elo) | Window/order/combine by `INTERNAL_RATING` (measured internal scale) | This phase (fixes the 2026-07-12 bug) | Every cell in the 2026-07-12 run reported `any_clamped=true`; the fix should make most well-chosen cells report a real (non-clamped) estimate |
| Single flat static-window + dynamic-cutoff traversal per cell (D-15, Phase 168.5) | Two-pass locate (rough placement) → measure (bracketed by 3-4 nearest, cross-family-forced) per cell | This phase (D-07) | More targeted anchor selection per cell; static window mechanism's continued role after this change is an open question (see below) |
| Single combined per-cell advisory ELO estimate (`combineAnchorEstimates`, weighted mean of independent inversions) | Two independent pinned-anchor MLE fits per cell (`rating_vs_maia`, `rating_vs_sf`) | This phase (D-06) | `G_preset` becomes a first-class measured output instead of averaged away |
| Maia anchors only (`maiaNNNN` in every 2026-07-12 TSV row) | Both anchor families (Maia argmax rungs + Stockfish Skill Levels) | This phase (in-scope item 3) | Cross-family split becomes measurable at all — was structurally impossible before |

**Deprecated/outdated:**
- `ANCHOR_ELO_WINDOW = 400` measured on the nominal axis: its numeric value (400) may or may not
  still be the right window WIDTH once re-based on `INTERNAL_RATING` — worth a planner decision
  (the internal scale's own spread is narrower: the whole 10-anchor pool only spans ~840 internal
  points, 1069–1908, vs the nominal pool's likely much wider span).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Human's 5 `bot_elo` points should be exactly the 5 measured Maia rungs (700/1100/1500/1900/2300) | Q1 grid recommendation | If Human's true ceiling (sampling, not argmax) differs enough from the argmax anchors' internal rating, the top point may under- or over-shoot SEED-104's expected ~1900-2000 ceiling; low risk since the two-pass locate step self-corrects the BRACKET even if the raw `bot_elo` choice isn't perfectly centered |
| A2 | Light's 5 points {1100,1300,1500,1700,1900} and Deep's 5 points {1100,1500,1900,2300,2600} are reasonable D-03-compliant choices | Q1 grid recommendation | blend=0.05/0.5 have NEVER been measured post-fix (only the OLD clamped 0/0.5/1 run exists, and even that run's blend-0.5 numbers are lower-bound-only per Finding 3) — the actual internal-rating landing zone for these `bot_elo` values is genuinely unknown until the locate pass runs; if wildly off, some cells may land entirely outside the anchor ladder (Pitfall 4), costing precision but not correctness (the two-pass schedule surfaces this rather than silently producing a bad number) |
| A3 | No new raw per-game ledger is needed for D-06's bootstrap CI — the existing aggregated WDL-count TSV is statistically sufficient because the 10 anchors are held FIXED (not being jointly refit) | Q5 fit design | If a reviewer wants CI parity with Phase 173's exact game-level bootstrap method (not just the same asymptotic properties), a raw ledger addition would be required — this is a genuine methodological simplification, flagged explicitly as an Open Question below |
| A4 | Anchor rating uncertainty (their own Phase-173 bootstrap CI) is NOT propagated into the bot-cell CI — anchors are treated as exactly fixed at their point estimate | Q5 fit design | Understates the bot cell's TRUE combined uncertainty somewhat (a two-stage bootstrap that also resamples anchor ratings within their own CI would be more rigorous); D-06's literal wording ("hold the 10 anchors fixed") supports this simplification |
| A5 | `internalRatingFor` should throw (fail loud) rather than fall back to nominal rating for an unmeasured anchor token | Pattern 1 / Pitfall 1 | If wrong (i.e. a fallback is actually desired for forward-compat with future anchor additions), the throw would need loosening — but a silent fallback reintroduces exactly the bug this phase fixes, so failing loud is the safer default absent contrary guidance |
| A6 | `ANCHOR_ELO_WINDOW`'s role is superseded by the two-pass bracket-selection logic for bot cells (not run in parallel with it) | Open Questions | If the planner instead wants both mechanisms layered (static window AS a pre-filter before locate/bracket), the numeric window value (400) needs re-basing to the internal scale's narrower spread (~840 total) rather than reused verbatim |

**If this table is empty:** N/A — six assumptions logged above, all flagged.

## Open Questions

1. **Does the two-pass locate/bracket mechanism REPLACE the existing static-window +
   dynamic-cutoff (D-15) traversal, or run alongside it?**
   - What we know: CONTEXT.md lists "internal-scale windowing" and "locate-then-measure two-pass"
     as two SEPARATE in-scope fixes, suggesting iterative layering onto the existing mechanism
     rather than a wholesale replacement. But the existing D-15 mechanism was designed for a flat,
     single-pass grid sweep with NO prior placement estimate — once a locate pass exists, the
     static window's job (pruning obviously-uninformative anchors before playing them) is largely
     redundant with the bracket-selection step.
   - What's unclear: whether `ANCHOR_ELO_WINDOW`/`partitionAnchorsByWindow`/
     `orderAnchorsForDynamicCutoff` survive as a first-pass filter feeding INTO the locate step, or
     get superseded entirely by a fresh bot-cell-schedule module (mirroring how
     `calibration-anchor-ladder.mjs` became a wholly separate script from
     `calibration-harness.mjs` rather than a mode flag on it, in Phase 173).
   - Recommendation: supersede — write the locate/bracket logic as the sole cell-level anchor
     selection mechanism for the two-pass path, and treat `ANCHOR_ELO_WINDOW`/D-15 as retired for
     this run (their job is now done by the bracket-size parameter). Keep the D-15 code in place
     (do not delete — other future non-two-pass uses of the harness might still want it), simply
     don't wire it into this phase's cell loop.

2. **`--resume` semantics under variable-length two-pass cells (Pitfall 5).**
   - What we know: the existing cell-keyed resume validates a FIXED `--games-per-cell` per row;
     Phase 173's anchor-ladder script instead resumes at raw-ledger granularity because pair
     progress is inherently variable-length under its own two-pass schedule.
   - What's unclear: whether Phase 180's bot-cell resume should follow the anchor-ladder's
     raw-ledger-replay pattern (more code, more faithful) or extend the existing cell-keyed model
     with a per-cell "expected games" computed from that cell's own discovered bracket size
     (less code, more surgical).
   - Recommendation: raw-ledger-replay (mirror `calibration-anchor-ladder.mjs`'s approach) — it's
     already a proven pattern in this exact codebase, and the bot-cell schedule is structurally
     closer to the anchor-ladder's variable-pair-progress model than to the old fixed-grid model.

3. **Should the operator-run full sweep's fit re-run per preset with `G_preset` as one scalar per
   preset, or does the shipped constant come from averaging per-cell `G_preset` values?**
   - What we know: SEED-104 wants ONE `G_preset` number per preset for the shipping offset formula
     (`human_blitz = internal_rating − G_preset + C`).
   - What's unclear: whether that scalar is a simple/weighted mean of the preset's 5 cells'
     per-cell `G_preset` values, or something else (e.g. median, or a fit-once-across-all-cells
     joint estimate).
   - Recommendation: report BOTH — per-cell `G_preset` (diagnostic, validates the "single style-
     inflation gap" assumption is roughly cell-invariant) AND a combined per-preset scalar
     (inverse-CI-weighted mean, same weighting convention as `combineAnchorEstimates`) as the
     final artifact field SEED-104 consumes. This is a fit-script design decision, not a blocker
     for this phase's own harness-fix scope.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | `.mjs` harness scripts | ✓ (existing project requirement) | project-pinned | — |
| Python 3.13 + uv | `calibration_anchor_fit.py` | ✓ (CLAUDE.md-documented stack) | 3.13 | — |
| Stockfish engine binary/pool | anchor moves, grading, adjudication | ✓ (already used by `stockfish-pool.mjs`, proven in Phase 168/173) | existing pinned build | — |
| ONNX Maia model + onnxruntime-node | policy calls, Maia-agreement metric | ✓ (already used, `createMaiaSession`, proven in Phase 168/173/174) | existing pinned | — |
| `scripts/lib/frontend-alias-hook.mjs` | running `.check.mjs`/scripts with `@/` aliasing | ✓ (existing project tooling) | — | — |

No new external dependency is introduced. All engine/runtime dependencies were already proven
working end-to-end by Phase 173's real multi-hour anchor-ladder sweep (2026-07-15), which used the
identical bring-up path (`setupHarnessEngines`) this phase reuses unchanged.

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (Node side) | Node built-in `node:assert/strict`, standalone `.check.mjs` scripts (project convention, NOT vitest — mirrors Phase 173's own `173-VALIDATION.md`) |
| Framework (Python side) | pytest (existing convention; `tests/scripts/test_calibration_anchor_fit.py` already exists as the precedent) |
| Config file | none for `.check.mjs` (run via `node --import ./scripts/lib/frontend-alias-hook.mjs <file>`); pytest config in `pyproject.toml` |
| Quick run command | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-bot-cell-schedule.check.mjs` (new) / `uv run pytest tests/scripts/test_calibration_anchor_fit.py -x` |
| Full suite command | `uv run pytest -n auto` (backend, includes the fit extension tests) + run each new/touched `.check.mjs` once |
| Estimated runtime | Unit checks ~seconds each; the D-01 full operator sweep is multi-hour, manual-only, explicitly OUT of this phase's interactive critical path |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-04 (internal-scale windowing fix) | `internalRatingFor` matches `INTERNAL_RATING`, throws on unmeasured token | unit | `node --import ./scripts/lib/frontend-alias-hook.mjs -e "import('./scripts/calibration-harness.mjs').then(m=>{...assert internalRatingFor throws on maia1300...})"` | ❌ Wave 0 (new assertion) |
| D-07 (two-pass bracket selection) | `pickLocateAnchors`/`selectMeasureBracket` produce correct widely-spaced-then-bracketed selections on canned fixtures, cross-family-forced | unit | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-bot-cell-schedule.check.mjs` | ❌ Wave 0 (new file) |
| D-06 (pinned-anchor fit) | `fit_bot_cell_rating` converges to a known synthetic ground truth; `G_preset` sign/magnitude sane on a fabricated Human/Light/Deep fixture | unit (TDD, RED-first per 173-03's precedent) | `uv run pytest tests/scripts/test_calibration_anchor_fit.py -k bot_cell -x` | ❌ Wave 0 (new test) |
| D-02(b) (real-engine pilot) | 1-2 real cells at low N: sane (non-clamped) score, correct anchors selected (both families present), `--resume` byte-identical continuation | manual (`checkpoint:human-verify`, mirrors 173-04's Task 1 pattern) | see Manual-Only Verifications | N/A (produced by the pilot run) |
| Near-free metrics (draw rate, game length, ACPL, blunder rate, SF-agreement, Maia-agreement) | Metric columns populate correctly on a fabricated fixed-eval-sequence provider | unit | new `.check.mjs` covering the `onPly` extension, fabricated eval/policy providers (mirrors `calibration-parity.check.mjs`'s stub-provider style) | ❌ Wave 0 (new check) |

### Sampling Rate
- **Per task commit:** the relevant `.check.mjs` / `pytest -k <keyword>` for the piece just built.
- **Per wave merge:** `uv run pytest -n auto` (Python side) + every new/touched `.check.mjs` once.
- **Phase gate:** all `.check.mjs` + `test_calibration_anchor_fit.py` green, THEN the D-02(b)
  real-engine pilot checkpoint (small N, minutes not hours) — the full 1,440-game/18-22h sweep is
  explicitly NOT part of this phase's gate (D-01), it is the separate operator-run HUMAN-UAT step.

### Wave 0 Gaps
- [ ] `scripts/lib/calibration-bot-cell-schedule.mjs` + `.check.mjs` — locate/bracket pure logic, D-07
- [ ] `internalRatingFor` assertion coverage (throw-on-missing + correct-lookup) — could live in a
      new small `.check.mjs` or as an addition to an existing harness-adjacent check
- [ ] `tests/scripts/test_calibration_anchor_fit.py` extension (or sibling file) for `fit_bot_cell_rating`,
      including a synthetic ground-truth fixture (mirrors 173-03's RED-first pattern exactly)
- [ ] A near-free-metrics `.check.mjs` with fabricated eval/policy providers (no real engines)

*(Phase 173's precedent for all four of the above already exists in this exact codebase — this is
extension of a proven pattern, not new tooling invention.)*

## Security Domain

This phase has no user-facing, network-facing, or persisted-data surface — it is a local CLI tool
operating on the developer's own machine, spawning local Stockfish/ONNX subprocesses, writing to
`reports/data/` and committing generated `.mjs`/`.json`/`.py` files. The standard ASVS categories
(authentication, session management, access control, cryptography) do not apply; this mirrors
Phase 173's own threat register, which used a lightweight local-run STRIDE table instead of a full
ASVS pass.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — no auth surface, local CLI only |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes (narrow) | CLI flag parsing already fail-loud (`requireFlagValue`, `parsePositiveIntFlag`, etc.) — extend the same discipline to any new flags |
| V6 Cryptography | no | N/A — no secrets, no crypto |

### Known Threat Patterns for this stack (mirrors 173's STRIDE table)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Fit runs on a corrupted/mis-keyed TSV → meaningless published bot-curves artifact consumed downstream by SEED-104 | Tampering | Same discipline as Phase 173's `check_connectivity` fail-loud guard: `fit_bot_cell_rating` should validate its inputs (non-empty games, fixed_ratings covers every referenced anchor label) before fitting, throwing rather than silently producing NaN/garbage |
| Internal-scale bot-curves artifact mis-consumed downstream as human ELO | Information Disclosure | Carry the D-13 "INTERNAL SCALE — NOT human ELO" caveat verbatim into every new artifact (JSON header, module docstring, findings note) — same pattern already established |
| A killed multi-hour operator sweep loses all progress | Denial of Service | `--resume` from a durable ledger, resolved per Open Question 2 above |
| npm/pip supply chain | Tampering | N/A — zero new packages this phase |

## Sources

### Primary (HIGH confidence — direct repo reads)
- `scripts/calibration-harness.mjs` — full read, confirmed exact windowing/ordering/combining call
  sites and TSV schema
- `scripts/lib/calibration-anchor-schedule.mjs` + `.check.mjs` — full read, confirmed reusable vs
  non-reusable primitives
- `scripts/calibration-anchor-ladder.mjs` — full read, the Phase 173 two-pass orchestrator this
  phase's D-07 adaptation is modeled on
- `scripts/calibration_anchor_fit.py` — full read, confirmed fit/bootstrap/output-shape mechanics
- `scripts/lib/calibration-elo.mjs`, `calibration-anchors.mjs`, `calibration-game-loop.mjs`,
  `calibration-providers.mjs` — full reads, confirmed reusable primitives and near-free-metric hook
  points (`onPly`, `pool.evalPosition`, adjudication `bestmove` byproduct)
- `scripts/lib/calibration-internal-scale.mjs`, `reports/data/anchor-ladder-internal-scale.json` —
  the measured 10-anchor ratings + CIs + residuals used for the Q1 grid recommendation and Q4 SE
  arithmetic
- `.planning/notes/2026-07-15-anchor-ladder-self-calibration-findings.md`,
  `.planning/notes/2026-07-13-bot-calibration-findings.md` — the compression verdict, Finding 4
  cross-family residuals, the 2026-07-12 clamped-run root cause
- `.planning/milestones/v2.3-phases/173-anchor-ladder-self-calibration-seed-101/173-04-PLAN.md`,
  `173-VALIDATION.md` — the pilot/checkpoint pattern this phase's Validation Architecture mirrors
- `frontend/src/lib/maiaEncoding.ts` — `MAIA_ELO_LADDER` bounds/step, the 1100-2000 validated band
- `frontend/src/lib/liveFlaw.ts` — the reusable blunder/mistake/inaccuracy classification for the
  ACPL/blunder-rate near-free metric

### Secondary (MEDIUM confidence)
- `.planning/seeds/SEED-102-iso-strength-surface-sweep.md`, `SEED-104-iso-strength-inversion-table.md`
  — the run spec and downstream consumer, both authoritative for scope but the SE-arithmetic/budget
  numbers in SEED-102 are themselves estimates carried forward from the 2026-07-13 note

### Tertiary (LOW confidence — flagged [ASSUMED] in the Assumptions Log)
- The specific `bot_elo` point-value recommendations for Light/Deep (Q1) — no measurement of
  blend=0.05 exists anywhere in this codebase yet; these are reasoned proposals from spacing +
  D-03's shape requirement, not measured facts

## Metadata

**Confidence breakdown:**
- Standard stack / architecture / patterns: HIGH — every function/file/line cited was read
  directly from the current repo state, not inferred
- Grid point recommendations (D-04, Q1): MEDIUM — well-justified for Human (exact anchor-rung
  alignment), reasoned-but-unmeasured for Light/Deep (blend=0.05 is genuinely new)
- Games/cell precision (D-05, Q4): HIGH — the SE arithmetic reproduces the exact numbers already
  stated in CONTEXT.md/SEED-102, cross-checked algebraically
- Fit extension design (D-06, Q5): MEDIUM-HIGH — the single-parameter MLE is a straightforward
  specialization of the already-proven `fit_bradley_terry`, but the "no raw ledger needed"
  simplification (A3/A4) is a genuine methodological judgment call flagged for planner sign-off
- Two-pass adaptation (D-07, Q3): MEDIUM — the reusable-vs-non-reusable primitive split is HIGH
  confidence (read directly from code), but the exact bracket-selection algorithm is this
  research's own proposal, not something already built and tested elsewhere

**Research date:** 2026-07-19
**Valid until:** 30 days (stable in-repo tooling; would go stale if Phase 173's anchor set is ever
re-measured or expanded before this phase executes)
