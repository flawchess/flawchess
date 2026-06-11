/**
 * EvalChart — per-game expected-score area chart (Phase 109, LIBG-10).
 *
 * White-perspective ES per ply, shown as a filled eval bar: the area below the
 * ES line (0% → eval) is grey, the area above it (eval → 100%) is near-black,
 * with rounded chart corners, at most two
 * phase-transition annotations (fine top tick + rotated label) centered on the
 * phase boundary (middlegame, endgame — no full vertical lines, no ply-0
 * annotation per D-06), and
 * dual-marker flaw dots (filled = player, hollow = opponent, color = severity — D-07).
 *
 * Flaw dots use a custom `dot` render prop on an invisible <Line> overlay inside
 * ComposedChart — the established EndgameClockDiffOverTimeChart pattern. This
 * replaces the previously considered <Scatter> approach; recharts 3.8.1 Scatter
 * uses area-based `size` not radius `r`, making pixel-precise sizing unreliable.
 *
 * Interaction model: one `activePly` state (hoverPly ?? sliderPly) drives the white
 * crosshair + active-ply dot, the floating tooltip, the slider thumb, and the parent
 * miniboard. The native range slider below the chart is the persistent scrub input
 * (and the only one on touch); chart hover is a transient scrub layered on top.
 * Mouse-leave reverts activePly to the slider value; at rest the slider defaults to
 * the last eval'd ply. The tooltip is self-positioned at the active datapoint's x
 * (flipping sides at the chart's midpoint): vertically centered on the chart while
 * hover-driven, bottom-aligned just above the thumb while slider-driven. Semi-
 * transparent so the chart stays readable beneath it; shown only while interacting
 * (hover or slider focus).
 */

import { useEffect, useMemo, useState } from 'react';
import { Area, ComposedChart, Line, ReferenceDot, ReferenceLine, XAxis, YAxis } from 'recharts';
import { ChartContainer } from '@/components/ui/chart';
import { ChartTooltipBox } from '@/components/ui/chart-tooltip-box';
import {
  EVAL_CHART_AREA_BLACK_AHEAD,
  EVAL_CHART_AREA_WHITE_AHEAD,
  EVAL_CHART_CURSOR,
  EVAL_CHART_LINE,
  EVAL_CHART_PHASE_LABEL,
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
  /**
   * Tailwind height class for the chart area only — 'h-[116px]' (desktop) or
   * 'h-[114px]' (mobile). Chart height + the 16px (h-4) slider row should equal
   * the adjacent miniboard size so the eval block lines up with the board.
   */
  heightClass?: string;
  /**
   * Flip the chart vertically (player perspective). The eval series is always
   * white-perspective, so for a black player "white ahead" would read as the line
   * going down when they're winning. Setting this reverses the Y axis so the
   * player's advantage reads as up and their (dark) share fills from the bottom,
   * matching the flipped miniboard. The tooltip eval number stays white-perspective
   * (standard chess/engine convention). Pass `user_color === 'black'`.
   */
  flipped?: boolean;
  /**
   * Reports the active scrub ply (from slider or chart hover) to the parent so
   * the miniboard scrubs in sync. At rest the resting slider ply is reported
   * (always a number, never null). During chart hover the hovered ply is reported;
   * on mouse-leave it reverts to the slider value.
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
  /**
   * The single ply the card was opened to focus (the flaw clicked in the Flaws
   * subtab). Its marker gets an expanding "ping" ring in its severity color so the
   * eye lands on it the moment the modal opens. Purely additive — it does NOT dim
   * or enlarge anything, so it never competes with `highlightedPlies`. The parent
   * clears it (passes null) the first time the user hovers a tag/severity or scrubs
   * the chart, handing the chart back to the hover-driven highlight systems.
   */
  focusedPly?: number | null;
}

// ─── Constants ────────────────────────────────────────────────────────────────

/** ES domain bounds — the two area fills span from the eval line to these. */
const ES_FLOOR = 0;
const ES_CEIL = 1;

