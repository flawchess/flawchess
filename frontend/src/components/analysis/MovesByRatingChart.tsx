/**
 * MovesByRatingChart — "Moves by Rating" chart (Phase 151 Plan 05, SURF-01/02/03;
 * recolored by Stockfish-graded quality in Phase 151.1 Plan 04, D-01/D-03/D-08).
 *
 * Recharts port of spike 006 (.planning/spikes/006-moves-by-rating-chart): one line
 * per candidate move's probability across the Maia ELO ladder, rendering exactly the
 * caller-selected `shownSans` (Phase 151.1: `selectCandidatesByMass`'s 0.95-mass set,
 * replacing this component's own top-N-by-peak cap), a "you are here"
 * `<ReferenceLine>` at the selected ELO (SURF-02), and played/best lines emphasized
 * with a thicker stroke (SURF-01) — DECOUPLED from color, which now encodes the
 * move's Stockfish-graded `MoveQuality` bucket (D-01/D-07) instead of played/best
 * identity.
 *
 * The spike hand-rolled imperative SVG to run with zero build — this component is
 * an idiomatic Recharts port (LineChart/Line/ReferenceLine/XAxis/YAxis, custom
 * tooltip via the `content` prop) following the existing chart conventions in
 * EvalChart.tsx / ScoreChart.tsx, not a line-by-line port of the spike's DOM code.
 */

