import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LoadError } from '@/components/ui/load-error';
import { FindingCard } from '@/components/openings/stats/FindingCard';
import { SECTION_HEADING_CLASS } from '@/components/openings/stats/headingClasses';
import type { FilterState } from '@/components/filters/FilterPanel';
import { useOpeningInsights } from '@/hooks/useOpeningInsights';
import { trackFeature } from '@/lib/analytics';
import { cn } from '@/lib/utils';
import type { OpeningInsightFinding, OpeningInsightsResponse } from '@/types/insights';

/** Phones show this many cards per section before "Show more" (D-08). */
const INITIAL_VISIBLE_PHONE = 2;
const SKELETON_SECTION_COUNT = 2;

type FindingKind = 'weakness' | 'strength';
type FindingColor = 'white' | 'black';

interface KindMeta {
  kind: FindingKind;
  title: string;
  subtitle: string;
}

const KINDS: readonly KindMeta[] = [
  { kind: 'weakness', title: 'Moves that Cost You', subtitle: 'You score clearly below 50%.' },
  { kind: 'strength', title: 'Moves that Work', subtitle: 'You score clearly above 50%.' },
];

interface SectionData {
  cards: OpeningInsightFinding[];
  notClear: OpeningInsightFinding[];
  notClearCount: number;
}

function colorLabel(color: FindingColor): string {
  return color === 'white' ? 'White' : 'Black';
}

/** The selected colour's lists for one kind; the switch is client-side (the request stays 'all'). */
function sectionData(data: OpeningInsightsResponse, color: FindingColor, kind: FindingKind): SectionData {
  const base = `${color}_${kind === 'weakness' ? 'weaknesses' : 'strengths'}` as const;
  return {
    cards: data[base],
    notClear: data[`${base}_not_clear`],
    notClearCount: data[`${base}_not_clear_count`],
  };
}

/** "3 moves lean this way, but could still be chance." (singular: "1 move leans"). */
function leanText(count: number): string {
  const plural = count !== 1;
  return `${count} move${plural ? 's' : ''} lean${plural ? '' : 's'} this way, but could still be chance.`;
}

function FindingsSkeleton() {
  return (
    <div className="animate-pulse space-y-4" data-testid="opening-findings-loading">
      {Array.from({ length: SKELETON_SECTION_COUNT }, (_, i) => (
        <div key={i} className="space-y-2">
          <div className="h-5 w-48 rounded bg-muted/30" />
          <div className="h-24 w-full rounded bg-muted/30" />
        </div>
      ))}
    </div>
  );
}

function FindingsError({ onRetry }: { onRetry: () => void }) {
  return (
    <div data-testid="opening-findings-error" role="alert">
      <LoadError resource="opening insights" />
      <Button
        variant="brand-outline"
        onClick={onRetry}
        data-testid="btn-opening-findings-retry"
        className="mt-3"
      >
        Try again
      </Button>
    </div>
  );
}

/**
 * Collapsed list of the medium candidates (D-09, D-10), drawn as the same finding cards as the
 * 99% ones; their verdicts and arrows stay uncoloured because none passed the 99% gate.
 */
