#!/usr/bin/env node
/**
 * calibration-bot-cell-schedule.mjs — pure-logic, engine-free two-pass
 * scheduler for a hub-and-spoke bot CELL (Phase 180, Plan 01, D-07). No
 * engines, no I/O — every function is a deterministic transform over anchor
 * specs + pre-computed probe/locate scores, unit-testable independent of any
 * real engine run (see `calibration-bot-cell-schedule.check.mjs`).
 *
 * WHY THIS MODULE EXISTS (the 2026-07-12 clamped-run incident, D-07):
 * the Phase-173 anchor-graph scheduler selected and ordered anchors by their
 * NOMINAL bot_elo (`anchorRatingFor`, the folklore SF Skill-Level→Elo table),
 * NOT by the MEASURED internal-scale rating. For a bot cell whose true
 * strength was known only approximately, this pulled the wrong bracket of
 * anchors and let the advisory Elo inversion clamp against mis-rated
 * opponents — producing a silently biased cell rating. This module replaces
 * that logic for bot cells: it selects and orders anchors strictly on the
 * MEASURED `INTERNAL_RATING` scale, and fails loud on any anchor token that
 * was never measured (see `internalRatingFor` below).
 *
 * WHAT DOES NOT PORT FROM calibration-anchor-schedule.mjs, AND WHY:
 * `checkConnectivity`, `buildCandidateGraph`, and `rescueConnectivity` are
 * graph-connectivity primitives that guarantee anchor-vs-anchor
 * identifiability across a game GRAPH (every anchor's rating defined relative
 * to the others via a connected, cross-family-linked edge set). A bot cell is
 * NOT a graph node — it is a single hub measured against a spoke of fixed,
 * already-rated anchors. There is no anchor-vs-anchor edge to keep connected
 * here; the fixed `INTERNAL_RATING` anchors are the coordinate frame. Only the
 * topology-agnostic primitives port: `scoreInInformativeBand` and
 * `bandDistance` (D-01's information gate), imported verbatim below — the
 * D-07 reuse boundary.
 */
import { INTERNAL_RATING } from './calibration-internal-scale.mjs';
import { scoreInInformativeBand, bandDistance } from './calibration-anchor-schedule.mjs';
import { combineAnchorEstimates } from './calibration-elo.mjs';

// ─── Named constants (no magic numbers, CLAUDE.md) ─────────────────────────

/** Games played against each of the two widely-spaced locate anchors (locate pass). */
export const LOCATE_PASS_GAMES = 8;

/** Number of anchors in the measure-pass bracket (nearest-to-estimate, cross-family-floored). */
export const DEFAULT_BRACKET_SIZE = 4;

/** Minimum surviving anchors per family (Maia / SF) in a measure bracket, where the ladder allows (D-07 cross-family). */
export const MIN_BRACKET_PER_FAMILY = 2;

// ─── Internal-scale accessor (fail-loud, the bug this phase fixes) ─────────

function isMaiaSpec(anchorSpec) {
  return anchorSpec.kind === 'maia';
}

/**
 * MEASURED internal-scale rating for an anchor spec — the ONLY rating source a
 * bot-cell schedule may use. Looks up `INTERNAL_RATING` by `anchorSpec.label`
 * and THROWS (fail-loud, WR-02) on any label not among the 10 Phase-173
 * measured anchors (maia700/1100/1500/1900/2300, sf0/3/5/8/10).
 *
 * BUG-FIX (2026-07-12 clamped-run incident, D-07): the predecessor selected
 * anchors on the NOMINAL `anchorRatingFor` scale (folklore SF Skill→Elo),
 * which mis-rated the bracket and biased the cell fit. We NEVER fall back to
 * `anchorRatingFor` here (Pitfall 1) — a silent nominal-scale fallback would
 * reintroduce the exact bug. An unmeasured token is a programming error in the
 * anchor set, not a value to guess, so we throw rather than degrade.
 */
export function internalRatingFor(anchorSpec) {
  const rating = INTERNAL_RATING[anchorSpec.label];
  if (rating === undefined) {
    throw new Error(
      `internalRatingFor: no measured INTERNAL_RATING for ${anchorSpec.label} — ` +
        'only the 10 Phase-173 anchors (maia700/1100/1500/1900/2300, sf0/3/5/8/10) are usable',
    );
  }
  return rating;
}

// ─── Locate pass: two widely-spaced anchors → rough estimate ───────────────

/**
 * The two locate-pass anchors: the weakest and strongest available anchors by
 * MEASURED internal rating (not nominal bot_elo). Widely-spaced endpoints
 * bracket the cell's likely strength cheaply before the fuller measure pass.
 */
export function pickLocateAnchors(anchorSpecs) {
  const sorted = [...anchorSpecs].sort((a, b) => internalRatingFor(a) - internalRatingFor(b));
  return [sorted[0], sorted[sorted.length - 1]];
}

/** Locate results sorted by closeness to the informative band (least-lopsided first). */
function nearestToBandFirst(withRating) {
  return [...withRating].sort((a, b) => bandDistance(a.score) - bandDistance(b.score));
}

