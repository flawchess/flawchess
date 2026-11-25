import type { ReactNode } from 'react';
import { SlidersHorizontal, Tags } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { isCoverageBelowThreshold } from '@/components/library/analysisCoverageCopy';
import { CoverageSignupButton, EvalCoverageLine } from '@/components/library/EvalCoverageBadge';

interface LibraryMobileFilterBarProps {
  /** "123 games matched"; null while the first page loads or failed to. */
  matchLabel: string | null;
  analyzedN: number;
  totalN: number;
  isCoverageError: boolean;
  isGuest: boolean;
  /** The Games and Flaws tabs name their filter button differently (tests, aria). */
  filtersButton: { testId: string; ariaLabel: string };
  filtersDot: ReactNode;
  onOpenFilters: () => void;
  tagsDot: ReactNode;
  onOpenTags: () => void;
}

/** Button labels drop on narrow phones so the two text lines beside them fit, as in the Stats
 *  tab's control bar (GlobalStats). */
const LABEL_CLASS = 'hidden min-[420px]:inline';
const ICON_CLASS = 'h-4 w-4 min-[420px]:mr-2';
const BUTTON_CLASS = 'relative shrink-0';

/**
 * The Library Games and Flaws tabs' control bar below lg: match count and analysis coverage on
 * the left, the Filters and Tags buttons on the right, pinned on scroll.
 *
 * Bug fix: the counts used to sit in their own row under the buttons and wrapped to two lines
 * on phones, so the first card started about 250px down the screen.
 */
export function LibraryMobileFilterBar({
  matchLabel,
  analyzedN,
  totalN,
  isCoverageError,
  isGuest,
  filtersButton,
  filtersDot,
  onOpenFilters,
  tagsDot,
  onOpenTags,
}: LibraryMobileFilterBarProps) {
  return (
    <>
      <div
        className="sticky top-0 z-20 flex items-center gap-2 py-1 bg-background/80 backdrop-blur-sm"
        data-testid="library-mobile-filter-bar"
      >
        <div className="min-w-0 flex-1 text-sm text-muted-foreground">
          {matchLabel !== null && <p className="truncate">{matchLabel}</p>}
          <EvalCoverageLine analyzedN={analyzedN} totalN={totalN} isCoverageError={isCoverageError} />
        </div>
        <Button
          variant="brand-outline"
          className={BUTTON_CLASS}
          onClick={onOpenFilters}
          aria-label={filtersButton.ariaLabel}
          data-testid={filtersButton.testId}
        >
          <SlidersHorizontal className={ICON_CLASS} />
          <span className={LABEL_CLASS}>Filters</span>
          {filtersDot}
        </Button>
        <Button
          variant="brand-outline"
          className={BUTTON_CLASS}
          onClick={onOpenTags}
          aria-label="Open tags"
          data-testid="btn-flaw-filters"
        >
          <Tags className={ICON_CLASS} />
          <span className={LABEL_CLASS}>Tags</span>
          {tagsDot}
        </Button>
      </div>
      {isGuest && !isCoverageError && isCoverageBelowThreshold(analyzedN, totalN) && (
        <div className="flex justify-end">
          <CoverageSignupButton />
        </div>
      )}
    </>
  );
}
