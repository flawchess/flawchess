import { useState } from 'react';
import type { ReactNode } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { InfoPopover } from '@/components/ui/info-popover';
import { OpeningFindingCard } from './OpeningFindingCard';
import { useOpeningInsights } from '@/hooks/useOpeningInsights';
import type { OpeningInsightFinding, OpeningInsightsResponse } from '@/types/insights';
import type { FilterState } from '@/components/filters/FilterPanel';

// Phase 76 D-17 — single shared copy for all four section-title InfoPopovers.
// Co-located with consumer (this file) per RESEARCH.md Open Question 3 — keeps
// openingInsights.ts as a pure .ts module (no JSX rename).
// Exported so the Move Explorer's "Move" header InfoPopover can reuse the same
// confidence explanation verbatim.
export const OPENING_INSIGHTS_CONFIDENCE_COPY: ReactNode = (
  <>
    <p>
      <strong>Confidence</strong> is based on the p-value, the chance of seeing
      this difference by pure chance (one-sided Wald test against 50%). High confidence
      can both result from a small difference based on a high number of games, or
      from a large difference based on a small number of games:
    </p>
    <ul className="list-disc pl-4 space-y-0.5">
      <li><em>high</em>: p &lt; 0.05 (likely a real effect)</li>
      <li><em>medium</em>: p &lt; 0.10 (possibly a real effect)</li>
      <li><em>low</em>: p ≥ 0.10, or fewer than 10 games (could plausibly be chance)</li>
    </ul>
  </>
);

const OPENING_INSIGHTS_POPOVER_COPY: ReactNode = (
  <div className="space-y-2">
    <p>
      <strong>Score</strong> is your win rate plus half your draw rate.
      50% means you and your opponents broke even.
    </p>
    <p>
      A finding shows up when your score is below 45% or above 55% over at
      least 10 games, enough of a difference from 50% to be worth a closer look.
    </p>
    {OPENING_INSIGHTS_CONFIDENCE_COPY}
    <p className="italic">
      Tip: Use the filters to select recency, time control, or opponent strength
      for a more targeted search.
    </p>
  </div>
);

// Show the top 3 findings per section by default; remaining (up to backend cap of 10) are
// revealed via a "X more" toggle. The backend always returns up to 10 per section so a
// single roundtrip covers both states.
const INITIAL_VISIBLE_PER_SECTION = 3;

interface OpeningInsightsBlockProps {
  debouncedFilters: FilterState;
  onFindingClick: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}

type SectionKind = 'weakness' | 'strength';
type SectionColor = 'white' | 'black';

interface SectionMeta {
  key: 'white-weaknesses' | 'black-weaknesses' | 'white-strengths' | 'black-strengths';
  kind: SectionKind;
  color: SectionColor;
  title: string;
  findingsKey: keyof OpeningInsightsResponse;
}

// Order locked by D-01: white-weaknesses, black-weaknesses, white-strengths, black-strengths.
const SECTIONS: SectionMeta[] = [
  {
    key: 'white-weaknesses',
    kind: 'weakness',
    color: 'white',
    title: 'White Opening Weaknesses',
    findingsKey: 'white_weaknesses',
  },
  {
    key: 'black-weaknesses',
    kind: 'weakness',
    color: 'black',
    title: 'Black Opening Weaknesses',
    findingsKey: 'black_weaknesses',
  },
  {
    key: 'white-strengths',
    kind: 'strength',
    color: 'white',
    title: 'White Opening Strengths',
    findingsKey: 'white_strengths',
  },
  {
    key: 'black-strengths',
    kind: 'strength',
    color: 'black',
    title: 'Black Opening Strengths',
    findingsKey: 'black_strengths',
  },
];

export function OpeningInsightsBlock({ debouncedFilters, onFindingClick, onOpenGames }: OpeningInsightsBlockProps) {
  const query = useOpeningInsights({
    recency: debouncedFilters.recency,
    timeControls: debouncedFilters.timeControls,
    platforms: debouncedFilters.platforms,
    rated: debouncedFilters.rated,
    opponentType: debouncedFilters.opponentType,
    opponentStrength: debouncedFilters.opponentStrength,
  });

  const { data, isLoading, isError, refetch } = query;

  const allEmpty =
    data !== undefined &&
    data.white_weaknesses.length === 0 &&
    data.black_weaknesses.length === 0 &&
    data.white_strengths.length === 0 &&
    data.black_strengths.length === 0;

  return (
    <div
      data-testid="opening-insights-block"
      className="flex flex-col gap-3"
    >

      {isLoading ? (
        <SkeletonBlock />
      ) : isError ? (
        <ErrorState onRetry={() => void refetch()} />
      ) : allEmpty ? (
        <EmptyBlock />
      ) : (
        <SectionsContent data={data!} onFindingClick={onFindingClick} onOpenGames={onOpenGames} />
      )}
    </div>
  );
}

