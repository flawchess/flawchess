/**
 * LeaderboardMedalsDemo — admin-only playground for the weekly Train medals
 * (Phase 231). Client-only fixtures, no backend, so it works in dev and prod.
 *
 * It renders the production TrainLeaderboardCardView and MedalClaimDialog
 * through their props, so what the demo shows is what users get. The claim
 * callbacks only close the dialog (no POST). /admin sends no Umami events and
 * the demo uses no queries, so there is nothing to track or capture.
 *
 * Toggles are simulated through props: muted and reduced motion go straight to
 * MedalClaimDialog, "375 px frame" narrows the card. The real persisted mute
 * preference still silences playSound, and the CSS prefers-reduced-motion media
 * query still stops the pop animation when the OS reduces motion.
 */
import { useState } from 'react';
import type { ReactElement } from 'react';

import { MedalClaimDialog } from '@/components/train/medals/MedalClaimDialog';
import { TrainLeaderboardCardView } from '@/components/train/TrainLeaderboardCard';
import { Button } from '@/components/ui/button';
import {
  DEMO_BOARD_SCENARIOS,
  DEMO_CELEBRATE_SCENARIOS,
  DEMO_REMAINING_SECONDS,
} from '@/lib/leaderboardMedalsDemoData';
import type { BoardScenarioId, CelebrateScenarioId } from '@/lib/leaderboardMedalsDemoData';
import { parseLeaderboardTab } from '@/lib/trainLeaderboard';
import type { LeaderboardBoardKind } from '@/types/train';

const INITIAL_BOARD_SCENARIO: BoardScenarioId = 'podium-tie';
/** Phone-width frame the narrow toggle applies; the default is the Train page card width. */
const NARROW_FRAME_CLASS = 'max-w-[375px]';
const WIDE_FRAME_CLASS = 'max-w-xl';

const TOGGLE_HELPER =
  'Muted and reduced motion are simulated for the dialog only. The real persisted mute preference still ' +
  'silences the sound, and the CSS media query still stops the animation when your OS reduces motion.';

export function LeaderboardMedalsDemo(): ReactElement {
  const [boardId, setBoardId] = useState<BoardScenarioId>(INITIAL_BOARD_SCENARIO);
  const [tab, setTab] = useState<LeaderboardBoardKind>(DEMO_BOARD_SCENARIOS[INITIAL_BOARD_SCENARIO].tab);
  const [celebrateId, setCelebrateId] = useState<CelebrateScenarioId | null>(null);
  const [muted, setMuted] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [narrow, setNarrow] = useState(false);

  const boardScenario = DEMO_BOARD_SCENARIOS[boardId];
  const celebrateScenario = celebrateId === null ? null : DEMO_CELEBRATE_SCENARIOS[celebrateId];

  function pickBoard(id: BoardScenarioId): void {
    setBoardId(id);
    setTab(DEMO_BOARD_SCENARIOS[id].tab);
  }

  function closeDialog(): void {
    setCelebrateId(null);
  }

  return (
    <div className="charcoal-texture rounded-md p-4 space-y-3" data-testid="admin-leaderboard-medals-demo">
      <p className="text-sm text-muted-foreground">
        Fixtures only: nothing is fetched or saved. The board and the claim dialog below are the real
        production components.
      </p>
      <p className="text-sm text-muted-foreground">{TOGGLE_HELPER}</p>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="brand-outline"
          aria-pressed={muted}
          data-testid="btn-medals-demo-toggle-muted"
          onClick={() => setMuted((value) => !value)}
        >
          {muted ? 'Muted: on' : 'Muted: off'}
        </Button>
        <Button
          variant="brand-outline"
          aria-pressed={reducedMotion}
          data-testid="btn-medals-demo-toggle-reduced-motion"
          onClick={() => setReducedMotion((value) => !value)}
        >
          {reducedMotion ? 'Reduced motion: on' : 'Reduced motion: off'}
        </Button>
        <Button
          variant="brand-outline"
          aria-pressed={narrow}
          data-testid="btn-medals-demo-toggle-narrow"
          onClick={() => setNarrow((value) => !value)}
        >
          {narrow ? '375 px frame: on' : '375 px frame: off'}
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(DEMO_BOARD_SCENARIOS) as BoardScenarioId[]).map((id) => (
          <Button
            key={id}
            variant="brand-outline"
            data-testid={`btn-medals-demo-board-${id}`}
            onClick={() => pickBoard(id)}
          >
            {DEMO_BOARD_SCENARIOS[id].label}
          </Button>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(DEMO_CELEBRATE_SCENARIOS) as CelebrateScenarioId[]).map((id) => (
          <Button
            key={id}
            variant="brand-outline"
            data-testid={`btn-medals-demo-celebrate-${id}`}
            onClick={() => setCelebrateId(id)}
          >
            {`Celebrate: ${DEMO_CELEBRATE_SCENARIOS[id].label}`}
          </Button>
        ))}
      </div>
      <div className={narrow ? NARROW_FRAME_CLASS : WIDE_FRAME_CLASS} data-testid="medals-demo-card-frame">
        <TrainLeaderboardCardView
          data={boardScenario.data}
          isPending={false}
          isError={false}
          remaining={DEMO_REMAINING_SECONDS}
          tab={tab}
          onTabChange={(value) => {
            if (value !== '') setTab(parseLeaderboardTab(value));
          }}
          isGuest={false}
        />
      </div>
      <MedalClaimDialog
        open={celebrateScenario !== null}
        medals={celebrateScenario?.medals ?? []}
        muted={muted}
        reducedMotion={reducedMotion}
        onClaim={closeDialog}
        onDismiss={closeDialog}
      />
    </div>
  );
}
