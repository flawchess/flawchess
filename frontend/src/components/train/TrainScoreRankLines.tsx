import type { ReactElement } from 'react';
import { LoadError } from '@/components/ui/load-error';
import { useTrainLeaderboard } from '@/hooks/useTrainLeaderboard';
import { scoreRankLines } from '@/lib/trainLeaderboard';

/**
 * TrainScoreRankLines — compact rank-change lines under "Points: x/y" on the
 * session score screen (Phase 230 D-11, D-12). One GET /train/leaderboard
 * request carrying this session's id, made when the score screen mounts: the
 * server returns the viewer's rank with and without this session, so the
 * client never recomputes anything.
 *
 * All branching lives here and in the pure `scoreRankLines` copy rules, not in
 * TrainScoreScreen (which sits at its complexity cap). It renders no buttons:
 * the score bubble's guest ask is the only sign-up CTA (D-17).
 */
export function TrainScoreRankLines({ sessionId }: { sessionId: number | null }): ReactElement | null {
  // Hook first and unconditionally (rules of hooks); it is disabled for a null id.
  const { data, isError } = useTrainLeaderboard({ sessionId });
  if (sessionId === null) return null;
  return (
    // min-h-10 holds room for two lines so the Next session line and the
    // button row do not jump when the ranks arrive.
    <div
      className="flex min-h-10 flex-col items-center gap-0.5 text-sm text-muted-foreground"
      data-testid="train-score-rank-lines"
    >
      {data !== undefined &&
        scoreRankLines(data).map((line) => (
          <p key={line.id} data-testid={`train-score-rank-${line.id}`}>
            {line.text}
          </p>
        ))}
      {isError && (
        <LoadError resource="your leaderboard rank" variant="inline" data-testid="train-score-rank-error" />
      )}
    </div>
  );
}
