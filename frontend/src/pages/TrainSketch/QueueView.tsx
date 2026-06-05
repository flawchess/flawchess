import { Flame, Swords, Target, ShieldCheck, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { KIND_LABEL, type Puzzle, type PuzzleKind } from './puzzles';

interface QueueViewProps {
  puzzles: Puzzle[];
  onStart: () => void;
}

const KIND_ICON: Record<PuzzleKind, typeof Swords> = {
  blunder: Swords,
  miss: Target,
  red_herring: ShieldCheck,
};

function QueueCard({ puzzle, index }: { puzzle: Puzzle; index: number }) {
  const Icon = KIND_ICON[puzzle.kind];
  return (
    <div
      className="charcoal-texture flex items-center gap-3 rounded border border-border/20 border-l-4 border-l-brand-brown-light px-4 py-3"
      data-testid={`train-queue-card-${index}`}
    >
      <Icon className="h-5 w-5 shrink-0 text-brand-brown-light" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-brand text-base text-white">{KIND_LABEL[puzzle.kind]}</span>
          <span className="rounded-full bg-white/10 px-2 py-0.5 text-sm text-white/80">
            {puzzle.userColor === 'white' ? 'White' : 'Black'}
          </span>
        </div>
        <p className="truncate text-sm text-white/60">
          vs {puzzle.opponent} ({puzzle.opponentRating}) · {puzzle.timeControl} · {puzzle.playedAgo}
        </p>
      </div>
      <ChevronRight className="h-5 w-5 shrink-0 text-white/40" />
    </div>
  );
}

export function QueueView({ puzzles, onStart }: QueueViewProps) {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6" data-testid="train-queue">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-brand text-2xl text-foreground">Today’s training</h1>
          <p className="text-sm text-muted-foreground">
            Positions from your recent games, served back to you on a spaced schedule.
          </p>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-brand-brown/15 px-3 py-1.5 text-brand-brown-light">
          <Flame className="h-4 w-4" />
          <span className="text-sm font-semibold tabular-nums">5 day streak</span>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-sm font-semibold text-muted-foreground">
          {puzzles.length} positions due
        </span>
        {puzzles.map((p, i) => (
          <QueueCard key={p.id} puzzle={p} index={i} />
        ))}
      </div>

      <Button
        size="lg"
        className="w-full"
        onClick={onStart}
        data-testid="train-btn-start"
      >
        Start session
      </Button>
    </div>
  );
}
