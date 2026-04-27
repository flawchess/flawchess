import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { OpeningFindingCard } from './OpeningFindingCard';
import { useOpeningInsights } from '@/hooks/useOpeningInsights';
import type { OpeningInsightFinding, OpeningInsightsResponse } from '@/types/insights';
import type { FilterState } from '@/components/filters/FilterPanel';

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
      <p
        className="text-sm italic text-muted-foreground"
        data-testid="opening-insights-tip"
      >
        <span className="font-semibold text-foreground/80">Tip:</span> Use the
        recency and time control filters to get more specific insights.
      </p>

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
      No opening findings cleared the threshold under your current filters. Try widening
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
      </h3>
      {findings.length === 0 ? (
        <p className="text-sm text-muted-foreground italic">
          No {section.kind} findings cleared the threshold under your current
          filters.
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