/**
 * Extra Y-domain headroom above 1.0 and below 0.0 so flaw markers sitting at the
 * extremes (es ≈ 0 / 1, e.g. a checkmate ply) aren't clipped at the chart edges.
 * The area fills still span only ES_FLOOR..ES_CEIL, so this reads as a thin strip
 * of card background above and below the eval bar.
 */
const ES_PAD = 0.08;

/** Game-phase tags — excluded from the tooltip tag list (shown via phase lines). */
const PHASE_TAGS: ReadonlySet<FlawTag> = new Set(['opening', 'middlegame', 'endgame']);

/**
 * The API's middlegame_ply / endgame_ply is the FIRST ply *in* the new phase
 * (the first middlegame/endgame position). Drawing the vertical on that ply sits
 * it on top of that data point, reading as one move late — the move that ply
 * represents is what *entered* the phase. Render the line one ply earlier so it
 * falls on the boundary between the last prior-phase ply and the first new-phase
 * ply. (The API value itself is left untouched — it's reused as the "phase entry"
 * ply by the endgame analytics.)
 */
const PHASE_LINE_PLY_OFFSET = 1;

/** Rotated phase-boundary label geometry (SVG px). */
const PHASE_LABEL_FONT_SIZE = 10;
const PHASE_TICK_LENGTH = 5; // fine tick hanging down from the chart top edge
const PHASE_TICK_WIDTH = 1;
const PHASE_LABEL_TOP_PAD = 3; // px gap between tick end and label start

/** Mistake/blunder flaw-dot radius. */
const FLAW_DOT_RADIUS = 4.5;

/** Radius multiplier for an emphasized (hover-highlighted) marker. */
const HIGHLIGHT_RADIUS_FACTOR = 1.45;

/** Opacity for non-matching markers while a hover highlight is active. */
const DIMMED_MARKER_OPACITY = 0.2;

/** Hollow-square half-side as a fraction of FLAW_DOT_RADIUS (visually balances the filled circle). */
const SQUARE_HALF_SIDE_FACTOR = 0.85;

/** White-outline stroke width for filter-matched flaw markers. */
const FLAW_MARKER_OUTLINE_WIDTH = 1.5;

/** Focus "ping" ring: expands from the dot radius to this radius while fading out. */
const FOCUS_PULSE_MAX_RADIUS = 13;
/** Focus-ping stroke width and one-cycle duration (SVG SMIL). */
const FOCUS_PULSE_STROKE_WIDTH = 2;
const FOCUS_PULSE_DURATION = '1.4s';

/** Inline glyph size (px) for MarkerGlyph in the tooltip flaw detail. */
const GLYPH_BOX = 12;

/** Active-ply dot radius — slightly under FLAW_DOT_RADIUS so flaw markers stay dominant. */
const ACTIVE_DOT_RADIUS = 4;

/** Horizontal gap (px) between the active datapoint and the tooltip box. */
const TOOLTIP_GAP_PX = 10;
/** Datapoint x-position (%) past which the tooltip flips to the left side. */
const TOOLTIP_SIDE_FLIP_PCT = 50;

/**
 * Slider thumb diameter (px) — MUST match the w-3/h-3 thumb classes on the range
 * input below. The slider container is widened by this amount (half on each side)
 * so the thumb center, rather than its edge, spans the chart's full width.
 */
const SLIDER_THUMB_PX = 12;

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Map FlawSeverity to its theme color constant. No inline literals. */
function severityColor(sev: FlawSeverity): string {
  if (sev === 'blunder') return SEV_BLUNDER;
  if (sev === 'mistake') return SEV_MISTAKE;
  return SEV_INACCURACY;
}

/**
 * `label` render prop for a phase-transition ReferenceLine: a fine tick hanging
 * from the chart's top edge plus vertical text reading top-to-bottom
 * ("Midgame" / "Endgame"), both horizontally centered on the phase boundary x
 * (the stroke-less ReferenceLine's position). recharts passes the line's viewBox
 * (x = boundary x, y = chart top). The text is rotated 90° about its anchor so it
 * hangs downward below the tick; dominantBaseline="central" centers the glyphs
 * across the rotated baseline, i.e. horizontally on the boundary.
 */
