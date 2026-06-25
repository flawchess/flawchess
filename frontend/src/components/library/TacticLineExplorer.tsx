/**
 * TacticLineExplorer — walkable PV stepper for tagged flaws (Phase 135, D-01..D-05).
 *
 * Renders as:
 * - Dialog (desktop ≥768px): board-sized modal, single-column stacked layout
 *   (board → BoardControls → horizontal move list) — Quick 260625.
 * - Drawer (mobile <768px): same stacked layout (board → BoardControls → move list).
 *
 * Entry points: FlawCard button row (D-04) and LibraryGameCard Explore button (D-03).
 *
 * Data: useTacticLines (lazy, enabled only when open).
 * Navigation: useTacticLine (PV stepper cloned from useChessGame).
 */

import { useState, useEffect } from 'react';
import { Cpu, Loader2, X } from 'lucide-react';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerClose,
} from '@/components/ui/drawer';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { ChessBoard } from '@/components/board/ChessBoard';
import { BoardControls } from '@/components/board/BoardControls';
import { HorizontalMoveList } from '@/components/board/HorizontalMoveList';
import type { HorizontalMoveItem } from '@/components/board/HorizontalMoveList';
import { TacticMotifChip } from '@/components/library/TacticMotifChip';
import { BlunderIcon, MistakeIcon } from '@/components/icons/SeverityGlyphIcon';
import { moveLabel } from '@/lib/moveNumberLabel';
import { useTacticLines } from '@/hooks/useLibrary';
import { useTacticLine } from '@/hooks/useTacticLine';
import { useFlawFilterStore } from '@/hooks/useFlawFilterStore';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';
import { TACTIC_FAMILY_FOR_MOTIF } from '@/lib/tacticComparisonMeta';
import { DEFAULT_TACTIC_DEPTH_VALUE } from '@/lib/tacticDepth';
import { uciToSquares, sanToSquares } from '@/lib/sanToSquares';
import {
  BEST_MOVE_ARROW,
  PAYOFF_MOVE_ARROW,
  TAC_ALLOWED,
  TAC_MISSED,
  TAC_MISSED_LABEL,
  TAC_ALLOWED_LABEL,
} from '@/lib/theme';
import { toDisplayDepthForOrientation } from '@/lib/tacticDepth';
import { formatFlawEvalPart, mateAtPly } from '@/lib/formatFlawEval';
import type { TacticDepthOrientation } from '@/lib/tacticDepth';
import type { BoardArrow } from '@/components/board/ChessBoard';

// ─── Constants ───────────────────────────────────────────────────────────────

const MOBILE_BREAKPOINT_PX = 768; // matches Tailwind `md`

// Horizontal move-list height. Mobile's drawer is narrower than the desktop modal, so
// the same 3-line content wraps into a 4th row and would show a scrollbar — mobile gets
// extra height (h-28 ≈ 112px) while the wider desktop modal fits 3 lines at h-24 ≈ 96px
// (Quick 260625). The `md` breakpoint (768px) matches MOBILE_BREAKPOINT_PX, so the class
// resolves per surface: mobile surface (<768px) → h-28, desktop surface (≥768px) → h-24.
const MOVE_LIST_HEIGHT = 'h-28 md:h-24';

// Safe fallback FEN for useTacticLine when data is not yet loaded (hooks must
// always be called — use the chess starting position as a no-op placeholder).
const FALLBACK_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

// (PAYOFF_MOVE_ARROW imported from theme.ts — no local hex literals)

// ─── useIsMobile hook ─────────────────────────────────────────────────────────

/**
 * Returns true when window width < MOBILE_BREAKPOINT_PX.
 * Cloned from ScoreChart.tsx useIsMobile pattern (Phase 135 PATTERNS.md).
 */
function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

// ─── Board orientation helper ─────────────────────────────────────────────────

/**
 * True when Black is to move in the given FEN (2nd field). Used to default the board
 * to the flaw-maker's perspective: the side to move at the decision position sits at
 * the bottom, so the board flips when that player is Black (Phase 135 UAT).
 */
function isBlackToMove(fen: string): boolean {
  return fen.split(' ')[1] === 'b';
}

/**
 * Whether a tactic orientation passes the active flaw filter (Phase 135 UAT). Mirrors
 * how the Games/Flaws tabs gate each orientation's chip — orientation axis, tactic-family
 * narrowing, and the raw 0-based depth range. So the explore modal hides a missed/allowed
 * tag+line when it is filtered out in the list. Fields are optional-chained defensively
 * (older persisted/mocked filter objects may omit newer fields).
 */
