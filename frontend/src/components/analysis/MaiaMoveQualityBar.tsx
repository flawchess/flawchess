/**
 * MaiaMoveQualityBar — a stacked horizontal "move-quality" bar shown below the
 * Human Move Probability chart + ELO slider (quick 260705-kfg; mockup
 * screenshots/maia-bar.png).
 *
 * It reuses the SAME inputs the Moves-by-Rating chart already receives — the
 * shown candidate SANs, their Stockfish-graded quality, and the Maia per-ELO
 * curve — and aggregates them into four severity segments (Blunders / Mistakes
 * / Inaccuracies / Good Moves), plus a trailing neutral segment for candidates
 * the streaming grading pass hasn't classified yet. Segment widths are the
 * moves' Maia probability mass at the selected ELO, normalized so the bar
 * always fills.
 *
 * Interaction (D-locked in the quick task):
 * - The bar shows alone by default. Hovering (or tapping, for touch) a segment
 *   reveals ONLY that segment's move list under the bar.
 * - The same hover lifts the segment's moves up via `onHoverMovesChange` so the
 *   page can draw a board arrow per move in the segment's severity color.
 * - No icons inside the bars (mockup had severity glyphs — omitted).
 *
 * Resting-state text (quick 260705-m3z): when no segment is hovered, the slot
 * below the bar shows a prose position verdict at the selected ELO
 * (positionVerdict.ts's computePositionVerdict) instead of static help text.
 * Named moves in the sentence are interactive spans. Hovering (or tapping, for
 * touch) draws a severity-colored board arrow (reusing the same
 * `onHoverMovesChange` mechanism as the bar segments) AND opens a white Popover
 * with the move's Maia % + Stockfish eval. The popover mirrors InfoPopover: a
 * short hover-intent delay plus a content-bridge (moving the pointer onto the
 * popover keeps it open) so it doesn't flicker. Falls back to the original help
 * text when evals aren't loaded yet or none of the shown moves are graded.
 */

import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import {
  MOVE_QUALITY_BLUNDER,
  MOVE_QUALITY_GOOD,
  MOVE_QUALITY_INACCURACY,
  MOVE_QUALITY_MISTAKE,
  MOVE_QUALITY_PENDING,
} from '@/lib/theme';
import {
  bucketMovesByQuality,
  type QualityBucket,
  type QualityBucketKey,
} from '@/lib/moveQuality';
import { computePositionVerdict, formatVerdictEval, type PositionVerdictResult, type VerdictMove } from '@/lib/positionVerdict';
import { ProseSpan } from '@/components/analysis/ProseSpan';
import type { MoveQualityEval } from '@/components/analysis/MovesByRatingChart';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';

/** One move surfaced to the page for a board arrow: its SAN + severity color. */
export interface HoveredQualityMove {
  san: string;
  color: string;
}

/** Per-bucket display metadata. `pending` is non-interactive (no label/hover). */
const BUCKET_META: Record<
  QualityBucketKey,
  { label: string; color: string; interactive: boolean; darkText: boolean }
> = {
  blunder: { label: 'Blunders', color: MOVE_QUALITY_BLUNDER, interactive: true, darkText: false },
  mistake: { label: 'Mistakes', color: MOVE_QUALITY_MISTAKE, interactive: true, darkText: false },
  inaccuracy: {
    label: 'Inaccuracies',
    color: MOVE_QUALITY_INACCURACY,
    interactive: true,
    darkText: true,
  },
  good: { label: 'Good Moves', color: MOVE_QUALITY_GOOD, interactive: true, darkText: true },
  pending: { label: 'Pending', color: MOVE_QUALITY_PENDING, interactive: false, darkText: false },
};

// A segment narrower than this (% of the bar) hides its inline percentage so the
// text never overflows a sliver; the value is still reachable via the hover list.
const MIN_INLINE_LABEL_PCT = 12;

export interface MaiaMoveQualityBarProps {
  /** useMaiaEngine's perElo (same value the chart receives); [] renders nothing. */
  perElo: MoveCurvePoint[];
  /** The ELO whose Maia probabilities weight the segments (EloSelector's value). */
  selectedElo: number;
  /** The shown candidate set (Analysis.tsx's selectCandidatesByMass output). */
  shownSans: string[];
  /** Per-SAN Stockfish-graded quality + eval, keyed by SAN (D-08). */
  qualityBySan: Map<string, MoveQualityEval>;
  /**
   * Fired with the hovered segment's moves (SAN + severity color) so the page
   * can draw board arrows, or null when nothing is hovered. Omitted on surfaces
   * with no board in view (currently always wired, but kept optional).
   */
  onHoverMovesChange?: (moves: HoveredQualityMove[] | null) => void;
  /** True when the analysed position is the opponent's move — frames the verdict
   *  around "your opponent" rather than "you" (quick 260705-m3z). */
  isOpponentToMove?: boolean;
  /** Plays a named prose move as a free move on the board (quick 260705-mth).
   *  Receives the move's SAN at the current position. Omitted where no board is
   *  in view (kept optional; currently always wired from Analysis). */
  onPlayMove?: (san: string) => void;
}

