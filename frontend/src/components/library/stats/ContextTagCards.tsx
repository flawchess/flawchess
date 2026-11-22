import type { ReactNode } from 'react';

import { Card, CardBody, CardHeader } from '@/components/ui/card';
import {
  CONTEXT_TAG_CARDS,
  FLAW_GAP_META,
  flawMetricCell,
  libraryBasisText,
  metricTestIdSegment,
  type ContextTagCardDef,
  type ContextTagMetric,
} from '@/lib/flawComparisonMeta';
import { GapAxisCaption } from './GapAxisCaption';
import { GapPopover } from './GapPopover';
import { GapRow } from './GapRow';
import type { FlawComparisonTc } from '@/types/library';

/** Cards per row from lg up; the `afterFirstRow` slot goes in after this many cards. */
const CARDS_PER_ROW = 2;

interface ContextTagRowProps {
  metric: ContextTagMetric;
  tcStats: FlawComparisonTc;
}

/** One tag row: unchanged name, one-line hint, gap bar, Search popover. */
function ContextTagRow({ metric, tcStats }: ContextTagRowProps) {
  const cell = flawMetricCell(tcStats, metric);
  if (!cell) return null;
  const meta = FLAW_GAP_META[metric];
  const segment = metricTestIdSegment(metric);
  return (
    <GapRow
      label={meta.label}
      hint={meta.hint}
      cell={cell}
      testId={`context-row-${segment}`}
      popover={
        cell.delta === null ? undefined : (
          <GapPopover
            testId={`gap-popover-${segment}-tc-${tcStats.tc}`}
            label={meta.label}
            definition={meta.definition}
            unit="per 100 moves"
            noun={meta.noun}
            basis={libraryBasisText(tcStats.analyzed_n, tcStats.tc)}
            cell={cell}
          />
        )
      }
    />
  );
}

interface ContextTagCardProps {
  card: ContextTagCardDef;
  tcStats: FlawComparisonTc;
}

function ContextTagCard({ card, tcStats }: ContextTagCardProps) {
  const testId = `context-card-${card.key.replace(/_/g, '-')}`;
  return (
    <Card data-testid={testId}>
      <CardHeader>
        {card.title}
        <small className="text-sm font-normal text-muted-foreground">{card.subtitle}</small>
      </CardHeader>
      <CardBody className="space-y-4">
        {card.metrics.map((metric) => (
          <ContextTagRow key={metric} metric={metric} tcStats={tcStats} />
        ))}
        <GapAxisCaption testId={`${testId}-axis`} />
      </CardBody>
    </Card>
  );
}

interface ContextTagCardsProps {
  /** The selected time control's comparison entry. */
  tcStats: FlawComparisonTc;
  /** Full-width content between the first and second card rows (the Clock by game phase heatmap). */
  afterFirstRow?: ReactNode;
  /** The last grid child, after the four cards (the Facepalm blunders card): one column from lg up, last on phones. */
  trailing?: ReactNode;
}

/**
 * The four context-tag cards: Game phase, Clock, Lost advantages, Opponent
 * errors. Two columns from lg up, one on phones. Each card ends with the
 * better / worse axis caption: fewer flaws (better) sit left on every gap bar. A `trailing`
 * card goes in last and carries its own caption.
 */
export function ContextTagCards({ tcStats, afterFirstRow, trailing }: ContextTagCardsProps) {
  const renderCards = (cards: readonly ContextTagCardDef[]) =>
    cards.map((card) => <ContextTagCard key={card.key} card={card} tcStats={tcStats} />);
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2" data-testid="context-tag-cards">
      {renderCards(CONTEXT_TAG_CARDS.slice(0, CARDS_PER_ROW))}
      {afterFirstRow && <div className="lg:col-span-2">{afterFirstRow}</div>}
      {renderCards(CONTEXT_TAG_CARDS.slice(CARDS_PER_ROW))}
      {trailing}
    </div>
  );
}
