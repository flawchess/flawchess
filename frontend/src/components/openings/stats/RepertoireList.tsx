import { useState } from 'react';
import { ChevronDown, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { FilterState } from '@/components/filters/FilterPanel';
import { RepertoireCard } from '@/components/openings/stats/RepertoireCard';
import type { RepertoireRowModel } from '@/pages/openings/useRepertoireRows';
import { trackFeature } from '@/lib/analytics';
import { REPERTOIRE_MIN_GAMES_FOR_VERDICT } from '@/lib/openingVerdict';
import { cn } from '@/lib/utils';
import { REPERTOIRE_HEADING_CLASS } from './headingClasses';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';

const INTRO_CLASS = 'text-sm text-muted-foreground';
const COPY_BOOKMARKS_INTRO = 'Openings you saved.';
/** Explains the card bars once, under whichever repertoire heading comes first. */
const COPY_METRICS_INTRO =
  "Score counts a draw as half a win. Eval is the engine's view when the middlegame starts.";
const COPY_PLAYED_BEFORE_POINTER = 'Older ones sit under Played before.';

const GROUP_HEADING_CLASS = 'text-sm font-semibold uppercase tracking-wide text-muted-foreground';
/** One column on phones and tablets, two from lg. items-start: an open chart never stretches its neighbour. */
const CARD_GRID_CLASS = 'grid grid-cols-1 items-start gap-3 lg:grid-cols-2';

interface RepertoireListProps {
  color: 'white' | 'black';
  bookmarkRows: RepertoireRowModel[];
  currentRows: RepertoireRowModel[];
  pastRows: RepertoireRowModel[];
  /** ISO cutoff of the current repertoire for this colour; null when every opening is current. */
  currentCutoff: string | null;
  onOpenSuggestions: () => void;
  /** Sidebar filters (debounced) that scope the cards' score series. */
  debouncedFilters: FilterState;
  /** Card links: Moves tab, Games tab (most-played rows) and Games tab (bookmark rows). */
  onOpenMoves: (pgn: string, color: 'white' | 'black') => void;
  onOpenGames: (pgn: string, color: 'white' | 'black') => void;
  onOpenBookmarkGames: (bookmark: PositionBookmarkResponse) => void;
}

function colorLabel(color: 'white' | 'black'): string {
  return color === 'white' ? 'White' : 'Black';
}

/** "14 Feb 2026" from the backend cutoff, so the frontend hard-codes no window length. */
function formatCutoffDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function PlayedBeforeToggle({
  count,
  hint,
  expanded,
  onToggle,
}: {
  count: number;
  hint: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      className={cn(
        GROUP_HEADING_CLASS,
        'flex w-full flex-wrap items-center gap-x-2 text-left transition-colors hover:text-foreground',
      )}
      aria-expanded={expanded}
      onClick={onToggle}
      data-testid="repertoire-played-before-toggle"
    >
      <span>Played before ({count})</span>
      {hint && <span className="font-normal normal-case tracking-normal">{hint}</span>}
      <ChevronDown
        className={cn('h-4 w-4 transition-transform', expanded && 'rotate-180')}
        aria-hidden="true"
      />
    </button>
  );
}

function Footer({
  color,
  bookmarkCount,
  currentCount,
  pastCount,
  onOpenSuggestions,
}: {
  color: 'white' | 'black';
  bookmarkCount: number;
  currentCount: number;
  pastCount: number;
  onOpenSuggestions: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
      <span data-testid="repertoire-footer-counts">
        {bookmarkCount} bookmarks · {currentCount} most played as {colorLabel(color).toLowerCase()}
        {pastCount > 0 ? ` · ${pastCount} played before` : ''}
      </span>
      <Button
        size="sm"
        variant="brand-outline"
        onClick={onOpenSuggestions}
        data-testid="btn-suggest-bookmarks-footer"
      >
        <Sparkles className="h-4 w-4" />
        Suggest bookmarks
      </Button>
    </div>
  );
}

function mostPlayedIntro(color: 'white' | 'black', hasPast: boolean): string {
  const base = `Your most frequent openings as ${colorLabel(color)} lately.`;
  return hasPast ? `${base} ${COPY_PLAYED_BEFORE_POINTER}` : base;
}

/** A group's h2 with its intro line underneath (the Library Stats section pattern). */
function GroupHeading({ title, intro }: { title: string; intro: string }) {
  return (
    <div className="space-y-1">
      <h2 className={REPERTOIRE_HEADING_CLASS}>{title}</h2>
      <p className={INTRO_CLASS}>{intro}</p>
    </div>
  );
}

/**
 * The selected colour's repertoire as cards: pinned bookmarks, the current most-played
 * openings and the collapsed "Played before (n)" group, then the counts footer. Each group
 * heading carries an intro line; the first one also explains Score and Eval.
 */
export function RepertoireList({
  color,
  bookmarkRows,
  currentRows,
  pastRows,
  currentCutoff,
  onOpenSuggestions,
  debouncedFilters,
  onOpenMoves,
  onOpenGames,
  onOpenBookmarkGames,
}: RepertoireListProps) {
  const [pastExpanded, setPastExpanded] = useState(false);
  const visiblePast = pastExpanded ? pastRows : [];
  const ordered = [...bookmarkRows, ...currentRows, ...visiblePast];
  const indexOf = new Map(ordered.map((row, i) => [row.key, i]));

  const renderGroup = (rows: RepertoireRowModel[]) => (
    <div className={CARD_GRID_CLASS}>
      {rows.map((row) => (
        <RepertoireCard
          key={row.key}
          row={row}
          index={indexOf.get(row.key) ?? 0}
          debouncedFilters={debouncedFilters}
          onOpenMoves={onOpenMoves}
          onOpenGames={onOpenGames}
          onOpenBookmarkGames={onOpenBookmarkGames}
        />
      ))}
    </div>
  );

  const handleTogglePast = () => {
    // Discovery only: track the expand, never the collapse.
    if (!pastExpanded) trackFeature('panel-open', { target: 'opening-stats-more' });
    setPastExpanded((prev) => !prev);
  };
  const hint = currentCutoff
    ? `not played as ${colorLabel(color)} since ${formatCutoffDate(currentCutoff)}`
    : '';

  return (
    <section className="flex flex-col gap-4" data-testid={`repertoire-list-${color}`}>
      {bookmarkRows.length > 0 && (
        <div className="space-y-2" data-testid="repertoire-group-bookmarks">
          <GroupHeading
            title="Bookmarked Openings"
            intro={`${COPY_BOOKMARKS_INTRO} ${COPY_METRICS_INTRO}`}
          />
          {renderGroup(bookmarkRows)}
        </div>
      )}
      {currentRows.length > 0 && (
        <div className="space-y-2" data-testid="repertoire-group-most-played">
          <GroupHeading
            title="Most Played Openings"
            intro={
              bookmarkRows.length > 0
                ? mostPlayedIntro(color, pastRows.length > 0)
                : `${mostPlayedIntro(color, pastRows.length > 0)} ${COPY_METRICS_INTRO}`
            }
          />
          {renderGroup(currentRows)}
        </div>
      )}
      {ordered.length === 0 && pastRows.length === 0 && (
        <p
          className="charcoal-texture rounded-md px-3 py-6 text-center text-sm text-muted-foreground"
          data-testid="repertoire-empty"
        >
          {/* The backend drops most-played openings under its game floor (D-36), so an empty
              list can mean games spread thin, not no games at all. */}
          No {colorLabel(color)} opening has {REPERTOIRE_MIN_GAMES_FOR_VERDICT} or more games under
          the current filters yet.
        </p>
      )}
      {pastRows.length > 0 && (
        <div className="space-y-2" data-testid="repertoire-group-played-before">
          <PlayedBeforeToggle
            count={pastRows.length}
            hint={hint}
            expanded={pastExpanded}
            onToggle={handleTogglePast}
          />
          {pastExpanded && renderGroup(visiblePast)}
        </div>
      )}
      <Footer
        color={color}
        bookmarkCount={bookmarkRows.length}
        currentCount={currentRows.length}
        pastCount={pastRows.length}
        onOpenSuggestions={onOpenSuggestions}
      />
    </section>
  );
}
