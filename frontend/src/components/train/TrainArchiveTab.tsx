import { useEffect } from 'react';
import type { ReactElement } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadError } from '@/components/ui/load-error';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Pagination } from '@/components/results/Pagination';
import {
  TRAIN_CTA_BUTTON_CLASS,
  TRAIN_FILTER_PILL_CLASS,
  TRAIN_FILTER_PILL_SPACING,
} from '@/components/train/buttonStyles';
import { TrainPuzzleCard } from '@/components/train/TrainPuzzleCard';
import { ARCHIVE_PAGE_SIZE, useTrainArchive } from '@/hooks/useTrainArchive';
import { useTrainProgress } from '@/hooks/useTrainProgress';
import { buildArchivePath, parseArchivePage, TRAIN_TAB_PATHS } from '@/lib/trainRoute';
import type { ArchiveList } from '@/types/train';

/**
 * TrainArchiveTab — the Archive tab: Mastered / Parked filter pills over a grid
 * of the player's archived puzzles. Read-only: it never starts a session or loads
 * the engine (D-06), and it lists only mastered and parked puzzles, never an
 * active one, because seeing a puzzle before its next review would defeat
 * spaced repetition.
 *
 * The list lives in the path and the page in `?page=`, so the browser Back from
 * Analysis returns to the same spot and no Umami event is needed for either
 * (URL-routed views are covered by the pageview, frontend/CLAUDE.md).
 */

// Prose mirror of app.services.train_scheduler's MASTERY_STREAK_THRESHOLD and
// PARK_FAIL_THRESHOLD. Keep in step by hand: the numbers appear only in this copy.
// "3 or more" covers both park doors: 3 lifetime misses on a puzzle never solved,
// or LEECH_FAIL_THRESHOLD (4) lifetime misses on any puzzle.
const ARCHIVE_EXPLAINER: Record<ArchiveList, string> = {
  mastered: 'Solved correctly twice in a row.',
  parked: 'Missed 3 or more times and set aside.',
};

/** Placeholder cards while a page loads. */
const ARCHIVE_SKELETON_COUNT = 4;

const ARCHIVE_GRID_CLASS = 'grid grid-cols-1 lg:grid-cols-2 gap-4';

interface ArchiveEmptyCopy {
  testId: string;
  title: string;
}

// Title only: ARCHIVE_EXPLAINER already sits just above the empty state. Neither
// list offers an import button: the Archive fills from puzzles played on Today,
// whatever the account's games.
const EMPTY_COPY: Record<ArchiveList, ArchiveEmptyCopy> = {
  mastered: {
    testId: 'train-archive-empty-mastered',
    title: 'No mastered puzzles yet',
  },
  parked: {
    testId: 'train-archive-empty-parked',
    title: 'Nothing parked',
  },
};

function isArchiveList(value: string): value is ArchiveList {
  return value === 'mastered' || value === 'parked';
}

interface ArchiveToggleItemProps {
  list: ArchiveList;
  label: string;
  count: number | undefined;
}

function ArchiveToggleItem({ list, label, count }: ArchiveToggleItemProps): ReactElement {
  return (
    <ToggleGroupItem
      value={list}
      data-testid={`train-archive-toggle-${list}`}
      className={TRAIN_FILTER_PILL_CLASS}
    >
      {label}
      {count !== undefined && (
        <>
          {' '}
          <span className="tabular-nums">{count}</span>
        </>
      )}
    </ToggleGroupItem>
  );
}

