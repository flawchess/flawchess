import { Cpu } from 'lucide-react';
import { CoverageSignupButton } from '@/components/library/EvalCoverageBadge';
import {
  ANALYSIS_COVERAGE_INFO_COPY,
  LOW_COVERAGE_THRESHOLD,
} from '@/components/library/analysisCoverageCopy';
import { StickyTcBar } from '@/components/stats/StickyTcBar';
import { TcSwitch } from '@/components/stats/TcSwitch';
import { InfoPopover } from '@/components/ui/info-popover';
import { FlawTrendChart } from '@/components/library/FlawTrendChart';
import { LoadError } from '@/components/ui/load-error';
import { DEFAULT_FLAW_FILTER } from '@/hooks/useFlawFilterStore';
import {
  useLibraryFlawComparison,
  useLibraryFlawStats,
  useTacticComparison,
} from '@/hooks/useLibrary';
import { useLibraryStatsTc } from '@/hooks/useLibraryStatsTc';
import { libraryCoverageBasisText } from '@/lib/flawComparisonMeta';
import { cn } from '@/lib/utils';
import { ContextTagCards } from './ContextTagCards';
import { FlawTiles } from './FlawTiles';
import { GapGateSlot } from './GapBar';
import { MostCommonTacticsCard } from './MostCommonTacticsCard';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { TimeControlBucket } from '@/types/endgames';
import type { FlawComparisonTc, FlawStatsResponse, TacticComparisonTc } from '@/types/library';

const NO_TCS: readonly FlawComparisonTc[] = [];
const NO_TACTIC_TCS: readonly TacticComparisonTc[] = [];
const COPY_NO_ANALYZED = 'No analyzed games in the current filters yet.';
const COPY_NO_TACTIC_DATA = 'No tactic data for this time control yet.';
const SECTION_HEADING_CLASS = 'font-brand text-lg font-semibold text-foreground';
const FLAW_STATS_TITLE = 'Flaw Stats';
const COPY_VS_OPPONENTS_INTRO =
  "Your flaws per 100 of your moves, next to your opponents' in the same games. " +
  'The grey band is the gap most players at your level have against their opponents.';
const COPY_TACTICS_INTRO =
  'Tactics you missed (your opponent left one on the board) and tactics you allowed ' +
  '(your move handed one over), per 100 games, next to your opponents.';

interface LibraryStatsSectionsProps {
  /** Sidebar filters: every query of the Stats tab reads these (D-01). */
  filters: FilterState;
  isGuest: boolean;
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

/**
 * The basis line, merged with the coverage readout: "1,768 of 1,790 rapid games analyzed
 * in the current filters." It replaced the library-wide "N of M analyzed" badge, which
 * counted every TC while every number below it is for the selected TC only.
 */
function CoverageBasisLine({ tcStats, isGuest }: { tcStats: FlawComparisonTc; isGuest: boolean }) {
  const isIncomplete = tcStats.analyzed_n < tcStats.total_n;
  const isLowCoverage = tcStats.analyzed_n < tcStats.total_n * LOW_COVERAGE_THRESHOLD;
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-2">
      <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <Cpu className={cn('h-4 w-4 shrink-0', isIncomplete && 'animate-pulse')} aria-hidden="true" />
        <p data-testid="flaw-stats-basis">
          {libraryCoverageBasisText(tcStats.analyzed_n, tcStats.total_n, tcStats.tc)}
        </p>
        <InfoPopover ariaLabel="About game analysis coverage" testId="flaw-stats-coverage-info">
          <p>{ANALYSIS_COVERAGE_INFO_COPY}</p>
        </InfoPopover>
      </div>
      {isGuest && isLowCoverage && <CoverageSignupButton />}
    </div>
  );
}

/**
 * Testid prefix per mounted copy: the desktop sticky bar and the mobile Filters row are both
 * in the DOM (one CSS-hidden), so each copy needs its own testids.
 */
type LibraryStatsTcSwitchIdPrefix = 'library-stats' | 'library-stats-mobile';

interface LibraryStatsTcSwitchProps {
  filters: FilterState;
  idPrefix: LibraryStatsTcSwitchIdPrefix;
}

/**
 * The Library Stats time-control switch (D-02, D-05), bound to the one remembered Library
 * TC store every section reads. The page pins it in a sticky bar, so it stays in reach
 * while scrolling. Offers the flaw-comparison TCs (the tactic TCs are a subset).
 */
export function LibraryStatsTcSwitch({ filters, idPrefix }: LibraryStatsTcSwitchProps) {
  const comparison = useLibraryFlawComparison(filters, DEFAULT_FLAW_FILTER);
  const tcs = comparison.data?.tcs ?? NO_TCS;
  const [selectedTc, setSelectedTc] = useLibraryStatsTc(tcs);
  if (tcs.length === 0) return null;
  return (
    <TcSwitch
      idPrefix={idPrefix}
      tcs={tcs.map((t) => t.tc)}
      selected={selectedTc}
      onSelect={setSelectedTc}
      trackTarget="library-stats-tc"
    />
  );
}

