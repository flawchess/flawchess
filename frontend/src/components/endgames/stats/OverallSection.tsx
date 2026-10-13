import type { ReactNode } from 'react';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { EndgameEloTimelineSection } from '@/components/charts/EndgameEloTimelineSection';
import { EndgameScoreOverTimeChart } from '@/components/charts/EndgameScoreOverTimeChart';
import { useEndgameStatsTc } from '@/hooks/useEndgameStatsTc';
import type { EndgameWDLSummary, RankedTcStats } from '@/types/endgames';
import { BracketedWdlBar } from './BracketedWdlBar';
import { RankedMetricRow } from './RankedMetricRow';
import { SECTION_ID_OVERALL, TC_LABELS } from './rankedMetrics';

const NO_VALUE = '—';
const PERCENT_SCALE = 100;
const ENTRY_EVAL_DECIMALS = 2;

interface OverallSectionProps {
  tcs: readonly RankedTcStats[];
  /** Rendered under the section question, above the cards: the narration slot. */
  children?: ReactNode;
}

/** Score = (W + D/2) / total as a fraction; null when there are no games. */
function wdlScore(wdl: EndgameWDLSummary): number | null {
  if (wdl.total === 0) return null;
  return (wdl.wins + wdl.draws / 2) / wdl.total;
}

function formatScore(score: number | null): string {
  return score === null ? NO_VALUE : `${(score * PERCENT_SCALE).toFixed(1)}%`;
}

interface ScoreColumnProps {
  label: string;
  wdl: EndgameWDLSummary;
  testId: string;
}

function ScoreColumn({ label, wdl, testId }: ScoreColumnProps) {
  return (
    <div className="min-w-0 flex-1" data-testid={testId}>
      <div className="text-sm text-muted-foreground">
        {label} · {wdl.total.toLocaleString()} games
      </div>
      <div className="text-2xl font-semibold tabular-nums" data-testid={`${testId}-score`}>
        {formatScore(wdlScore(wdl))}
      </div>
      {wdl.total > 0 && (
        <BracketedWdlBar
          shares={{ win: wdl.win_pct, draw: wdl.draw_pct, loss: wdl.loss_pct }}
          covered={wdl.win_pct + wdl.draw_pct / 2}
          testId={testId}
        />
      )}
    </div>
  );
}

/** Card 1: score with vs. without an endgame, then the Endgame Score Gap verdict. */
function ScoreCard({ tcStats }: { tcStats: RankedTcStats }) {
  const { overall, tc } = tcStats;
  return (
    <Card className="flex flex-col" data-testid="endgame-overall-score-card">
      <CardHeader>Score with vs. without endgame</CardHeader>
      <CardBody className="flex flex-1 flex-col gap-4">
        <p className="text-sm text-muted-foreground">
          Your {tc} games from the last 36 months vs. opponents within ±100 Elo.
        </p>
        <div className="flex items-end gap-4">
          <ScoreColumn
            label="No endgame"
            wdl={overall.non_endgame_wdl}
            testId="endgame-overall-no-endgame"
          />
          <span className="pb-6 text-xl text-muted-foreground" aria-hidden="true">
            →
          </span>
          <ScoreColumn
            label="Endgame"
            wdl={overall.endgame_wdl}
            testId="endgame-overall-endgame"
          />
        </div>
        <hr className="mt-auto border-card-edge" />
        <RankedMetricRow
          metric={tcStats.metrics.score_gap}
          tcStats={tcStats}
          testId="endgame-overall-score-gap"
        />
      </CardBody>
    </Card>
  );
}

/** Entry eval in pawns, signed with two decimals: "+0.31". */
function formatEntryEval(pawns: number | null): string {
  if (pawns === null) return NO_VALUE;
  return `${pawns >= 0 ? '+' : ''}${pawns.toFixed(ENTRY_EVAL_DECIMALS)}`;
}

interface FlowBoxProps {
  label: string;
  value: string;
  testId: string;
}

