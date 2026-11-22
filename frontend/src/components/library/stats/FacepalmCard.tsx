import { FacepalmBlunderIcon } from '@/components/icons/SeverityGlyphIcon';

import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { InfoPopover } from '@/components/ui/info-popover';
import { LoadError } from '@/components/ui/load-error';
import { FACEPALM_CARD_INFO, FACEPALM_LOW_COVERAGE_NOTE } from '@/lib/facepalm';
import {
  FACEPALM_GAP_META,
  FACEPALM_METRICS,
  facepalmMetricCell,
  libraryBasisText,
  metricTestIdSegment,
} from '@/lib/flawComparisonMeta';
import type { FacepalmBullet, FacepalmMetric, FlawComparisonTc } from '@/types/library';
import { facepalmRangeNote } from './facepalmRangeNote';
import { GapAxisCaption } from './GapAxisCaption';
import { GapPopover } from './GapPopover';
import { GapRow } from './GapRow';

/** The card intro (257 D-16): the comparison only, nothing on what a higher rate means. */
const FACEPALM_INTRO =
  "Your facepalm blunders per 100 of your moves, next to your opponents' in the same games.";

interface FacepalmRowProps {
  metric: FacepalmMetric;
  tcStats: FlawComparisonTc;
  bullets: readonly FacepalmBullet[];
}

/** One facepalm row: label, hint, gap bar and the popover, like a context-tag row. */
function FacepalmRow({ metric, tcStats, bullets }: FacepalmRowProps) {
  const cell = facepalmMetricCell(bullets, metric);
  if (!cell) return null;
  const meta = FACEPALM_GAP_META[metric];
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
            rangeNote={facepalmRangeNote(cell)}
          />
        )
      }
    />
  );
}

interface FacepalmCardProps {
  /** The selected TC of /flaw-comparison: the analyzed count and TC of the popover basis. */
  tcStats: FlawComparisonTc;
  /** The selected TC's rows from /facepalm-comparison; undefined while that request loads. */
  bullets: readonly FacepalmBullet[] | undefined;
  isError: boolean;
  /** The rows are withheld: too few of either side's blunders carry a facepalm score. */
  lowCoverage: boolean;
}

/**
 * The Facepalm blunders card of You vs. your opponents (257 D-11): the user's facepalm
 * blunders per 100 of their moves next to their opponents' in the same games, in total and
 * per type. Each row carries its own per-TC typical band and the standard verdict colour (like
 * the other cards, with the better / worse axis caption), and a type row compares the user
 * with the opponents' same type only (D-04). Its rows come from their
 * own request (257 D-21), so the card loads and fails on its own without holding the section.
 */
export function FacepalmCard({ tcStats, bullets, isError, lowCoverage }: FacepalmCardProps) {
  const renderRows = () => {
    if (isError) return <LoadError resource="facepalm blunders" />;
    if (!bullets) {
      return (
        <div
          className="h-32 animate-pulse rounded bg-charcoal"
          data-testid="context-card-facepalm-loading"
        />
      );
    }
    if (lowCoverage) {
      return (
        <p className="text-sm text-muted-foreground" data-testid="context-card-facepalm-low-coverage">
          {FACEPALM_LOW_COVERAGE_NOTE}
        </p>
      );
    }
    return (
      <>
        {FACEPALM_METRICS.map((metric) => (
          <FacepalmRow key={metric} metric={metric} tcStats={tcStats} bullets={bullets} />
        ))}
        <GapAxisCaption testId="context-card-facepalm-axis" />
      </>
    );
  };

  return (
    <Card data-testid="context-card-facepalm">
      <CardHeader className="flex items-center gap-2">
        <FacepalmBlunderIcon className="h-4 w-4" aria-hidden="true" />
        Facepalm blunders
        <InfoPopover ariaLabel="About facepalm blunders" testId="context-card-facepalm-info">
          <p>{FACEPALM_CARD_INFO}</p>
        </InfoPopover>
      </CardHeader>
      <CardBody className="space-y-4">
        <p className="text-sm text-muted-foreground" data-testid="context-card-facepalm-intro">
          {FACEPALM_INTRO}
        </p>
        {renderRows()}
      </CardBody>
    </Card>
  );
}
