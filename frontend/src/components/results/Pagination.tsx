import { Button } from '@/components/ui/button';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

type PaginationItem = number | 'ellipsis-start' | 'ellipsis-end';

// Page-window constants: show all pages when <= MAX_PAGES_UNTRUNCATED,
// otherwise keep a window of WINDOW_SIZE pages either side of the current page.
const MAX_PAGES_UNTRUNCATED = 7;
const WINDOW_RADIUS = 2;

/**
 * Returns an array of page numbers and ellipsis markers for truncated pagination.
 *
 * Rules:
 * - If totalPages <= 7, show all pages.
 * - Otherwise: always show page 1 and last page; show a window of 2 pages on
 *   either side of the current page; fill gaps with ellipsis markers.
 */
function getPaginationItems(currentPage: number, totalPages: number): PaginationItem[] {
  if (totalPages <= MAX_PAGES_UNTRUNCATED) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const items: PaginationItem[] = [];
  // Always include first page
  items.push(1);

  // Window: currentPage - 2 to currentPage + 2, clamped inside [2, totalPages - 1]
  const windowStart = Math.max(2, currentPage - WINDOW_RADIUS);
  const windowEnd = Math.min(totalPages - 1, currentPage + WINDOW_RADIUS);

  // Ellipsis before window?
  if (windowStart > 2) {
    items.push('ellipsis-start');
  }

  for (let p = windowStart; p <= windowEnd; p++) {
    items.push(p);
  }

  // Ellipsis after window?
  if (windowEnd < totalPages - 1) {
    items.push('ellipsis-end');
  }

  // Always include last page
  items.push(totalPages);

  return items;
}

/**
 * Shared pagination control row (prev / numbered pages / ellipsis / next).
 *
 * Renders nothing when totalPages <= 1. The parent component owns offset math
 * and scroll-to-top behavior; onPageChange receives a 1-based page number.
 */
export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  const paginationItems = getPaginationItems(currentPage, totalPages);

  return (
    <div className="flex flex-wrap items-center justify-center gap-1">
      <Button
        variant="ghost"
        size="sm"
        disabled={currentPage === 1}
        onClick={() => onPageChange(currentPage - 1)}
        data-testid="pagination-prev"
        aria-label="Previous page"
      >
        &lt;
      </Button>

      {paginationItems.map((item, idx) => {
        if (item === 'ellipsis-start' || item === 'ellipsis-end') {
          return (
            <span
              key={item}
              className="inline-flex h-8 min-w-8 items-center justify-center text-sm text-muted-foreground"
              aria-hidden="true"
            >
              ...
            </span>
          );
        }
        return (
          <Button
            key={`page-${item}-${idx}`}
            variant={item === currentPage ? 'default' : 'ghost'}
            size="sm"
            onClick={() => onPageChange(item)}
            className="min-w-8"
            data-testid={`pagination-page-${item}`}
            aria-label={`Go to page ${item}`}
            aria-current={item === currentPage ? 'page' : undefined}
          >
            {item}
          </Button>
        );
      })}

      <Button
        variant="ghost"
        size="sm"
        disabled={currentPage === totalPages}
        onClick={() => onPageChange(currentPage + 1)}
        data-testid="pagination-next"
        aria-label="Next page"
      >
        &gt;
      </Button>
    </div>
  );
}
