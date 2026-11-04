import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const GROUP_HEADING_CLASS = 'text-sm font-semibold uppercase tracking-wide text-muted-foreground';

/** The collapsed "Played before (n)" heading shared by the repertoire and the move findings. */
export function PlayedBeforeToggle({
  count,
  hint,
  expanded,
  onToggle,
  testId,
}: {
  count: number;
  hint?: string;
  expanded: boolean;
  onToggle: () => void;
  testId: string;
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
      data-testid={testId}
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
