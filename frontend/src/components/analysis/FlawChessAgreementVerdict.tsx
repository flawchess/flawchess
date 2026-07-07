/**
 * FlawChessAgreementVerdict — the FlawChess-vs-Stockfish agreement prose
 * verdict rendered below `FlawChessEngineLines` on `/analysis` (Phase 157-02,
 * REVIEW-02). Consumes the Plan 01 pure classifier
 * (`@/lib/flawChessVerdict`'s `computeFlawChessVerdict`) to narrate whether
 * FlawChess's practical #1 pick agrees with Stockfish's objective #1 pick,
 * and if not, whether the divergence is a cheap/"safe" swap or a costly
 * "sharp" trap for a human. Named moves render as `ProseSpan`s (extracted in
 * Task 1 from `MaiaMoveQualityBar`'s `ProseMoveSpan`): hovering isolates that
 * pick's board arrow (amber = FlawChess, blue = Stockfish, D-09), the popover
 * shows an engine-labeled two-line breakdown (D-10), and clicking plays the
 * move as a free move via `onPlayMove` (D-11).
 *
 * D-01: the Stockfish side is read from `stockfishLine` (the caller passes
 * `engine.pvLines[0]`) — NEVER `engineTopLines[0]`, which silently degrades to
 * a FlawChess row when standalone Stockfish is off.
 * D-02/D-03: when `engineEnabled` is false, only the fixed-height muted
 * prompt renders — the classifier is not consulted at all.
 * D-06: a null classifier result (partial snapshot mid-search, or an
 * unresolvable UCI->SAN conversion) falls back to the SAME muted slot so the
 * tier can refine live with the search without ever emitting a bogus tier or
 * shifting the layout.
 * D-08: no UI string in this module reads the bare unqualified phrase this
 * decision forbids (see REQUIREMENTS.md REVIEW-02 / ARROW-04).
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { Chess } from 'chess.js';

import { computeFlawChessVerdict, type FlawChessVerdictResult } from '@/lib/flawChessVerdict';
import type { RankedLine } from '@/lib/engine/types';
import type { PvLine } from '@/hooks/uciParser';
import { sideToMoveFromFen, expectedScoreToWhitePovCp, type MoverColor } from '@/lib/liveFlaw';
import { formatScore } from '@/components/analysis/EngineLines';
import { ProseSpan } from '@/components/analysis/ProseSpan';
import type { HoveredQualityMove } from '@/components/analysis/MaiaMoveQualityBar';

/** Hover-intent delay before a verdict move's popover opens (ms) — matches
 *  MaiaMoveQualityBar's PROSE_POPOVER_OPEN_DELAY_MS / InfoPopover precedent. */
const PROSE_POPOVER_OPEN_DELAY_MS = 100;

/** Shown in the fixed-height slot whenever there's nothing to narrate yet:
 *  Stockfish off (D-03), a partial snapshot mid-search (D-06), or an
 *  unresolvable UCI->SAN conversion (Pitfall 2 — never fall through to a
 *  raw-UCI render). */
const MUTED_PROMPT_TEXT = 'Turn on Stockfish to compare picks.';

export interface FlawChessAgreementVerdictProps {
  /** FlawChess's practical #1 pick (`flawChessEngine.rankedLines[0]`), or null pre-snapshot. */
  flawChessLine: RankedLine | null;
  /** Stockfish's TRUE objective #1 pick (`engine.pvLines[0]`, D-01) — never `engineTopLines[0]`. */
  stockfishLine: PvLine | null;
  /** The full ranked-lines list, used to look up whether the Stockfish pick was ALSO FlawChess-ranked (D-10). */
  flawChessRankedLines: RankedLine[];
  /** Standalone Stockfish toggle — gates the whole render (D-02/D-03). */
  engineEnabled: boolean;
  /** The shared on-page Maia/FlawChess ELO (`selectedElo`) — cited in the safe-divergence prose to
   *  frame the human-friendliness of the practical pick at this skill level. */
  elo: number;
  /** FEN of the position both engines analyzed — used to convert each pick's UCI to a legal SAN. */
  baseFen: string;
  /** Lifts the hovered pick's move (SAN + tier color) for the board-arrow overlay, or null on leave (D-09). */
  onHoverMovesChange?: (moves: HoveredQualityMove[] | null) => void;
  /** Plays a named pick as a free move on the board (D-11). */
  onPlayMove?: (san: string) => void;
}

/** Which engine's pick is currently hovered/focused — drives both the open popover and the lifted arrow. */
type ActiveRole = 'flawchess' | 'stockfish' | null;

/**
 * Converts a root-relative UCI move to its SAN at `baseFen`, or null when it's
 * not legal there (a stale/partial snapshot lagging the current position).
 * Never feeds a raw UCI string to a rendered span or the hover callback
 * (Pitfall 2) — callers must treat a null result as "nothing to show".
 */
