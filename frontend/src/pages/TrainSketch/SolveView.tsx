import { Swords, Target, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { KIND_LABEL, type Puzzle, type PuzzleKind } from './puzzles';

interface SolveViewProps {
  puzzle: Puzzle;
  index: number;
  total: number;
  onGiveUp: () => void;
}

const KIND_ICON: Record<PuzzleKind, typeof Swords> = {
  blunder: Swords,
  miss: Target,
  red_herring: ShieldCheck,
};

export function SolveView({ puzzle, index, total, onGiveUp }: SolveViewProps) {
  const Icon = KIND_ICON[puzzle.kind];
  const toMove = puzzle.userColor === 'white' ? 'White' : 'Black';
  return (
    <div className="flex w-full flex-col gap-4" data-testid="train-solve">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-muted-foreground tabular-nums">
          Position {index + 1} of {total}
        </span>
        <span className="flex items-center gap-1.5 rounded-full bg-brand-brown/15 px-3 py-1 text-sm text-brand-brown-light">
          <Icon className="h-4 w-4" />
          {KIND_LABEL[puzzle.kind]}
        </span>
      </div>

      <div className="rounded-lg bg-card p-4 ring-1 ring-foreground/10">
        <p className="font-brand text-lg text-foreground">{toMove} to move</p>
        <p className="mt-1 text-sm text-muted-foreground">{puzzle.prompt}</p>
        <p className="mt-3 text-sm text-muted-foreground/80">
          vs {puzzle.opponent} ({puzzle.opponentRating}) · {puzzle.timeControl} · {puzzle.playedAgo}
        </p>
      </div>

      <p className="text-sm text-muted-foreground">
        Make your move on the board — drag a piece or tap from-square then to-square.
      </p>

      <Button
        variant="brand-outline"
        onClick={onGiveUp}
        data-testid="train-btn-giveup"
        className="self-start"
      >
        Give up &amp; show answer
      </Button>
    </div>
  );
}
