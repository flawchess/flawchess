/**
 * GameMoveLine — the avatar's one line about the game blunder ("Ne7 ???: allowed fork in 2,
 * loses material."), and `VerdictExtras`, the divider block it sits in (Phase 264 D-08, D-16).
 *
 * Shared by the personalized puzzle's verdict (`TrainVerdictDetails`) and the blunder-check
 * solution, so the divider, the subject and the tag colours cannot drift between the two. The
 * line starts with the move and its quality icon, the same glyph as the Game chip and the board
 * badge (owner, 2026-11-26; "Game move:" is only the fallback without a SAN). A scored blunder's
 * badge opens the facepalm popover, as in the move list and the analysis move strip (D-23). The
 * parts come from `gameBlunderParts`; the tags keep the analysis move strip's two colours.
 */

import type { ReactElement, ReactNode } from 'react';
import { FacepalmGlyphBadge } from '@/components/analysis/FacepalmGlyphBadge';
import { MoveQualityIcon } from '@/components/icons/MoveQualityIcon';
import { FacepalmBlunderIcon } from '@/components/icons/SeverityGlyphIcon';
import { TACTIC_COLOR } from '@/lib/explainBar';
import { isFacepalmBlunder } from '@/lib/facepalm';
import { GAME_MOVE_FALLBACK_SUBJECT, NO_GAME_MOVE_HEAD, gameBlunderSeparator } from '@/lib/gameBlunderSentence';
import type { GameBlunderPart, GameMoveHead } from '@/lib/gameBlunderSentence';

/** The additional-info block below the verdict: a horizontal divider, then its lines. */
export function VerdictExtras({ children, testid }: { children: ReactNode; testid: string }): ReactElement {
  return (
    <div className="flex flex-col gap-1 border-t border-border pt-2 text-sm" data-testid={testid}>
      {children}
    </div>
  );
}

// The analysis move strip's badge alignment (ExplainBar HEADLINE_BADGE_CLASS): align-text-bottom
// alone sits the 16px icon 2px low against the move's text, so it is nudged up by -top-0.5.
const SUBJECT_ICON_CLASS = 'relative -top-0.5 ml-1.5 inline-block size-4 align-text-bottom';

/**
 * Testid, and Umami popover-open target, of the line's facepalm popover: one target for the
 * puzzle and blunder check. Never interpolate the SAN (frontend/CLAUDE.md, popover targets).
 */
const GAME_MOVE_FACEPALM_POPOVER_TESTID = 'train-game-move-facepalm-popover';

/**
 * The quality glyph. A blunder with a facepalm score and type opens the facepalm explanation,
 * as the analysis strip's HeadlineBadge does (FacepalmGlyphBadge picks "??" or "???"); without
 * them, or when the chip grades the move other than a blunder, it is the plain glyph. The box
 * keeps its size while the quality is unknown.
 */
function SubjectBadge({ head, inert }: { head: GameMoveHead; inert: boolean }): ReactElement {
  const { quality, facepalmScore, facepalmType } = head;
  if (quality === 'blunder' && facepalmScore !== null && facepalmType !== null && !inert) {
    return (
      <span data-testid="game-move-quality" data-quality={quality} data-facepalm={isFacepalmBlunder(facepalmScore) ? 'true' : undefined}>
        <FacepalmGlyphBadge
          score={facepalmScore}
          type={facepalmType}
          byOpponent={head.byOther}
          className={SUBJECT_ICON_CLASS}
          testId={GAME_MOVE_FACEPALM_POPOVER_TESTID}
          // The strip's placement (ExplainBar HeadlineBadge), so the trigger sits like the plain glyph.
          alignClassName="align-text-bottom"
        />
      </span>
    );
  }
  const facepalm = quality === 'blunder' && isFacepalmBlunder(facepalmScore);
  return (
    <span
      aria-hidden="true"
      className={SUBJECT_ICON_CLASS}
      data-testid={inert ? undefined : 'game-move-quality'}
      data-quality={quality ?? undefined}
      data-facepalm={facepalm ? 'true' : undefined}
    >
      {quality !== null &&
        (facepalm ? (
          <FacepalmBlunderIcon className="block size-4" />
        ) : (
          <MoveQualityIcon quality={quality} className="block size-4" />
        ))}
    </span>
  );
}

/**
 * The move, its quality icon and the colon, set like the analysis move strip's headline. The icon's box has a fixed size also while the quality is
 * unknown (the puzzle's game move is graded a moment after the reveal lands), so the line never
 * re-wraps when the glyph appears. `inert` drops the test ids (the reserved placeholder).
 */
function GameMoveSubject({ head, inert = false }: { head: GameMoveHead; inert?: boolean }): ReactElement {
  if (head.san === null) return <>{GAME_MOVE_FALLBACK_SUBJECT}:</>;
  return (
    // nowrap: the move, its icon and the colon always stay together.
    <span className="whitespace-nowrap">
      <span className="font-mono font-bold text-foreground" data-testid={inert ? undefined : 'game-move-san'}>
        {head.san}
      </span>
      <SubjectBadge head={head} inert={inert} />
      :
    </span>
  );
}

/** The line; renders nothing without parts (no line, and the caller no divider). */
export function GameMoveLine({
  parts,
  head,
}: {
  parts: readonly GameBlunderPart[];
  head: GameMoveHead;
}): ReactElement | null {
  if (parts.length === 0) return null;
  return (
    <p data-testid="game-move-line">
      <GameMoveSubject head={head} />{' '}
      {parts.map((part, index) => (
        <span
          key={part.kind === 'tactic' ? part.orientation : part.kind}
          data-part={part.kind === 'tactic' ? part.orientation : part.kind}
          style={part.kind === 'tactic' ? { color: TACTIC_COLOR[part.orientation] } : undefined}
        >
          {gameBlunderSeparator(part, index)}
          {part.text}
        </span>
      ))}
      .
    </p>
  );
}

/** A stand-in SAN of typical width for the reserved slot; never shown. */
const PLACEHOLDER_HEAD: GameMoveHead = { ...NO_GAME_MOVE_HEAD, san: 'Nf3' };

/**
 * The line's reserved slot while the reveal is still loading, built like the real line (the bold
 * mono move and the icon box make the first line box a little taller than plain text), so the
 * bubble is measured at its final height and does not change when the line arrives. Two lines
 * (D-25): with the score sentence appended, a line with a tag or a type part wraps to a second
 * line on desktop, and that is the common case; a score-only line fills one of them.
 */
export function GameMoveLinePlaceholder(): ReactElement {
  return (
    <p aria-hidden="true" className="invisible" data-testid="game-move-line-placeholder">
      <GameMoveSubject head={PLACEHOLDER_HEAD} inert />
      <br />
      {'\u00a0'}
    </p>
  );
}