function phaseLineLabel(text: string) {
  return function PhaseLineLabel(props: {
    viewBox?: { x?: number; y?: number };
  }): React.ReactElement {
    const vb = props.viewBox;
    if (!vb || vb.x == null) return <g />;
    const x = vb.x;
    const top = vb.y ?? 0;
    const y = top + PHASE_TICK_LENGTH + PHASE_LABEL_TOP_PAD;
    return (
      <g aria-hidden="true">
        <line
          x1={x}
          x2={x}
          y1={top}
          y2={top + PHASE_TICK_LENGTH}
          stroke={EVAL_CHART_PHASE_LABEL}
          strokeWidth={PHASE_TICK_WIDTH}
        />
        <text
          x={x}
          y={y}
          fill={EVAL_CHART_PHASE_LABEL}
          fontSize={PHASE_LABEL_FONT_SIZE}
          textAnchor="start"
          dominantBaseline="central"
          transform={`rotate(90, ${x}, ${y})`}
        >
          {text}
        </text>
      </g>
    );
  };
}

/**
 * Trim leading/trailing plies with no eval (es == null) from the series. Most
 * games have 1-2 trailing eval-less plies (the final position after the last move
 * is never evaluated). recharts' XAxis defaults to allowDataOverflow={false}, so
 * it extends the x-domain to fit EVERY data point's ply value regardless of an
 * explicit domain — those trailing points padded the right edge, stopping the fill
 * (and its right rounded corners) short. Dropping them from the data is what
 * actually makes the last eval'd ply land on the right edge. Interior eval gaps are
 * kept (connectNulls={false} renders them as breaks).
 */
function trimToEvalRange(series: EvalPoint[]): EvalPoint[] {
  let start = 0;
  let end = series.length;
  while (start < end && series[start]?.es == null) start++;
  while (end > start && series[end - 1]?.es == null) end--;
  return series.slice(start, end);
}

/**
 * Expanding-and-fading "ping" ring behind the focused flaw's marker — the same
 * attention affordance the app uses elsewhere (Tailwind `animate-ping`), expressed
 * as SVG SMIL since this lives inside the recharts surface. Drawn in the marker's
 * severity color. Self-contained (no extra deps) and additive: it sits behind the
 * normal dot and changes nothing about how the dot itself renders, so the hover
 * enlarge/dim and the filter outline are entirely unaffected.
 */
function focusPulseElement(color: string, cx: number, cy: number, key: string): React.ReactElement {
  return (
    <circle
      key={key}
      cx={cx}
      cy={cy}
      r={FLAW_DOT_RADIUS}
      fill="none"
      stroke={color}
      strokeWidth={FOCUS_PULSE_STROKE_WIDTH}
      aria-hidden="true"
    >
      <animate
        attributeName="r"
        values={`${FLAW_DOT_RADIUS};${FOCUS_PULSE_MAX_RADIUS}`}
        dur={FOCUS_PULSE_DURATION}
        repeatCount="indefinite"
      />
      <animate
        attributeName="opacity"
        values="0.9;0"
        dur={FOCUS_PULSE_DURATION}
        repeatCount="indefinite"
      />
    </circle>
  );
}