function tacticOrientationPasses(
  orientation: TacticDepthOrientation,
  motif: string | null,
  depthRaw: number | null,
  filter: FlawFilterState,
): boolean {
  const orientationFilter = filter.tacticOrientation ?? 'either';
  if (orientationFilter !== 'either' && orientationFilter !== orientation) return false;

  const families = filter.tacticFamilies ?? [];
  if (families.length > 0) {
    const family = motif != null ? TACTIC_FAMILY_FOR_MOTIF[motif] : undefined;
    if (family == null || !families.includes(family)) return false;
  }

  const depthMin = filter.tacticDepthMin ?? DEFAULT_TACTIC_DEPTH_VALUE.min;
  const depthMax = filter.tacticDepthMax ?? DEFAULT_TACTIC_DEPTH_VALUE.max;
  if (depthRaw != null && (depthRaw < depthMin || depthRaw > depthMax)) return false;

  return true;
}

// ─── Arrow builders ───────────────────────────────────────────────────────────

/**
 * Build arrows for the root position (ply 0): both the best-move (blue) and the
 * flaw-move (red) arrows are shown simultaneously, matching the miniboard. The
 * best-move (blue) arrow is shown for BOTH orientations — in the allowed line it
 * still tells the user what they should have played instead of the flaw move.
 * Colors and labels come exclusively from theme.ts — no hex literals here.
 */
