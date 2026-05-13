import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { InfoPopover } from '@/components/ui/info-popover';
import { OpeningFindingCard } from './OpeningFindingCard';
import { useOpeningInsights } from '@/hooks/useOpeningInsights';
import type { OpeningInsightFinding, OpeningInsightsResponse } from '@/types/insights';
import type { FilterState } from '@/components/filters/FilterPanel';

// Show the top 4 findings per section by default; remaining (up to backend cap of 10) are
// revealed via a "X more" toggle. The backend always returns up to 10 per section so a
// single roundtrip covers both states. 4 fits exactly two rows of the lg+ 2-column card grid.
const INITIAL_VISIBLE_PER_SECTION = 4;

interface OpeningInsightsBlockProps {
  debouncedFilters: FilterState;
  onFindingClick: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}

type SectionKind = 'weakness' | 'strength';
type SectionColor = 'white' | 'black';

// Only the four findings keys — not the eval baseline number fields.
type FindingsKey = 'white_weaknesses' | 'black_weaknesses' | 'white_strengths' | 'black_strengths';

interface SectionMeta {
  key: 'white-weaknesses' | 'black-weaknesses' | 'white-strengths' | 'black-strengths';
  kind: SectionKind;
  color: SectionColor;
  title: string;
  findingsKey: FindingsKey;
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

  // Sections stack vertically full-width. Within each section, finding cards
  // render in a 2-column grid on lg+ (single column on mobile) — mirrors the
  // Stats subtab layout. Section order is locked by D-01:
  // white-weaknesses → black-weaknesses → white-strengths → black-strengths.
  return (
    <div className="flex flex-col gap-6">
      {SECTIONS.map((section, sectionIdx) => (
        <FindingsSection
          key={section.key}
          section={section}
          findings={data[section.findingsKey]}
          startIdx={sectionStartIdxs[sectionIdx] ?? 0}
          // Per-color MG-entry eval baseline tick for the finding card bullet chart.
          evalBaselinePawns={
            section.color === 'white'
              ? data.eval_baseline_pawns_white
              : data.eval_baseline_pawns_black
          }
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
  evalBaselinePawns,
  onFindingClick,
  onOpenGames,
}: {
  section: SectionMeta;
  findings: OpeningInsightFinding[];
  startIdx: number;
  evalBaselinePawns: number;
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
      className="space-y-3"
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
          <div className="space-y-2">
            <p>
              A strength or weakness shows up when your score is below 45% or above 55% over at
              least 20 games. The cards are dimmed when the difference from 50% is plausibly due to chance.
              The more games you have, the higher the statistical confidence in the findings.
            </p>
            <p>
              All your games are scanned up to 16 half-moves, and evaluated with Stockfish at the transition from opening to middlegame.
            </p>
            <p className="italic">
              Tip: Use the filters to select recency, time control, or opponent strength
              for a more targeted search.
            </p>
          </div>
        </InfoPopover>
      </h3>
      {findings.length === 0 ? (
        <p className="text-sm text-muted-foreground italic">
          No {section.kind} findings under your current filters.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-6 gap-y-3">
            {visibleFindings.map((finding, i) => (
              <OpeningFindingCard
                key={`${section.key}-${i}`}
                finding={finding}
                idx={startIdx + i}
                evalBaselinePawns={evalBaselinePawns}
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
