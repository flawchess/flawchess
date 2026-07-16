#!/usr/bin/env node
/**
 * calibration-anchor-schedule.mjs — pure-logic probe→measure scheduler +
 * connectivity guard (Phase 173, Plan 02, D-01/D-02/D-04). No engines, no
 * I/O — every function here is a deterministic transform over anchor labels
 * and pre-computed probe scores, unit-testable independent of any real
 * engine run (see `calibration-anchor-schedule.check.mjs`).
 *
 * D-01: play the full measure-pass games budget ONLY on pairs whose
 * probe-predicted score sits in the informative [0.2, 0.8] band — a
 * 0.95-expected-score pair carries no information (SEED-101's binding
 * directive: maximize information per game). `scoreInInformativeBand` is the
 * single gate both the probe→measure decision (`selectMeasurePairs`) and any
 * caller-side re-targeting logic must use.
 *
 * D-02: the base candidate graph is NOT a full round-robin — adjacent Maia
 * rungs, adjacent Stockfish skills, plus a handful of cross-family
 * candidates seeded from the folklore `SF_SKILL_ELO` table (Pitfall 3,
 * 173-RESEARCH.md: folklore is used ONLY to pick which Maia rung to probe a
 * given Stockfish skill against first — never as a fit input; the joint
 * Bradley-Terry fit derives every anchor's real rating from played games).
 *
 * D-04: after any pruning, the played graph MUST stay connected AND the
 * Maia/Stockfish subgraphs MUST be joined by at least
 * `MIN_CROSS_FAMILY_EDGES` informative cross-family links — otherwise the
 * two families' ratings are only defined relative to each other WITHIN each
 * family, and the combined scale is meaningless (173-RESEARCH.md Pitfall 1:
 * non-identifiability from a disconnected game graph). `checkConnectivity`
 * throws (fail loud) rather than let a disconnected/under-cross-linked graph
 * silently proceed to the measure pass.
 */
import { anchorRatingFor } from './calibration-anchors.mjs';

// ─── D-01: the informative-band gate ───────────────────────────────────────

/** Lower bound of the "carries information" probe-score band (D-01). */
export const INFORMATIVE_BAND_LOW = 0.2;
/** Upper bound of the "carries information" probe-score band (D-01). */
export const INFORMATIVE_BAND_HIGH = 0.8;

/** True iff a probe-predicted score (anchor_a POV) is informative enough to justify the full measure-pass budget. */
export function scoreInInformativeBand(score) {
  return score >= INFORMATIVE_BAND_LOW && score <= INFORMATIVE_BAND_HIGH;
}

// ─── Canonical pair identity (dedupe (a,b) === (b,a)) ──────────────────────

/** Canonically orders two anchor labels so `(x,y)` and `(y,x)` always produce the SAME tuple. */
export function canonicalPair(a, b) {
  return a < b ? [a, b] : [b, a];
}

/** String key for a canonical pair — stable Map/object key shape shared by the scheduler and its caller. */
export function pairKey(a, b) {
  const [x, y] = canonicalPair(a, b);
  return `${x}|${y}`;
}

/** True iff exactly one of `a`/`b` is a `maia*` label — the joint-scale-critical cross-family edge test (D-04). */
export function isCrossFamilyPair(a, b) {
  return a.startsWith('maia') !== b.startsWith('maia');
}

// ─── D-02: base candidate graph ────────────────────────────────────────────

/** How many of the nearest Maia rungs each Stockfish anchor gets an initial cross-family candidate against. */
const NEAREST_MAIA_RUNGS_PER_SF_ANCHOR = 2;

function isMaiaSpec(anchorSpec) {
  return anchorSpec.kind === 'maia';
}

/** Adjacent-rung pairs within ONE family, sorted ascending by rating (D-02 base graph, same-family half). */
function adjacentPairs(anchorSpecs) {
  const sorted = [...anchorSpecs].sort((a, b) => anchorRatingFor(a) - anchorRatingFor(b));
  const pairs = [];
  for (let i = 0; i + 1 < sorted.length; i++) {
    pairs.push(canonicalPair(sorted[i].label, sorted[i + 1].label));
  }
  return pairs;
}