/**
 * The flaw-marker glyph: filled circle for the player (is_user), hollow square
 * for the opponent — color = severity (D-07). Shared by the chart dot renderer
 * and the tooltip so the two surfaces stay in sync. fill="none" is explicit
 * on the square to avoid SVG's default black fill (Pitfall 6 — omitting the fill
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
  focusedPly?: number | null,
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
    const focused = focusedPly != null && payload.ply === focusedPly;
    // Inaccuracies stay hidden unless explicitly highlighted (their badge hover) or
    // the card was opened focused on them (defensive — Flaws subtab is M/B only).
    if (marker.severity === 'inaccuracy' && !matched && !focused) {
      return <g key={`nodot-${payload.ply}`} />;
    }
    const color = severityColor(marker.severity);
    // Matched M/B dots enlarge for emphasis; a revealed inaccuracy dot renders at
    // the normal blunder size (hidden→visible is itself the emphasis).
    const enlarge = matched && marker.severity !== 'inaccuracy';
    const radius = enlarge ? FLAW_DOT_RADIUS * HIGHLIGHT_RADIUS_FACTOR : FLAW_DOT_RADIUS;
    const opacity = !highlightActive || matched ? 1 : DIMMED_MARKER_OPACITY;
    const outline = outlinedPlies != null && outlinedPlies.has(payload.ply);
    const dot = flawDotElement(
      marker.is_user,
      color,
      cx,
      cy,
      radius,
      `dot-${payload.ply}`,
      opacity,
      outline,
    );
    // Focus ping: a separate, additive channel. Group the ping ring behind the
    // (untouched) dot so the dot keeps its normal hover/filter rendering.
    if (!focused) return dot;
    return (
      <g key={`focus-${payload.ply}`}>
        {focusPulseElement(color, cx, cy, `pulse-${payload.ply}`)}
        {dot}
      </g>
    );
  };
}

/** PGN move-number label for a ply — even ply = White ("N.san"), odd = Black ("N...san"). */
function formatMoveLabel(ply: number, san: string | null): string {
  if (!san) return `Ply ${ply}`; // fallback when SAN is missing (e.g. final position)
  const moveNumber = Math.floor(ply / 2) + 1;
  return ply % 2 === 0 ? `${moveNumber}.${san}` : `${moveNumber}...${san}`;
}

/**
 * Bare white-perspective eval value for a ply — mate takes priority over cp.
 * Returns the bare value without a "Eval:" prefix so callers can compose labels.
 * Mate-priority and '#'-ending "Checkmate" detection preserved.
 */
function formatEvalBare(point: EvalPoint | undefined): string {
  if (point?.eval_mate != null) {
    return `Mate in ${point.eval_mate}#`;
  }
  if (point?.eval_cp != null) {
    const cpValue = point.eval_cp / 100;
    const sign = cpValue >= 0 ? '+' : '';
    return `${sign}${cpValue.toFixed(1)}`;
  }
  return '—';
}

/** Clock remaining as m:ss (floored), e.g. 179.4 → "2:59". */
function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/** Inline glyph matching the chart's flaw dot, for the tooltip flaw detail. */
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

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Expected-score area chart embedded in LibraryGameCard (Phase 109, LIBG-10).
 *
 * Renders the chart at the height specified by `heightClass` (desktop: h-[116px],
 * mobile: h-[114px]) with a native range scrub slider below it, and a floating
 * semi-transparent tooltip anchored at the active datapoint while interacting.
 * The outer wrapper keeps data-testid + aria-label for accessibility.
 */
