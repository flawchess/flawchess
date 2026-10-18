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
/** Mirrors backend OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE. */
const MIN_GAMES_PER_FINDING = 20;
const MERGED_EMPTY_TITLE = 'Moves that Stand Out';

type FindingKind = 'weakness' | 'strength';
type FindingColor = 'white' | 'black';

interface KindMeta {
  kind: FindingKind;
  title: string;
  intro: string;
}

const KINDS: readonly KindMeta[] = [
  {
    kind: 'weakness',
    title: 'Moves that Cost You',
    intro: "Moves after which you score below 50%, your own moves and your opponents' replies. The clearest come first.",
  },
  {
    kind: 'strength',
    title: 'Moves that Work',
    intro: "Moves after which you score above 50%, your own moves and your opponents' replies. The clearest come first.",
  },
];

function colorLabel(color: FindingColor): string {
  return color === 'white' ? 'White' : 'Black';
}

/** The selected colour's cards for one kind; the switch is client-side (the request stays 'all'). */
function sectionCards(
  data: OpeningInsightsResponse,
  color: FindingColor,
  kind: FindingKind,
): OpeningInsightFinding[] {
  return data[`${color}_${kind === 'weakness' ? 'weaknesses' : 'strengths'}`];
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

/** Phones only (md:hidden): desktop already shows every card, at most FINDINGS_CARD_CAP. */
function ShowMoreButton({
  testId,
  expanded,
  onToggle,
}: {
  testId: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      className="flex items-center gap-1 px-2 text-sm text-muted-foreground transition-colors hover:text-foreground md:hidden"
      aria-expanded={expanded}
      onClick={onToggle}
      data-testid={testId}
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

/** Two-column finding cards with the phone "Show more" (D-08); desktop shows every card. */
function FindingCardGrid({
  findings,
  testId,
  onOpenMoves,
  onOpenGames,
}: {
  findings: OpeningInsightFinding[];
  testId: string;
  onOpenMoves: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const handleToggle = () => {
    // Discovery only: track the expand, never the collapse.
    if (!expanded) trackFeature('panel-open', { target: 'opening-insights-more' });
    setExpanded((prev) => !prev);
  };
  return (
    <>
      {/* Same grid as the repertoire cards (two columns from lg) now that both share one layout. */}
      <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-2" data-testid={`${testId}-list`}>
        {findings.map((finding, i) => (
          <div key={i} className={cn(!expanded && i >= INITIAL_VISIBLE_PHONE && 'max-md:hidden')}>
            <FindingCard
              finding={finding}
              testId={`${testId}-card-${i}`}
              onOpenMoves={onOpenMoves}
              onOpenGames={onOpenGames}
            />
          </div>
        ))}
      </div>
      {findings.length > INITIAL_VISIBLE_PHONE && (
        <ShowMoreButton
          testId={`${testId}-btn-more`}
          expanded={expanded}
          onToggle={handleToggle}
        />
      )}
    </>
  );
}

function SectionHeading({ title, intro }: { title: string; intro: string }) {
  return (
    <div className="space-y-1">
      <h2 className={SECTION_HEADING_CLASS}>{title}</h2>
      <p className="text-sm text-muted-foreground">{intro}</p>
    </div>
  );
}

function FindingsSubsection({
  meta,
  color,
  cards,
  onOpenMoves,
  onOpenGames,
}: {
  meta: KindMeta;
  color: FindingColor;
  cards: OpeningInsightFinding[];
  onOpenMoves: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}) {
  const testId = `opening-findings-${meta.kind}`;
  const body =
    cards.length > 0 ? (
      <FindingCardGrid
        findings={cards}
        testId={testId}
        onOpenMoves={onOpenMoves}
        onOpenGames={onOpenGames}
      />
    ) : (
      <p className="text-sm text-muted-foreground" data-testid={`${testId}-empty`}>
        Nothing stands out as {colorLabel(color)} yet.
      </p>
    );
  return (
    <div className="space-y-3" data-testid={testId}>
      <SectionHeading title={meta.title} intro={meta.intro} />
      {body}
    </div>
  );
}

/** Both sections empty: one short block instead of two headings with "nothing yet" each. */
function MergedEmpty({ color }: { color: FindingColor }) {
  return (
    <div className="space-y-1" data-testid="opening-findings-empty">
      <h2 className={SECTION_HEADING_CLASS}>{MERGED_EMPTY_TITLE}</h2>
      <p className="text-sm text-muted-foreground">
        No moves stand out as {colorLabel(color)} yet. A move needs at least {MIN_GAMES_PER_FINDING} games
        before it can show up here.
      </p>
    </div>
  );
}

function FindingsSections({
  data,
  color,
  onOpenMoves,
  onOpenGames,
}: {
  data: OpeningInsightsResponse;
  color: FindingColor;
  onOpenMoves: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}) {
  const sections = KINDS.map((meta) => ({ meta, cards: sectionCards(data, color, meta.kind) }));
  if (sections.every((section) => section.cards.length === 0)) return <MergedEmpty color={color} />;
  return (
    <div className="flex flex-col gap-6">
      {sections.map((section) => (
        <FindingsSubsection
          key={section.meta.kind}
          meta={section.meta}
          color={color}
          cards={section.cards}
          onOpenMoves={onOpenMoves}
          onOpenGames={onOpenGames}
        />
      ))}
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
 * "Moves that Work", each the backend's top 10 by Wilson bound, any confidence (D-38), with a
 * phone "Show more" (D-08). Each card's colour carries the 95% verdict, so a finding that could
 * still be chance draws blue. A section without cards says so in one line, and both sections
 * empty merge into one block.
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
        <FindingsSections
          data={data}
          color={color}
          onOpenMoves={onOpenMoves}
          onOpenGames={onOpenGames}
        />
      ) : null}
    </section>
  );
}
