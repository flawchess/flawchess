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
/** Desktop cap for leaning cards shown inline in a section without clear ones. */
const INLINE_NOT_CLEAR_DESKTOP = 4;
const SKELETON_SECTION_COUNT = 2;
/** Mirrors backend OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE. */
const MIN_GAMES_PER_FINDING = 20;
const COPY_NOT_CLEAR = 'Not clear yet';
const COPY_LEANING = 'Leaning this way, but could still be chance.';
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
    intro: "Moves after which you score clearly below 50%, your own moves and your opponents' replies.",
  },
  {
    kind: 'strength',
    title: 'Moves that Work',
    intro: "Moves after which you score clearly above 50%, your own moves and your opponents' replies.",
  },
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

function ShowMoreButton({
  testId,
  expanded,
  hideOnDesktop,
  onToggle,
}: {
  testId: string;
  expanded: boolean;
  /** True when every card already fits on desktop, so only phones need the button. */
  hideOnDesktop: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      className={cn(
        'flex items-center gap-1 px-2 text-sm text-muted-foreground transition-colors hover:text-foreground',
        hideOnDesktop && 'md:hidden',
      )}
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

/** Classes hiding a card beyond the phone / desktop initial counts while collapsed. */
function hiddenClass(index: number, desktopInitial: number | undefined): string | undefined {
  const phoneHidden = index >= INITIAL_VISIBLE_PHONE;
  const desktopHidden = desktopInitial !== undefined && index >= desktopInitial;
  if (phoneHidden && desktopHidden) return 'hidden';
  if (phoneHidden) return 'max-md:hidden';
  return undefined;
}

/**
 * Two-column finding cards with the phone "Show more" (D-08). `desktopInitial` also caps
 * desktop before Show more; undefined shows every card there.
 */
function FindingCardGrid({
  findings,
  testId,
  desktopInitial,
  neutralArrow = false,
  onOpenMoves,
  onOpenGames,
}: {
  findings: OpeningInsightFinding[];
  testId: string;
  desktopInitial?: number;
  neutralArrow?: boolean;
  onOpenMoves: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const handleToggle = () => {
    // Discovery only: track the expand, never the collapse.
    if (!expanded) trackFeature('panel-open', { target: 'opening-insights-more' });
    setExpanded((prev) => !prev);
  };
  const overflowsDesktop = desktopInitial !== undefined && findings.length > desktopInitial;
  return (
    <>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2" data-testid={`${testId}-list`}>
        {findings.map((finding, i) => (
          <div key={i} className={cn(!expanded && hiddenClass(i, desktopInitial))}>
            <FindingCard
              finding={finding}
              testId={`${testId}-card-${i}`}
              onOpenMoves={onOpenMoves}
              onOpenGames={onOpenGames}
              neutralArrow={neutralArrow}
            />
          </div>
        ))}
      </div>
      {findings.length > INITIAL_VISIBLE_PHONE && (
        <ShowMoreButton
          testId={`${testId}-btn-more`}
          expanded={expanded}
          hideOnDesktop={!overflowsDesktop}
          onToggle={handleToggle}
        />
      )}
    </>
  );
}

/** "Not clear yet (n)" label with its one-line explanation, as a toggle or a plain label. */
function NotClearLabel({ count }: { count: number }) {
  return (
    <>
      <span>
        {COPY_NOT_CLEAR} ({count})
      </span>
      <span className="font-normal">{COPY_LEANING}</span>
    </>
  );
}

const NOT_CLEAR_LABEL_CLASS = 'flex w-full flex-wrap items-center gap-x-2 text-left text-sm font-semibold text-muted-foreground';

/**
 * Medium candidates (D-09, D-10) below clear cards: collapsed behind a toggle. Drawn as the
 * same finding cards as the 99% ones; their verdicts and arrows stay uncoloured.
 */
function NotClearYetCollapsed({
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
  const testId = `opening-findings-${kind}-unclear`;
  const handleToggle = () => {
    // Discovery only: track the expand, never the collapse.
    if (!expanded) trackFeature('panel-open', { target: 'opening-findings-unclear' });
    setExpanded((prev) => !prev);
  };
  return (
    <div className="space-y-3" data-testid={testId}>
      <button
        type="button"
        className={cn(NOT_CLEAR_LABEL_CLASS, 'transition-colors hover:text-foreground')}
        aria-expanded={expanded}
        onClick={handleToggle}
        data-testid={`${testId}-toggle`}
      >
        <NotClearLabel count={count} />
        <ChevronDown
          className={cn('h-4 w-4 shrink-0 transition-transform', expanded && 'rotate-180')}
          aria-hidden="true"
        />
      </button>
      {expanded && (
        <FindingCardGrid
          findings={findings}
          testId={testId}
          neutralArrow
          onOpenMoves={onOpenMoves}
          onOpenGames={onOpenGames}
        />
      )}
    </div>
  );
}

/**
 * A section without clear cards shows its leaning cards inline: a toggle hiding a single card
 * was friction, and the section would otherwise read as empty.
 */
function NotClearYetInline({
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
  const testId = `opening-findings-${kind}-unclear`;
  return (
    <div className="space-y-3" data-testid={testId}>
      <p className={NOT_CLEAR_LABEL_CLASS} data-testid={`${testId}-label`}>
        <NotClearLabel count={count} />
      </p>
      <FindingCardGrid
        findings={findings}
        testId={testId}
        desktopInitial={INLINE_NOT_CLEAR_DESKTOP}
        neutralArrow
        onOpenMoves={onOpenMoves}
        onOpenGames={onOpenGames}
      />
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
  const testId = `opening-findings-${meta.kind}`;
  const notClearProps = {
    kind: meta.kind,
    findings: data.notClear,
    count: data.notClearCount,
    onOpenMoves,
    onOpenGames,
  };
  const body =
    data.cards.length > 0 ? (
      <>
        <FindingCardGrid
          findings={data.cards}
          testId={testId}
          onOpenMoves={onOpenMoves}
          onOpenGames={onOpenGames}
        />
        <NotClearYetCollapsed {...notClearProps} />
      </>
    ) : data.notClear.length > 0 ? (
      <NotClearYetInline {...notClearProps} />
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

function sectionIsEmpty(data: SectionData): boolean {
  return data.cards.length === 0 && data.notClear.length === 0;
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
  const sections = KINDS.map((meta) => ({ meta, data: sectionData(data, color, meta.kind) }));
  if (sections.every((section) => sectionIsEmpty(section.data))) return <MergedEmpty color={color} />;
  return (
    <div className="flex flex-col gap-6">
      {sections.map((section) => (
        <FindingsSubsection
          key={section.meta.kind}
          meta={section.meta}
          color={color}
          data={section.data}
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
 * "Moves that Work", each at most 5 cards from the 99%-gated backend lists (D-00), with a
 * phone "Show more" (D-08) and a collapsed "Not clear yet (n)" list (D-09, D-10). A section
 * without clear cards shows its leaning cards inline; both sections empty merge into one line.
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
