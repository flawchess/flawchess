import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LoadError } from '@/components/ui/load-error';
import { FindingCard } from '@/components/openings/stats/FindingCard';
import { SECTION_HEADING_CLASS } from '@/components/openings/stats/headingClasses';
import type { FilterState } from '@/components/filters/FilterPanel';
import { useOpeningInsights } from '@/hooks/useOpeningInsights';
import { trackFeature } from '@/lib/analytics';
import { REPERTOIRE_MIN_GAMES_FOR_VERDICT } from '@/lib/openingVerdict';
import type { OpeningInsightFinding, OpeningInsightsResponse } from '@/types/insights';

/** Cards shown per section before the "N more" toggle (two rows of the lg 2-column grid). */
const INITIAL_VISIBLE_PER_SECTION = 4;
const SKELETON_SECTION_COUNT = 2;
const MERGED_EMPTY_TITLE = 'Moves that Stand Out';
const ZONE_DIVIDER_LABEL = 'Move insights';

type FindingKind = 'weakness' | 'strength';
type FindingColor = 'white' | 'black';

interface KindMeta {
  kind: FindingKind;
  title: string;
  intro: string;
}

const KINDS: readonly KindMeta[] = [
  {
    kind: 'strength',
    title: 'Moves that Work',
    intro: "Moves after which you score above 50%, your own moves and your opponents' replies. The clearest come first.",
  },
  {
    kind: 'weakness',
    title: 'Moves that Cost You',
    intro: "Moves after which you score below 50%, your own moves and your opponents' replies. The clearest come first.",
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

/** "N more" / "Less" toggle under a section's first INITIAL_VISIBLE_PER_SECTION cards (as on main). */
function ShowMoreButton({
  testId,
  kind,
  hiddenCount,
  expanded,
  onToggle,
}: {
  testId: string;
  kind: FindingKind;
  hiddenCount: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      className="flex items-center gap-1 px-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
      aria-expanded={expanded}
      aria-label={expanded ? `Show fewer ${kind} findings` : `Show ${hiddenCount} more ${kind} findings`}
      onClick={onToggle}
      data-testid={testId}
    >
      {expanded ? (
        <>
          <ChevronUp className="h-4 w-4" />
          Less
        </>
      ) : (
        <>
          <ChevronDown className="h-4 w-4" />
          {hiddenCount} more
        </>
      )}
    </button>
  );
}

/** Two-column finding cards: the first INITIAL_VISIBLE_PER_SECTION, the rest behind "N more". */
function FindingCardGrid({
  findings,
  kind,
  testId,
  onOpenMoves,
  onOpenGames,
}: {
  findings: OpeningInsightFinding[];
  kind: FindingKind;
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
  const visibleFindings = expanded ? findings : findings.slice(0, INITIAL_VISIBLE_PER_SECTION);
  const hiddenCount = findings.length - INITIAL_VISIBLE_PER_SECTION;
  return (
    <>
      {/* Same grid as the repertoire cards (two columns from lg) now that both share one layout. */}
      <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-2" data-testid={`${testId}-list`}>
        {visibleFindings.map((finding, i) => (
          <FindingCard
            key={i}
            finding={finding}
            testId={`${testId}-card-${i}`}
            onOpenMoves={onOpenMoves}
            onOpenGames={onOpenGames}
          />
        ))}
      </div>
      {hiddenCount > 0 && (
        <ShowMoreButton
          testId={`${testId}-btn-more`}
          kind={kind}
          hiddenCount={hiddenCount}
          expanded={expanded}
          onToggle={handleToggle}
        />
      )}
    </>
  );
}

/**
 * Labelled rule between the opening cards above and the move cards below, so scrolling past
 * the repertoire shows where one kind of card ends and the other begins.
 */
function ZoneDivider() {
  return (
    // Foreground label and a 25% rule: the first version (muted label, card-edge rule) blended
    // into the "Played before" toggle above it and the line was all but invisible (UAT round 15).
    <div className="flex items-center gap-3 pt-6" data-testid="opening-findings-divider">
      <span className="h-px flex-1 bg-foreground/25" aria-hidden="true" />
      <span className="text-sm font-semibold uppercase tracking-wide whitespace-nowrap text-foreground">
        {ZONE_DIVIDER_LABEL}
      </span>
      <span className="h-px flex-1 bg-foreground/25" aria-hidden="true" />
    </div>
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
        kind={meta.kind}
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
        No moves stand out as {colorLabel(color)} yet. A move needs at least {REPERTOIRE_MIN_GAMES_FOR_VERDICT} games
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
 * Findings for the selected colour below the repertoire cards: "Moves that Work" and
 * "Moves that Cost You", each the backend's top 10 by Wilson bound, any confidence (D-38): the
 * first four cards, the rest behind an "N more" toggle (UAT round 14, main's pattern). Each card's colour carries the 95% verdict, so a finding that could
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
      <ZoneDivider />
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
