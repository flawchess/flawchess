import { Card, CardBody, CardHeader } from '@/components/ui/card';
import {
  FLAW_GAP_META,
  TEMPO_PHASE_PHASES,
  TEMPO_PHASE_TEMPOS,
  metricTestIdSegment,
  tempoPhaseGapCell,
} from '@/lib/flawComparisonMeta';
import { GAP_EMPTY_WORDS, gapWords } from '@/lib/gapBar';
import type { FlawComparisonTc, FlawPhaseMetric, FlawTempoMetric } from '@/types/library';

interface HeatmapCellProps {
  tcStats: FlawComparisonTc;
  tempo: FlawTempoMetric;
  phase: FlawPhaseMetric;
}

/** One grid cell: the gap in words, or the bars' empty copy when neither side has such a flaw. */
function HeatmapCell({ tcStats, tempo, phase }: HeatmapCellProps) {
  const cell = tempoPhaseGapCell(tcStats, tempo, phase);
  // A missing payload cell keeps the grid shape with an empty placeholder.
  if (!cell) return <div />;
  const cellId = `tempo-phase-cell-${metricTestIdSegment(tempo)}-${metricTestIdSegment(phase)}`;
  return (
    <div
      className="flex min-h-14 min-w-0 flex-wrap items-center justify-center gap-1 rounded border border-border px-1 py-2 text-center"
      data-testid={cellId}
    >
      {cell.delta === null ? (
        <span className="text-sm text-muted-foreground" data-testid={`${cellId}-words`}>
          {GAP_EMPTY_WORDS}
        </span>
      ) : (
        <span
          className="text-sm font-semibold tabular-nums text-foreground"
          data-testid={`${cellId}-words`}
        >
          {gapWords(cell.delta)}
        </span>
      )}
    </div>
  );
}

interface TempoPhaseHeatmapProps {
  /** The selected time control's comparison entry. */
  tcStats: FlawComparisonTc;
}

/**
 * The Clock by game phase card (quick 261014-pb9): the three clock tags (columns) crossed
 * with the three game phases (rows). Each cell is the you-minus-opponents gap per 100 of
 * your moves for flaws carrying BOTH tags, worded like the gap bars. Flaws with no clock
 * data are in no cell.
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
      </CardBody>
    </Card>
  );
}

function PhaseRow({ tcStats, phase }: { tcStats: FlawComparisonTc; phase: FlawPhaseMetric }) {
  return (
    <>
      <div className="self-center pr-2 text-sm text-muted-foreground">
        {FLAW_GAP_META[phase].label}
      </div>
      {TEMPO_PHASE_TEMPOS.map((tempo) => (
        <HeatmapCell key={tempo} tcStats={tcStats} tempo={tempo} phase={phase} />
      ))}
    </>
  );
}
