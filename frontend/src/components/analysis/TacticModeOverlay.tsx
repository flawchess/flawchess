/**
 * TacticModeOverlay — conditional tactic chrome for the /analysis page (Phase 139).
 *
 * Rendered by Analysis.tsx when `isTacticMode` (game_id + flaw_ply params present).
 * Provides: motif chip(s), missed/allowed switch, and a mobile-only decorated
 * HorizontalMoveList with real-game-ply numbering (desktop uses the vertical
 * VariationTree as the single move list).
 *
 * Exports `buildRootArrows` and `buildPvArrow` so Analysis.tsx can drive the shared
 * ChessBoard arrows without duplicating the arrow-building logic.
 *
 * Design:
 * - NO board, NO BoardControls (those stay in Analysis.tsx).
 * - NO URL state, NO next/prev rail (D-01).
 * - All interactive elements carry data-testid and aria attributes per CLAUDE.md.
 */

import { HorizontalMoveList } from '@/components/board/HorizontalMoveList';
import type { HorizontalMoveItem } from '@/components/board/HorizontalMoveList';
import { TacticMotifChip } from '@/components/library/TacticMotifChip';
import { BlunderIcon, MistakeIcon } from '@/components/icons/SeverityGlyphIcon';
import { moveLabel } from '@/lib/moveNumberLabel';
import { useFlawFilterStore } from '@/hooks/useFlawFilterStore';
import { resolveVisibleTactic } from '@/lib/tacticComparisonMeta';
import { uciToSquares, sanToSquares } from '@/lib/sanToSquares';
import {
  BEST_MOVE_ARROW,
  PAYOFF_MOVE_ARROW,
  TAC_ALLOWED,
  TAC_MISSED,
  TAC_MISSED_LABEL,
  TAC_ALLOWED_LABEL,
} from '@/lib/theme';
import type { TacticDepthOrientation } from '@/lib/tacticDepth';
import type { BoardArrow } from '@/components/board/ChessBoard';
import type { TacticLinesResponse } from '@/types/library';

// ─── Constants ───────────────────────────────────────────────────────────────

/** Horizontal move-list height: matches TacticLineExplorer (Quick 260625). */
const MOVE_LIST_HEIGHT = 'h-28 md:h-24';

// ─── Board orientation helper ─────────────────────────────────────────────────

/**
 * True when Black is to move in the given FEN (2nd field). Used to default the board
 * to the flaw-maker's perspective: the side to move at the decision position sits at
 * the bottom, flipping when that player is Black (Phase 135 UAT).
 * Ported unchanged from TacticLineExplorer.tsx.
 */
export function isBlackToMove(fen: string): boolean {
  return fen.split(' ')[1] === 'b';
}

// ─── Arrow builders (ported UNCHANGED from TacticLineExplorer.tsx) ────────────

/**
 * Build arrows for the root position (ply 0): best-move (blue) and flaw-move (red)
 * shown simultaneously. Colors from theme.ts — no hex literals.
 * Exported so Analysis.tsx can drive the shared ChessBoard without duplicating logic.
 */
export function buildRootArrows(
  positionFen: string,
  bestMoveUci: string | null,
  flawMoveSan: string | null,
  missedDepthLabel: string | undefined,
  allowedDepthLabel: string | undefined,
): BoardArrow[] {
  const arrows: BoardArrow[] = [];
  const bestMoveSquares = uciToSquares(bestMoveUci);
  if (bestMoveSquares) {
    arrows.push({
      startSquare: bestMoveSquares.from,
      endSquare: bestMoveSquares.to,
      color: BEST_MOVE_ARROW,
      width: 0.5,
      label: missedDepthLabel,
      labelColor: TAC_MISSED_LABEL,
    });
  }
  if (flawMoveSan) {
    const flawSquares = sanToSquares(positionFen, flawMoveSan);
    if (flawSquares) {
      arrows.push({
        startSquare: flawSquares.from,
        endSquare: flawSquares.to,
        color: TAC_ALLOWED,
        width: 0.5,
        label: allowedDepthLabel,
        labelColor: TAC_ALLOWED_LABEL,
      });
    }
  }
  return arrows;
}