/** Rounded Maia probability as a percent string (matches the chart tooltip). */
function pct(probability: number): string {
  return `${Math.round(probability * 100)}%`;
}

/**
 * Joins rendered move-span nodes into prose grammar (mirrors positionVerdict's
 * joinMoveNames, but produces interactive React nodes instead of a string):
 * 1 -> A; 2 -> "A {c} B"; 3+ -> "A, B, ... {c} Z" (no comma before the final
 * conjunction).
 */
function interleaveWithConjunction(nodes: React.ReactNode[], conjunction: 'and' | 'or'): React.ReactNode {
  const n = nodes.length;
  if (n === 0) return null;
  if (n === 1) return nodes[0];
  const parts: React.ReactNode[] = [];
  nodes.forEach((node, i) => {
    parts.push(<Fragment key={i}>{node}</Fragment>);
    if (i < n - 2) parts.push(', ');
    else if (i === n - 2) parts.push(` ${conjunction} `);
  });
  return <>{parts}</>;
}

/** Hover-intent delay before a prose move's popover opens (ms) — matches InfoPopover. */
const PROSE_POPOVER_OPEN_DELAY_MS = 100;

/**
 * One interactive move span (controlled by the parent). Hover/tap/focus opens a
 * white Maia%+eval popover with the same mechanics + styling as InfoPopover
 * (hover-intent open, content-bridge, outside-click/Escape close via Radix). The
 * parent owns the open state + hover timer so the board arrow it lifts stays in
 * sync and never fights the bar-segment hover.
 *
 * Clicking/tapping the move PLAYS it as a free move on the board (quick
 * 260705-mth). The show-vs-play split keys off whether the popover was already
 * open when the press started (captured at pointerdown, before focus/hover can
 * flip it): open-at-press → play; closed-at-press → just reveal it. That gives
 * "hover shows, click plays" on desktop and "first tap shows, second tap plays"
 * on touch from a single rule. We anchor (not trigger) the popover so Radix
 * never toggles open state on click and fights this logic — open is fully
 * parent-controlled; onOpenChange only carries Radix's outside-click/Escape close.
 */
function ProseMoveSpan({
  move,
  isOpen,
  onOpenDelayed,
  onOpenNow,
  onClose,
  onPlay,
}: {
  move: VerdictMove;
  isOpen: boolean;
  onOpenDelayed: () => void;
  onOpenNow: () => void;
  onClose: () => void;
  onPlay?: () => void;
}): React.ReactElement {
  const evalText = formatVerdictEval(move.evalCp, move.evalMate);
  const ariaLabel = `${move.san}, ${move.maiaPct}% at this rating, evaluated ${evalText}. Click to play it.`;

  return (
    <ProseSpan
      label={move.san}
      textColor={move.textColor}
      ariaLabel={ariaLabel}
      testId={`maia-prose-move-${move.san}`}
      tooltipTestId={`maia-prose-move-tooltip-${move.san}`}
      isOpen={isOpen}
      onOpenDelayed={onOpenDelayed}
      onOpenNow={onOpenNow}
      onClose={onClose}
      onPlay={onPlay}
    >
      {`${move.maiaPct}% at this rating · ${evalText}`}
    </ProseSpan>
  );
}

/**
 * Assembles the prose verdict sentence for the resting-state slot, following
 * the safe/tricky/highly-difficult copy templates. `renderMove` produces the
 * interactive span for one named move. `owner` is "you" on the user's move or
 * "your opponent" when the position is the opponent's move (quick 260705-m3z).
 */
