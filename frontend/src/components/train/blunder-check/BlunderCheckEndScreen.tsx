/**
 * BlunderCheckEndScreen: the session end screen (Phase 249, D-14).
 *
 * The personalized-puzzle score screen's own view (`TrainScoreScreenView`, Phase 249 UAT):
 * a bot bubble, the Score % ring with "Points: x/y" beside it, and a full-width Done. A
 * short per-outcome summary of the sequences takes the rank lines' slot. Blunder check has no schedule, leaderboard
 * or reminders yet (Phase 251), so the next-session line and the reminder row are absent.
 * Every number is the finish endpoint's (Pitfall 13); nothing is derived from local state.
 * "Done" returns to the start screen. No Umami event (D-19).
 */

import { useEffect, useMemo } from 'react';
import type { ReactElement } from 'react';
import { TrainScoreScreenView } from '@/components/train/TrainScoreScreen';
import { WINDOW_OUTCOME_LABELS } from '@/lib/blunderCheckDrill';
import { prefersReducedMotion } from '@/lib/confetti';
import { blunderCheckScoreBubbleCopy, pickBot } from '@/lib/trainBotCopy';
import { resolveRatingBand } from '@/lib/trainScore';
import { celebrateScore } from '@/lib/trainScoreCelebration';
import type { SessionResultResponse, WindowOutcome, WindowResultItem } from '@/types/blunderCheck';

/** Score % is a whole number 0 to 100; the rating band takes a 0 to 1 ratio. */
const PERCENT_PER_RATIO = 100;

/** The summary's two lines: what happened to the blunders, then the sequences without a catch. */
const OUTCOME_SUMMARY_ROWS: ReadonlyArray<{ id: string; outcomes: readonly WindowOutcome[] }> = [
  { id: 'blunders', outcomes: ['caught', 'missed'] },
  { id: 'clean', outcomes: ['cleared', 'false_alarm'] },
];

/**
 * The sequences summed up by outcome, in the score screen's rank-line style. Not one line per
 * sequence: a session may hold too many to list (Phase 249 UAT). Outcomes with no sequence
 * are left out.
 */
function SequenceSummary({ windows }: { windows: WindowResultItem[] }): ReactElement {
  const countOf = (outcome: WindowOutcome): number =>
    windows.filter((window) => window.outcome === outcome).length;
  return (
    <div
      className="flex flex-col items-start gap-0.5 text-sm text-muted-foreground"
      data-testid="blunder-check-end-summary"
    >
      <p data-testid="blunder-check-end-sequences">Sequences: {windows.length}</p>
      {OUTCOME_SUMMARY_ROWS.map((row) => {
        const parts = row.outcomes
          .filter((outcome) => countOf(outcome) > 0)
          .map((outcome) => `${WINDOW_OUTCOME_LABELS[outcome]}: ${countOf(outcome)}`);
        if (parts.length === 0) return null;
        return (
          <p key={row.id} data-testid={`blunder-check-end-${row.id}`}>
            {parts.join(' · ')}
          </p>
        );
      })}
    </div>
  );
}

export function BlunderCheckEndScreen({
  result,
  onDone,
}: {
  result: SessionResultResponse;
  onDone: () => void;
}): ReactElement {
  const band = resolveRatingBand(result.score_pct / PERCENT_PER_RATIO);
  // A random smart bot hosts the bubble, picked once per mount like the Train score screen.
  const bot = useMemo(() => pickBot('smart'), []);
  // Drawn once per mount: the rationale is random, so a re-render must not swap it.
  const bubbleLines = useMemo(() => blunderCheckScoreBubbleCopy(band).lines, [band]);
  // Read once per render so the badge animation and the confetti decision agree.
  const reducedMotion = prefersReducedMotion();
  useEffect(() => {
    // The Train score screen's result sound and confetti, once per mount.
    celebrateScore(band, reducedMotion);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div data-testid="blunder-check-end-screen">
      <TrainScoreScreenView
        score={{ total: result.session_points, max: result.points_possible }}
        percentage={result.score_pct}
        nextSessionLine={null}
        persona={bot}
        bubbleLines={bubbleLines}
        bubbleActions={undefined}
        rankLines={<SequenceSummary windows={result.windows} />}
        reminderControl={null}
        reminderBelowRow={null}
        reducedMotion={reducedMotion}
        onDone={onDone}
      />
    </div>
  );
}
