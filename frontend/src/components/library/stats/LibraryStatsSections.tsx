import { EvalCoverageBadge } from '@/components/library/EvalCoverageBadge';
import { FlawTrendChart } from '@/components/library/FlawTrendChart';
import { TacticComparisonGrid } from '@/components/library/TacticComparisonGrid';
import { LoadError } from '@/components/ui/load-error';
import { DEFAULT_FLAW_FILTER } from '@/hooks/useFlawFilterStore';
import { useLibraryFlawComparison, useLibraryFlawStats } from '@/hooks/useLibrary';
import { useLibraryStatsTc } from '@/hooks/useLibraryStatsTc';
import { librarySectionBasisText } from '@/lib/flawComparisonMeta';
import { ContextTagCards } from './ContextTagCards';
import { FlawTiles } from './FlawTiles';
import { GapGateSlot } from './GapBar';
import { LibraryTcSwitch } from './LibraryTcSwitch';
import { WhatStandsOut } from './WhatStandsOut';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { TimeControlBucket } from '@/types/endgames';
import type { FlawComparisonTc, FlawStatsResponse } from '@/types/library';

const NO_TCS: readonly FlawComparisonTc[] = [];
const COPY_NO_ANALYZED = 'No analyzed games in the current filters yet.';
const SECTION_HEADING_CLASS = 'font-brand text-lg font-semibold text-foreground';
const COPY_VS_OPPONENTS_INTRO =
  "Your flaws per 100 of your moves, next to your opponents' in the same games. " +
  'The grey band is the gap most players at your level have against their opponents.';

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

function VsOpponentsSkeleton() {
  return (
    <div className="animate-pulse space-y-4" data-testid="vs-opponents-loading">
      <div className="h-40 rounded border border-border bg-charcoal" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="h-56 rounded border border-border bg-charcoal" />
        <div className="h-56 rounded border border-border bg-charcoal" />
      </div>
    </div>
  );
}

/**
 * You vs. your opponents (D-00f, D-00g): What stands out, then the four context-tag cards
 * for the selected TC. It reads the same comparison query as Flaw Stats (one cache entry,
 * no extra request) and the same remembered TC store, so a switch click here also switches
 * Flaw Stats (D-02). Below the gate one slot replaces everything (D-03).
 */
function VsOpponentsSection({ filters }: { filters: FilterState }) {
  const comparison = useLibraryFlawComparison(filters, DEFAULT_FLAW_FILTER);
  const tcs = comparison.data?.tcs ?? NO_TCS;
  const [selectedTc] = useLibraryStatsTc(tcs);
  const tcStats = tcs.find((t) => t.tc === selectedTc);

  const renderBody = () => {
    if (comparison.isError) return <LoadError resource="opponent comparison" />;
    if (comparison.isLoading || !comparison.data) return <VsOpponentsSkeleton />;
    if (!tcStats) return <p className="text-sm text-muted-foreground">{COPY_NO_ANALYZED}</p>;
    if (tcStats.below_gate) {
      return (
        <GapGateSlot
          analyzedN={tcStats.analyzed_n}
          gate={comparison.data.analyzed_gate}
          testId="vs-opponents-gate"
        />
      );
    }
    return (
      <>
        <WhatStandsOut tcStats={tcStats} />
        <ContextTagCards tcStats={tcStats} />
      </>
    );
  };

  return (
    <section
      className="space-y-4"
      data-testid="vs-opponents-section"
      aria-label="You vs. your opponents"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className={SECTION_HEADING_CLASS}>You vs. your opponents</h2>
        {tcs.length > 0 && <LibraryTcSwitch sectionId="library-vs-opponents" tcs={tcs} />}
      </div>
      <p className="text-sm text-muted-foreground">{COPY_VS_OPPONENTS_INTRO}</p>
      {renderBody()}
    </section>
  );
}

/**
 * The redesigned top of the Library Stats tab: Flaw Stats, You vs. your opponents, then
 * Tactic motifs. The sections share one remembered TC switch (D-05). The sidebar filters
 * flow into every query (D-01).
 */
export function LibraryStatsSections(props: LibraryStatsSectionsProps) {
  return (
    <>
      <FlawStatsSection {...props} />
      <VsOpponentsSection filters={props.filters} />
      <section className="space-y-4" data-testid="tactic-motifs-section">
        <h2 className={SECTION_HEADING_CLASS}>Tactic motifs</h2>
        <TacticComparisonGrid filters={props.filters} flawFilter={DEFAULT_FLAW_FILTER} />
      </section>
    </>
  );
}
