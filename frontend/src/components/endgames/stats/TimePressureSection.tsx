import type { ReactNode } from 'react';
import { EndgameClockDiffOverTimeChart } from '@/components/charts/EndgameClockDiffOverTimeChart';
import { ScoreGapByTimePressureChart } from '@/components/charts/ScoreGapByTimePressureChart';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { useEndgameStatsTc } from '@/hooks/useEndgameStatsTc';
import type { RankedTcStats } from '@/types/endgames';
import { RankedMetricRow } from './RankedMetricRow';
import { TC_LABELS } from '@/lib/timeControlLabels';
import { SECTION_ID_TIME_PRESSURE } from './rankedMetrics';

interface TimePressureSectionProps {
  tcs: readonly RankedTcStats[];
  /** Rendered under the heading, above the charts: the narration slot. */
  children?: ReactNode;
}

/**
 * Endgame Time Pressure (D-06, D-00f): for the selected time control, the Clock
 * Gap timeline and the score-vs-clock curve (both with one grey typical band, a
 * neutral line and zone-colored dots) plus the three peer-ranked clock metrics. The TC comes from the
 * shared selection store, so one switch drives the whole section.
 */
export function TimePressureSection({ tcs, children }: TimePressureSectionProps) {
  const [selectedTc] = useEndgameStatsTc(tcs);
  const tcStats = tcs.find((t) => t.tc === selectedTc);
  if (!tcStats) return null;

  const hasClockTimeline = tcStats.clock_diff_timeline.length > 0;

  return (
    <section
      id={SECTION_ID_TIME_PRESSURE}
      className="flex scroll-mt-16 flex-col gap-4"
      data-testid="endgame-time-pressure-section"
      aria-label={`Time Pressure, ${TC_LABELS[tcStats.tc]}`}
    >
      <h2 className="font-brand text-lg font-semibold text-foreground">Time Pressure</h2>
      {children}
      {hasClockTimeline && (
        <div
          className="charcoal-texture rounded-md overflow-hidden"
          data-testid="time-pressure-clock-card"
        >
          <EndgameClockDiffOverTimeChart timeline={tcStats.clock_diff_timeline} />
        </div>
      )}
      <Card data-testid="time-pressure-curve-card">
        <CardHeader>How does your score change under time pressure?</CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div className="min-w-0">
              <h4 className="font-semibold">Score vs. opponent by clock left</h4>
              <p className="mb-2 text-sm text-muted-foreground">
                Your score minus your opponents&apos; score when they had the same clock left.
              </p>
              <ScoreGapByTimePressureChart
                quintiles={tcStats.time_pressure.quintiles}
                tc={tcStats.tc}
              />
            </div>
            <div className="flex min-w-0 flex-col gap-4" data-testid="time-pressure-peers">
              <h4 className="font-semibold">Your clock vs. peers</h4>
              <RankedMetricRow
                metric={tcStats.metrics.clock_gap}
                tcStats={tcStats}
                testId="time-pressure-clock-gap"
                label="Clock Gap at entry"
              />
              <RankedMetricRow
                metric={tcStats.metrics.net_flag_rate}
                tcStats={tcStats}
                testId="time-pressure-net-flag-rate"
              />
              <RankedMetricRow
                metric={tcStats.metrics.time_pressure_score_gap}
                tcStats={tcStats}
                testId="time-pressure-score-gap"
                label="Score under time pressure"
              />
            </div>
          </div>
        </CardBody>
      </Card>
    </section>
  );
}