function buildRootArrows(
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
 * Flaw lead-in (allowed line, ply 1 = the prepended flaw move): red (the user's
 * error), but still carries its depth-countdown label so the counter is unbroken.
 */
function buildPvArrow(
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

interface TacticLineExplorerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** ID of the game containing the flaw. */
  gameId: number | null;
  /** Real game ply of the flaw. */
  ply: number | null;
}

// ─── ExplorerBody — shared body between Dialog and Drawer ────────────────────

/**
 * Inner body of the explorer (shared by the Dialog and Drawer surfaces so the
 * layout logic is not duplicated). The outer wrapper supplies the surface shell.
 */
function ExplorerBody({
  gameId,
  ply,
  open,
  isMobile,
}: {
  gameId: number | null;
  ply: number | null;
  open: boolean;
  isMobile: boolean;
}) {
  const { data, isLoading, isError } = useTacticLines(gameId, ply, open);

  // Orientation state. Default to 'missed'; if only one line exists, force that
  // orientation and hide the toggle (Pitfall 5 / D-05 single-line rule).
  const [orientation, setOrientation] = useState<TacticDepthOrientation>('missed');
  const [flipped, setFlipped] = useState(false);

  // Apply the active flaw filter (Phase 135 UAT): an orientation is visible only when
  // its tactic is actually TAGGED (motif present) AND its line exists AND it passes the
  // same tactic filters the Games/Flaws tabs use, so a missed/allowed tag+line filtered
  // out in the list is also hidden here.
  //
  // The motif gate matters because the backend ALWAYS returns missed_moves (the
  // decision-position engine PV exists for every flaw, tagged or not) — only the motif
  // tells us a missed tactic was actually detected. Without it, an allowed-only flaw
  // would still report hasMissed=true and default to the flaw_ply PV instead of the
  // flaw_ply+1 refutation line (Phase 135 UAT).
  const [flawFilter] = useFlawFilterStore();
  const hasMissed =
    data?.missed_motif != null &&
    data.missed_moves != null &&
    tacticOrientationPasses('missed', data.missed_motif, data.missed_depth, flawFilter);
  const hasAllowed =
    data?.allowed_motif != null &&
    data.allowed_moves != null &&
    tacticOrientationPasses('allowed', data.allowed_motif, data.allowed_depth, flawFilter);
  const showToggle = hasMissed && hasAllowed;

  // Default the board to the flaw-maker's perspective (Phase 135 UAT): orient so the
  // side to move at the decision position is at the bottom, flipping when Black moved.
  // Keyed on position_fen so it re-applies per flaw but preserves manual flips within one.
  const positionFen = data?.position_fen;
  useEffect(() => {
    if (positionFen != null) setFlipped(isBlackToMove(positionFen));
  }, [positionFen]);

  // Resolve to a visible orientation: keep the user's choice when it is visible,
  // otherwise fall back to the other visible one (single-line / filtered-out cases).
  const resolvedOrientation: TacticDepthOrientation =
    orientation === 'allowed' ? (hasAllowed ? 'allowed' : 'missed') : hasMissed ? 'missed' : 'allowed';

  // Active line based on orientation. A filtered-out / absent orientation yields null
  // moves so the empty state shows instead of a hidden line.
  const activeMoves =
    resolvedOrientation === 'missed'
      ? hasMissed
        ? (data?.missed_moves ?? null)
        : null
      : hasAllowed
        ? (data?.allowed_moves ?? null)
        : null;
  const activeDepthRaw =
    resolvedOrientation === 'missed'
      ? (data?.missed_depth ?? 0)
      : (data?.allowed_depth ?? 0);
  const activePlyIndex =
    resolvedOrientation === 'missed'
      ? (data?.missed_tactic_ply_index ?? 0)
      : (data?.allowed_tactic_ply_index ?? 0);

  // PV stepper hook (useTacticLine from Plan 02).
  // FALLBACK_FEN is used when data is absent (loading/error) so useTacticLine
  // never receives an invalid FEN — hooks must always be called unconditionally.
  // Destructuring extracts containerRef so it can be passed directly as a `ref`
  // prop without triggering eslint-plugin-react-hooks/refs (v7 false-positive
  // on containerRef property access inside JSX).
  const {
    position,
    currentPly,
    lastMove,
    displayDepth,
    isPayoff,
    goForward,
    goBack,
    goToMove,
    reset,
    canGoForward,
    canGoBack,
    containerRef,
  } = useTacticLine({
    moves: activeMoves,
    rootFen: data?.position_fen ?? FALLBACK_FEN,
    tacticDepthRaw: activeDepthRaw,
    orientation: resolvedOrientation,
  });

  // Depth labels for root-position arrows.
  const missedDepthLabel =
    data?.missed_depth != null
      ? String(toDisplayDepthForOrientation(data.missed_depth, 'missed'))
      : undefined;
  const allowedDepthLabel =
    data?.allowed_depth != null
      ? String(toDisplayDepthForOrientation(data.allowed_depth, 'allowed'))
      : undefined;

  // Build arrows for the current ply.
  const currentArrows: BoardArrow[] =
    data != null && currentPly === 0
      ? buildRootArrows(
          data.position_fen,
          data.best_move_uci,
          data.flaw_move_san,
          missedDepthLabel,
          allowedDepthLabel,
        )
      : buildPvArrow(
          lastMove,
          displayDepth,
          isPayoff,
          resolvedOrientation,
          // Allowed line, ply 1 is the prepended flaw move (the user's error) — show it
          // red with no depth label so the refutation countdown starts at flaw_ply+1.
          resolvedOrientation === 'allowed' && currentPly === 1,
        );

  // Toggle between Missed and Allowed orientations (resets stepper). No-op when the
  // already-active tag is clicked so it doesn't reset the line you're viewing.
  const handleOrientationChange = (next: TacticDepthOrientation) => {
    if (next === resolvedOrientation) return;
    setOrientation(next);
    reset();
  };

  // ── Loading / error / empty states ─────────────────────────────────────────

  if (isLoading) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-4 p-8"
        aria-label="Loading tactic line"
      >
        <div className="w-full aspect-square max-w-xs bg-card/50 rounded animate-pulse" />
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isError) {
    return (
      <p className="text-sm text-muted-foreground p-4">
        Failed to load tactic line. Please try again.
      </p>
    );
  }

  if (!data || activeMoves == null) {
    return (
      <p className="text-sm text-muted-foreground p-4">
        Tactic line not available for this flaw.
      </p>
    );
  }

  // ── Eval indicator (Phase 135 UAT) ───────────────────────────────────────────
  // Stockfish eval of the CURRENT board, shown in the header row (top-right, outside
  // the board) and updated as you step. Always white-POV (positive = white's
  // advantage) — never flipped to the mover. Ply 0 is the shared decision position
  // (both orientations), so it reads the decision-position eval (missed_eval_cp).
  // Once the allowed line steps past the flaw move (ply >= 1) the board is the
  // post-flaw position, so the eval becomes allowed_eval_cp. (The backend sources
  // these one ply back from the naive position because game_positions.eval_cp is the
  // post-move eval — see fetch_tactic_lines.) The missed (best) line holds the
  // decision eval along its PV; we only store these two engine evals, so intermediate
  // PV plies reuse the line's anchor eval (the PV is best play, eval ~constant).
  const showsPostFlawEval = resolvedOrientation === 'allowed' && currentPly >= 1;
  const evalCp = showsPostFlawEval ? data.allowed_eval_cp : data.missed_eval_cp;
  const evalMate = showsPostFlawEval ? data.allowed_eval_mate : data.missed_eval_mate;
  // Mate counts down as you step toward it (Phase 135 UAT). The eval anchor is the
  // decision position (ply 0) for the missed line, or the post-flaw position (ply 1)
  // for the allowed line — the flaw move flips the side to move, so the anchor's
  // side-to-move is inverted there. mateAtPly offsets the mating side's remaining
  // moves by how many plies we've stepped past that anchor.
  const anchorSideIsWhite = showsPostFlawEval
    ? isBlackToMove(data.position_fen)
    : !isBlackToMove(data.position_fen);
  const mateStepPlies = showsPostFlawEval ? currentPly - 1 : currentPly;
  const displayMate =
    evalMate != null ? mateAtPly(evalMate, mateStepPlies, evalMate > 0 === anchorSideIsWhite) : null;
  const hasEval = evalCp != null || evalMate != null;
  const evalBadge = hasEval ? (
    <div
      data-testid="tactic-eval"
      className="ml-auto inline-flex items-center gap-1 rounded-md border border-border bg-background/90 px-2 py-0.5 text-sm font-semibold shadow-sm"
    >
      <Cpu className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      {formatFlawEvalPart(evalCp, displayMate)}
    </div>
  ) : null;

  // ── Explorer header (Missed/Allowed switch or single motif chip + eval badge) ──

  // Phase 135 UAT: when both lines have a tagged motif, the colored motif tags ARE the
  // switch — clicking the blue (Missed) or red (Allowed) tag selects that line, and the
  // active tag gets a white border. When only one motif is present we still show that
  // single tag (non-interactive) so the user always sees which tactic is being explored.
  // The Stockfish eval badge sits at the right end of this row (top-right, outside the
  // board) and updates per step.
  const showSwitch = showToggle && data.missed_motif != null && data.allowed_motif != null;

  const headerRow = (
    <div className="flex items-center gap-3 flex-wrap">
      {showSwitch ? (
        <div className="flex gap-2" role="group" aria-label="Tactic line switch">
          <TacticMotifChip
            motif={data.missed_motif!}
            flawId={gameId ?? 0}
            orientation="missed"
            selected={resolvedOrientation === 'missed'}
            testId="tactic-toggle-missed"
            onActivate={() => handleOrientationChange('missed')}
            noTruncate={!isMobile}
          />
          <TacticMotifChip
            motif={data.allowed_motif!}
            flawId={gameId ?? 0}
            orientation="allowed"
            selected={resolvedOrientation === 'allowed'}
            testId="tactic-toggle-allowed"
            onActivate={() => handleOrientationChange('allowed')}
            noTruncate={!isMobile}
          />
        </div>
      ) : (
        <div className="flex gap-2">
          {hasMissed && data.missed_motif != null && (
            <TacticMotifChip
              motif={data.missed_motif}
              flawId={gameId ?? 0}
              orientation="missed"
              noTruncate={!isMobile}
            />
          )}
          {hasAllowed && data.allowed_motif != null && (
            <TacticMotifChip
              motif={data.allowed_motif}
              flawId={gameId ?? 0}
              orientation="allowed"
              noTruncate={!isMobile}
            />
          )}
        </div>
      )}
      {evalBadge}
    </div>
  );

  // ── Board ───────────────────────────────────────────────────────────────────

  const board = (
    <div
      ref={containerRef}
      aria-label="Tactic board"
      // Both surfaces: the board fills the (now single-column) width as a square. The
      // Dialog is sized to the board (sm:max-w-md) so it renders at a comfortable size.
      className="w-full aspect-square"
    >
      <ChessBoard
        id="tactic-explorer-board"
        position={position}
        onPieceDrop={() => false}
        flipped={flipped}
        lastMove={lastMove ?? undefined}
        arrows={currentArrows.length > 0 ? currentArrows : undefined}
      />
    </div>
  );

  // ── BoardControls ───────────────────────────────────────────────────────────

  const controls = (
    <BoardControls
      onBack={goBack}
      onForward={goForward}
      onReset={reset}
      onFlip={() => setFlipped((f) => !f)}
      canGoBack={canGoBack}
      canGoForward={canGoForward}
      size={isMobile ? 'md' : 'sm'}
    />
  );

  // ── Horizontal move list (Phase 135 UAT mobile; Quick 260625 desktop) ───────
  // Same look as the Openings move list (shared HorizontalMoveList), but keeps
  // the tactic decorations: colored depth-0 punchline move, dimmed payoff /
  // flaw-lead-in moves, and the severity glyph on the allowed-line flaw move.
  // Used by BOTH surfaces (the desktop vertical ladder was retired here).
  const flawSeverity = data.flaw_severity;
  const moveItems: HorizontalMoveItem[] = activeMoves.map((san, i) => {
    const isPunchline = i === activePlyIndex;
    const isPayoff = i > activePlyIndex;
    const isFlawLeadIn = resolvedOrientation === 'allowed' && i === 0;
    const showGlyph = isFlawLeadIn && flawSeverity !== 'inaccuracy';
    return {
      key: i,
      ply: i + 1,
      numberLabel: moveLabel(data.flaw_ply, i),
      san,
      isCurrent: currentPly === i + 1,
      color: isPunchline
        ? resolvedOrientation === 'missed'
          ? TAC_MISSED
          : TAC_ALLOWED
        : undefined,
      dimmed: isPayoff || isFlawLeadIn,
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

  const moveList = (
    <HorizontalMoveList
      items={moveItems}
      onMoveClick={goToMove}
      heightClass={MOVE_LIST_HEIGHT}
      testId="tactic-san-ladder"
    />
  );

  // ── Layout: single-column stacked on BOTH surfaces (Quick 260625) ────────────
  // header → board → controls → horizontal move list. The desktop Dialog is sized to
  // the board (sm:max-w-md) and grows taller (max-h-[90vh]) for the move list. Mobile
  // adds its own padding/scroll since the Drawer body has none; the Dialog supplies p-6.
  return (
    <div
      className={
        isMobile ? 'flex flex-col gap-3 px-4 pb-4 overflow-y-auto' : 'flex flex-col gap-3'
      }
    >
      {headerRow}
      {board}
      {controls}
      {moveList}
    </div>
  );
}

// ─── TacticLineExplorer ───────────────────────────────────────────────────────

/**
 * Public component: renders Dialog (desktop) or Drawer (mobile) per D-05.
 * Switching surface type is driven by useIsMobile (MOBILE_BREAKPOINT_PX = 768).
 */
export function TacticLineExplorer({
  open,
  onOpenChange,
  gameId,
  ply,
}: TacticLineExplorerProps) {
  const isMobile = useIsMobile();
  const title = 'Explore Tactic';

  const body = <ExplorerBody gameId={gameId} ply={ply} open={open} isMobile={isMobile} />;

  if (isMobile) {
    // Right-side drawer with a top-right close button, mirroring MobileFilterDrawer
    // (Phase 135 UAT mobile): full width on phones, 3/4 on small tablets.
    const closeLabel = 'Close tactic explorer';
    return (
      <Drawer open={open} onOpenChange={onOpenChange} direction="right">
        <DrawerContent
          data-testid="tactic-explorer-drawer"
          className="!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[95vh]"
        >
          <DrawerHeader className="flex flex-row items-center justify-between">
            <DrawerTitle className="text-base font-semibold">{title}</DrawerTitle>
            <Tooltip content={closeLabel}>
              <DrawerClose asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={closeLabel}
                  data-testid="tactic-explorer-close"
                >
                  <X className="h-4 w-4" />
                </Button>
              </DrawerClose>
            </Tooltip>
          </DrawerHeader>
          {body}
        </DrawerContent>
      </Drawer>
    );
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onOpenChange(false)}>
      <DialogContent
        data-testid="tactic-explorer-dialog"
        // Sized to the board (sm:max-w-md), free to grow taller for the move list
        // below the controls (max-h-[90vh]) — Quick 260625.
        className="no-scrollbar max-w-[calc(100%-1rem)] sm:max-w-md overflow-y-auto max-h-[90vh] sm:p-6"
        aria-label={title}
      >
        <DialogTitle className="text-base font-semibold">{title}</DialogTitle>
        {body}
      </DialogContent>
    </Dialog>
  );
}