function renderVerdictSentence(
  verdict: PositionVerdictResult,
  elo: number,
  owner: string,
  renderMove: (m: VerdictMove) => React.ReactNode,
): React.ReactNode {
  const goodNodes = verdict.moves.filter((m) => m.role === 'good').map(renderMove);
  const badNodes = verdict.moves.filter((m) => m.role === 'bad').map(renderMove);
  const escapeMove = verdict.moves.find((m) => m.role === 'escape');

  if (verdict.tier === 'safe') {
    if (goodNodes.length === 0) return <>At {elo} Elo, this position looks safe for {owner}.</>;
    return (
      <>
        At {elo} Elo, this position is safe for {owner} — {interleaveWithConjunction(goodNodes, 'and')} keep the
        game on track.
      </>
    );
  }

  const tierWord = verdict.tier === 'tricky' ? 'tricky' : 'highly difficult';
  const badList = badNodes.length > 0 ? interleaveWithConjunction(badNodes, 'or') : null;
  const escapeNode = escapeMove ? renderMove(escapeMove) : null;

  if (badList === null && escapeNode === null) return <>At {elo} Elo, this position is {tierWord} for {owner}.</>;
  if (badList === null) {
    return (
      <>
        At {elo} Elo, this position is {tierWord} for {owner}, though {escapeNode} ({escapeMove!.maiaPct}%) keeps
        things on track.
      </>
    );
  }
  if (escapeNode === null) {
    return (
      <>
        At {elo} Elo, this position is {tierWord} for {owner} — {badList} lead to trouble.
      </>
    );
  }
  return (
    <>
      At {elo} Elo, this position is {tierWord} for {owner} — {badList} lead to trouble, but {escapeNode} (
      {escapeMove!.maiaPct}%) keeps things on track.
    </>
  );
}