function NotClearYet({
  kind,
  findings,
  count,
  onOpenMoves,
  onOpenGames,
}: {
  kind: FindingKind;
  findings: OpeningInsightFinding[];
  count: number;
  onOpenMoves: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  if (count <= 0) return null;
  const testId = `opening-findings-${kind}`;
  const handleToggle = () => {
    // Discovery only: track the expand, never the collapse.
    if (!expanded) trackFeature('panel-open', { target: 'opening-findings-unclear' });
    setExpanded((prev) => !prev);
  };
  return (
    <div className="space-y-3" data-testid={`${testId}-unclear`}>
      <button
        type="button"
        className="flex w-full items-center gap-2 text-left text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground"
        aria-expanded={expanded}
        onClick={handleToggle}
        data-testid={`${testId}-unclear-toggle`}
      >
        <span>Not clear yet ({count})</span>
        <span className="font-normal">
          Leaning this way, but the difference from 50% could still be chance.
        </span>
        <ChevronDown
          className={cn('h-4 w-4 shrink-0 transition-transform', expanded && 'rotate-180')}
          aria-hidden="true"
        />
      </button>
      {expanded && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2" data-testid={`${testId}-unclear-list`}>
          {findings.map((finding, i) => (
            <FindingCard
              key={i}
              finding={finding}
              testId={`${testId}-unclear-card-${i}`}
              onOpenMoves={onOpenMoves}
              onOpenGames={onOpenGames}
              neutralArrow
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ShowMoreButton({
  kind,
  expanded,
  onToggle,
}: {
  kind: FindingKind;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      className="flex items-center gap-1 px-2 text-sm text-muted-foreground transition-colors hover:text-foreground md:hidden"
      aria-expanded={expanded}
      onClick={onToggle}
      data-testid={`opening-findings-${kind}-btn-more`}
    >
      {expanded ? (
        <>
          <ChevronUp className="h-4 w-4" />
          Show less
        </>
      ) : (
        <>
          <ChevronDown className="h-4 w-4" />
          Show more
        </>
      )}
    </button>
  );
}

function FindingsSubsection({
  meta,
  color,
  data,
  onOpenMoves,
  onOpenGames,
}: {
  meta: KindMeta;
  color: FindingColor;
  data: SectionData;
  onOpenMoves: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const testId = `opening-findings-${meta.kind}`;
  const handleToggle = () => {
    // Discovery only: track the expand, never the collapse.
    if (!expanded) trackFeature('panel-open', { target: 'opening-insights-more' });
    setExpanded((prev) => !prev);
  };
  return (
    <div className="space-y-3" data-testid={testId}>
      <div className="space-y-1">
        <h2 className={SECTION_HEADING_CLASS}>{meta.title}</h2>
        <p className="text-sm text-muted-foreground">{meta.subtitle}</p>
      </div>
      {data.cards.length === 0 ? (
        <p className="text-sm text-muted-foreground" data-testid={`${testId}-empty`}>
          Nothing clear yet as {colorLabel(color)}.
          {data.notClearCount > 0 && ` ${leanText(data.notClearCount)}`}
        </p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {data.cards.map((finding, i) => (
              <div
                key={i}
                className={cn(i >= INITIAL_VISIBLE_PHONE && !expanded && 'max-md:hidden')}
              >
                <FindingCard
                  finding={finding}
                  testId={`${testId}-card-${i}`}
                  onOpenMoves={onOpenMoves}
                  onOpenGames={onOpenGames}
                />
              </div>
            ))}
          </div>
          {data.cards.length > INITIAL_VISIBLE_PHONE && (
            <ShowMoreButton kind={meta.kind} expanded={expanded} onToggle={handleToggle} />
          )}
        </>
      )}
      <NotClearYet
        kind={meta.kind}
        findings={data.notClear}
        count={data.notClearCount}
        onOpenMoves={onOpenMoves}
        onOpenGames={onOpenGames}
      />
    </div>
  );
}

interface OpeningFindingsProps {
  color: FindingColor;
  debouncedFilters: FilterState;
  onOpenMoves: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}

/**
 * Findings for the selected colour below the repertoire cards: "Moves that Cost You" and
 * "Moves that Work", each at most 5 cards from the 99%-gated backend lists (D-00), with a
 * phone "Show more" (D-08), a collapsed "Not clear yet (n)" list (D-09, D-10) and the
 * empty-state copy (D-11).
 */
export function OpeningFindings({ color, debouncedFilters, onOpenMoves, onOpenGames }: OpeningFindingsProps) {
  const { data, isLoading, isError, refetch } = useOpeningInsights({
    recency: debouncedFilters.recency,
    customRange: debouncedFilters.customRange,
    timeControls: debouncedFilters.timeControls,
    platforms: debouncedFilters.platforms,
    rated: debouncedFilters.rated,
    opponentType: debouncedFilters.opponentType,
    opponentStrength: debouncedFilters.opponentStrength,
  });

  return (
    <section className="space-y-3" data-testid="opening-findings">
      {isLoading ? (
        <FindingsSkeleton />
      ) : isError ? (
        <FindingsError onRetry={() => void refetch()} />
      ) : data ? (
        <div className="flex flex-col gap-6">
          {KINDS.map((meta) => (
            <FindingsSubsection
              key={meta.kind}
              meta={meta}
              color={color}
              data={sectionData(data, color, meta.kind)}
              onOpenMoves={onOpenMoves}
              onOpenGames={onOpenGames}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}