/**
 * Build the single engine-PV arrow for ply 1+.
 * At the punchline (depth 0): standard BEST_MOVE_ARROW with depth label.
 * Past punchline (isPayoff): lighter blue, no depth label.
 * Flaw lead-in (allowed line, ply 1 = the prepended flaw move): red arrow with countdown.
 * Exported so Analysis.tsx can drive the shared ChessBoard.
 */
export function buildPvArrow(
  lastMove: { from: string; to: string } | null,
  displayDepth: number,
  isPayoff: boolean,
  orientation: TacticDepthOrientation,
  isFlawLeadIn: boolean,
): BoardArrow[] {
  if (!lastMove) return [];
  if (isFlawLeadIn) {
    return [
      {
        startSquare: lastMove.from,
        endSquare: lastMove.to,
        color: TAC_ALLOWED,
        width: 0.5,
        label: String(displayDepth),
        labelColor: TAC_ALLOWED_LABEL,
      },
    ];
  }
  return [
    {
      startSquare: lastMove.from,
      endSquare: lastMove.to,
      color: isPayoff ? PAYOFF_MOVE_ARROW : BEST_MOVE_ARROW,
      width: 0.5,
      label: isPayoff ? undefined : String(displayDepth),
      labelColor: isPayoff
        ? undefined
        : orientation === 'missed'
          ? TAC_MISSED_LABEL
          : TAC_ALLOWED_LABEL,
    },
  ];
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface TacticModeOverlayProps {
  /** Full tactic-lines response from the tactic-lines endpoint. */
  data: TacticLinesResponse;
  /** Resolved orientation (fallback applied); drives active line + chip selection. */
  resolvedOrientation: TacticDepthOrientation;
  /**
   * Current position in the stored PV (0 = decision position / root).
   * `mainLine.indexOf(currentNodeId) + 1` from Analysis.tsx; -1+1=0 when off-line.
   */
  currentPly: number;
  /**
   * True when the board sits on the stored PV (root or a seeded mainLine node).
   * False once the user forks off into a live variation (WR-01): the motif chip's
   * active-line border is anchored to the stored line, so it is dropped off-line.
   */
  onStoredLine: boolean;
  /** Called when the user switches the missed/allowed orientation. */
  onOrientationChange: (next: TacticDepthOrientation) => void;
  /**
   * Called when the user clicks a move in the PV list.
   * `ply` is 1-based (index + 1); Analysis.tsx maps this to `goToNode(mainLine[ply-1])`.
   */
  onMoveClick: (ply: number) => void;
}

// ─── TacticModeOverlay ────────────────────────────────────────────────────────

/**
 * Tactic chrome panel rendered by Analysis.tsx when `isTacticMode`.
 * Contains the motif switch, eval badge, depth counter, arrow-source toggle,
 * and the decorated move list. No board, no BoardControls.
 */
export function TacticModeOverlay({
  data,
  resolvedOrientation,
  currentPly,
  onStoredLine,
  onOrientationChange,
  onMoveClick,
}: TacticModeOverlayProps) {
  // ── Filter-gated visibility (mirrors TacticLineExplorer ExplorerBody exactly) ─
  const [flawFilter] = useFlawFilterStore();

  const missedVisible = resolveVisibleTactic(
    'missed',
    data.missed_motif ?? null,
    data.missed_depth ?? null,
    flawFilter,
  );
  const allowedVisible = resolveVisibleTactic(
    'allowed',
    data.allowed_motif ?? null,
    data.allowed_depth ?? null,
    flawFilter,
  );
  const hasMissed = missedVisible != null && data.missed_moves != null;
  const hasAllowed = allowedVisible != null && data.allowed_moves != null;
  const showToggle = hasMissed && hasAllowed;
  const showSwitch = showToggle && data.missed_motif != null && data.allowed_motif != null;

  // ── Active line (moves + punchline index) for the selected orientation ────────
  const activeMoves =
    resolvedOrientation === 'missed'
      ? hasMissed
        ? (data.missed_moves ?? null)
        : null
      : hasAllowed
        ? (data.allowed_moves ?? null)
        : null;

  const activePlyIndex =
    resolvedOrientation === 'missed'
      ? (data.missed_tactic_ply_index ?? 0)
      : (data.allowed_tactic_ply_index ?? 0);

  // ── Motif chip header row ─────────────────────────────────────────────────────

  const gameId = data.flaw_ply; // stable per-flaw ID for chip testid (mirrors TLE usage)

  const headerRow = (
    <div className="flex items-center gap-3 flex-wrap">
      {showSwitch ? (
        <div className="flex gap-2" role="group" aria-label="Tactic line switch">
          <TacticMotifChip
            motif={data.missed_motif!}
            flawId={gameId}
            orientation="missed"
            // White "active line" border only while on the stored PV; diverging
            // into a live variation drops it, and it returns on reset/back (UAT).
            selected={onStoredLine && resolvedOrientation === 'missed'}
            testId="tactic-toggle-missed"
            onActivate={() => onOrientationChange('missed')}
            noTruncate
          />
          <TacticMotifChip
            motif={data.allowed_motif!}
            flawId={gameId}
            orientation="allowed"
            selected={onStoredLine && resolvedOrientation === 'allowed'}
            testId="tactic-toggle-allowed"
            onActivate={() => onOrientationChange('allowed')}
            noTruncate
          />
        </div>
      ) : (
        <div className="flex gap-2">
          {hasMissed && data.missed_motif != null && (
            <TacticMotifChip
              motif={data.missed_motif}
              flawId={gameId}
              orientation="missed"
              noTruncate
            />
          )}
          {hasAllowed && data.allowed_motif != null && (
            <TacticMotifChip
              motif={data.allowed_motif}
              flawId={gameId}
              orientation="allowed"
              noTruncate
            />
          )}
        </div>
      )}
    </div>
  );

  // ── Decorated move list (Behavior C: real-game-ply numbering) ────────────────

  const flawSeverity = data.flaw_severity;

  const moveItems: HorizontalMoveItem[] =
    activeMoves == null
      ? []
      : activeMoves.map((san, i) => {
          const isPunchline = i === activePlyIndex;
          const isPayoffItem = i > activePlyIndex;
          const isFlawLeadIn = resolvedOrientation === 'allowed' && i === 0;
          const showGlyph = isFlawLeadIn && flawSeverity !== 'inaccuracy';
          return {
            key: i,
            ply: i + 1,
            // Behavior C: real-game-ply move number label (not "1." from restart)
            numberLabel: moveLabel(data.flaw_ply, i),
            san,
            isCurrent: currentPly === i + 1,
            color: isPunchline
              ? resolvedOrientation === 'missed'
                ? TAC_MISSED
                : TAC_ALLOWED
              : undefined,
            dimmed: isPayoffItem || isFlawLeadIn,
            // Behavior C: testId anchors to real game ply (data.flaw_ply + i)
            testId: `tactic-san-move-${data.flaw_ply + i}`,
            trailing: showGlyph ? (
              <span
                className="flex items-center shrink-0"
                aria-label={`${flawSeverity} move`}
                data-testid={`tactic-san-flaw-severity-${flawSeverity}`}
              >
                {flawSeverity === 'blunder' ? (
                  <BlunderIcon className="h-4 w-4" />
                ) : (
                  <MistakeIcon className="h-4 w-4" />
                )}
              </span>
            ) : undefined,
          };
        });

  // ── Layout: header → depth/controls → move list (or empty state) ────────────

  return (
    <div
      data-testid="tactic-mode-overlay"
      className="flex flex-col gap-3"
    >
      {headerRow}
      {activeMoves == null ? (
        <p className="text-sm text-muted-foreground">
          Tactic line not available for this flaw.
        </p>
      ) : (
        /* Mobile-only tactic SAN ladder. On desktop (sm+) the vertical
           VariationTree is the single move list (UAT: no redundant lists);
           its punchline/blunder coloring is driven from Analysis.tsx. */
        <div className="sm:hidden">
          <HorizontalMoveList
            items={moveItems}
            onMoveClick={onMoveClick}
            heightClass={MOVE_LIST_HEIGHT}
            testId="tactic-san-ladder"
          />
        </div>
      )}
    </div>
  );
}
