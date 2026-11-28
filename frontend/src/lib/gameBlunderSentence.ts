/**
 * gameBlunderSentence — the avatar's line about the game blunder (Phase 264), for the
 * personalized puzzle reveal and the blunder-check solution: "Ne7 ???: allowed fork in 2, loses
 * material." The subject (move and quality icon) is rendered by `GameMoveLine`; this module
 * resolves what follows the colon.
 *
 * One pure resolver from (tag slots, type line) to the line's parts. Both surfaces render the
 * parts with `GameMoveLine`; neither keeps its own copy table for these lines (D-09). The
 * reference for every sentence is the seed's list "Possible Sentences And Their Conditions"
 * (rows T1-T6, P1-P6, C1-C14), which the table-driven test walks.
 *
 * - Tag part: every visible tag as the analysis move strip writes it (`tacticSlotsText`),
 *   missed first (D-12, D-18). The slots arrive already nulled by the server gate; the strip's
 *   family guard runs inside `tacticSlotsText`.
 * - Depth cut, avatar only (D-10): a tag shown as "in 6" or deeper is left out, unless it is a
 *   checkmate. The strip itself is unchanged.
 * - Type part: what the blunder loses or misses (D-15). A checkmate tag suppresses the type
 *   part on the same side (D-17), so checkmate is never said twice; a hanging-piece tag
 *   suppresses the material type part on the same side (D-21, owner 2026-11-28).
 * - Score part (D-23 and D-25, owner 2026-11-28, partly reversing D-11), on every scored blunder:
 *   how hard the blunder was to spot, in three bands at the app's two existing cuts, with the
 *   score: "hard to spot (facepalm score 23%)" below 50%, "fairly easy to spot (...)" up to 69%,
 *   "easy to spot (...)" from the 70% "???" cut. After a tag or a type part it is its own
 *   sentence ("allowed fork in 1, loses material. Hard to spot (facepalm score 14%)"), alone it
 *   is the line's only item. When the bubble already says how hard it was (blunder check's
 *   "hard to catch" line, same 50% cut) the band word is dropped: "facepalm score 23%". It is
 *   always last and never changes the tag or type wording.
 * - Nothing known: no parts, and the caller renders no line and no divider (D-05). With the
 *   score part only an unscored blunder ends here.
 */

import { tacticSlotsText, type ExplainOrientation, type TacticSlotInput } from '@/lib/explainBar';
import { FACEPALM_HARD_TO_SPOT_BELOW, FACEPALM_HIGH_CUTOFF, toFacepalmPct } from '@/lib/facepalm';
import { resolveVisibleTactic } from '@/lib/tacticComparisonMeta';
import type { TrainMoveQuality } from '@/lib/trainArrows';
import type { BlunderTypeLine } from '@/types/blunderCheck';
import type { FacepalmType } from '@/types/library';

/**
 * The line's fallback subject when the move's SAN is unknown. Normally the line starts with the
 * move itself and its quality icon ("Ne7 ???: ...", owner 2026-11-26, replacing the fixed
 * "Game move:" label of D-04). Either way it is neutral: never "your".
 */
export const GAME_MOVE_FALLBACK_SUBJECT = 'Game move';

/** The deepest tag the avatar comments on, as the number the user sees ("in 5"). */
export const MAX_COMMENTED_TACTIC_DEPTH = 5;

/** The strip's label for every named mate (`tacticMotifLabel`). */
const CHECKMATE_LABEL = 'checkmate';

/** A hanging-piece tag already says the piece goes, so it suppresses the material type part. */
const HANGING_PIECE_LABEL = 'hanging-piece';

/** The type parts that only restate a hanging piece: material, not mate. */
const MATERIAL_TYPE_LINES: ReadonlySet<BlunderTypeLine> = new Set(['allowed_material', 'missed_material']);

const PART_SEPARATOR = ', ';

/** Between the tag and type parts and the score, which starts its own sentence (D-25). */
const SENTENCE_SEPARATOR = '. ';

/** What the blunder loses or misses, as the line's last item (D-15). */
const TYPE_PART_COPY: Record<BlunderTypeLine, string> = {
  allowed_material: 'loses material',
  allowed_mate: 'allows checkmate',
  missed_material: 'missed a chance to win material',
  missed_mate: 'missed checkmate',
};

const TYPE_PART_SIDE: Record<BlunderTypeLine, ExplainOrientation> = {
  allowed_material: 'allowed',
  allowed_mate: 'allowed',
  missed_material: 'missed',
  missed_mate: 'missed',
};

/** The line's subject: the game move and how it is badged. */
export interface GameMoveHead {
  /** The move's SAN; null (unknown) falls back to "Game move". */
  san: string | null;
  /** The move's quality as the Game chip shows it; null while the engine has not graded it. */
  quality: TrainMoveQuality | null;
  /**
   * The blunder's facepalm score, raw 0..1; null when unscored. Picks "???" over "??"
   * (`isFacepalmBlunder`) and, with the type, makes the badge open the facepalm popover (D-23).
   */
  facepalmScore: number | null;
  /** The blunder's facepalm type, named in the popover; null when unknown. */
  facepalmType: FacepalmType | null;
  /** Someone else's blunder (a foreign puzzle or window): the popover says "their level". */
  byOther: boolean;
}

/** A head with no move and no badge: no line (false alarms, herrings). */
export const NO_GAME_MOVE_HEAD: GameMoveHead = {
  san: null,
  quality: null,
  facepalmScore: null,
  facepalmType: null,
  byOther: false,
};

