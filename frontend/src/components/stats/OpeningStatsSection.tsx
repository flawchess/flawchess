import { useState } from 'react';
import type { ReactNode } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { OpeningWDL } from '@/types/stats';
import { OpeningStatsCard } from './OpeningStatsCard';

const MPO_DEFAULT_VISIBLE_COUNT = 4;

export interface OpeningStatsSectionDescriptor {
  key: 'white-bookmarks' | 'black-bookmarks' | 'mpo-white' | 'mpo-black';
  color: 'white' | 'black';
  title: ReactNode;
  headingExtra?: ReactNode;
  openings: OpeningWDL[];
  evalBaselinePawns: number;
  onOpenMoves: (opening: OpeningWDL, color: 'white' | 'black') => void;
  onOpenGames: (opening: OpeningWDL, color: 'white' | 'black') => void;
  showAll?: boolean;
  initialVisibleCount?: number;
  testId: string;
  cardTestIdPrefix: string;
}

interface OpeningStatsSectionProps {
  section: OpeningStatsSectionDescriptor;
}

export function OpeningStatsSection({ section }: OpeningStatsSectionProps) {
  const [expanded, setExpanded] = useState(false);

  if (section.openings.length === 0) return null;

  const showAll = section.showAll ?? false;
  const initialVisible = section.initialVisibleCount ?? MPO_DEFAULT_VISIBLE_COUNT;
  const visibleOpenings =
    showAll || expanded ? section.openings : section.openings.slice(0, initialVisible);
  const hiddenCount = section.openings.length - initialVisible;
  const hasMore = !showAll && hiddenCount > 0;

  return (
    <section data-testid={section.testId} className="space-y-3">
      <h2 className="text-lg font-medium flex items-center gap-1.5">
        {section.title}
        {section.headingExtra}
      </h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-6 gap-y-3">
        {visibleOpenings.map((opening, i) => (
          <OpeningStatsCard
            key={`${section.key}-${opening.full_hash || opening.opening_eco || `${opening.opening_name}-${i}`}`}
            opening={opening}
            color={section.color}
            idx={i}
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