/**
 * Initial cross-family candidates (D-02): for each Stockfish anchor, the
 * `NEAREST_MAIA_RUNGS_PER_SF_ANCHOR` Maia rungs whose rating is closest to
 * that Stockfish anchor's FOLKLORE `SF_SKILL_ELO` value — scheduling-only
 * (Pitfall 3), never a fit input.
 */
function initialCrossFamilyPairs(sfAnchors, maiaAnchors) {
  const pairs = [];
  for (const sf of sfAnchors) {
    const sfElo = anchorRatingFor(sf);
    const nearest = [...maiaAnchors]
      .sort((a, b) => Math.abs(anchorRatingFor(a) - sfElo) - Math.abs(anchorRatingFor(b) - sfElo))
      .slice(0, NEAREST_MAIA_RUNGS_PER_SF_ANCHOR);
    for (const maia of nearest) {
      pairs.push(canonicalPair(sf.label, maia.label));
    }
  }
  return pairs;
}

/**
 * Builds the D-02 base candidate pair set: adjacent Maia rungs + adjacent SF
 * skills + initial cross-family guesses, de-duplicated and canonically
 * ordered so `(x,y)` and `(y,x)` never both appear. Returns an array of
 * `[a, b]` tuples.
 */
export function buildCandidateGraph(anchorSpecs) {
  const maiaAnchors = anchorSpecs.filter(isMaiaSpec);
  const sfAnchors = anchorSpecs.filter((spec) => !isMaiaSpec(spec));

  const allPairs = [
    ...adjacentPairs(maiaAnchors),
    ...adjacentPairs(sfAnchors),
    ...initialCrossFamilyPairs(sfAnchors, maiaAnchors),
  ];

  const seen = new Set();
  const deduped = [];
  for (const [a, b] of allPairs) {
    const key = pairKey(a, b);
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push([a, b]);
  }
  return deduped;
}

// ─── D-04: connectivity + cross-family-edge guard ──────────────────────────

/** Minimum surviving cross-family links required for the Maia/SF scales to be jointly identifiable (D-04). */
export const MIN_CROSS_FAMILY_EDGES = 2;

/**
 * Fail-loud connectivity guard (D-04): throws if any labeled anchor is
 * unreachable from the others via `pairs`, or if fewer than
 * `MIN_CROSS_FAMILY_EDGES` cross-family (`maia*` vs `sf*`) edges survive.
 * Stdlib BFS — no library dependency (173-RESEARCH.md "Don't Hand-Roll").
 */
export function checkConnectivity(pairs, anchorLabels) {
  const adjacency = new Map(anchorLabels.map((label) => [label, new Set()]));
  for (const [a, b] of pairs) {
    adjacency.get(a)?.add(b);
    adjacency.get(b)?.add(a);
  }

  const start = anchorLabels[0];
  const visited = new Set(start === undefined ? [] : [start]);
  const frontier = start === undefined ? [] : [start];
  while (frontier.length > 0) {
    const node = frontier.pop();
    for (const neighbor of adjacency.get(node) ?? []) {
      if (visited.has(neighbor)) continue;
      visited.add(neighbor);
      frontier.push(neighbor);
    }
  }
  const unreached = anchorLabels.filter((label) => !visited.has(label));
  if (unreached.length > 0) {
    throw new Error(`checkConnectivity: anchor graph is disconnected — unreached: ${unreached.join(', ')}`);
  }

  const crossFamilyEdges = pairs.filter(([a, b]) => isCrossFamilyPair(a, b));
  if (crossFamilyEdges.length < MIN_CROSS_FAMILY_EDGES) {
    throw new Error(
      `checkConnectivity: only ${crossFamilyEdges.length} cross-family link(s), need >= ${MIN_CROSS_FAMILY_EDGES} (D-04)`,
    );
  }
}

// ─── D-04 fallback: band-relaxing connectivity rescue ──────────────────────

