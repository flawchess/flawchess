import { Button } from '@/components/ui/button';

// ─── Props ────────────────────────────────────────────────────────────────────

interface FilterActionsProps {
  onReset: () => void;
  onApply: () => void;
  resetTestId?: string;
  applyTestId?: string;
  resetLabel?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * FilterActions — reusable 50/50 Reset + Apply footer row for filter panels.
 *
 * Reset is on the LEFT (brand-outline), Apply is on the RIGHT (btn-brand, no variant).
 * Matches the Import "Sync" button style exactly.
 *
 * Both buttons are full-width within the row (flex-1), ensuring a 50/50 split.
 * The wrapper adds a top border to separate the footer from the filter controls.
 *
 * data-testids default to btn-filter-reset / btn-filter-apply.
 */
export function FilterActions({
  onReset,
  onApply,
  resetTestId = 'btn-filter-reset',
  applyTestId = 'btn-filter-apply',
  resetLabel = 'Reset',
}: FilterActionsProps) {
  return (
    <div className="pt-2 border-t border-border/40">
      <div className="flex gap-2">
        <Button
          type="button"
          variant="brand-outline"
          size="lg"
          className="flex-1 min-h-11 sm:min-h-0"
          data-testid={resetTestId}
          aria-label={resetLabel}
          onClick={onReset}
        >
          {resetLabel}
        </Button>
        <button
          type="button"
          className="btn-brand flex-1 min-h-11 sm:min-h-0"
          data-testid={applyTestId}
          aria-label="Apply"
          onClick={onApply}
        >
          Apply
        </button>
      </div>
    </div>
  );
}
