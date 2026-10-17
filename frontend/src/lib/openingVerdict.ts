/**
 * Pure verdict rules for the Openings verdict bars (Moves/Games End Eval row, and the
 * repertoire cards and finding cards built on the same primitives).
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

import { gapPosition, gapVerdictColor, type GapVerdict } from '@/lib/gapBar';
import {
  EVAL_BASELINE_PAWNS_BLACK,
  EVAL_BASELINE_PAWNS_WHITE,
  EVAL_NEUTRAL_MAX_PAWNS,
} from '@/lib/openingStatsZones';
import { SCORE_BULLET_CENTER, SCORE_BULLET_NEUTRAL_MAX } from '@/lib/scoreBulletConfig';
import type { ConfidenceLevel } from '@/lib/scoreConfidence';

/** Fewer games than this never get a verdict. Mirrors backend OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE. */
export const REPERTOIRE_MIN_GAMES_FOR_VERDICT = 20;

/** Half-width of the grey typical band on the eval bar, in pawns (benchmark section 2.1 centred IQR). */
export const EVAL_VERDICT_BAND = EVAL_NEUTRAL_MAX_PAWNS;

/** Half-width of the typical score band: 5 points around 50% (D-00b, shared SCORE_BULLET band). */
export const SCORE_VERDICT_BAND = SCORE_BULLET_NEUTRAL_MAX;

const PERCENT_SCALE = 100;
/**
 * Decimals kept when comparing a computed delta to the band edge. Far finer than any real
 * difference (a score moves in steps of 1 / games), coarse enough to absorb IEEE-754 noise.
 */
const BAND_COMPARE_DECIMALS = 6;
const BAND_COMPARE_SCALE = 10 ** BAND_COMPARE_DECIMALS;
/** An eval that rounds to 0.0 reads without a sign. */
const EVAL_COMPACT_ZERO_BELOW = 0.05;
const EVAL_COMPACT_DECIMALS = 1;
const TYPOGRAPHIC_MINUS = '\u2212';
/** Opening names carry a trailing " (B12)" ECO code that the repertoire cards drop (no ECO codes). */
const TRAILING_ECO_PATTERN = / \([A-E]\d\d\)$/;

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
  // Round before the band test: score - 0.5 is -0.04999999999999999 at 45% but
  // 0.050000000000000044 at 55%, so the raw compare coloured one band edge and not the
  // other (WR-03). Rounding makes both edges land exactly on the band, i.e. typical.
  const delta = Math.round(input.delta * BAND_COMPARE_SCALE) / BAND_COMPARE_SCALE;
  if (Math.abs(delta) <= input.band) return 'typical';
  if (input.confidence !== 'high') return 'chance';
  return input.delta > 0 ? 'better' : 'worse';
}

/** The dot colour verdict: better / worse only for a confident, large-sample, out-of-band delta. */
export function openingVerdict(input: OpeningVerdictInput): GapVerdict {
  const reason = openingVerdictReason(input);
  return reason === 'better' || reason === 'worse' ? reason : 'typical';
}

/** Colour of a verdict's value text: the dot colour when better or worse, none (plain foreground) otherwise. */
export function verdictValueColor(verdict: GapVerdict): string | undefined {
  return verdict === 'better' || verdict === 'worse' ? gapVerdictColor(verdict) : undefined;
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

/** Score minus the 50% centre, as a fraction (0.06 = six points above break-even). */
export function scoreDelta(score: number): number {
  return score - SCORE_BULLET_CENTER;
}

/** "56%": the compact score cell text. */
export function formatScorePercent(score: number): string {
  return `${Math.round(score * PERCENT_SCALE)}%`;
}

/** Compact signed eval for the verdict value: "+0.9", "−0.4", "0.0" when it rounds to zero. */
export function formatEvalCompact(pawns: number): string {
  if (Math.abs(pawns) < EVAL_COMPACT_ZERO_BELOW) return (0).toFixed(EVAL_COMPACT_DECIMALS);
  const sign = pawns > 0 ? '+' : TYPOGRAPHIC_MINUS;
  return `${sign}${Math.abs(pawns).toFixed(EVAL_COMPACT_DECIMALS)}`;
}

/** Drops a trailing " (B12)" ECO suffix; names without one pass through. */
export function stripEcoSuffix(name: string): string {
  return name.replace(TRAILING_ECO_PATTERN, '');
}

/** Rows under the verdict game floor are drawn faded and never coloured (D-00). */
export function isFadedRow(games: number): boolean {
  return games < REPERTOIRE_MIN_GAMES_FOR_VERDICT;
}

/**
 * The one-line "why" under a finding's eval bar: only the opening eval can explain a score, so
 * it says nothing when the eval verdict is typical (sketch 012 why()).
 */
export function whyLine(verdict: GapVerdict, color: 'white' | 'black'): string | null {
  if (verdict === 'typical') return null;
  const side = color === 'black' ? 'Black' : 'White';
  return `You come out of the opening ${verdict} than an average ${side} game.`;
}
