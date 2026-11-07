import type { ReactElement } from 'react';
import { InfoPopover } from '@/components/ui/info-popover';
import { LoadError } from '@/components/ui/load-error';
import { useTrainLeaderboard } from '@/hooks/useTrainLeaderboard';
import { scoreRankLines } from '@/lib/trainLeaderboard';
import type { TrainLeaderboardResponse } from '@/types/train';

/**
 * The rank lines from props: no fetching, so the admin score screen demo shows
 * production markup. A line carrying `info` gets an InfoPopover beside it.
 */
export function TrainScoreRankLinesView({
  data,
  isError,
}: {
  data: TrainLeaderboardResponse | undefined;
  isError: boolean;
}): ReactElement {
  return (
    // min-h-10 holds room for two lines so the Next session line and the
    // button row do not jump when the ranks arrive.
    <div
      className="flex min-h-10 flex-col items-start gap-0.5 text-sm text-muted-foreground"
      data-testid="train-score-rank-lines"
    >
      {data !== undefined &&
        scoreRankLines(data).map((line) => (
          <p key={line.id} data-testid={`train-score-rank-${line.id}`}>
            {line.text}
            {line.info !== undefined && (
              // Inline, so a wrapped line keeps the icon right after its last word.
              <span className="ml-1 inline-flex align-middle">
                <InfoPopover ariaLabel="About this rank" testId={`train-score-rank-${line.id}-info`} side="top">
                  {line.info}
                </InfoPopover>
              </span>
            )}
          </p>
        ))}
      {isError && (
        <LoadError resource="your leaderboard rank" variant="inline" data-testid="train-score-rank-error" />
      )}
    </div>
  );
}

/**
 * TrainScoreRankLines — compact rank-change lines under "Points: x/y" on the
 * session score screen. One GET /train/leaderboard request carrying this
 * session's id, made when the score screen mounts: the server returns the
 * viewer's rank with and without this session, so the client never
 * recomputes anything.
 *
 * All branching lives here and in the pure `scoreRankLines` copy rules, not in
 * TrainScoreScreen. It renders no buttons: the score bubble's guest ask is
 * the only sign-up CTA.
 */
export function TrainScoreRankLines({ sessionId }: { sessionId: number | null }): ReactElement | null {
  // Hook first and unconditionally (rules of hooks); it is disabled for a null id.
  const { data, isError } = useTrainLeaderboard({ sessionId });
  if (sessionId === null) return null;
  return <TrainScoreRankLinesView data={data} isError={isError} />;
}
