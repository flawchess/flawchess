/**
 * EvalChart — per-game expected-score area chart (Phase 109, LIBG-10).
 *
 * White-perspective ES per ply, shown as a filled eval bar: the area below the
 * ES line (0% → eval) is grey, the area above it (eval → 100%) is near-black,
 * with rounded chart corners, a 50% midline, at most two
 * phase-transition vertical lines
 * (middlegame, endgame — no ply-0 line per D-06), and dual-marker flaw dots
 * (filled = player, hollow = opponent, color = severity — D-07).
 *
 * Flaw dots use a custom `dot` render prop on an invisible <Line> overlay inside
 * ComposedChart — the established EndgameClockDiffOverTimeChart pattern. This
 * replaces the previously considered <Scatter> approach; recharts 3.8.1 Scatter
 * uses area-based `size` not radius `r`, making pixel-precise sizing unreliable.
 */

import { useEffect, useRef, useState } from 'react';
import { Area, ComposedChart, Line, ReferenceLine, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import {
  EVAL_CHART_AREA_BLACK_AHEAD,
  EVAL_CHART_AREA_WHITE_AHEAD,
  EVAL_CHART_LINE,
  EVAL_CHART_MIDLINE,
  EVAL_CHART_PHASE_LINE,
  EVAL_MARKER_FILTER_OUTLINE,
  SEV_BLUNDER,
  SEV_INACCURACY,
  SEV_MISTAKE,
} from '@/lib/theme';
import type {
  EvalPoint,
  FlawMarker,
  FlawSeverity,
  FlawTag,
  PhaseTransitions,
} from '@/types/library';

// ─── Props ────────────────────────────────────────────────────────────────────

interface EvalChartProps {
  gameId: number;
  evalSeries: EvalPoint[];
  flawMarkers: FlawMarker[];
  phaseTransitions: PhaseTransitions;
  /** SAN mainline (moves[i] = move at ply i) — labels the tooltip for any ply. */
  moves: string[];
  /** Tailwind height class — 'h-24' (desktop default) or 'h-20' (mobile). */
  heightClass?: string;
  /**
   * Fired with the exact hovered ply (null on mouse-leave) so the parent card can
   * drive its miniboard to that position. No snapping — the crosshair, tooltip,
   * and board all track the precise hovered ply.
   */
  onHoverPlyChange?: (ply: number | null) => void;
  /**
   * Plies to emphasize while the user hovers a tag chip / severity badge in the
   * card's flaw column. null (default) renders markers normally. A non-empty set
   * emphasizes matching M/B markers and dims the rest. An empty set is a no-op
   * (never dims everything).
   */
  highlightedPlies?: ReadonlySet<number> | null;
  /**
   * Plies whose (user) marker tags match the active flaw-tag filter. Those markers
   * get a white outline, mirroring the TagChip active-filter ring on the chart.
   * Independent of highlightedPlies — both can apply at once.
   */
  outlinedPlies?: ReadonlySet<number> | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Map FlawSeverity to its theme color constant. No inline literals. */
function severityColor(sev: FlawSeverity): string {
  if (sev === 'blunder') return SEV_BLUNDER;
  if (sev === 'mistake') return SEV_MISTAKE;
  return SEV_INACCURACY;
}

/** ES midline — the 50% reference line. */
const ES_MIDLINE = 0.5;

/** ES domain bounds — the two area fills span from the eval line to these. */
const ES_FLOOR = 0;
const ES_CEIL = 1;

/** Game-phase tags — excluded from the tooltip tag list (shown via phase lines). */
const PHASE_TAGS: ReadonlySet<FlawTag> = new Set(['opening', 'middlegame', 'endgame']);

/** Mistake/blunder flaw-dot radius. */
const FLAW_DOT_RADIUS = 4.5;

/** Radius multiplier for an emphasized (hover-highlighted) marker. */
const HIGHLIGHT_RADIUS_FACTOR = 1.45;

/** Opacity for non-matching markers while a hover highlight is active. */
const DIMMED_MARKER_OPACITY = 0.2;

/** Touch movement (px) past which a touch is treated as a drag, not a tap. */
const TOUCH_SLOP_PX = 10;

/** Hollow-square half-side as a fraction of FLAW_DOT_RADIUS (visually balances the filled circle). */
const SQUARE_HALF_SIDE_FACTOR = 0.85;

/** White-outline stroke width for filter-matched flaw markers. */
const FLAW_MARKER_OUTLINE_WIDTH = 1.5;

/**
 * The flaw-marker glyph: filled circle for the player (is_user), hollow square
 * for the opponent — color = severity (D-07). Shared by the chart dot renderer
 * and the tooltip so the two surfaces stay in sync. fill="none" is explicit on
 * the square to avoid SVG's default black fill (Pitfall 6 — omitting the fill
 * attribute is not the same as transparent).
 */
function flawDotElement(
  isUser: boolean,
  color: string,
  cx: number,
  cy: number,
  r: number,
  key: string,
  opacity = 1,
  // outline: draw a white ring around the marker when its tag matches an active
  // flaw-tag filter. Only used for the user's filled-circle markers (the filter is
  // scoped to is_user); opponent hollow squares are never outlined.
  outline = false,
): React.ReactElement {
  if (isUser) {
    return (
      <circle
        key={key}
        cx={cx}
        cy={cy}
        r={r}
        fill={color}
        opacity={opacity}
        stroke={outline ? EVAL_MARKER_FILTER_OUTLINE : undefined}
        strokeWidth={outline ? FLAW_MARKER_OUTLINE_WIDTH : undefined}
      />
    );
  }
  const s = r * SQUARE_HALF_SIDE_FACTOR;
  return (
    <rect
      key={key}
      x={cx - s}
      y={cy - s}
      width={2 * s}
      height={2 * s}
      fill="none"
      stroke={color}
      strokeWidth={2}
      strokeLinejoin="round"
      opacity={opacity}
    />
  );
}

/**
 * Custom dot render prop for the invisible <Line> overlay.
 * Draws filled circles (player) or hollow squares (opponent). Mistake/blunder dots
 * are always drawn; inaccuracy dots are off-chart by default and only drawn when
 * their ply is highlighted (Inaccuracies-badge hover/tap), rendered yellow at the
 * normal blunder size. Returns empty <g> for non-flaw / hidden plies — never null
 * (Pitfall 7). `markerMap` carries all severities (the caller filters via drawing).
 */
function buildDotRenderer(
  markerMap: Map<number, FlawMarker>,
  highlightedPlies?: ReadonlySet<number> | null,
  outlinedPlies?: ReadonlySet<number> | null,
) {
  // An empty set is treated as no-op so a tag/badge with no user markers never
  // dims the whole chart.
  const highlightActive = highlightedPlies != null && highlightedPlies.size > 0;
  return function customDotRenderer(props: {
    cx?: number;
    cy?: number;
    payload?: EvalPoint;
  }): React.ReactElement {
    const { cx, cy, payload } = props;
    if (!payload || cx == null || cy == null || !Number.isFinite(cx) || !Number.isFinite(cy)) {
      // Empty <g> not null — avoids React key warning (recharts 3.8.1 Pitfall 7).
      return <g key={`nodot-${String(payload?.ply ?? cx)}`} />;
    }
    const marker = markerMap.get(payload.ply);
    if (!marker || payload.es == null) {
      return <g key={`nodot-${payload.ply}`} />;
    }
    const matched = highlightActive && highlightedPlies!.has(payload.ply);
    // Inaccuracies stay hidden unless explicitly highlighted (their badge hover).
    if (marker.severity === 'inaccuracy' && !matched) {
      return <g key={`nodot-${payload.ply}`} />;
    }
    const color = severityColor(marker.severity);
    // Matched M/B dots enlarge for emphasis; a revealed inaccuracy dot renders at
    // the normal blunder size (hidden→visible is itself the emphasis).
    const enlarge = matched && marker.severity !== 'inaccuracy';
    const radius = enlarge ? FLAW_DOT_RADIUS * HIGHLIGHT_RADIUS_FACTOR : FLAW_DOT_RADIUS;
    const opacity = !highlightActive || matched ? 1 : DIMMED_MARKER_OPACITY;
    const outline = outlinedPlies != null && outlinedPlies.has(payload.ply);
    return flawDotElement(
      marker.is_user,
      color,
      cx,
      cy,
      radius,
      `dot-${payload.ply}`,
      opacity,
      outline,
    );
  };
}

/** PGN move-number label for a ply — even ply = White ("N.san"), odd = Black ("N...san"). */
function formatMoveLabel(ply: number, san: string | null): string {
  if (!san) return `Ply ${ply}`; // fallback when SAN is missing (e.g. final position)
  const moveNumber = Math.floor(ply / 2) + 1;
  return ply % 2 === 0 ? `${moveNumber}.${san}` : `${moveNumber}...${san}`;
}

/** White-perspective eval string for a ply — mate takes priority over cp. */
function formatEval(point: EvalPoint | undefined): string {
  if (point?.eval_mate != null) {
    // Signed, white-perspective: "Mate in 5#" (White) / "Mate in -6#" (Black).
    return `Eval: Mate in ${point.eval_mate}#`;
  }
  if (point?.eval_cp != null) {
    const cpValue = point.eval_cp / 100;
    const sign = cpValue >= 0 ? '+' : '';
    return `Eval: ${sign}${cpValue.toFixed(1)}`;
  }
  return 'Eval: —';
}

/** Clock remaining as m:ss (floored), e.g. 179.4 → "2:59". */
function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/** Inline glyph matching the chart's flaw dot, for the tooltip legend. */
const GLYPH_BOX = 12;
function MarkerGlyph({ isUser, color }: { isUser: boolean; color: string }): React.ReactElement {
  const c = GLYPH_BOX / 2;
  return (
    <svg
      width={GLYPH_BOX}
      height={GLYPH_BOX}
      viewBox={`0 0 ${GLYPH_BOX} ${GLYPH_BOX}`}
      className="shrink-0"
      aria-hidden="true"
    >
      {flawDotElement(isUser, color, c, c, FLAW_DOT_RADIUS, 'glyph')}
    </svg>
  );
}

/** Flaw detail block (glyph + You/Opponent + severity + tags) for a M/B marker. */
function FlawTooltipDetail({ marker }: { marker: FlawMarker }): React.ReactElement {
  const color = severityColor(marker.severity);
  // Drop game-phase tags (opening/middlegame/endgame) — conveyed by the phase
  // lines, not the tooltip.
  const tags = marker.tags.filter((t) => !PHASE_TAGS.has(t));
  return (
    <>
      <div className="flex items-center gap-1.5" style={{ color }}>
        <MarkerGlyph isUser={marker.is_user} color={color} />
        <span>
          {marker.is_user ? 'You' : 'Opponent'} &middot;{' '}
          {marker.severity.charAt(0).toUpperCase() + marker.severity.slice(1)}
        </span>
      </div>
      {tags.length > 0 && (
        <ul className="list-disc pl-5 text-muted-foreground">
          {tags.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      )}
    </>
  );
}

/**
 * Tooltip content render prop. Tracks the exact hovered ply (no snapping): shows
 * that ply's move (PGN notation) + white-perspective eval, plus a You/Opponent
 * glyph + severity + tags when the hovered ply is itself a mistake/blunder.
 * Returns null for plies with no eval (es == null).
 */
function buildTooltipContent(
  moves: string[],
  markerMap: Map<number, FlawMarker>,
  evalByPly: Map<number, EvalPoint>,
) {
  return function TooltipContent({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: Array<{ payload?: EvalPoint }>;
  }): React.ReactElement | null {
    if (!active || !payload?.length) return null;
    const point = payload[0]?.payload as EvalPoint | undefined;
    if (!point || point.ply == null || point.es == null) return null;

    const evalStr = formatEval(evalByPly.get(point.ply));
    const moveLabel = formatMoveLabel(point.ply, moves[point.ply] ?? null);
    const marker = markerMap.get(point.ply); // M/B only — undefined on clean plies

    return (
      // text-xs: intentional — established project recharts chart-tooltip pattern.
      // Same as EndgameScoreOverTimeChart, EndgameClockDiffOverTimeChart, FlawTrendChart.
      // CLAUDE.md explicitly exempts hover/tap chart tooltips (popover-surface exception).
      <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
        <div className="text-muted-foreground">
          {moveLabel} &middot; {evalStr}
        </div>
        {(point.clock_seconds != null || point.move_seconds != null) && (
          <div className="text-muted-foreground">
            {point.clock_seconds != null && <>Clock: {formatClock(point.clock_seconds)}</>}
            {point.clock_seconds != null && point.move_seconds != null && <> &middot; </>}
            {point.move_seconds != null && <>Move: {point.move_seconds.toFixed(1)}s</>}
          </div>
        )}
        {marker && <FlawTooltipDetail marker={marker} />}
      </div>
    );
  };
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Expected-score area chart embedded in LibraryGameCard (Phase 109, LIBG-10).
 *
 * Renders at desktop height h-24 (default) or mobile height h-20 when
 * `heightClass="h-20"` is passed. Wraps in a div with data-testid + aria-label
 * for browser automation and accessibility.
 */
export function EvalChart({
  gameId,
  evalSeries,
  flawMarkers,
  phaseTransitions,
  moves,
  heightClass = 'h-24',
  onHoverPlyChange,
  highlightedPlies,
  outlinedPlies,
}: EvalChartProps) {
  // evalByPly resolves a ply to its eval string for the tooltip.
  const mbMarkers = flawMarkers.filter((m) => m.severity !== 'inaccuracy');
  const evalByPly = new Map(evalSeries.map((p) => [p.ply, p]));

  // Tooltip stays mistakes/blunders-only (inaccuracy plies show eval only, no flaw
  // detail). The dot renderer gets the all-severity map so it can reveal inaccuracy
  // dots when the Inaccuracies badge is hovered; it hides them otherwise.
  const markerMap = new Map(mbMarkers.map((m) => [m.ply, m]));
  const allMarkerMap = new Map(flawMarkers.map((m) => [m.ply, m]));
  const dotRenderer = buildDotRenderer(allMarkerMap, highlightedPlies, outlinedPlies);
  const tooltipContent = buildTooltipContent(moves, markerMap, evalByPly);

  // Numeric x-domain [firstPly, lastPly]. A numeric XAxis maps the first/last ply
  // to the chart's left/right edges, so the area fill spans the full width. The
  // default category axis band-centers points, leaving the last ply short of the
  // right edge (fill ended before the edge, breaking the right rounded corners).
  const plies = evalSeries.map((p) => p.ply);
  const xDomain: [number, number] = [Math.min(...plies), Math.max(...plies)];

  // Hover crosshair tracks the EXACT hovered ply (no snapping). We mirror the ply
  // up to the parent (onHoverPlyChange) so the card's miniboard scrubs in sync,
  // and draw our own vertical ReferenceLine at that ply (the default tooltip
  // cursor is disabled below).
  const [hoverPly, setHoverPly] = useState<number | null>(null);
  const updateHoverPly = (ply: number | null) => {
    setHoverPly(ply);
    onHoverPlyChange?.(ply);
  };

  // Mobile sticky-tooltip fix. A touch *drag* emits no synthesized mouse events, so
  // after the finger lifts a subsequent outside tap never fires the chart's
  // mouseleave — the path that normally dismisses Recharts' tooltip + our crosshair
  // (a simple tap works because it *does* synthesize mouse events), leaving the
  // tooltip up but un-dismissable by an outside tap. We want it to STAY on release
  // and only clear on an outside tap, so after a real drag we "pin" the tooltip and
  // arm a document-level outside-pointer listener (below) to dismiss it. Recharts
  // keeps its tooltip active after the drag, so we leave active uncontrolled
  // (undefined) and only force it hidden (active={false}) when dismissing.
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [suppressTooltip, setSuppressTooltip] = useState(false);
  const [pinned, setPinned] = useState(false);
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const draggedRef = useRef(false);

  // Mouse and touch share this handler. Recharts fires onMouseMove only on
  // pointer devices, so on touch the crosshair + parent miniboard never updated
  // (the tooltip kept working because Recharts tracks tooltip state internally,
  // independent of these callbacks). onTouchMove delivers the same nextState
  // with activeLabel, so wiring it here syncs the crosshair/miniboard on drag.
  const handlePointerMove = (state: { activeLabel?: string | number }) => {
    setSuppressTooltip(false); // any fresh move re-enables the tooltip
    const raw = state?.activeLabel;
    updateHoverPly(raw == null ? null : Number(raw));
  };
  const handleMouseLeave = () => updateHoverPly(null);

  // Raw touch tracking on the wrapper (Recharts' chart-level handlers don't expose
  // pixel coordinates). A movement past TOUCH_SLOP_PX counts as a drag.
  const handleTouchStart = (e: React.TouchEvent): void => {
    const t = e.touches[0];
    touchStartRef.current = t ? { x: t.clientX, y: t.clientY } : null;
    draggedRef.current = false;
    setPinned(false); // a new touch inside the chart starts a fresh interaction
    // suppress is left as-is — handlePointerMove re-enables on the first real move,
    // so a stale (pre-dismiss) Recharts tooltip never flashes before the new ply.
  };
  const handleTouchMoveRaw = (e: React.TouchEvent): void => {
    const start = touchStartRef.current;
    const t = e.touches[0];
    if (
      start &&
      t &&
      (Math.abs(t.clientX - start.x) > TOUCH_SLOP_PX ||
        Math.abs(t.clientY - start.y) > TOUCH_SLOP_PX)
    ) {
      draggedRef.current = true;
    }
  };
  const handleTouchEnd = (): void => {
    // Keep the tooltip up after a drag (do NOT clear). Pin it so the document
    // listener below can dismiss it on the next tap outside the chart.
    if (draggedRef.current) setPinned(true);
    touchStartRef.current = null;
  };

  // While pinned (tooltip left up after a touch drag), a tap/click anywhere outside
  // the chart dismisses it — the "tap outside to close" the synthesized-mouse path
  // can't deliver after a drag. Only armed on mobile (pinned is set by a drag).
  useEffect(() => {
    if (!pinned) return;
    const onOutsidePointerDown = (e: PointerEvent): void => {
      const node = wrapperRef.current;
      if (node && e.target instanceof Node && node.contains(e.target)) return; // inside → keep
      setSuppressTooltip(true); // force Recharts' still-active tooltip hidden
      setHoverPly(null);
      onHoverPlyChange?.(null);
      setPinned(false);
    };
    document.addEventListener('pointerdown', onOutsidePointerDown, true);
    return () => document.removeEventListener('pointerdown', onOutsidePointerDown, true);
  }, [pinned, onHoverPlyChange]);

  return (
    <div
      ref={wrapperRef}
      data-testid={`eval-chart-${gameId}`}
      aria-label={`Expected score chart for game ${gameId}`}
      role="img"
      // Suppress the UA focus outline recharts shows when its surface / tabIndex=-1
      // tooltip wrapper takes focus on click (looked like a white border on the chart).
      //
      // relative z-10 while hovering: the tooltip escapes the chart viewBox (y=true)
      // and overlaps the card content stacked below it (the mobile flaw block, which
      // is later in DOM within the same .charcoal-texture column and would otherwise
      // paint on top). Lifting the chart's subtree keeps the tooltip readable. The
      // card itself bumps to z-30 on hover to clear the *following* card (see
      // LibraryGameCard).
      className={`w-full [&_:focus]:outline-none [&_:focus-visible]:outline-none${
        hoverPly != null ? ' relative z-10' : ''
      }`}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMoveRaw}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={handleTouchEnd}
    >
      <ChartContainer
        config={{}}
        // Clip the recharts surface SVG (not the wrapper) to rounded corners:
        // !overflow-hidden overrides recharts' inline overflow:visible, and rounds
        // the fill. This does NOT clip the escape-viewBox tooltip, which lives in a
        // sibling div outside the surface.
        className={`w-full ${heightClass} [&_.recharts-surface]:!overflow-hidden [&_.recharts-surface]:rounded-md`}
      >
        <ComposedChart
          data={evalSeries}
          // Zero margins so the eval-bar fill spans the chart's full height and
          // width, aligning its top/bottom with the adjacent miniboard.
          margin={{ top: 0, right: 0, left: 0, bottom: 0 }}
          onMouseMove={handlePointerMove}
          onMouseLeave={handleMouseLeave}
          onTouchMove={handlePointerMove}
        >
          {/* Hidden axes — compact sparkline mode, no ticks or labels.
              type="number" + explicit domain so the fill reaches both edges. */}
          <XAxis dataKey="ply" type="number" domain={xDomain} hide />
          <YAxis hide domain={[ES_FLOOR, ES_CEIL]} />

          {/* Eval bar — two solid regions split by the ES line. The black area
              fills from the line up to 100% (baseValue=ES_CEIL); the grey area
              fills from the line down to 0% (baseValue=ES_FLOOR). Grey is drawn
              last so it carries the ES stroke line. */}
          <Area
            type="monotone"
            dataKey="es"
            baseValue={ES_CEIL}
            stroke="none"
            fill={EVAL_CHART_AREA_BLACK_AHEAD}
            fillOpacity={1}
            dot={false}
            activeDot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="es"
            baseValue={ES_FLOOR}
            stroke={EVAL_CHART_LINE}
            strokeWidth={1.5}
            fill={EVAL_CHART_AREA_WHITE_AHEAD}
            fillOpacity={1}
            dot={false}
            activeDot={false}
            connectNulls={false}
            isAnimationActive={false}
          />

          {/* 50% midline — dashed horizontal reference. */}
          <ReferenceLine
            y={ES_MIDLINE}
            stroke={EVAL_CHART_MIDLINE}
            strokeWidth={1}
            strokeDasharray="3 3"
            aria-hidden="true"
          />

          {/* Hover crosshair — tracks the exact hovered ply (no snapping). The
              default tooltip cursor is disabled; this dashed vertical line is
              drawn at the hovered ply via the real x-axis scale. */}
          {hoverPly != null && (
            <ReferenceLine
              x={hoverPly}
              stroke={EVAL_CHART_MIDLINE}
              strokeWidth={1}
              strokeDasharray="3 3"
              aria-hidden="true"
            />
          )}

          {/* Phase-transition vertical lines — at most two (D-06).
              Opening boundary (ply 0) gets no line — implicit start of chart. */}
          {phaseTransitions.middlegame_ply != null && (
            <ReferenceLine
              x={phaseTransitions.middlegame_ply}
              stroke={EVAL_CHART_PHASE_LINE}
              strokeWidth={1}
              aria-hidden="true"
            />
          )}
          {phaseTransitions.endgame_ply != null && (
            <ReferenceLine
              x={phaseTransitions.endgame_ply}
              stroke={EVAL_CHART_PHASE_LINE}
              strokeWidth={1}
              aria-hidden="true"
            />
          )}

          {/*
            Invisible line overlay — renders flaw dots via custom dot render prop.
            stroke="none" keeps the line invisible; the dot prop draws the markers.
            Uses the EndgameClockDiffOverTimeChart hollow/filled circle pattern.
          */}
          <Line
            type="monotone"
            dataKey="es"
            stroke="none"
            dot={dotRenderer}
            activeDot={false}
            connectNulls={false}
            isAnimationActive={false}
          />

          {/* Per-ply tooltip showing eval + You/Opponent flaw info.
              allowEscapeViewBox y=true lets it render above/below the short
              sparkline instead of covering it (the chart is only h-20/h-24, so
              an in-viewBox tooltip blankets the whole thing on mobile). */}
          <ChartTooltip
            content={tooltipContent}
            cursor={false}
            allowEscapeViewBox={{ x: false, y: true }}
            // Controlled only to force-hide after a touch drag (see suppressTooltip);
            // undefined otherwise so Recharts keeps its normal hover/tap behavior.
            active={suppressTooltip ? false : undefined}
          />
        </ComposedChart>
      </ChartContainer>
    </div>
  );
}