export interface GameBlunderInput {
  /** The two tag slots as the server sent them (already gated; null: not shown). */
  allowedTactic: TacticSlotInput | null;
  missedTactic: TacticSlotInput | null;
  typeLine: BlunderTypeLine | null;
  /** The blunder's facepalm score (raw 0..1); spoken only when nothing else is (D-23). */
  facepalmScore: number | null;
  /**
   * The bubble already says how hard the blunder was to catch (blunder check's hard-to-catch
   * line): the score part then drops its band word. Omitted: false.
   */
  difficultySaid?: boolean;
}

/**
 * One item of the line: a tag in its strip colour, the type part in the text colour, or the
 * facepalm score, always last (its own sentence after a tag or a type part).
 */
export type GameBlunderPart =
  | { kind: 'tactic'; orientation: ExplainOrientation; text: string }
  | { kind: 'type'; text: string }
  | { kind: 'score'; text: string };

/** How hard the blunder was to spot, by the whole-percent score (D-23). */
function spotBand(pct: number): string {
  if (pct < FACEPALM_HARD_TO_SPOT_BELOW) return 'hard to spot';
  return pct < FACEPALM_HIGH_CUTOFF ? 'fairly easy to spot' : 'easy to spot';
}

/**
 * The score part: its band word and the score, or the score alone when the band is said already.
 * Capitalized when it starts its own sentence after a tag or a type part (D-25).
 */
function facepalmScoreText(score: number, difficultySaid: boolean, ownSentence: boolean): string {
  // Floored like every shown facepalm percent, so the band and the number never disagree.
  const pct = toFacepalmPct(score);
  const scoreText = `facepalm score ${pct}%`;
  const text = difficultySaid ? scoreText : `${spotBand(pct)} (${scoreText})`;
  return ownSentence ? text.charAt(0).toUpperCase() + text.slice(1) : text;
}

interface CommentedSlot {
  slot: TacticSlotInput | null;
  isCheckmate: boolean;
  isHangingPiece: boolean;
}

/** A slot after the avatar's cuts: the slot itself, null when left out, and whether it is a checkmate. */
function commentedSlot(
  orientation: ExplainOrientation,
  slot: TacticSlotInput | null,
): CommentedSlot {
  const hidden = { slot: null, isCheckmate: false, isHangingPiece: false };
  if (slot === null) return hidden;
  const visible = resolveVisibleTactic(orientation, slot.motif, slot.depth, undefined, false);
  if (visible === null) return hidden;
  const isCheckmate = visible.motifLabel === CHECKMATE_LABEL;
  const tooDeep = visible.depthLabel !== null && Number(visible.depthLabel) > MAX_COMMENTED_TACTIC_DEPTH;
  const isHangingPiece = visible.motifLabel === HANGING_PIECE_LABEL;
  return tooDeep && !isCheckmate ? hidden : { slot, isCheckmate, isHangingPiece };
}

/**
 * Whether a shown tag already says what the type part would (D-17, D-21): a checkmate tag
 * covers any type part on its side, a hanging-piece tag the material one on its side. Parts on
 * different sides are both shown.
 */
function typePartCovered(typeLine: BlunderTypeLine, missed: CommentedSlot, allowed: CommentedSlot): boolean {
  const sameSide = TYPE_PART_SIDE[typeLine] === 'allowed' ? allowed : missed;
  return sameSide.isCheckmate || (sameSide.isHangingPiece && MATERIAL_TYPE_LINES.has(typeLine));
}

/**
 * The line's items in order: tags (missed first), the type part, then the facepalm score on a
 * scored blunder; empty: no line.
 */
export function gameBlunderParts(input: GameBlunderInput): GameBlunderPart[] {
  const parts = tagAndTypeParts(input);
  if (input.facepalmScore === null) return parts;
  const text = facepalmScoreText(input.facepalmScore, input.difficultySaid ?? false, parts.length > 0);
  return [...parts, { kind: 'score', text }];
}

/** The tags and the type part; the score never enters here, so it cannot change their wording. */
function tagAndTypeParts(input: GameBlunderInput): GameBlunderPart[] {
  const missed = commentedSlot('missed', input.missedTactic);
  const allowed = commentedSlot('allowed', input.allowedTactic);
  const parts: GameBlunderPart[] = tacticSlotsText(missed.slot, allowed.slot).map((tactic) => ({
    kind: 'tactic',
    ...tactic,
  }));
  if (input.typeLine === null) return parts;
  if (!typePartCovered(input.typeLine, missed, allowed)) parts.push({ kind: 'type', text: TYPE_PART_COPY[input.typeLine] });
  return parts;
}

/**
 * The separator before a part: none before the first, ", " between tags and the type part, and
 * ". " before the score, which starts its own sentence (D-25).
 */
export function gameBlunderSeparator(part: GameBlunderPart, index: number): string {
  if (index === 0) return '';
  return part.kind === 'score' ? SENTENCE_SEPARATOR : PART_SEPARATOR;
}

/**
 * The whole line as plain text, without the quality icon ("Ne7: allowed fork in 2, loses
 * material."); null without parts. `san` null falls back to "Game move".
 */
export function gameBlunderSentence(parts: readonly GameBlunderPart[], san: string | null = null): string | null {
  if (parts.length === 0) return null;
  const body = parts.map((part, index) => gameBlunderSeparator(part, index) + part.text).join('');
  return `${san ?? GAME_MOVE_FALLBACK_SUBJECT}: ${body}.`;
}
