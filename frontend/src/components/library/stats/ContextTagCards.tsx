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
import { GAP_AXIS_LABELS } from '@/lib/gapBar';
import { GapPopover } from './GapPopover';
import { GapRow } from './GapRow';
import type { FlawComparisonTc } from '@/types/library';

// Fewer flaws (better) sit left on every gap bar; the caption read worse/better, inverted.
/**
 * Right margin that ends the caption row where the bar track ends: on phones the words
 * column (6rem) and popover sit right of the track; from md up the track is full width.
 */
const AXIS_CAPTION_CLASS = 'mr-34 md:mr-0 flex justify-between text-sm text-muted-foreground';

interface ContextTagRowProps {
  metric: ContextTagMetric;
  tcStats: FlawComparisonTc;
}

/** One tag row: unchanged name, one-line hint, gap bar, Search popover (D-00f). */
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
        <div className={AXIS_CAPTION_CLASS} data-testid={`${testId}-axis`}>
          {GAP_AXIS_LABELS.map((label) => (
            <span key={label}>{label}</span>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

interface ContextTagCardsProps {
  /** The selected time control's comparison entry. */
  tcStats: FlawComparisonTc;
}

/**
 * The four context-tag cards (D-00f, D-00j): Clock, Game phase, Opponent errors, Lost
 * advantages. Two columns from lg up, one on phones. Rows under the sample minimum fade
 * inside GapRow (D-12).
 */
export function ContextTagCards({ tcStats }: ContextTagCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2" data-testid="context-tag-cards">
      {CONTEXT_TAG_CARDS.map((card) => (
        <ContextTagCard key={card.key} card={card} tcStats={tcStats} />
      ))}
    </div>
  );
}
