import { Flame, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ZONE_SUCCESS } from '@/lib/theme';
import type { Verdict } from './puzzles';

interface DoneViewProps {
  results: Verdict[];
  onRestart: () => void;
}

export function DoneView({ results, onRestart }: DoneViewProps) {
  const correct = results.filter((v) => v === 'solved' || v === 'herring_ok').length;
  const total = results.length;
  return (
    <div className="mx-auto flex w-full max-w-md flex-col items-center gap-6 text-center" data-testid="train-done">
      <div
        className="flex h-20 w-20 items-center justify-center rounded-full"
        style={{ backgroundColor: `${ZONE_SUCCESS}1f`, color: ZONE_SUCCESS }}
      >
        <Flame className="h-10 w-10" />
      </div>
      <div>
        <h1 className="font-brand text-2xl text-foreground">Session complete</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          You solved <span className="font-semibold text-foreground tabular-nums">{correct}</span> of{' '}
          <span className="font-semibold text-foreground tabular-nums">{total}</span>. Streak extended to 6 days.
        </p>
      </div>
      <p className="text-sm text-muted-foreground">
        Missed positions come back tomorrow; solved ones return on a longer interval.
      </p>
      <Button variant="brand-outline" onClick={onRestart} data-testid="train-btn-restart">
        <RotateCcw className="h-4 w-4" />
        Run the demo again
      </Button>
    </div>
  );
}
