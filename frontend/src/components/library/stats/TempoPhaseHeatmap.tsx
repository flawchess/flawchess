import { Card, CardBody, CardHeader } from '@/components/ui/card';
import {
  FLAW_GAP_META,
  TEMPO_PHASE_PHASES,
  TEMPO_PHASE_TEMPOS,
  libraryBasisText,
  metricTestIdSegment,
  tempoPhaseGapCell,
  tempoPhaseMeta,
} from '@/lib/flawComparisonMeta';
import {
  HEATMAP_EMPTY_WORDS,
  gapHeatmapFill,
  gapWords,
  type GapCell,
} from '@/lib/gapBar';
import type { FlawComparisonTc, FlawPhaseMetric, FlawTempoMetric } from '@/types/library';
import { GapPopover } from './GapPopover';

const COPY_ZONELESS_SIGNIFICANT =
  'There is no typical range for this combination, but the gap is too large to be chance.';
const COPY_LEGEND =
  'Green: fewer flaws than your opponents. Red: more. Grey: typical for your level or no clear difference.';

interface HeatmapCellProps {
  tcStats: FlawComparisonTc;
  tempo: FlawTempoMetric;
  phase: FlawPhaseMetric;
  /** The adapted cell, null when the payload carries none. */
  cell: GapCell | null;
}

/** One grid cell: the gap in words on a gap-bar-rule tint, plus its popover. */
function HeatmapCell({ tcStats, tempo, phase, cell }: HeatmapCellProps) {
  // A missing payload cell keeps the grid shape with an empty placeholder.
  if (!cell) return <div />;
  const tempoSeg = metricTestIdSegment(tempo);
  const phaseSeg = metricTestIdSegment(phase);
  const cellId = `tempo-phase-cell-${tempoSeg}-${phaseSeg}`;
  const meta = tempoPhaseMeta(tempo, phase);
  const fill = gapHeatmapFill(cell);
  return (
    <div
      className="flex min-h-14 min-w-0 flex-wrap items-center justify-center gap-1 rounded px-1 py-2 text-center"
      style={{ backgroundColor: fill.background }}
      data-tint={fill.tint}
      data-tint-percent={fill.percent}
      data-testid={cellId}
    >
      {cell.delta === null ? (
        <span className="text-sm text-muted-foreground" data-testid={`${cellId}-words`}>
          {HEATMAP_EMPTY_WORDS}
        </span>
      ) : (
        <>
          <span className="sr-only">{meta.label}: </span>
          <span
            className="text-sm font-semibold tabular-nums text-foreground"
            data-testid={`${cellId}-words`}
          >
            {gapWords(cell.delta)}
          </span>
          <GapPopover
            testId={`gap-popover-tempo-phase-${tempoSeg}-${phaseSeg}-tc-${tcStats.tc}`}
            label={meta.label}
            definition={meta.definition}
            unit="per 100 moves"
            noun={meta.noun}
            basis={libraryBasisText(tcStats.analyzed_n, tcStats.tc)}
            cell={cell}
            zonelessSignificantCopy={COPY_ZONELESS_SIGNIFICANT}
          />
        </>
      )}
    </div>
  );
}

interface PhaseRowProps {
  tcStats: FlawComparisonTc;
  phase: FlawPhaseMetric;
}

function PhaseRow({ tcStats, phase }: PhaseRowProps) {
  return (
    <>
      <div className="self-center pr-2 text-sm text-muted-foreground">
        {FLAW_GAP_META[phase].label}
      </div>
      {TEMPO_PHASE_TEMPOS.map((tempo) => (
        <HeatmapCell
          key={tempo}
          tcStats={tcStats}
          tempo={tempo}
          phase={phase}
          cell={tempoPhaseGapCell(tcStats, tempo, phase)}
        />
      ))}
    </>
  );
}

interface TempoPhaseHeatmapProps {
  /** The selected time control's comparison entry. */
  tcStats: FlawComparisonTc;
}

/**
 * The Clock by game phase card: the three clock tags (columns) crossed
 * with the three game phases (rows). Each cell is the you-minus-opponents gap per 100 of
 * your moves for flaws carrying BOTH tags, worded like the gap bars. Colour follows the gap
 * bars: green (fewer) or red (more) only when the gap is outside the typical range for your
 * level and too large to be chance; strength grows with the distance beyond the range. The
 * low-clock opening and low-clock middlegame cells have no range and are judged on chance
 * alone (the backend sends has_zone false). Flaws with no clock data are in no cell.
 */
export function TempoPhaseHeatmap({ tcStats }: TempoPhaseHeatmapProps) {
  return (
    <Card data-testid="tempo-phase-card">
      <CardHeader>
        Clock by game phase
        <small className="text-sm font-normal text-muted-foreground">
          how much time you had, in each phase
        </small>
      </CardHeader>
      <CardBody className="space-y-4">
        <div
          className="grid grid-cols-[auto_repeat(3,minmax(0,1fr))] gap-1"
          data-testid="tempo-phase-grid"
        >
          <div aria-hidden="true" />
          {TEMPO_PHASE_TEMPOS.map((tempo) => (
            <div key={tempo} className="text-center text-sm text-muted-foreground">
              {FLAW_GAP_META[tempo].label}
            </div>
          ))}
          {TEMPO_PHASE_PHASES.map((phase) => (
            <PhaseRow key={phase} tcStats={tcStats} phase={phase} />
          ))}
        </div>
        <p className="text-sm text-muted-foreground" data-testid="tempo-phase-legend">
          {COPY_LEGEND}
        </p>
      </CardBody>
    </Card>
  );
}