import { CartesianGrid, LabelList, Line, LineChart, ReferenceLine, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { ChartTooltipBox } from '@/components/ui/chart-tooltip-box';
import {
  MOVE_QUALITY_BEST,
  MOVE_QUALITY_BLUNDER,
  MOVE_QUALITY_GOOD,
  MOVE_QUALITY_INACCURACY,
  MOVE_QUALITY_MISTAKE,
  MOVE_QUALITY_PENDING,
  MOVES_BY_RATING_REFERENCE_LINE,
} from '@/lib/theme';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';
import type { MoveQuality } from '@/lib/moveQuality';

// Emphasized (played/best) vs. muted (other shown) stroke widths.
const EMPHASIZED_STROKE_WIDTH = 3;
const OTHER_STROKE_WIDTH = 1.5;

// Max x-axis ticks shown — keeps the ELO axis legible at ~360px (D-02).
const MAX_X_TICKS = 5;

// Fixed chart height — shared by the loading skeleton and the rendered chart so the
// card holds a constant height instead of jumping when Maia results arrive (matches
// the engine card's no-jump skeleton — UAT quick 260705-dj5).
const CHART_HEIGHT_CLASS = 'h-64';

// End-of-line move labels (UAT quick 260705-dj5): each shown line is tagged with its
// SAN at its right end (like the desktop reference), so the chart carries its own
// legend. MOVE_LABEL_RIGHT_MARGIN reserves room for them; the tighter Y_AXIS_WIDTH
// reclaims the left gutter so the plot itself gets wider.
const MOVE_LABEL_FONT_SIZE = 11;
const MOVE_LABEL_OFFSET_X = 4;
const MOVE_LABEL_RIGHT_MARGIN = 40;
const Y_AXIS_WIDTH = 36;

// Fallback y-axis ticks (0-100%) used only when no probability data is available.
const PROBABILITY_TICKS = [0, 0.25, 0.5, 0.75, 1];

// Adaptive y-axis (UAT quick 260705-bm3): candidate tick steps + the max number of
// intervals we'll draw. We pick the smallest step that keeps the axis at/below
// Y_AXIS_MAX_INTERVALS divisions, then round the peak shown probability up to it.
const Y_AXIS_STEP_CANDIDATES = [0.05, 0.1, 0.2, 0.25] as const;
const Y_AXIS_MAX_INTERVALS = 5;
const Y_AXIS_FULL = 1;

/**
 * Adaptive y-axis domain + ticks: a "nice" ceiling just above the peak shown
 * probability so the curves fill the vertical space instead of hugging the floor of
 * a fixed 0-100% axis (most human-move probabilities sit well below 100%, and at the
 * extrapolated ELO extremes they can be very small). Floor stays at 0; ceiling is
 * capped at 1. Falls back to the full 0-100% axis when there's no positive data.
 */
function computeYAxis(
  rows: Record<string, number>[],
  shownSans: string[],
): { domain: [number, number]; ticks: number[] } {
  let dataMax = 0;
  for (const row of rows) {
    for (const san of shownSans) {
      const v = row[san];
      if (typeof v === 'number' && v > dataMax) dataMax = v;
    }
  }
  if (dataMax <= 0) return { domain: [0, Y_AXIS_FULL], ticks: PROBABILITY_TICKS };

  const capped = Math.min(Y_AXIS_FULL, dataMax);
  const step = Y_AXIS_STEP_CANDIDATES.find((s) => capped / s <= Y_AXIS_MAX_INTERVALS) ?? 0.25;
  const top = Math.min(Y_AXIS_FULL, Math.ceil(capped / step) * step);

  const ticks: number[] = [];
  for (let v = 0; v <= top + 1e-9; v += step) ticks.push(Math.round(v * 100) / 100);
  return { domain: [0, top], ticks };
}

/** Per-SAN quality + white-POV eval, as computed by Analysis.tsx from the grading hook's gradeMap. */
export interface MoveQualityEval {
  quality: MoveQuality;
  evalCp: number | null;
  evalMate: number | null;
}

/**
 * One primary-engine PV line's first move + white-POV eval — the authoritative
 * eval bar / engine-card search (useStockfishEngine, MultiPV=2), shown as a
 * reference header in the tooltip (151.1 UAT: surface the engine's best and
 * second-best line evals alongside the Maia probabilities).
 */
export interface EngineLine {
  san: string;
  evalCp: number | null;
  evalMate: number | null;
}

export interface MovesByRatingChartProps {
  /** One entry per MAIA_ELO_LADDER rung (useMaiaEngine's perElo; [] until first result). */
  perElo: MoveCurvePoint[];
  /** SAN the user actually played at this position, or null if none (e.g. free exploration). */
  playedSan: string | null;
  /** SAN of the engine's best move at this position, or null if unknown. */
  bestSan: string | null;
  /** The ELO the "you are here" reference line marks (EloSelector's current value). */
  selectedElo: number;
  /** The already-selected candidate set to render (Analysis.tsx's selectCandidatesByMass output). */
  shownSans: string[];
  /** Per-SAN Stockfish-graded quality + eval, for line/label color and the tooltip (D-08). Missing entries render MOVE_QUALITY_PENDING (D-05). */
  qualityBySan: Map<string, MoveQualityEval>;
  /** Primary engine's top PV lines (best + 2nd-best), shown as a reference header in the tooltip (151.1 UAT). */
  engineTopLines: EngineLine[];
  /** Tailwind height class for the plot (and its no-jump skeleton). Defaults to the
   * desktop `h-64`; mobile passes a shorter class to reclaim vertical space (151.1 UAT). */
  heightClass?: string;
}

/** Pivot perElo into Recharts row data: one row per ELO rung, one field per shown SAN. */
function pivotRows(perElo: MoveCurvePoint[], shownSans: string[]): Record<string, number>[] {
  return perElo.map((point) => {
    const row: Record<string, number> = { elo: point.elo };
    for (const san of shownSans) {
      row[san] = point.moveProbabilities[san] ?? 0;
    }
    return row;
  });
}

/**
 * Color encodes quality ONLY (D-01/D-07) — stroke width (below) handles
 * played/best emphasis independently. Ungraded (not-yet-arrived, D-05)
 * candidates render MOVE_QUALITY_PENDING's neutral gray until the streaming
 * grading hook commits their first grade.
 */
function colorForQuality(quality: MoveQuality | undefined): string {
  switch (quality) {
    case 'best':
      return MOVE_QUALITY_BEST;
    case 'good':
      return MOVE_QUALITY_GOOD;
    case 'inaccuracy':
      return MOVE_QUALITY_INACCURACY;
    case 'mistake':
      return MOVE_QUALITY_MISTAKE;
    case 'blunder':
      return MOVE_QUALITY_BLUNDER;
    default:
      return MOVE_QUALITY_PENDING;
  }
}

/** White-POV eval text for the tooltip (D-08): "+1.2" for cp, "#N"/"#-N" for mate, "—" ungraded. */
function formatEvalText(evalCp: number | null, evalMate: number | null): string {
  if (evalMate !== null) return evalMate > 0 ? `#${evalMate}` : `#-${Math.abs(evalMate)}`;
  if (evalCp !== null) {
    const pawns = evalCp / 100;
    return pawns >= 0 ? `+${pawns.toFixed(1)}` : pawns.toFixed(1);
  }
  return '—';
}

/** Capitalized quality word for the tooltip (D-08), e.g. "Best"/"Inaccuracy". Ungraded → "Pending". */
function qualityWord(quality: MoveQuality | undefined): string {
  if (quality === undefined) return 'Pending';
  return quality[0]!.toUpperCase() + quality.slice(1);
}

/** Sample at most `maxTicks` values from `values`, always including the first and last. */
function sampleTicks(values: number[], maxTicks: number): number[] {
  if (values.length <= maxTicks) return values;
  const step = (values.length - 1) / (maxTicks - 1);
  const indices = new Set<number>();
  for (let i = 0; i < maxTicks; i++) indices.add(Math.round(i * step));
  return Array.from(indices)
    .map((i) => values[i])
    .filter((v): v is number => v !== undefined);
}

/**
 * `content` render prop for a per-line LabelList that draws the move's SAN at the
 * RIGHT end of its line only (the last ELO rung), in the line's own color — an
 * on-chart legend mirroring the desktop reference (UAT quick 260705-dj5).
 */
function endOfLineLabel(san: string, color: string, lastIndex: number) {
  return function EndOfLineLabel(props: {
    x?: number | string;
    y?: number | string;
    index?: number;
  }): React.ReactElement {
    if (props.index !== lastIndex || props.x == null || props.y == null) return <g />;
    return (
      <text
        x={Number(props.x) + MOVE_LABEL_OFFSET_X}
        y={Number(props.y)}
        textAnchor="start"
        dominantBaseline="central"
        fontSize={MOVE_LABEL_FONT_SIZE}
        fill={color}
      >
        {san}
      </text>
    );
  };
}

type TooltipPayloadItem = {
  dataKey?: string | number | ((obj: unknown) => unknown);
  value?: number | string | readonly (number | string)[];
  color?: string;
};

type ResolvedTooltipPayloadItem = { dataKey: string; value: number; color?: string };

export interface MovesTooltipRow {
  san: string;
  probability: number;
  color?: string;
}

/**
 * Custom tooltip body (D-08): ELO rung header, an engine-reference line showing
 * the primary engine's top PV lines (best + 2nd-best; 151.1 UAT), then every
 * shown move's row `${san}${roleSuffix}: ${qualityWord} · ${evalText} · ${prob}%`,
 * sorted by probability descending. The best move carries no role suffix — its
 * "Best" quality word already says so (151.1 UAT: the old `· best` suffix was
 * redundant). Exported as a standalone component (mirroring
 * ScoreGapByTimePressureChart.tsx's `ScoreGapTooltipContent` convention) so
 * it's directly unit-testable without simulating a recharts hover.
 */
export function MovesByRatingTooltipContent({
  label,
  rows,
  playedSan,
  engineTopLines,
  qualityBySan,
}: {
  label: string | number;
  rows: MovesTooltipRow[];
  playedSan: string | null;
  engineTopLines: EngineLine[];
  qualityBySan: Map<string, MoveQualityEval>;
}): React.ReactElement {
  return (
    <ChartTooltipBox data-testid="moves-by-rating-tooltip">
      <div className="font-medium text-foreground">{`ELO ${label}`}</div>
      {engineTopLines.length > 0 && (
        <div className="text-muted-foreground" data-testid="moves-by-rating-tooltip-engine">
          {`Engine: ${engineTopLines
            .map((line) => `${line.san} ${formatEvalText(line.evalCp, line.evalMate)}`)
            .join(' · ')}`}
        </div>
      )}
      {rows.map((row) => {
        const { san } = row;
        const roleSuffix = san === playedSan ? ' · played' : '';
        const graded = qualityBySan.get(san);
        const evalText = formatEvalText(graded?.evalCp ?? null, graded?.evalMate ?? null);
        return (
          <div
            key={san}
            data-testid={`moves-by-rating-tooltip-row-${san}`}
            style={{ color: row.color }}
          >
            {`${san}${roleSuffix}: ${qualityWord(graded?.quality)} · ${evalText} · ${Math.round(row.probability * 100)}%`}
          </div>
        );
      })}
    </ChartTooltipBox>
  );
}

/**
 * `content` render prop factory wiring recharts' raw tooltip payload into
 * `MovesByRatingTooltipContent` — a thin adapter (payload extraction/sorting
 * only), mirroring ScoreGapByTimePressureChart.tsx's inline `content` wrapper.
 */
function movesTooltipContent(
  playedSan: string | null,
  engineTopLines: EngineLine[],
  qualityBySan: Map<string, MoveQualityEval>,
): (props: {
  active?: boolean;
  payload?: readonly TooltipPayloadItem[];
  label?: string | number;
}) => React.ReactElement | null {
  return function MovesTooltipContentAdapter({ active, payload, label }) {
    if (!active || !payload || payload.length === 0) return null;
    const rows: MovesTooltipRow[] = payload
      .filter(
        (p): p is ResolvedTooltipPayloadItem =>
          typeof p.dataKey === 'string' && typeof p.value === 'number',
      )
      .map((p) => ({ san: p.dataKey, probability: p.value, color: p.color }))
      .sort((a, b) => b.probability - a.probability);
    return (
      <MovesByRatingTooltipContent
        label={label ?? ''}
        rows={rows}
        playedSan={playedSan}
        engineTopLines={engineTopLines}
        qualityBySan={qualityBySan}
      />
    );
  };
}

/**
 * "Moves by Rating" chart: one probability line per shown candidate move over the
 * Maia ELO ladder (caller-selected `shownSans`), colored by Stockfish-graded
 * quality, with a "you are here" reference line at the selected ELO. Renders a
 * minimal placeholder while `perElo` is empty (Maia not yet ready for this
 * position).
 */
export function MovesByRatingChart({
  perElo,
  playedSan,
  bestSan,
  selectedElo,
  shownSans,
  qualityBySan,
  engineTopLines,
  heightClass = CHART_HEIGHT_CLASS,
}: MovesByRatingChartProps): React.ReactElement {
  if (perElo.length === 0) {
    return (
      <div
        data-testid="moves-by-rating-chart"
        className={`w-full ${heightClass}`}
        role="img"
        aria-label="Moves by rating chart: waiting for Maia analysis"
      >
        {/* Fixed-height pulsing placeholder — same no-jump loading pattern as the
            engine (Stockfish) card, so the card keeps its size until Maia is ready. */}
        <div
          data-testid="moves-by-rating-chart-skeleton"
          aria-busy="true"
          className="h-full w-full animate-pulse rounded-md bg-muted/30"
        />
        <span className="sr-only">Waiting for Maia analysis...</span>
      </div>
    );
  }

  const rows = pivotRows(perElo, shownSans);
  const elos = perElo.map((p) => p.elo);
  const xTicks = sampleTicks(elos, MAX_X_TICKS);
  const { domain: yDomain, ticks: yTicks } = computeYAxis(rows, shownSans);

  return (
    <div
      data-testid="moves-by-rating-chart"
      role="img"
      aria-label="Moves by rating chart"
    >
      <ChartContainer config={{}} className={`w-full ${heightClass}`}>
        <LineChart data={rows} margin={{ top: 8, right: MOVE_LABEL_RIGHT_MARGIN, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="elo"
            type="number"
            domain={[elos[0] ?? 0, elos[elos.length - 1] ?? 0]}
            ticks={xTicks}
          />
          <YAxis
            width={Y_AXIS_WIDTH}
            domain={yDomain}
            ticks={yTicks}
            tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
          />

          <ReferenceLine
            x={selectedElo}
            stroke={MOVES_BY_RATING_REFERENCE_LINE}
            strokeDasharray="4 4"
            strokeWidth={1.5}
          />

          <ChartTooltip content={movesTooltipContent(playedSan, engineTopLines, qualityBySan)} />

          {shownSans.map((san) => {
            // Stroke width encodes played/best emphasis ONLY; color encodes quality
            // ONLY — the two are decoupled (D-01/D-07). A played or SF-best move
            // keeps the emphasized stroke regardless of its quality color.
            const emphasized = san === playedSan || san === bestSan;
            const color = colorForQuality(qualityBySan.get(san)?.quality);
            return (
              <Line
                key={san}
                type="monotone"
                dataKey={san}
                stroke={color}
                strokeWidth={emphasized ? EMPHASIZED_STROKE_WIDTH : OTHER_STROKE_WIDTH}
                dot={false}
                isAnimationActive={false}
              >
                <LabelList content={endOfLineLabel(san, color, rows.length - 1)} />
              </Line>
            );
          })}
        </LineChart>
      </ChartContainer>
    </div>
  );
}
