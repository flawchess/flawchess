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
 * backend confidence is 'medium' or 'high' (the 95% gate: p < 0.05 against the reference,
 * D-33), and the
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
import { isConfident } from '@/lib/significance';

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
  /** Backend confidence against the reference; 'medium' or 'high' (95%) colours a dot. */
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
  if (!isConfident(input.confidence)) return 'chance';
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

/** How one bar reads for the card sentence: chance, too few evals and no eval all collapse to 'unknown'. */
type SentenceState = 'better' | 'worse' | 'typical' | 'unknown';

function sentenceState(reason: OpeningVerdictReason | null): SentenceState {
  if (reason === 'better' || reason === 'worse' || reason === 'typical') return reason;
  return 'unknown';
}

const SENTENCE_TOO_FEW = 'Too few games to call it yet.';
const SENTENCE_SCORE_BELOW = 'You score clearly below 50% from these positions.';
const SENTENCE_SCORE_ABOVE = 'You score clearly above 50% from these positions.';
const SENTENCE_SCORE_EVEN = 'You score in the typical range here.';
const SENTENCE_CHANCE = 'Nothing clear yet. The differences could still be chance.';

/**
 * Score row x eval column. Only the parts that passed the 95% gate are stated as clear: an
 * unclear eval falls back to the score-only sentence. Every cell has a sentence, so a card
 * without one never reads as missing.
 */
const VERDICT_SENTENCES: Record<SentenceState, Record<SentenceState, string>> = {
  worse: {
    worse: 'You come out of the opening worse, and it shows in your results.',
    typical: 'You score below 50% even though the opening itself goes fine. The points slip away later.',
    better: 'You come out of the opening better but still score below 50%.',
    unknown: SENTENCE_SCORE_BELOW,
  },
  better: {
    worse: 'You come out of the opening worse but outplay your opponents later.',
    typical: SENTENCE_SCORE_ABOVE,
    better: 'You come out of the opening better and make it count.',
    unknown: SENTENCE_SCORE_ABOVE,
  },
  typical: {
    worse: 'You come out of the opening worse but hold your own.',
    typical: 'An ordinary opening for you: average positions and a typical score.',
    better: "You come out of the opening better, but your results don't show it yet.",
    unknown: SENTENCE_SCORE_EVEN,
  },
  unknown: {
    worse: 'You come out of the opening worse than an average game.',
    typical: 'Average positions out of the opening. Your score could still be chance.',
    better: 'You come out of the opening better than an average game.',
    unknown: SENTENCE_CHANCE,
  },
};

/**
 * One plain sentence reading the Score and Eval verdicts together (repertoire and finding
 * cards). `evalReason` is null when the card has no eval (no analysis yet, or no evals).
 */
export function openingVerdictSentence(
  scoreReason: OpeningVerdictReason,
  evalReason: OpeningVerdictReason | null,
): string {
  if (scoreReason === 'too-few') return SENTENCE_TOO_FEW;
  return VERDICT_SENTENCES[sentenceState(scoreReason)][sentenceState(evalReason)];
}