export function MaiaMoveQualityBar({
  perElo,
  selectedElo,
  shownSans,
  qualityBySan,
  onHoverMovesChange,
  isOpponentToMove = false,
  onPlayMove,
}: MaiaMoveQualityBarProps): React.ReactElement | null {
  const [activeKey, setActiveKey] = useState<QualityBucketKey | null>(null);
  // The prose move whose popover is open (and whose board arrow is lit). The
  // parent owns this + the hover-intent timer so the lifted arrow stays in sync
  // and segment- vs prose-hover never fight over the board overlay.
  const [activeProseSan, setActiveProseSan] = useState<string | null>(null);
  const proseHoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const buckets = useMemo(
    () => bucketMovesByQuality(perElo, selectedElo, shownSans, qualityBySan),
    [perElo, selectedElo, shownSans, qualityBySan],
  );

  const totalMass = useMemo(
    () => buckets.reduce((sum, b) => sum + b.probabilityMass, 0),
    [buckets],
  );

  const verdict = useMemo(
    () => computePositionVerdict(perElo, selectedElo, shownSans, qualityBySan),
    [perElo, selectedElo, shownSans, qualityBySan],
  );

  // Single source of truth for the board-arrow overlay: segment hover always
  // wins over a prose-span hover (structurally they can't both be driven by a
  // live pointer at once — the segment branch replaces the prose branch below
  // — but deriving from both here, with segment priority, keeps a stale prose
  // hover from ever clobbering a live segment arrow).
  const hoveredArrowMoves = useMemo<HoveredQualityMove[] | null>(() => {
    if (activeKey !== null) {
      const bucket = buckets.find((b) => b.key === activeKey);
      const color = BUCKET_META[activeKey].color;
      return bucket ? bucket.moves.map((m) => ({ san: m.san, color })) : null;
    }
    if (activeProseSan !== null) {
      const move = verdict?.moves.find((m) => m.san === activeProseSan);
      return move ? [{ san: move.san, color: move.arrowColor }] : null;
    }
    return null;
  }, [activeKey, activeProseSan, buckets, verdict]);

  // Lift the active move(s) up for the board arrows; clear on leave and on
  // unmount so a stale arrow set can't linger.
  useEffect(() => {
    if (!onHoverMovesChange) return;
    onHoverMovesChange(hoveredArrowMoves);
    return () => onHoverMovesChange(null);
  }, [hoveredArrowMoves, onHoverMovesChange]);

  // Clear a pending hover-intent timer if the bar unmounts mid-hover.
  useEffect(
    () => () => {
      if (proseHoverTimer.current) clearTimeout(proseHoverTimer.current);
    },
    [],
  );

  // Nothing to show until Maia has produced probabilities for this position.
  if (totalMass <= 0) return null;

  const activeBucket: QualityBucket | null =
    activeKey === null ? null : (buckets.find((b) => b.key === activeKey) ?? null);

  // Segment hover/tap always clears any prose-span hover (and vice versa) so
  // the two sources never fight over the resting-state slot or the arrow.
  const clearProseTimer = (): void => {
    if (proseHoverTimer.current) {
      clearTimeout(proseHoverTimer.current);
      proseHoverTimer.current = null;
    }
  };

  const handleEnter = (key: QualityBucketKey) => () => {
    clearProseTimer();
    setActiveProseSan(null);
    setActiveKey(key);
  };
  const handleLeave = () => setActiveKey(null);
  const handleToggle = (key: QualityBucketKey) => () =>
    setActiveKey((prev) => (prev === key ? null : key)); // tap-to-toggle for touch

  // Opening a prose popover also lights its board arrow and clears any hovered
  // segment. Hover uses a short intent delay (matches InfoPopover); focus/tap and
  // the content-bridge open immediately.
  const openProseNow = (san: string): void => {
    clearProseTimer();
    setActiveKey(null);
    setActiveProseSan(san);
  };
  const openProseDelayed = (san: string): void => {
    clearProseTimer();
    proseHoverTimer.current = setTimeout(() => openProseNow(san), PROSE_POPOVER_OPEN_DELAY_MS);
  };
  const closeProse = (): void => {
    clearProseTimer();
    setActiveProseSan(null);
  };

  const renderMove = (m: VerdictMove): React.ReactNode => (
    <ProseMoveSpan
      key={m.san}
      move={m}
      isOpen={activeProseSan === m.san}
      onOpenDelayed={() => openProseDelayed(m.san)}
      onOpenNow={() => openProseNow(m.san)}
      onClose={closeProse}
      onPlay={
        onPlayMove
          ? () => {
              closeProse();
              onPlayMove(m.san);
            }
          : undefined
      }
    />
  );

  return (
    <div className="flex flex-col gap-2" data-testid="maia-move-quality-bar">
      {/* The stacked bar. Segments abut inside a single rounded, clipped track. */}
      <div className="flex h-7 w-full overflow-hidden rounded-md" role="group" aria-label="Move quality distribution">
        {buckets.map((bucket) => {
          if (bucket.probabilityMass <= 0) return null;
          const meta = BUCKET_META[bucket.key];
          const widthPct = (bucket.probabilityMass / totalMass) * 100;
          const showLabel = widthPct >= MIN_INLINE_LABEL_PCT;
          const label = `${meta.label}: ${Math.round(widthPct)}% of shown moves`;
          const style: React.CSSProperties = {
            width: `${widthPct}%`,
            backgroundColor: meta.color,
            color: meta.darkText ? '#1a1a1a' : '#ffffff',
          };
          const inline = showLabel ? (
            <span className="text-sm font-semibold leading-none">{Math.round(widthPct)}%</span>
          ) : null;

          if (!meta.interactive) {
            // Pending (ungraded) sliver — visual only, not hoverable.
            return (
              <div
                key={bucket.key}
                className="flex items-center justify-center"
                style={style}
                aria-hidden="true"
                data-testid="maia-quality-segment-pending"
              >
                {inline}
              </div>
            );
          }

          return (
            <button
              key={bucket.key}
              type="button"
              className="flex items-center justify-center transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              style={style}
              aria-label={label}
              data-testid={`maia-quality-segment-${bucket.key}`}
              onMouseEnter={handleEnter(bucket.key)}
              onMouseLeave={handleLeave}
              onFocus={handleEnter(bucket.key)}
              onBlur={handleLeave}
              onClick={handleToggle(bucket.key)}
            >
              {inline}
            </button>
          );
        })}
      </div>

      {/* Hovered segment's move list, or (resting state) the prose position
          verdict, or (nothing graded yet) the original static help text.
          Fixed min-height so switching between them doesn't shift the layout. */}
      <div className="min-h-[1.5rem] text-sm" data-testid="maia-quality-hovered-list">
        {activeBucket && activeBucket.moves.length > 0 ? (
          <span>
            <span className="font-semibold" style={{ color: BUCKET_META[activeBucket.key].color }}>
              {BUCKET_META[activeBucket.key].label}:
            </span>{' '}
            <span className="text-muted-foreground">
              {activeBucket.moves.map((m) => `${m.san} ${pct(m.probability)}`).join(', ')}
            </span>
          </span>
        ) : verdict ? (
          <span data-testid="maia-position-verdict">
            {renderVerdictSentence(verdict, selectedElo, isOpponentToMove ? 'your opponent' : 'you', renderMove)}
          </span>
        ) : (
          <span className="text-muted-foreground">
            Hover a segment to list its moves and highlight them on the board.
          </span>
        )}
      </div>
    </div>
  );
}