export function EvalChart({
  gameId,
  evalSeries,
  flawMarkers,
  phaseTransitions,
  moves,
  heightClass = 'h-[116px]',
  flipped = false,
  onHoverPlyChange,
  highlightedPlies,
  outlinedPlies,
  focusedPly,
}: EvalChartProps) {
  // Tooltip stays mistakes/blunders-only (inaccuracy plies show eval only, no flaw
  // detail). The dot renderer gets the all-severity map so it can reveal inaccuracy
  // dots when the Inaccuracies badge is hovered; it hides them otherwise.
  const mbMarkers = flawMarkers.filter((m) => m.severity !== 'inaccuracy');
  const evalByPly = useMemo(() => new Map(evalSeries.map((p) => [p.ply, p])), [evalSeries]);
  const markerMap = useMemo(() => new Map(mbMarkers.map((m) => [m.ply, m])), [mbMarkers]);
  const allMarkerMap = useMemo(() => new Map(flawMarkers.map((m) => [m.ply, m])), [flawMarkers]);
  const dotRenderer = buildDotRenderer(allMarkerMap, highlightedPlies, outlinedPlies, focusedPly);

  // Chart data trimmed to the eval'd ply range so the fill spans the full width
  // (see trimToEvalRange). Fall back to the raw series if every ply lacks an eval.
  // MUST be memoized: a fresh array each render resets recharts' internal hover state.
  // The same trimmed array drives BOTH the chart domain AND the slider min/max bounds.
  const chartSeries = useMemo(() => {
    const trimmed = trimToEvalRange(evalSeries);
    return trimmed.length > 0 ? trimmed : evalSeries;
  }, [evalSeries]);

  // Slider bounds derived from the trimmed eval range.
  const sliderMin = chartSeries[0]?.ply ?? 0;
  const sliderMax = chartSeries[chartSeries.length - 1]?.ply ?? 0;

  // STATE MODEL: one active-ply source of truth.
  //   hoverPly — transient, chart-hover-only; null when not hovering.
  //   sliderPly — persistent; the last explicitly-set slider position.
  //   activePly — derived as hoverPly ?? sliderPly; drives crosshair, tooltip,
  //   slider thumb, and parent (hover sweeps the thumb along with it).
  //
  // Initialize sliderPly to the last eval'd ply (locked decision 5).
  const [sliderPly, setSliderPly] = useState<number>(sliderMax);
  const [hoverPly, setHoverPly] = useState<number | null>(null);

  // Reset sliderPly when the series identity changes (e.g. data swap on a different game).
  // useEffect runs after render — setState inside triggers a re-render with the new value.
  useEffect(() => {
    setSliderPly(sliderMax);
  }, [sliderMax]);

  const activePly = hoverPly ?? sliderPly;

  // Report activePly to parent on every change — drives the parent's miniboard.
  useEffect(() => {
    onHoverPlyChange?.(activePly);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePly]); // intentionally exclude onHoverPlyChange to avoid spurious re-fires

  // Chart mouse handlers: hover sets hoverPly; leave clears it (activePly falls back to sliderPly).
  const handlePointerMove = (state: { activeLabel?: string | number }) => {
    const raw = state?.activeLabel;
    setHoverPly(raw == null ? null : Number(raw));
  };
  const handleMouseLeave = () => setHoverPly(null);

  // Slider handler: explicit user scrub sets sliderPly (hoverPly stays null; activePly = sliderPly).
  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSliderPly(Number(e.target.value));
  };

  // Tooltip is interaction-gated: chart hover or slider focus. A focused slider keeps
  // the tooltip up after a drag (desktop click-away / mobile tap on another control
  // blurs it); at rest nothing floats over the chart.
  const [sliderFocused, setSliderFocused] = useState(false);
  const tooltipVisible = hoverPly != null || sliderFocused;

  // Tooltip content for activePly (original floating-tooltip content: move + eval,
  // clock + move time, M/B flaw detail — inaccuracy plies show eval only).
  const activeSan = moves[activePly] ?? null;
  const activePoint = evalByPly.get(activePly);
  // A mating move (SAN ends '#') has no engine eval — show "Checkmate" instead.
  const evalStr = activeSan?.endsWith('#') ? 'Checkmate' : `Eval: ${formatEvalBare(activePoint)}`;
  const moveLabel = formatMoveLabel(activePly, activeSan);
  // M/B flaw marker at activePly (undefined on clean or inaccuracy plies).
  const activeMarker = markerMap.get(activePly);
  const tooltipTags = activeMarker ? activeMarker.tags.filter((t) => !PHASE_TAGS.has(t)) : [];

  // Active datapoint position as a fraction of the eval'd ply range. Plies in
  // chartSeries are contiguous and recharts' point scale (zero padding, zero margins)
  // maps first→0% and last→100% of the chart width, so this percentage matches the
  // datapoint's x pixel. The slider is widened by one thumb width (see the slider
  // container below) so the thumb CENTER travels this same 0%–100% chart span —
  // crosshair, datapoint, and thumb center all share one x mapping.
  const plyRange = sliderMax - sliderMin;
  const activeXPct = plyRange > 0 ? ((activePly - sliderMin) / plyRange) * 100 : 50;
  // The tooltip box flips sides at the midpoint so it never runs off the near edge.
  // Vertical anchor depends on the input driving the scrub:
  //   chart hover  → vertically centered on the chart (the box is nearly chart-height;
  //                  anchoring to the datapoint's y would push it out of the card).
  //   slider scrub → bottom-aligned to the chart, i.e. floating just above the thumb,
  //                  so it tracks the cursor/finger like the original hover tooltip.
  const tooltipOnLeft = activeXPct > TOOLTIP_SIDE_FLIP_PCT;
  const hoverDriven = hoverPly != null;

  return (
    <div
      data-testid={`eval-chart-${gameId}`}
      aria-label={`Expected score chart for game ${gameId}`}
      role="img"
      // Suppress the UA focus outline recharts shows when its surface / tabIndex=-1
      // takes focus on click. Tooltip z-lift hack removed (tooltip is gone).
      className="w-full [&_:focus]:outline-none [&_:focus-visible]:outline-none"
    >
      {/* Chart area — relative so the self-positioned tooltip anchors to it. */}
      <div className="relative w-full">
      <ChartContainer
        config={{}}
        // Clip the recharts surface SVG (not the wrapper) to rounded corners.
        className={`w-full ${heightClass} [&_.recharts-surface]:!overflow-hidden [&_.recharts-surface]:rounded-md`}
      >
        <ComposedChart
          data={chartSeries}
          margin={{ top: 0, right: 0, left: 0, bottom: 0 }}
          onMouseMove={handlePointerMove}
          onMouseLeave={handleMouseLeave}
        >
          {/* Hidden axes — compact sparkline mode, no ticks or labels. */}
          <XAxis dataKey="ply" hide />
          {/* reversed when the player is black. */}
          <YAxis hide reversed={flipped} domain={[ES_FLOOR - ES_PAD, ES_CEIL + ES_PAD]} />

          {/* Eval bar — two solid regions split by the ES line. */}
          <Area
            type="monotone"
            dataKey="es"
            baseValue={ES_CEIL + ES_PAD}
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
            baseValue={ES_FLOOR - ES_PAD}
            stroke={EVAL_CHART_LINE}
            strokeWidth={1.5}
            fill={EVAL_CHART_AREA_WHITE_AHEAD}
            fillOpacity={1}
            dot={false}
            activeDot={false}
            connectNulls={false}
            isAnimationActive={false}
          />

          {/* Active crosshair — tracks the unified activePly (hover OR slider).
              Solid white (same as the slider thumb) so the interactive cursor is
              visually distinct from the dashed grey reference geometry. */}
          <ReferenceLine
            x={activePly}
            stroke={EVAL_CHART_CURSOR}
            strokeWidth={1}
            aria-hidden="true"
          />

          {/* Phase-transition labels (D-06) — stroke-less ReferenceLines used purely
              to position the rotated label at the boundary x; no visible line. */}
          {phaseTransitions.middlegame_ply != null && (
            <ReferenceLine
              x={phaseTransitions.middlegame_ply - PHASE_LINE_PLY_OFFSET}
              stroke="none"
              label={phaseLineLabel('Midgame')}
              aria-hidden="true"
            />
          )}
          {phaseTransitions.endgame_ply != null && (
            <ReferenceLine
              x={phaseTransitions.endgame_ply - PHASE_LINE_PLY_OFFSET}
              stroke="none"
              label={phaseLineLabel('Endgame')}
              aria-hidden="true"
            />
          )}

          {/* Invisible line overlay — renders flaw dots via custom dot render prop. */}
          <Line
            type="monotone"
            dataKey="es"
            stroke="none"
            dot={dotRenderer}
            activeDot={false}
            connectNulls={false}
            isAnimationActive={false}
          />

          {/* Active-ply dot — white highlight where the crosshair meets the ES line.
              Drawn after the flaw-marker overlay so on a flaw ply it sits inside the
              (slightly larger) severity dot, reading as a severity-colored ring around
              the white cursor dot. Skipped on eval-gap plies (no y to anchor to). */}
          {activePoint?.es != null && (
            <ReferenceDot
              x={activePly}
              y={activePoint.es}
              r={ACTIVE_DOT_RADIUS}
              fill={EVAL_CHART_CURSOR}
              stroke="none"
              aria-hidden="true"
            />
          )}
        </ComposedChart>
      </ChartContainer>

      {/* Floating tooltip — self-positioned at the active datapoint's x, vertically
          centered on the chart, flipping sides at the midpoint. Semi-transparent so
          the eval bar stays readable beneath it; pointer-events-none so it never
          steals the chart's hover. Shown only while interacting (hover / slider focus). */}
      {tooltipVisible && (
        <div
          data-testid={`eval-tooltip-${gameId}`}
          className={`absolute z-10 pointer-events-none ${hoverDriven ? 'top-1/2' : 'bottom-0'}`}
          style={{
            left: `${activeXPct}%`,
            transform: `translate(${
              tooltipOnLeft ? `calc(-100% - ${TOOLTIP_GAP_PX}px)` : `${TOOLTIP_GAP_PX}px`
            }, ${hoverDriven ? '-50%' : '0'})`,
          }}
        >
          <ChartTooltipBox className="bg-background/55 backdrop-blur-[2px] whitespace-nowrap">
            <div className="text-muted-foreground">
              {moveLabel} &middot; {evalStr}
            </div>
            {(activePoint?.clock_seconds != null || activePoint?.move_seconds != null) && (
              <div className="text-muted-foreground">
                {activePoint.clock_seconds != null && <>Clock: {formatClock(activePoint.clock_seconds)}</>}
                {activePoint.clock_seconds != null && activePoint.move_seconds != null && (
                  <> &middot; </>
                )}
                {activePoint.move_seconds != null && <>Move: {activePoint.move_seconds.toFixed(1)}s</>}
              </div>
            )}
            {activeMarker && (
              <>
                <div
                  className="flex items-center gap-1.5"
                  style={{ color: severityColor(activeMarker.severity) }}
                >
                  <MarkerGlyph
                    isUser={activeMarker.is_user}
                    color={severityColor(activeMarker.severity)}
                  />
                  <span>
                    {activeMarker.is_user ? 'You' : 'Opponent'} &middot;{' '}
                    {activeMarker.severity.charAt(0).toUpperCase() + activeMarker.severity.slice(1)}
                  </span>
                </div>
                {tooltipTags.length > 0 && (
                  <ul className="list-disc pl-5 text-muted-foreground">
                    {tooltipTags.map((t) => (
                      <li key={t}>{t}</li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </ChartTooltipBox>
        </div>
      )}
      </div>

      {/* Scrub slider — widened by one thumb width and shifted half a thumb left so
          the thumb CENTER (not its edge) travels exactly the chart's 0%–100% width.
          A native range thumb at min/max has its EDGE flush with the track end, which
          would put the thumb center half a thumb inside the chart edges and misalign
          it with the crosshair. The 6px overhang lands in the card's px-4 padding. */}
      <div
        className="relative"
        style={{
          width: `calc(100% + ${SLIDER_THUMB_PX}px)`,
          marginLeft: `${-SLIDER_THUMB_PX / 2}px`,
        }}
      >
        <input
          type="range"
          min={sliderMin}
          max={sliderMax}
          step={1}
          value={activePly}
          onChange={handleSliderChange}
          onFocus={() => setSliderFocused(true)}
          onBlur={() => setSliderFocused(false)}
          data-testid={`eval-slider-${gameId}`}
          aria-label={`Scrub move for game ${gameId}`}
          className="w-full h-4 appearance-none bg-transparent cursor-pointer
            [&::-webkit-slider-runnable-track]:h-1.5
            [&::-webkit-slider-runnable-track]:rounded-full
            [&::-webkit-slider-runnable-track]:bg-border/40
            [&::-moz-range-track]:h-1.5
            [&::-moz-range-track]:rounded-full
            [&::-moz-range-track]:bg-border/40
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-3
            [&::-webkit-slider-thumb]:h-3
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:bg-foreground
            [&::-webkit-slider-thumb]:mt-[-3px]
            [&::-moz-range-thumb]:w-3
            [&::-moz-range-thumb]:h-3
            [&::-moz-range-thumb]:rounded-full
            [&::-moz-range-thumb]:bg-foreground
            [&::-moz-range-thumb]:border-0"
        />
      </div>
    </div>
  );
}
