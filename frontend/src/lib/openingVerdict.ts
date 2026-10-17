/**
 * Pure verdict rules for the Openings verdict bars (Moves/Games End Eval row, and the
 * repertoire table and finding cards built on the same primitives).
 *
 * Direction: HIGHER is better for both score and eval, so a positive delta is drawn to the
 * RIGHT and is 'better'. (The Library GapBar is the opposite: fewer flaws is better.) That is
 * why this module reuses only the direction-agnostic gapBar math (gapPosition, the verdict
 * type and colours) and not its gapVerdict / effectiveVerdict.
 *
 * `delta` is the value minus its reference (the colour's baseline for eval, 50% for score).
 * A dot is green or red only when all three hold: the delta is outside the +/- band, the
 * backend confidence is 'high' (the 99% gate: p < 0.01 against the reference), and the
 * position has at least REPERTOIRE_MIN_GAMES_FOR_VERDICT games. Everything else is the
 * neutral blue.
 */

import { gapPosition, type GapVerdict } from '@/lib/gapBar';
import {
  EVAL_BASELINE_PAWNS_BLACK,
  EVAL_BASELINE_PAWNS_WHITE,
  EVAL_NEUTRAL_MAX_PAWNS,
} from '@/lib/openingStatsZones';
import type { ConfidenceLevel } from '@/lib/scoreConfidence';

/** Fewer games than this never get a verdict. Mirrors backend OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE. */
export const REPERTOIRE_MIN_GAMES_FOR_VERDICT = 20;

/** Half-width of the grey typical band on the eval bar, in pawns (benchmark section 2.1 centred IQR). */
export const EVAL_VERDICT_BAND = EVAL_NEUTRAL_MAX_PAWNS;

/** Why a bar reads the way it does; the popover turns this into a sentence. */
export type OpeningVerdictReason = 'too-few' | 'typical' | 'chance' | 'better' | 'worse';

export interface OpeningVerdictInput {
  /** value minus its reference (eval: minus the colour baseline; score: minus 50%). */
  delta: number;
  /** Half-width of the typical band, in the same unit as delta. */
  band: number;
  /** Backend confidence against the reference; only 'high' (99%) colours a dot. */
  confidence: ConfidenceLevel;
  games: number;
}

/** Precedence: too few games, then inside the band, then not confident, then the sign. */
export function openingVerdictReason(input: OpeningVerdictInput): OpeningVerdictReason {
  if (input.games < REPERTOIRE_MIN_GAMES_FOR_VERDICT) return 'too-few';
  if (Math.abs(input.delta) <= input.band) return 'typical';
  if (input.confidence !== 'high') return 'chance';
  return input.delta > 0 ? 'better' : 'worse';
}

/** The dot colour verdict: better / worse only for a confident, large-sample, out-of-band delta. */
export function openingVerdict(input: OpeningVerdictInput): GapVerdict {
  const reason = openingVerdictReason(input);
  return reason === 'better' || reason === 'worse' ? reason : 'typical';
}

/** The engine-balanced reference an average game of this colour reaches the middlegame at. */
export function evalBaselinePawns(color: 'white' | 'black'): number {
  return color === 'black' ? EVAL_BASELINE_PAWNS_BLACK : EVAL_BASELINE_PAWNS_WHITE;
}

/** Dot position, 0-100 % from the left, on a track centred on the reference (higher is right). */
export function verdictPosition(delta: number, band: number): number {
  return gapPosition(delta, -band, band);
}

/** Left offset and width (in %) of the drawn typical band. */
export function verdictBandRange(band: number): { leftPct: number; widthPct: number } {
  const leftPct = verdictPosition(-band, band);
  const rightPct = verdictPosition(band, band);
  return { leftPct, widthPct: rightPct - leftPct };
}