function ArchiveToggle({ list }: { list: ArchiveList }): ReactElement {
  const navigate = useNavigate();
  // A pending or failed progress read leaves the counts out: never a false 0.
  const { data: progress } = useTrainProgress();

  function handleValueChange(value: string): void {
    // Radix single-select emits '' when the active item is re-tapped: keep the
    // current list and do nothing (no navigation, no scroll).
    if (!isArchiveList(value) || value === list) return;
    navigate(buildArchivePath(value));
    window.scrollTo({ top: 0 });
  }

  // With nothing parked there is nothing to filter, so Mastered stands alone. Only
  // a known 0 hides the pills (a pending or failed read must not), and never on the
  // Parked list itself, where they are the way back to Mastered.
  const hidePills = list === 'mastered' && progress?.parked_count === 0;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2">
      {!hidePills && (
        <ToggleGroup
          type="single"
          value={list}
          onValueChange={handleValueChange}
          variant="outline"
          size="sm"
          spacing={TRAIN_FILTER_PILL_SPACING}
          aria-label="Archive list"
          data-testid="train-archive-toggle"
        >
          <ArchiveToggleItem list="mastered" label="Mastered" count={progress?.mastered_count} />
          <ArchiveToggleItem list="parked" label="Parked" count={progress?.parked_count} />
        </ToggleGroup>
      )}
      <p className="text-sm text-muted-foreground" data-testid="train-archive-explainer">
        {ARCHIVE_EXPLAINER[list]}
      </p>
    </div>
  );
}

function ArchiveSkeleton(): ReactElement {
  return (
    <div className={ARCHIVE_GRID_CLASS} data-testid="train-archive-loading">
      {Array.from({ length: ARCHIVE_SKELETON_COUNT }, (_, i) => (
        <div key={i} className="h-56 animate-pulse rounded-md bg-muted" />
      ))}
    </div>
  );
}

function ArchiveEmpty({ list }: { list: ArchiveList }): ReactElement {
  const copy = EMPTY_COPY[list];
  return (
    <EmptyState
      layout="page"
      title={copy.title}
      data-testid={copy.testId}
      action={
        <Button variant="brand-outline" asChild className={TRAIN_CTA_BUTTON_CLASS}>
          <Link to={TRAIN_TAB_PATHS.today} data-testid="btn-train-archive-today">
            Go to Today
          </Link>
        </Button>
      }
    />
  );
}

export function TrainArchiveTab({ list }: { list: ArchiveList }): ReactElement {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseArchivePage(searchParams.get('page'));
  const { data, isPending, isError, isPlaceholderData } = useTrainArchive(list, page);

  // Over-range page (a hand-typed URL, or a list that shrank): replace the URL
  // with the last page, with no history entry, so Back skips the dead one.
  // Real data only: placeholder data belongs to the previous page.
  useEffect(() => {
    if (data === undefined || isPlaceholderData) return;
    if (data.total === 0 || data.items.length > 0) return;
    const lastPage = Math.ceil(data.total / ARCHIVE_PAGE_SIZE);
    if (lastPage >= page) return;
    setSearchParams(lastPage === 1 ? {} : { page: String(lastPage) }, { replace: true });
  }, [data, isPlaceholderData, page, setSearchParams]);

  function handlePageChange(next: number): void {
    // A push, so Back steps through pages. Page 1 carries no param, which keeps
    // `/train/archive` the canonical URL.
    setSearchParams(next === 1 ? {} : { page: String(next) });
    window.scrollTo({ top: 0 });
  }

  let body: ReactElement;
  if (isError) {
    body = <LoadError resource="your archived puzzles" data-testid="train-archive-error" />;
  } else if (isPending || data === undefined) {
    body = <ArchiveSkeleton />;
  } else if (data.total === 0) {
    body = <ArchiveEmpty list={list} />;
  } else {
    body = (
      <>
        <div className={ARCHIVE_GRID_CLASS} data-testid="train-archive-grid">
          {data.items.map((item) => (
            <TrainPuzzleCard key={`${item.game_id}-${item.ply}`} item={item} list={list} />
          ))}
        </div>
        {data.total > ARCHIVE_PAGE_SIZE && (
          <div className="mt-6">
            <Pagination
              currentPage={page}
              totalPages={Math.ceil(data.total / ARCHIVE_PAGE_SIZE)}
              onPageChange={handlePageChange}
            />
          </div>
        )}
      </>
    );
  }

  return (
    <div data-testid="train-archive-tab">
      <ArchiveToggle list={list} />
      {body}
    </div>
  );
}
