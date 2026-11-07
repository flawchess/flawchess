/**
 * TrainScoreScreenDemo — admin-only playground for the Train session feedback
 * screen. Client-only fixtures, no backend, so it works in dev and prod.
 *
 * It renders the production TrainScoreScreenView through its props and takes
 * the bubble copy from the real `scoreBubbleCopy`, so what the demo shows is
 * what users get. Nothing is fetched or saved: the real screen's onboarding
 * stamp and reminder controls live in its container, not in the view. Sound and
 * confetti only fire on Replay, never when the admin page loads. /admin sends
 * no Umami events.
 */
import { useMemo, useState, type ReactElement } from 'react';
import { addDays, format, parseISO } from 'date-fns';
import { Check } from 'lucide-react';

import { TrainScoreRankLinesView } from '@/components/train/TrainScoreRankLines';
import { TrainScoreScreenView } from '@/components/train/TrainScoreScreen';
import { Button } from '@/components/ui/button';
import { pickBot, scoreBubbleCopy } from '@/lib/trainBotCopy';
import { localTodayIso, nextSessionWhen } from '@/lib/trainNextSession';
import { countMissedPuzzles, resolveRatingBand } from '@/lib/trainScore';
import { celebrateScore } from '@/lib/trainScoreCelebration';
import {
  DEMO_NEXT_SESSION_SCENARIO_IDS,
  DEMO_NEXT_SESSION_SCENARIOS,
  DEMO_RANK_SCENARIO_IDS,
  DEMO_RANK_SCENARIOS,
  DEMO_SCORE_SCENARIO_IDS,
  DEMO_SCORE_SCENARIOS,
} from '@/lib/trainScoreDemoData';
import type { NextSessionScenarioId, RankScenarioId, ScoreScenarioId } from '@/lib/trainScoreDemoData';

const ISO_DATE_FORMAT = 'yyyy-MM-dd';
const DEMO_AUDIENCE = { hasGames: true, isGuest: false } as const;

/** The real line lives inside useTrainReminderSlot, behind live push queries. */
const DEMO_REMINDER_LINE = (
  <span className="flex items-center justify-center gap-1 text-sm text-muted-foreground">
    <Check className="size-4" aria-hidden="true" />
    Reminders on — 16:00 on your training days
  </span>
);

function ScenarioButtons<Id extends string>({
  ids,
  labelOf,
  selected,
  onSelect,
  testIdPrefix,
}: {
  ids: readonly Id[];
  labelOf: (id: Id) => string;
  selected: Id;
  onSelect: (id: Id) => void;
  testIdPrefix: string;
}): ReactElement {
  return (
    <div className="flex flex-wrap gap-2">
      {ids.map((id) => (
        <Button
          key={id}
          variant={id === selected ? 'default' : 'brand-outline'}
          aria-pressed={id === selected}
          data-testid={`${testIdPrefix}-${id}`}
          onClick={() => onSelect(id)}
        >
          {labelOf(id)}
        </Button>
      ))}
    </div>
  );
}

export function TrainScoreScreenDemo(): ReactElement {
  const [scoreId, setScoreId] = useState<ScoreScenarioId>('strong');
  const [nextId, setNextId] = useState<NextSessionScenarioId>('tomorrow');
  const [rankId, setRankId] = useState<RankScenarioId>('ranked');
  const [reducedMotion, setReducedMotion] = useState(false);
  const [replayCount, setReplayCount] = useState(0);
  const persona = useMemo(() => pickBot('smart'), []);

  const { score, outcomes } = DEMO_SCORE_SCENARIOS[scoreId];
  const band = resolveRatingBand(score.total / score.max);

  const todayIso = localTodayIso(undefined);
  const nextDate = format(addDays(parseISO(todayIso), DEMO_NEXT_SESSION_SCENARIOS[nextId].daysAhead), ISO_DATE_FORMAT);
  const nextSession = nextSessionWhen(nextDate, todayIso);

  const bubble = scoreBubbleCopy({
    missedCount: countMissedPuzzles(outcomes),
    isFirstCompletedSession: false,
    isWarmup: false,
    reminderAsk: 'none',
    band,
    audience: DEMO_AUDIENCE,
    nextSessionSeeYou: nextSession.seeYou,
  });

  function replay(): void {
    setReplayCount((count) => count + 1);
    celebrateScore(band, reducedMotion);
  }

  return (
    <div className="charcoal-texture rounded-md p-4 space-y-3" data-testid="admin-train-score-demo">
      <p className="text-sm text-muted-foreground">
        Fixtures only: nothing is fetched or saved. The screen below is the real production view. Narrow the
        window to see the phone layout. Done does nothing here.
      </p>
      <ScenarioButtons
        ids={DEMO_SCORE_SCENARIO_IDS}
        labelOf={(id) => DEMO_SCORE_SCENARIOS[id].label}
        selected={scoreId}
        onSelect={setScoreId}
        testIdPrefix="btn-score-demo-score"
      />
      <ScenarioButtons
        ids={DEMO_NEXT_SESSION_SCENARIO_IDS}
        labelOf={(id) => DEMO_NEXT_SESSION_SCENARIOS[id].label}
        selected={nextId}
        onSelect={setNextId}
        testIdPrefix="btn-score-demo-next"
      />
      <ScenarioButtons
        ids={DEMO_RANK_SCENARIO_IDS}
        labelOf={(id) => DEMO_RANK_SCENARIOS[id].label}
        selected={rankId}
        onSelect={setRankId}
        testIdPrefix="btn-score-demo-rank"
      />
      <div className="flex flex-wrap gap-2">
        <Button variant="brand-outline" data-testid="btn-score-demo-replay" onClick={replay}>
          Replay with sound
        </Button>
        <Button
          variant="brand-outline"
          aria-pressed={reducedMotion}
          data-testid="btn-score-demo-toggle-reduced-motion"
          onClick={() => setReducedMotion((value) => !value)}
        >
          {reducedMotion ? 'Reduced motion: on' : 'Reduced motion: off'}
        </Button>
      </div>
      {/* -mx-4 cancels this panel's padding on phones, so the screen gets the same
          width as on the Train page and wraps the way users will see it.
          Re-keyed so a new score or a replay runs the arrival animation again. */}
      <div className="-mx-4 sm:mx-0" data-testid="score-demo-frame">
        <TrainScoreScreenView
          key={`${scoreId}-${replayCount}`}
          score={score}
          nextSessionLine={nextSession.line}
          persona={persona}
          bubbleLines={bubble.lines}
          bubbleActions={undefined}
          rankLines={<TrainScoreRankLinesView data={DEMO_RANK_SCENARIOS[rankId].data} isError={false} />}
          reminderControl={null}
          reminderBelowRow={DEMO_REMINDER_LINE}
          reducedMotion={reducedMotion}
          onDone={() => {}}
        />
      </div>
    </div>
  );
}