/**
 * Rough internal-rating estimate from the locate pass. `locateResults` is
 * `[{ anchorSpec, score, games }, ...]`. Delegates the actual inversion +
 * combination to `combineAnchorEstimates` (which already applies the Pitfall-4
 * small-sample clamp and Wilson-CI inverse-variance weighting) — never a
 * hand-rolled inversion.
 *
 * D-01 reuse: prefer locate anchors whose score sits in the informative
 * [0.2, 0.8] band — those pin the estimate tightly. If NEITHER widely-spaced
 * locate anchor landed in band (the cell crushed / was crushed by both — a
 * likely ladder-edge cell), fall back to the SINGLE locate result nearest the
 * band; the other is even more lopsided and its clamp-inflated inversion would
 * only drag the estimate. Warn-and-proceed, never throw (Pitfall 4).
 */
export function locateEstimate(locateResults) {
  const withRating = locateResults.map(({ anchorSpec, score, games }) => ({
    score,
    games,
    anchorRating: internalRatingFor(anchorSpec),
  }));
  const informative = withRating.filter(({ score }) => scoreInInformativeBand(score));
  const basis = informative.length > 0 ? informative : nearestToBandFirst(withRating).slice(0, 1);
  return combineAnchorEstimates(basis);
}

// ─── Measure pass: nearest-to-estimate bracket with a cross-family floor ────

/** Count of anchors in `specs` belonging to the requested family (Maia when `wantMaia`, else SF). */
function familyCount(specs, wantMaia) {
  return specs.filter((spec) => isMaiaSpec(spec) === wantMaia).length;
}

/** Index of the over-represented other-family member farthest from `estimate` (the swap-out victim), or -1. */
function farthestOtherFamilyIndex(specs, wantMaia, estimate) {
  let victimIndex = -1;
  let maxDistance = -Infinity;
  for (let i = 0; i < specs.length; i++) {
    const spec = specs[i];
    if (isMaiaSpec(spec) === wantMaia) continue; // only evict the OTHER, over-represented family
    const distance = Math.abs(internalRatingFor(spec) - estimate);
    if (distance > maxDistance) {
      maxDistance = distance;
      victimIndex = i;
    }
  }
  return victimIndex;
}

/**
 * Ensures at least `MIN_BRACKET_PER_FAMILY` members of `wantMaia`'s family
 * survive, swapping in the next-nearest anchors of that family (evicting the
 * farthest member of the over-represented family) where the ladder can supply
 * them. Mirrors calibration-anchor-schedule.mjs's `initialCrossFamilyPairs`
 * cross-family intent, applied per-cell.
 */
function ensureFamilyMinimum(bracket, byDistanceAll, wantMaia, estimate) {
  const shortfall = MIN_BRACKET_PER_FAMILY - familyCount(bracket, wantMaia);
  if (shortfall <= 0) return bracket;
  const inBracket = new Set(bracket.map((spec) => spec.label));
  const additions = byDistanceAll
    .filter((spec) => isMaiaSpec(spec) === wantMaia && !inBracket.has(spec.label))
    .slice(0, shortfall); // "where the ladder allows" — may be short if the family is exhausted
  const result = [...bracket];
  for (const addition of additions) {
    const victimIndex = farthestOtherFamilyIndex(result, wantMaia, estimate);
    if (victimIndex === -1) result.push(addition);
    else result[victimIndex] = addition;
  }
  return result;
}

/**
 * Measure-pass bracket: the `bracketSize` anchors nearest the locate `estimate`
 * on the MEASURED internal scale, then adjusted so at least
 * `MIN_BRACKET_PER_FAMILY` Maia AND `MIN_BRACKET_PER_FAMILY` SF survive where
 * the ladder makes that possible (a single-family bracket cannot cross-check
 * the two families' scales against each other — D-07). Pure: no engine, no I/O.
 */
export function selectMeasureBracket(anchorSpecs, estimate, bracketSize = DEFAULT_BRACKET_SIZE) {
  const byDistance = [...anchorSpecs].sort(
    (a, b) => Math.abs(internalRatingFor(a) - estimate) - Math.abs(internalRatingFor(b) - estimate),
  );
  let bracket = byDistance.slice(0, bracketSize);
  bracket = ensureFamilyMinimum(bracket, byDistance, true, estimate); // Maia floor
  bracket = ensureFamilyMinimum(bracket, byDistance, false, estimate); // SF floor
  return bracket;
}

/**
 * True when the cell sits PAST a ladder edge: the bracket has zero anchors
 * rated above the estimate (cell above the sf10=1907.93 ceiling) OR zero below
 * it (cell below the sf0=1069.33 floor). Warn-and-proceed flag — the caller
 * still measures the cell against the nearest available anchors and records a
 * `beyond_ladder` marker; it NEVER throws (Pitfall 4: an extreme-but-real
 * measurement is not a fatal condition).
 */
export function bracketBeyondLadder(estimate, bracketSpecs) {
  const ratings = bracketSpecs.map(internalRatingFor);
  const anyAbove = ratings.some((rating) => rating > estimate);
  const anyBelow = ratings.some((rating) => rating < estimate);
  return !anyAbove || !anyBelow;
}
