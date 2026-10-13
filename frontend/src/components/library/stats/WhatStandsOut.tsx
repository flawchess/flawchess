import { Card, CardBody, CardHeader } from '@/components/ui/card';
import {
  CONTEXT_TAG_METRICS,
  FLAW_GAP_META,
  flawMetricCell,
  libraryBasisText,
  metricTestIdSegment,
  type ContextTagMetric,
} from '@/lib/flawComparisonMeta';
import {
  gapVerdictColor,
  gapWords,
  pickStandouts,
  type GapVerdict,
  type RankedStandout,
  type StandoutRow,
} from '@/lib/gapBar';
import { GapPopover } from './GapPopover';
import type { FlawComparisonTc } from '@/types/library';

const COPY_NOTHING_OUTSIDE = 'Nothing outside the typical range.';
const TYPICAL_SEPARATOR = ', ';

type StandoutSide = Extract<GapVerdict, 'better' | 'worse'>;

/** Context rows that have a bullet in the payload (D-13: never blunder or mistake). */
function contextRows(tcStats: FlawComparisonTc): StandoutRow<ContextTagMetric>[] {
  const rows: StandoutRow<ContextTagMetric>[] = [];
  for (const key of CONTEXT_TAG_METRICS) {
    const cell = flawMetricCell(tcStats, key);
    if (cell) rows.push({ key, cell });
  }
  return rows;
}

interface StandoutItemProps {
  item: RankedStandout<ContextTagMetric>;
  side: StandoutSide;
  tcStats: FlawComparisonTc;
}

function StandoutItem({ item, side, tcStats }: StandoutItemProps) {
  const meta = FLAW_GAP_META[item.key];
  const segment = metricTestIdSegment(item.key);
  return (
    <li
      className="flex items-center justify-between gap-3 border-t border-card-edge py-2 first:border-t-0"
      data-testid={`standout-${segment}`}
    >
      <span>
        <span className="block font-semibold">{meta.label}</span>
        <span className="block text-sm text-muted-foreground">{meta.hint}</span>
      </span>
      <span className="inline-flex shrink-0 items-center gap-1.5">
        <span
          className="font-bold"
          style={{ color: gapVerdictColor(side) }}
          data-testid={`standout-${segment}-words`}
        >
          {item.cell.delta === null ? '' : gapWords(item.cell.delta)}
        </span>
        <GapPopover
          testId={`gap-popover-standout-${segment}-tc-${tcStats.tc}`}
          label={meta.label}
          definition={meta.definition}
          unit="per 100 moves"
          noun={meta.noun}
          basis={libraryBasisText(tcStats.analyzed_n, tcStats.tc)}
          cell={item.cell}
        />
      </span>
    </li>
  );
}

interface StandoutListProps {
  side: StandoutSide;
  title: string;
  items: readonly RankedStandout<ContextTagMetric>[];
  tcStats: FlawComparisonTc;
}

function StandoutList({ side, title, items, tcStats }: StandoutListProps) {
  return (
    <div data-testid={`what-stands-out-${side === 'better' ? 'strengths' : 'weaknesses'}`}>
      <div className="mb-1 flex items-center gap-2 font-semibold">
        <span
          className="size-2.5 rounded-full"
          style={{ backgroundColor: gapVerdictColor(side) }}
          aria-hidden="true"
        />
        {title}
      </div>
      {items.length === 0 ? (
        <p className="my-1.5 text-sm text-muted-foreground">{COPY_NOTHING_OUTSIDE}</p>
      ) : (
        <ul>
          {items.map((item) => (
            <StandoutItem key={item.key} item={item} side={side} tcStats={tcStats} />
          ))}
        </ul>
      )}
    </div>
  );
}

interface WhatStandsOutProps {
  /** The selected time control's comparison entry. */
  tcStats: FlawComparisonTc;
}

/**
 * What stands out (D-00g, D-13): the top 3 strengths and top 3 weaknesses among the 10
 * context tags by distance outside the typical band, then one line naming the typical
 * tags. Blunder and mistake have their own tiles and are never ranked; low-sample,
 * zoneless and flaw-less rows are dropped by pickStandouts before ranking.
 */
export function WhatStandsOut({ tcStats }: WhatStandsOutProps) {
  const { strengths, weaknesses, typical } = pickStandouts(contextRows(tcStats));
  return (
    <Card data-testid="what-stands-out">
      <CardHeader>What stands out</CardHeader>
      <CardBody>
        <div className="grid grid-cols-1 gap-x-6 gap-y-3 md:grid-cols-2">
          <StandoutList side="better" title="Strengths" items={strengths} tcStats={tcStats} />
          <StandoutList side="worse" title="Weaknesses" items={weaknesses} tcStats={tcStats} />
        </div>
        {typical.length > 0 && (
          <p
            className="mt-3 border-t border-card-edge pt-2.5 text-sm text-muted-foreground"
            data-testid="what-stands-out-typical"
          >
            Typical: {typical.map((row) => FLAW_GAP_META[row.key].label).join(TYPICAL_SEPARATOR)}.
          </p>
        )}
      </CardBody>
    </Card>
  );
}