function uciToSan(baseFen: string, uci: string): string | null {
  try {
    const from = uci.slice(0, 2);
    const to = uci.slice(2, 4);
    const promotion = uci.length > 4 ? uci.slice(4, 5) : undefined;
    const move = new Chess(baseFen).move({ from, to, promotion });
    return move ? move.san : null;
  } catch {
    return null;
  }
}

/** D-10 popover body for the FlawChess pick: always both lines (it's a ranked line with its own objective eval). */
function FlawChessPickPopoverBody({
  line,
  mover,
}: {
  line: RankedLine;
  mover: MoverColor;
}): React.ReactElement {
  const practicalCp = expectedScoreToWhitePovCp(line.practicalScore, mover);
  return (
    <>
      <div>FlawChess: {formatScore(practicalCp, null)} (practical)</div>
      <div>Stockfish: {formatScore(line.objectiveEvalCp, null)} (objective)</div>
    </>
  );
}

/** D-10 popover body for the Stockfish pick: the Stockfish line always shows; the
 *  FlawChess line shows ONLY when `matchedLine` (a rootMove match in
 *  flawChessRankedLines) is non-null — otherwise it's omitted entirely, no
 *  placeholder. */
function StockfishPickPopoverBody({
  evalCp,
  evalMate,
  matchedLine,
  mover,
}: {
  evalCp: number | null;
  evalMate: number | null;
  matchedLine: RankedLine | null;
  mover: MoverColor;
}): React.ReactElement {
  return (
    <>
      {matchedLine && (
        <div>FlawChess: {formatScore(expectedScoreToWhitePovCp(matchedLine.practicalScore, mover), null)} (practical)</div>
      )}
      <div>Stockfish: {formatScore(evalCp, evalMate)} (objective)</div>
    </>
  );
}

/** Assembles the D-07 prose sentence for the given tier, interpolating the
 *  already-built move spans. `moveSpan` is the single shared span used for the
 *  `aligned` tier (same move on both sides — only 1 span, per D-07/D-08). */
function renderVerdictSentence(
  verdict: FlawChessVerdictResult,
  elo: number,
  moveSpan: React.ReactNode,
  fcSpan: React.ReactNode,
  sfSpan: React.ReactNode,
): React.ReactNode {
  if (verdict.tier === 'aligned') {
    const evalText = formatScore(verdict.stockfishMove.evalCp, verdict.stockfishMove.evalMate);
    return (
      <>
        FlawChess and Stockfish agree on {moveSpan} — objectively {evalText}, and the practical pick too.
      </>
    );
  }

  const sfEvalText = formatScore(verdict.stockfishMove.evalCp, verdict.stockfishMove.evalMate);
  const fcEvalText = formatScore(verdict.flawChessMove.evalCp, verdict.flawChessMove.evalMate);

  if (verdict.tier === 'safe') {
    // Only claim "nearly the same eval" when the rendered centipawns actually agree (D-05 tier is
    // expected-score-based, which saturates at high evals — a ~1.5-pawn gap can still be 'safe').
    return (
      <>
        Objectively {sfSpan} ({sfEvalText}). But for a human at {elo} ELO here, FlawChess plays {fcSpan} ({fcEvalText})
        {' — '}
        {verdict.nearlySameEval
          ? 'nearly the same eval, far easier to find and play.'
          : "a safe, practical pick that's far easier to find and play."}
      </>
    );
  }

  return (
    <>
      {sfSpan} is objectively best ({sfEvalText}) but it&apos;s a trap for humans. FlawChess plays the safer {fcSpan}{' '}
      ({fcEvalText}) instead.
    </>
  );
}

