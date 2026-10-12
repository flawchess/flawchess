import { EvalCoverageBadge } from '@/components/library/EvalCoverageBadge';
import { FlawTrendChart } from '@/components/library/FlawTrendChart';
import { TacticComparisonGrid } from '@/components/library/TacticComparisonGrid';
import { LoadError } from '@/components/ui/load-error';
import { DEFAULT_FLAW_FILTER } from '@/hooks/useFlawFilterStore';
import { useLibraryFlawComparison, useLibraryFlawStats } from '@/hooks/useLibrary';
import { useLibraryStatsTc } from '@/hooks/useLibraryStatsTc';
import { librarySectionBasisText } from '@/lib/flawComparisonMeta';
import { FlawTiles } from './FlawTiles';
import { LibraryTcSwitch } from './LibraryTcSwitch';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { TimeControlBucket } from '@/types/endgames';
import type { FlawComparisonTc, FlawStatsResponse } from '@/types/library';

const NO_TCS: readonly FlawComparisonTc[] = [];
const COPY_NO_ANALYZED = 'No analyzed games in the current filters yet.';
const SECTION_HEADING_CLASS = 'font-brand text-lg font-semibold text-foreground';

interface LibraryStatsSectionsProps {
  /** Sidebar filters: every query of the Stats tab reads these (D-01). */
  filters: FilterState;
  analyzedCount: number;
  totalCount: number;
  isGuest: boolean;
  isCoverageError: boolean;
}

function SectionSkeleton() {
  return (
    <div className="animate-pulse space-y-3" data-testid="flaw-stats-loading">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="h-28 rounded border border-border bg-charcoal" />
        <div className="h-28 rounded border border-border bg-charcoal" />
      </div>
      <div className="h-48 rounded border border-border bg-charcoal" />
    </div>
  );
}

interface FlawTimelineProps {
  stats: FlawStatsResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  selectedTc: TimeControlBucket;
}

/** The selected time control's timeline; its own load/error states never hide the tiles. */
function FlawTimeline({ stats, isLoading, isError, selectedTc }: FlawTimelineProps) {
  if (isError) return <LoadError resource="flaws timeline" />;
  if (isLoading || !stats) {
    return <div className="h-48 animate-pulse rounded border border-border bg-charcoal" />;
  }
  const points = stats.trend_by_tc.find((t) => t.tc === selectedTc)?.points ?? [];
  return <FlawTrendChart trend={points} windowSize={stats.trend_window} />;
}

/** Flaw Stats (D-00e, D-00k): header with the TC switch, basis line, tiles, timeline. */
function FlawStatsSection({
  filters,
  analyzedCount,
  totalCount,
  isGuest,
  isCoverageError,
}: LibraryStatsSectionsProps) {
  const comparison = useLibraryFlawComparison(filters, DEFAULT_FLAW_FILTER);
  const stats = useLibraryFlawStats(filters, DEFAULT_FLAW_FILTER);
  // The selected TC picks an entry out of the payload; it is never part of a query key (D-02).
  const tcs = comparison.data?.tcs ?? NO_TCS;
  const [selectedTc] = useLibraryStatsTc(tcs);
  const tcStats = tcs.find((t) => t.tc === selectedTc);

  const renderBody = () => {
    if (comparison.isError) return <LoadError resource="flaw statistics" />;
    if (comparison.isLoading || !comparison.data) return <SectionSkeleton />;
    if (!tcStats || selectedTc === null) {
      return <p className="text-sm text-muted-foreground">{COPY_NO_ANALYZED}</p>;
    }
    return (
      <>
        <p className="text-sm text-muted-foreground" data-testid="flaw-stats-basis">
          {librarySectionBasisText(tcStats.analyzed_n, tcStats.tc)}
        </p>
        <FlawTiles tcStats={tcStats} analyzedGate={comparison.data.analyzed_gate} />
        <FlawTimeline
          stats={stats.data}
          isLoading={stats.isLoading}
          isError={stats.isError}
          selectedTc={selectedTc}
        />
      </>
    );
  };

  return (
    <section className="space-y-4" data-testid="flaw-stats-section" aria-label="Flaw Stats">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className={SECTION_HEADING_CLASS}>Flaw Stats</h2>
        <div className="flex flex-wrap items-center gap-3">
          <EvalCoverageBadge
            analyzedN={analyzedCount}
            totalN={totalCount}
            isGuest={isGuest}
            isCoverageError={isCoverageError}
          />
          {tcs.length > 0 && <LibraryTcSwitch sectionId="library-flaw-stats" tcs={tcs} />}
        </div>
      </div>
      {renderBody()}
    </section>
  );
}

/**
 * The redesigned top of the Library Stats tab: Flaw Stats, then (plan 239-10 inserts You
 * vs. your opponents between them) Tactic motifs. The sections share one remembered TC
 * switch (D-05). The sidebar filters flow into every query (D-01).
 */
export function LibraryStatsSections(props: LibraryStatsSectionsProps) {
  return (
    <>
      <FlawStatsSection {...props} />
      <section className="space-y-4" data-testid="tactic-motifs-section">
        <h2 className={SECTION_HEADING_CLASS}>Tactic motifs</h2>
        <TacticComparisonGrid filters={props.filters} flawFilter={DEFAULT_FLAW_FILTER} />
      </section>
    </>
  );
}