function SkeletonBlock() {
  return (
    <div className="animate-pulse space-y-4">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="space-y-2">
          <div className="h-5 w-48 bg-muted/30 rounded" />
          <div className="h-16 w-full bg-muted/30 rounded border-l-4 border-l-muted/30" />
          <div className="h-16 w-full bg-muted/30 rounded border-l-4 border-l-muted/30" />
        </div>
      ))}
    </div>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div data-testid="opening-insights-error" role="alert">
      <p className="text-sm text-muted-foreground">
        Failed to load opening insights. Something went wrong. Please try again in a moment.
      </p>
      <Button
        variant="brand-outline"
        onClick={onRetry}
        data-testid="btn-opening-insights-retry"
        className="mt-3"
      >
        Try again
      </Button>
    </div>
  );
}

function EmptyBlock() {
  return (
    <p className="text-sm text-muted-foreground" data-testid="opening-insights-empty">
      No opening findings under your current filters. Try widening
      filters (longer recency window, more time controls) or import more games.
    </p>
  );
}

function SectionsContent({
  data,
  onFindingClick,
  onOpenGames,
}: {
  data: OpeningInsightsResponse;
  onFindingClick: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}) {
  // Compute per-section start indices so each card gets a globally unique idx for data-testid.
  // White weaknesses start at 0; each subsequent section starts after the previous section's count.
  const sectionStartIdxs = SECTIONS.reduce<number[]>((acc, _section, i) => {
    const prev = acc[i - 1] ?? 0;
    const prevCount = i === 0 ? 0 : (data[SECTIONS[i - 1]!.findingsKey].length);
    acc.push(i === 0 ? 0 : prev + prevCount);
    return acc;
  }, []);

  return (
    <div className="space-y-4">
      {SECTIONS.map((section, sectionIdx) => (
        <FindingsSection
          key={section.key}
          section={section}
          findings={data[section.findingsKey]}
          startIdx={sectionStartIdxs[sectionIdx] ?? 0}
          onFindingClick={onFindingClick}
          onOpenGames={onOpenGames}
        />
      ))}
    </div>
  );
}

function FindingsSection({
  section,
  findings,
  startIdx,
  onFindingClick,
  onOpenGames,
}: {
  section: SectionMeta;
  findings: OpeningInsightFinding[];
  startIdx: number;
  onFindingClick: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const swatchClass = section.color === 'white' ? 'bg-white' : 'bg-zinc-900';

  const visibleFindings = expanded
    ? findings
    : findings.slice(0, INITIAL_VISIBLE_PER_SECTION);
  const hiddenCount = findings.length - INITIAL_VISIBLE_PER_SECTION;
  const hasMore = hiddenCount > 0;

  return (
    <section
      data-testid={`opening-insights-section-${section.key}`}
      className="space-y-2"
    >
      <h3 className="text-base font-semibold flex items-center gap-1.5">
        <span
          className={`inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground ${swatchClass}`}
          aria-hidden="true"
        />
        {section.title}
        <InfoPopover
          ariaLabel={`${section.title} info`}
          testId={`opening-insights-section-${section.key}-info`}
          side="bottom"
        >
          {OPENING_INSIGHTS_POPOVER_COPY}
        </InfoPopover>
      </h3>
      {findings.length === 0 ? (
        <p className="text-sm text-muted-foreground italic">
          No {section.kind} findings under your current filters.
        </p>
      ) : (
        <>
          <div className="space-y-3">
            {visibleFindings.map((finding, i) => (
              <OpeningFindingCard
                key={`${section.key}-${i}`}
                finding={finding}
                idx={startIdx + i}
                onFindingClick={onFindingClick}
                onOpenGames={onOpenGames}
              />
            ))}
          </div>
          {hasMore && (
            <button
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mt-2 px-2"
              onClick={() => setExpanded((prev) => !prev)}
              data-testid={`opening-insights-section-${section.key}-btn-more`}
              aria-label={
                expanded
                  ? `Show fewer ${section.kind} findings`
                  : `Show ${hiddenCount} more ${section.kind} findings`
              }
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
          )}
        </>
      )}
    </section>
  );
}
