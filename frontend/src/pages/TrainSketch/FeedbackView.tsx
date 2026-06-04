import { CheckCircle2, XCircle, CalendarClock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ZONE_SUCCESS, ZONE_DANGER } from '@/lib/theme';
import type { AcceptableMove, Puzzle, Verdict } from './puzzles';

interface FeedbackViewProps {
  puzzle: Puzzle;
  verdict: Verdict;
  userSan: string;
  chosenMove: AcceptableMove | null;
  onNext: () => void;
  isLast: boolean;
}

const pct = (score: number): string => `${Math.round(score * 100)}%`;

function MoveRow({ label, san, score, color }: { label: string; san: string; score: number; color: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-t border-border/40 py-2 text-sm first:border-t-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="flex items-center gap-2">
        <span className="font-semibold text-foreground tabular-nums">{san}</span>
        <span className="rounded px-1.5 py-0.5 text-sm font-medium tabular-nums" style={{ color }}>
          {pct(score)}
        </span>
      </span>
    </div>
  );
}

export function FeedbackView({ puzzle, verdict, userSan, chosenMove, onNext, isLast }: FeedbackViewProps) {
  const positive = verdict === 'solved' || verdict === 'herring_ok';
  const accent = positive ? ZONE_SUCCESS : ZONE_DANGER;
  const headline =
    verdict === 'solved' ? 'Solved' : verdict === 'herring_ok' ? 'Good awareness' : 'Not quite';
  const reveal = verdict === 'missed' ? puzzle.revealMissed : puzzle.revealSolved;
  const nextReview = positive ? puzzle.nextReviewSolved : puzzle.nextReviewMissed;
  const Icon = positive ? CheckCircle2 : XCircle;
  const best = puzzle.acceptable[0] ?? null;

  return (
    <div className="flex w-full flex-col gap-4" data-testid="train-feedback">
      <div
        className="flex items-center gap-2 rounded-lg px-4 py-3"
        style={{ backgroundColor: `${accent}1f`, color: accent }}
      >
        <Icon className="h-6 w-6" />
        <div>
          <p className="font-brand text-lg">{headline}</p>
          {chosenMove ? (
            <p className="text-sm opacity-90">
              {userSan} — {chosenMove.label}
            </p>
          ) : null}
        </div>
      </div>

      <p className="text-sm text-foreground/90">{reveal}</p>

      {puzzle.kind !== 'red_herring' ? (
        <div className="rounded-lg bg-card px-4 py-2 ring-1 ring-foreground/10">
          {verdict === 'solved' && chosenMove ? (
            <MoveRow label="Your move now" san={userSan} score={chosenMove.expectedScore} color={ZONE_SUCCESS} />
          ) : null}
          {best ? <MoveRow label="Best" san={best.san} score={best.expectedScore} color={ZONE_SUCCESS} /> : null}
          <MoveRow
            label="What you played in the game"
            san={puzzle.playedSan}
            score={puzzle.playedExpectedScore}
            color={ZONE_DANGER}
          />
        </div>
      ) : null}

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <CalendarClock className="h-4 w-4" />
        <span>{nextReview}</span>
      </div>

      <Button size="lg" className="w-full" onClick={onNext} data-testid="train-btn-next">
        {isLast ? 'Finish session' : 'Next position'}
      </Button>
    </div>
  );
}
