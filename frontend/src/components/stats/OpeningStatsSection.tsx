import { useState } from 'react';
import type { ReactNode } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { OpeningWDL } from '@/types/stats';
import { OpeningStatsCard } from './OpeningStatsCard';

// Default cap before the "X more" fold (matches the previous
// MostPlayedOpeningsTable INITIAL_VISIBLE_COUNT). Bookmark sections pass
// showAll to bypass the fold entirely.
const DEFAULT_INITIAL_VISIBLE_COUNT = 3;

export interface OpeningStatsSectionDescriptor {
  /** Stable React key + suffix for testid (e.g. "white-bookmarks"). */
  key: 'white-bookmarks' | 'black-bookmarks' | 'mpo-white' | 'mpo-black';
  /** Drives column placement at lg+. */
  color: 'white' | 'black';
  /** Section title (rendered inside the section heading). */
  title: ReactNode;
  /** Optional info popover (or any extra adornment) rendered next to the heading. */
  headingExtra?: ReactNode;
  /** The opening rows for this section. */
  openings: OpeningWDL[];
  /** Per-color engine-asymmetry baseline tick (in pawns). */
  evalBaselinePawns: number;
  /** Routes the Moves link for this section. */
  onOpenMoves: (opening: OpeningWDL, color: 'white' | 'black') => void;
  /** Routes the Games link for this section. */
  onOpenGames: (opening: OpeningWDL, color: 'white' | 'black') => void;
  /** Bookmark sections pass true to render every card without a fold. */
  showAll?: boolean;
  /** data-testid for the section container — preserves existing IDs from the
   * pre-refactor Stats subtab (bookmarks-white-section, mpo-white-section, etc.). */
  testId: string;
  /** testIdPrefix passed through to each card so card-level testids stay
   * consistent with the section. */
  cardTestIdPrefix: string;
}

interface OpeningStatsSectionProps {
  /** One or two descriptors per call (white + black). Each call lays out one
   * grid row at lg+; the parent invokes the component twice (bookmarks,
   * most-played) so the WinRateChart can sit between the two pairs. */
  sections: OpeningStatsSectionDescriptor[];
}

const COLUMN_PLACEMENT: Record<OpeningStatsSectionDescriptor['key'], string> = {
  // Each OpeningStatsSection call renders one row of the grid (a white + black
  // pair), so the row-start coordinate is implicit and only col-start matters.
  // Statistics-tab callers invoke this twice: once for bookmarks, once for
  // most-played, with the WinRateChart sandwiched between them. Mirrors
  // OpeningInsightsBlock's white-left/black-right placement on lg+.
  'white-bookmarks': 'lg:col-start-1',
  'mpo-white': 'lg:col-start-1',
  'black-bookmarks': 'lg:col-start-2',
  'mpo-black': 'lg:col-start-2',
};

export function OpeningStatsSection({ sections }: OpeningStatsSectionProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-6 gap-y-4">
      {sections.map((section, sectionIdx) => (
        <SectionColumn
          key={section.key}
          section={section}
          sectionIdx={sectionIdx}
        />
      ))}
    </div>
  );
}

function SectionColumn({
  section,
  sectionIdx,
}: {
  section: OpeningStatsSectionDescriptor;
  sectionIdx: number;
}) {
  const [expanded, setExpanded] = useState(false);

  if (section.openings.length === 0) return null;

  const showAll = section.showAll ?? false;
  const visibleOpenings = showAll || expanded
    ? section.openings
    : section.openings.slice(0, DEFAULT_INITIAL_VISIBLE_COUNT);
  const hiddenCount = section.openings.length - DEFAULT_INITIAL_VISIBLE_COUNT;
  const hasMore = !showAll && hiddenCount > 0;

  return (
    <section
      data-testid={section.testId}
      className={`charcoal-texture rounded-md p-4 space-y-3 ${COLUMN_PLACEMENT[section.key]}`}
    >
      <h2 className="text-lg font-medium flex items-center gap-1.5">
        {section.title}
        {section.headingExtra}
      </h2>
      <div className="space-y-3">
        {visibleOpenings.map((opening, i) => (
          <OpeningStatsCard
            key={`${section.key}-${opening.full_hash || opening.opening_eco || `${opening.opening_name}-${i}`}`}
            opening={opening}
            color={section.color}
            // Combine sectionIdx and row index so every card across all four
            // sections has a unique testid suffix. Sections placed earlier in
            // the parent's array land at lower-numbered indices; rows within
            // a section get sequential offsets.
            idx={sectionIdx * 100 + i}
            testIdPrefix={section.cardTestIdPrefix}
            onOpenMoves={section.onOpenMoves}
            onOpenGames={section.onOpenGames}
            evalBaselinePawns={section.evalBaselinePawns}
          />
        ))}
      </div>
      {hasMore && (
        <button
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          onClick={() => setExpanded((prev) => !prev)}
          data-testid={`${section.testId}-btn-more`}
          aria-label={
            expanded ? 'Show fewer openings' : `Show ${hiddenCount} more openings`
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
    </section>
  );
}