function FlowBox({ label, value, testId }: FlowBoxProps) {
  return (
    <div className="min-w-0 flex-1 rounded-md border border-card-edge bg-card-band px-1.5 py-2.5 text-center">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-2xl font-semibold tabular-nums" data-testid={testId}>
        {value}
      </div>
    </div>
  );
}

/** Card 2: do you keep your entry advantage? Entry eval, expected, actual, then the Eval Score Gap. */
function EntryCard({ tcStats }: { tcStats: RankedTcStats }) {
  const flow = tcStats.overall.entry_flow;
  return (
    <Card className="flex flex-col" data-testid="endgame-overall-entry-card">
      <CardHeader>Do you keep your entry advantage?</CardHeader>
      <CardBody className="flex flex-1 flex-col gap-4">
        <p className="text-sm text-muted-foreground">
          Your {tcStats.tc} games from the last 36 months vs. opponents within ±100 Elo.
        </p>
        <div className="flex items-center gap-2">
          <FlowBox
            label="Entry eval"
            value={formatEntryEval(flow.entry_eval_mean_pawns)}
            testId="endgame-overall-entry-eval"
          />
          <span className="text-muted-foreground" aria-hidden="true">
            →
          </span>
          <FlowBox
            label="Expected"
            value={formatScore(flow.expected_score)}
            testId="endgame-overall-expected"
          />
          <span className="text-muted-foreground" aria-hidden="true">
            →
          </span>
          <FlowBox
            label="Actual"
            value={formatScore(flow.actual_score)}
            testId="endgame-overall-actual"
          />
        </div>
        <hr className="mt-auto border-card-edge" />
        <RankedMetricRow
          metric={tcStats.metrics.achievable_score_gap}
          tcStats={tcStats}
          testId="endgame-overall-eval-score-gap"
        />
      </CardBody>
    </Card>
  );
}

/**
 * The two timelines under the cards (D-03, D-00i): visuals unchanged, series read
 * from the selected TC's ranked payload. The Score Gap chart hides when its series
 * is empty; the ELO timeline component renders its own empty state.
 */
function OverallTimelines({ tcStats }: { tcStats: RankedTcStats }) {
  return (
    <>
      {tcStats.score_gap_timeline.length > 0 && (
        <div className="charcoal-texture rounded-md overflow-hidden">
          <EndgameScoreOverTimeChart
            timeline={tcStats.score_gap_timeline}
            window={tcStats.score_gap_timeline_window}
          />
        </div>
      )}
      <div
        className="charcoal-texture rounded-md overflow-hidden"
        data-testid="endgame-elo-timeline-section"
      >
        <EndgameEloTimelineSection
          data={{ combos: tcStats.elo_timeline, timeline_window: tcStats.elo_timeline_window }}
          isLoading={false}
          isError={false}
        />
      </div>
    </>
  );
}

/**
 * Endgame Overall Performance (D-00h): one TC at a time, two cards, every number
 * from the ranked sample so the big numbers and the percentile describe the same
 * games. The TC comes from the shared selection store.
 */
export function OverallSection({ tcs, children }: OverallSectionProps) {
  const [selectedTc] = useEndgameStatsTc(tcs);
  const tcStats = tcs.find((t) => t.tc === selectedTc);
  if (!tcStats) return null;

  return (
    <section
      id={SECTION_ID_OVERALL}
      className="flex scroll-mt-16 flex-col gap-4"
      data-testid="endgame-overall-section"
      aria-label={`Endgame Overall Performance, ${TC_LABELS[tcStats.tc]}`}
    >
      {/* md:h-8: the page's StickyTcBar overlays this row on desktop (see StickyTcBar). */}
      <div className="flex flex-wrap items-center justify-between gap-2 md:h-8">
        <h2 className="font-brand text-lg font-semibold text-foreground">Endgame Overall Performance</h2>
      </div>
      <p className="text-sm text-muted-foreground">
        Do you perform better or worse when games reach an endgame?
      </p>
      {children}
      <div className="grid grid-cols-1 items-stretch gap-4 md:grid-cols-2">
        <ScoreCard tcStats={tcStats} />
        <EntryCard tcStats={tcStats} />
      </div>
      <OverallTimelines tcStats={tcStats} />
    </section>
  );
}