/** Flaw Stats (D-00e, D-00k): heading, coverage basis line, tiles, timeline. */
function FlawStatsSection({ filters, isGuest }: LibraryStatsSectionsProps) {
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
        <CoverageBasisLine tcStats={tcStats} isGuest={isGuest} />
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
    <section className="space-y-4" data-testid="flaw-stats-section" aria-label={FLAW_STATS_TITLE}>
      {/* md:h-8: the StickyTcBar overlays this row on desktop (see StickyTcBar). */}
      <h2 className={cn(SECTION_HEADING_CLASS, 'md:flex md:h-8 md:items-center')}>
        {FLAW_STATS_TITLE}
      </h2>
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
 * You vs. your opponents (D-00f): the four context-tag cards
 * for the selected TC. It reads the same comparison query as Flaw Stats (one cache entry,
 * no extra request) and the same remembered TC store as the page's one switch (D-02).
 * Below the gate one slot replaces everything (D-03).
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
    return <ContextTagCards tcStats={tcStats} />;
  };

  return (
    <section
      className="space-y-4"
      data-testid="vs-opponents-section"
      aria-label="You vs. your opponents"
    >
      <h2 className={SECTION_HEADING_CLASS}>You vs. your opponents</h2>
      <p className="text-sm text-muted-foreground">{COPY_VS_OPPONENTS_INTRO}</p>
      {renderBody()}
    </section>
  );
}

function TacticsSkeleton() {
  return (
    <div className="animate-pulse space-y-4" data-testid="tactic-comparison-loading">
      <div className="h-48 rounded border border-border bg-charcoal" />
      <div className="h-48 rounded border border-border bg-charcoal" />
    </div>
  );
}

/**
 * Tactic motifs (D-00h, D-17): one card of the four most common tactics for the selected TC.
 * The payload is per TC, so the TC is a client-side pick (never in the query key) bound
 * to the same remembered TC store as the other sections (D-02). Below the gate one slot replaces the card (D-03).
 *
 * The TC comes from the flaw-comparison list, the one the page switch offers: the tactic
 * list can lack a TC (blob-pending games), and resolving against it would silently show a
 * different TC than the switch says.
 */
function TacticMotifsSection({ filters }: { filters: FilterState }) {
  const comparison = useTacticComparison(filters, DEFAULT_FLAW_FILTER);
  const tcs = comparison.data?.tcs ?? NO_TACTIC_TCS;
  const flawComparison = useLibraryFlawComparison(filters, DEFAULT_FLAW_FILTER);
  // While the flaw comparison loads, select from an empty list: the tactic list would let the
  // store pin a tactic-based default the switch never offered. Fall back to the tactic list
  // only when the flaw comparison failed (there is no switch then).
  const selectionTcs = flawComparison.isError ? tcs : (flawComparison.data?.tcs ?? NO_TCS);
  const [selectedTc] = useLibraryStatsTc(selectionTcs);
  const tcStats = tcs.find((t) => t.tc === selectedTc);

  const renderBody = () => {
    if (comparison.isError) return <LoadError resource="tactic comparison" />;
    if (comparison.isLoading || flawComparison.isLoading || !comparison.data) {
      return <TacticsSkeleton />;
    }
    if (tcs.length === 0) return <p className="text-sm text-muted-foreground">{COPY_NO_ANALYZED}</p>;
    if (!tcStats) return <p className="text-sm text-muted-foreground">{COPY_NO_TACTIC_DATA}</p>;
    if (tcStats.below_gate) {
      return (
        <GapGateSlot
          analyzedN={tcStats.analyzed_n}
          gate={comparison.data.analyzed_gate}
          testId="tactic-motifs-gate"
        />
      );
    }
    return <MostCommonTacticsCard tcStats={tcStats} />;
  };

  return (
    <section className="space-y-4" data-testid="tactic-motifs-section" aria-label="Tactic motifs">
      <h2 className={SECTION_HEADING_CLASS}>Tactic motifs</h2>
      <p className="text-sm text-muted-foreground">{COPY_TACTICS_INTRO}</p>
      {renderBody()}
    </section>
  );
}

/**
 * The redesigned top of the Library Stats tab: Flaw Stats, You vs. your opponents, then
 * Tactic motifs. The sections share one remembered TC switch (D-05). The sidebar filters
 * flow into every query (D-01).
 *
 * The switch pins in a StickyTcBar scoped to this wrapper on desktop, so it unpins once the
 * sections scroll away (the rating and results sections below have no TC switch). Mobile
 * pins it in the page's sticky Filters bar instead (GlobalStats).
 */
export function LibraryStatsSections(props: LibraryStatsSectionsProps) {
  return (
    <div>
      <StickyTcBar showOnMobile={false} testId="library-stats-tc-bar">
        <LibraryStatsTcSwitch filters={props.filters} idPrefix="library-stats" />
      </StickyTcBar>
      <div className="space-y-8">
        <FlawStatsSection {...props} />
        <VsOpponentsSection filters={props.filters} />
        <TacticMotifsSection filters={props.filters} />
      </div>
    </div>
  );
}