export function FlawChessAgreementVerdict({
  flawChessLine,
  stockfishLine,
  flawChessRankedLines,
  engineEnabled,
  elo,
  baseFen,
  onHoverMovesChange,
  onPlayMove,
}: FlawChessAgreementVerdictProps): React.ReactElement {
  const [activeRole, setActiveRole] = useState<ActiveRole>(null);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const mover = sideToMoveFromFen(baseFen);

  // D-02/D-03: the classifier is only ever invoked when Stockfish is on.
  const verdict = useMemo<FlawChessVerdictResult | null>(
    () => (engineEnabled ? computeFlawChessVerdict(flawChessLine, stockfishLine, mover) : null),
    [engineEnabled, flawChessLine, stockfishLine, mover],
  );

  const fcSan = useMemo(
    () => (verdict ? uciToSan(baseFen, verdict.flawChessMove.uci) : null),
    [verdict, baseFen],
  );
  const sfSan = useMemo(
    () => (verdict ? uciToSan(baseFen, verdict.stockfishMove.uci) : null),
    [verdict, baseFen],
  );

  // D-10: was the Stockfish pick ALSO ranked by FlawChess (any rank, not just #1)?
  const matchedFlawChessLineForSf = useMemo(() => {
    if (!verdict) return null;
    return flawChessRankedLines.find((line) => line.rootMove === verdict.stockfishMove.uci) ?? null;
  }, [verdict, flawChessRankedLines]);

  const hoveredArrowMoves = useMemo<HoveredQualityMove[] | null>(() => {
    if (!verdict || activeRole === null) return null;
    if (activeRole === 'flawchess') {
      return fcSan ? [{ san: fcSan, color: verdict.flawChessMove.arrowColor }] : null;
    }
    return sfSan ? [{ san: sfSan, color: verdict.stockfishMove.arrowColor }] : null;
  }, [verdict, activeRole, fcSan, sfSan]);

  // Lift the hovered pick's move for the board-arrow overlay; clear on leave/unmount.
  useEffect(() => {
    if (!onHoverMovesChange) return;
    onHoverMovesChange(hoveredArrowMoves);
    return () => onHoverMovesChange(null);
  }, [hoveredArrowMoves, onHoverMovesChange]);

  // Clear a pending hover-intent timer if the component unmounts mid-hover.
  useEffect(
    () => () => {
      if (hoverTimer.current) clearTimeout(hoverTimer.current);
    },
    [],
  );

  const clearHoverTimer = (): void => {
    if (hoverTimer.current) {
      clearTimeout(hoverTimer.current);
      hoverTimer.current = null;
    }
  };
  const openNow = (role: ActiveRole): void => {
    clearHoverTimer();
    setActiveRole(role);
  };
  const openDelayed = (role: ActiveRole): void => {
    clearHoverTimer();
    hoverTimer.current = setTimeout(() => openNow(role), PROSE_POPOVER_OPEN_DELAY_MS);
  };
  const closeProse = (): void => {
    clearHoverTimer();
    setActiveRole(null);
  };

  // D-02/D-03 (Stockfish off) + D-06 (partial snapshot mid-search, or an
  // unresolvable UCI->SAN conversion) all collapse to the SAME fixed-height
  // muted slot — no tier prose, no layout jump.
  // `flawChessLine` is redundant with `!verdict` here (computeFlawChessVerdict
  // only ever returns non-null when flawChessLine is non-null) but keeps this
  // narrowing sound for TypeScript without an `as` cast below.
  if (!engineEnabled || !verdict || !fcSan || !sfSan || !flawChessLine) {
    return (
      <div className="min-h-[1.5rem] text-sm" data-testid="flawchess-verdict-slot">
        <span className="text-muted-foreground" data-testid="flawchess-verdict-prompt">
          {MUTED_PROMPT_TEXT}
        </span>
      </div>
    );
  }

  const fcSpan = (
    <ProseSpan
      label={fcSan}
      textColor={verdict.flawChessMove.textColor}
      ariaLabel={`${fcSan}, FlawChess's practical pick, evaluated ${formatScore(
        verdict.flawChessMove.evalCp,
        verdict.flawChessMove.evalMate,
      )}. Click to play it.`}
      testId={`flawchess-verdict-move-${fcSan}`}
      tooltipTestId={`flawchess-verdict-tooltip-${fcSan}`}
      isOpen={activeRole === 'flawchess'}
      onOpenDelayed={() => openDelayed('flawchess')}
      onOpenNow={() => openNow('flawchess')}
      onClose={closeProse}
      onPlay={
        onPlayMove
          ? () => {
              closeProse();
              onPlayMove(fcSan);
            }
          : undefined
      }
    >
      <FlawChessPickPopoverBody line={flawChessLine} mover={mover} />
    </ProseSpan>
  );

  const sfSpan = (
    <ProseSpan
      label={sfSan}
      textColor={verdict.stockfishMove.textColor}
      ariaLabel={`${sfSan}, Stockfish's objective pick, evaluated ${formatScore(
        verdict.stockfishMove.evalCp,
        verdict.stockfishMove.evalMate,
      )}. Click to play it.`}
      testId={`flawchess-verdict-move-${sfSan}`}
      tooltipTestId={`flawchess-verdict-tooltip-${sfSan}`}
      isOpen={activeRole === 'stockfish'}
      onOpenDelayed={() => openDelayed('stockfish')}
      onOpenNow={() => openNow('stockfish')}
      onClose={closeProse}
      onPlay={
        onPlayMove
          ? () => {
              closeProse();
              onPlayMove(sfSan);
            }
          : undefined
      }
    >
      <StockfishPickPopoverBody
        evalCp={verdict.stockfishMove.evalCp}
        evalMate={verdict.stockfishMove.evalMate}
        matchedLine={matchedFlawChessLineForSf}
        mover={mover}
      />
    </ProseSpan>
  );

  // Aligned: same move on both sides — a single shared span (fcSan === sfSan),
  // rendered via the FlawChess pick's own span (both-lines popover body) so
  // hovering it lights the FlawChess arrow color (D-09's aligned convention).
  const sentence = renderVerdictSentence(verdict, elo, fcSpan, fcSpan, sfSpan);

  return (
    <div className="min-h-[1.5rem] text-sm" data-testid="flawchess-verdict-slot">
      <span data-testid="flawchess-verdict-sentence">{sentence}</span>
    </div>
  );
}