/** Distance of a probe score from the informative band — 0 inside, else distance to the nearest bound. */
export function bandDistance(score) {
  if (score < INFORMATIVE_BAND_LOW) return INFORMATIVE_BAND_LOW - score;
  if (score > INFORMATIVE_BAND_HIGH) return score - INFORMATIVE_BAND_HIGH;
  return 0;
}

/**
 * D-04 last-resort fallback: when re-targeting is exhausted and the kept
 * graph is still disconnected, greedily add back the DROPPED probed edges
 * closest to the informative band — one bridging edge at a time — until the
 * graph is connected (or no probed edge bridges the remaining components).
 * Rationale: an out-of-band edge carries less rating information than an
 * in-band one (wider CI on that pair's gap), but it is categorically better
 * than a disconnected fit, which is meaningless (Pitfall 1). Discovered live
 * in the 2026-07-15 seed-101 run: {maia700, sf0} probed informative only
 * against EACH OTHER — the ladder bottom has no nearer rung to re-target to
 * (D-04's re-target fallback needs an untried nearer Maia rung), so without
 * this rescue the run fail-louds after burning the entire probe budget.
 *
 * Returns `{ kept, rescued }` — `kept` is the input plus rescued keys,
 * `rescued` lists what was added (for the caller to log and extend to the
 * full measure budget). Does NOT itself throw: the caller still runs
 * `checkConnectivity` on the result, which fail-louds if no probed edge can
 * reconnect the graph or cross-family links remain under the minimum.
 */
export function rescueConnectivity(keptPairKeys, probeScoreByPair, anchorLabels) {
  const entries =
    probeScoreByPair instanceof Map ? [...probeScoreByPair.entries()] : Object.entries(probeScoreByPair);
  const keptSet = new Set(keptPairKeys);

  // Union-find over anchor labels, seeded with the kept edges.
  const parent = new Map(anchorLabels.map((label) => [label, label]));
  const find = (x) => {
    while (parent.get(x) !== x) {
      parent.set(x, parent.get(parent.get(x)));
      x = parent.get(x);
    }
    return x;
  };
  for (const key of keptPairKeys) {
    const [a, b] = key.split('|');
    if (parent.has(a) && parent.has(b)) parent.set(find(a), find(b));
  }
  const componentCount = () => new Set(anchorLabels.map(find)).size;

  // Dropped probed edges, nearest-to-band first; deterministic key tiebreak.
  const droppedByCloseness = entries
    .filter(([key]) => !keptSet.has(key))
    .sort(([keyA, scoreA], [keyB, scoreB]) => bandDistance(scoreA) - bandDistance(scoreB) || (keyA < keyB ? -1 : 1));

  const rescued = [];
  while (componentCount() > 1) {
    const bridge = droppedByCloseness.find(([key]) => {
      const [a, b] = key.split('|');
      return parent.has(a) && parent.has(b) && find(a) !== find(b);
    });
    if (!bridge) break; // no probed edge bridges the remaining components — caller's checkConnectivity fail-louds
    const [key] = bridge;
    const [a, b] = key.split('|');
    parent.set(find(a), find(b));
    rescued.push(key);
    keptSet.add(key);
  }

  return { kept: [...keptPairKeys, ...rescued], rescued };
}

// ─── D-01: probe→measure gate ──────────────────────────────────────────────

/**
 * Splits a probe pass's per-pair scores into pairs worth spending the full
 * measure-pass budget on (informative band) vs. pairs to drop/re-target
 * (D-01). `probeScoreByPair` is a Map or plain object keyed by
 * `pairKey(a, b)` -> the probe score (anchor_a POV, `a`/`b` in canonical
 * order). Does NOT touch connectivity — the caller runs `checkConnectivity`
 * on the kept set and applies D-04's re-target fallback.
 */
export function selectMeasurePairs(probeScoreByPair) {
  const entries =
    probeScoreByPair instanceof Map ? [...probeScoreByPair.entries()] : Object.entries(probeScoreByPair);

  const kept = [];
  const dropped = [];
  for (const [key, score] of entries) {
    (scoreInInformativeBand(score) ? kept : dropped).push(key);
  }
  return { kept, dropped };
}
