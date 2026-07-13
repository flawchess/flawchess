/**
 * Bots — the /bots page assembling the clocked bot-play board (Phase 169).
 *
 * Default export (required by React.lazy in App.tsx, mirroring Analysis.tsx's
 * Pitfall 1 divergence from the app's named-export convention).
 *
 * D-14 stub: instantiates `useBotGame` with a hardcoded `BotGameSettings` —
 * Phase 171 replaces this with the real setup screen (ELO/blend/TC/color
 * pickers) and adds the nav entry. The game starts immediately on route load
 * (no explicit "Start game" affordance needed since the D-14 stub settings
 * are fixed); the page is a thin orchestrator wiring `useBotGame` (Plan 04)
 * to `ClockDisplay`/`MoveListPanel`/`GameControls` (Plan 05) and the result
 * surfaces (Plan 06 Task 1) around `ChessBoard`.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactElement } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChessBoard } from '@/components/board/ChessBoard';
import { ClockDisplay } from '@/components/bots/ClockDisplay';
import { MoveListPanel } from '@/components/bots/MoveListPanel';
import { GameControls } from '@/components/bots/GameControls';
import { GameResultDialog } from '@/components/bots/GameResultDialog';
import { GameResultStrip } from '@/components/bots/GameResultStrip';
import { useBotGame, type BotGameSettings, type UseBotGameState } from '@/hooks/useBotGame';
import { setMuted, unlockAudio, useMuted } from '@/lib/sounds';
import { buildAnalysisLineUrl } from '@/lib/analysisUrl';

/**
 * D-14 hardcoded start stub — a lichess-style 5+3 blitz preset (Claude's
 * discretion), bot at a mid-range ELO with a balanced human/Stockfish blend,
 * user playing white. Phase 171 replaces this with the real setup screen.
 */
const BOT_GAME_SETTINGS: BotGameSettings = {
  botElo: 1500,
  blend: 0.5,
  baseSeconds: 300,
  incrementSeconds: 3,
  userColor: 'white',
};

/** Matches the app's existing `lg` Tailwind breakpoint (1024px) — below this,
 * clocks/move-list/controls stack around the board (mobile: bot clock above,
 * user clock below, per lichess convention); at/above it they move into a
 * side column beside the board (desktop), per the UI-SPEC layout. */
const DESKTOP_BREAKPOINT_PX = 1024;

function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia(`(min-width: ${DESKTOP_BREAKPOINT_PX}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(min-width: ${DESKTOP_BREAKPOINT_PX}px)`);
    const update = () => setIsDesktop(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isDesktop;
}

interface GamePanelProps {
  game: UseBotGameState;
  muted: boolean;
  dialogDismissed: boolean;
  onToggleMute: () => void;
  onAnalyze: () => void;
}

/**
 * Move list + resign/draw/mute controls (or, once the result dialog is
 * dismissed, the persistent result strip REPLACING the controls area per the
 * UI-SPEC) — shared verbatim by the mobile and desktop layouts below, only
 * its position in the page differs.
 */
function GamePanel({
  game,
  muted,
  dialogDismissed,
  onToggleMute,
  onAnalyze,
}: GamePanelProps): ReactElement {
  const outcome = game.outcome;
  const showResultStrip = outcome !== null && dialogDismissed;

  return (
    <div className="flex flex-col gap-3">
      <MoveListPanel
        moveHistory={game.moveHistory}
        liveGamePly={game.liveGamePly}
        viewedPly={game.viewedPly}
        onViewPly={game.viewPly}
        onReturnToLive={game.returnToLive}
      />
      {showResultStrip && outcome !== null ? (
        <GameResultStrip
          outcome={outcome}
          userColor={BOT_GAME_SETTINGS.userColor}
          onNewGame={game.newGame}
          onAnalyze={onAnalyze}
        />
      ) : (
        <GameControls
          // WR-04: the props now mean what their names/docs say — `canOfferDraw`
          // is the D-01 "not already pending, game not over" gate;
          // `drawCooldownActive` is the D-04 cooldown throttle, which is what
          // the hook's own `canOfferDraw` (a cooldown-gate boolean) actually
          // reports (inverted). The net disabled state is unchanged.
          canOfferDraw={!game.drawOfferPending && game.outcome === null}
          drawCooldownActive={!game.canOfferDraw}
          muted={muted}
          onResignConfirmed={game.resign}
          onOfferDraw={game.offerDraw}
          onToggleMute={onToggleMute}
        />
      )}
    </div>
  );
}

/** Mobile: bot clock above the board, board, user clock below (lichess
 * convention), then the move list + controls/strip. */
function renderMobileLayout(
  botClock: ReactElement,
  userClock: ReactElement,
  board: ReactElement,
  panel: ReactElement,
): ReactElement {
  return (
    <div className="flex flex-col gap-3">
      {botClock}
      <div className="flex justify-center">{board}</div>
      {userClock}
      {panel}
    </div>
  );
}

/** Desktop: board on the left, a fixed-width side column (both clocks, then
 * the move list + controls/strip) on the right, per the UI-SPEC. */
function renderDesktopLayout(
  botClock: ReactElement,
  userClock: ReactElement,
  board: ReactElement,
  panel: ReactElement,
): ReactElement {
  return (
    <div className="flex flex-row gap-4">
      <div className="flex flex-1 justify-center">{board}</div>
      <div className="flex w-[320px] shrink-0 flex-col gap-3">
        {botClock}
        {userClock}
        {panel}
      </div>
    </div>
  );
}

export default function BotsPage(): ReactElement {
  const navigate = useNavigate();
  const isDesktop = useIsDesktop();
  const muted = useMuted();
  const game = useBotGame(BOT_GAME_SETTINGS);
  const [dialogDismissed, setDialogDismissed] = useState(false);
  const hasUnlockedAudioRef = useRef(false);

  // Reset the dismissed flag when a fresh game starts (outcome goes back to null).
  useEffect(() => {
    if (game.outcome === null) setDialogDismissed(false);
  }, [game.outcome]);

  // Pitfall 4: unlock iOS/mobile-Chrome audio playback from the page's first
  // user gesture of ANY kind (useBotGame.attemptMove also unlocks on the
  // first board move, but a gesture on the controls/board container before
  // any move should unlock playback too).
  const handleFirstInteraction = useCallback((): void => {
    if (hasUnlockedAudioRef.current) return;
    hasUnlockedAudioRef.current = true;
    unlockAudio();
  }, []);

  const handleToggleMute = useCallback((): void => {
    setMuted(!muted);
  }, [muted]);

  const handleAnalyze = useCallback((): void => {
    navigate(buildAnalysisLineUrl(game.moveHistory));
  }, [navigate, game.moveHistory]);

  const botColor = BOT_GAME_SETTINGS.userColor === 'white' ? 'black' : 'white';
  const flipped = BOT_GAME_SETTINGS.userColor === 'black';

  const botClock = (
    <ClockDisplay
      sideLabel="FlawChess Bot"
      remainingMs={botColor === 'white' ? game.whiteClockMs : game.blackClockMs}
      isActive={game.activeColor === botColor}
      isThinking={game.isBotThinking}
      testId="clock-bot"
    />
  );
  const userClock = (
    <ClockDisplay
      sideLabel="You"
      remainingMs={
        BOT_GAME_SETTINGS.userColor === 'white' ? game.whiteClockMs : game.blackClockMs
      }
      isActive={game.activeColor === BOT_GAME_SETTINGS.userColor}
      isThinking={false}
      testId="clock-user"
    />
  );
  const board = <ChessBoard position={game.position} onPieceDrop={game.attemptMove} flipped={flipped} />;
  const panel = (
    <GamePanel
      game={game}
      muted={muted}
      dialogDismissed={dialogDismissed}
      onToggleMute={handleToggleMute}
      onAnalyze={handleAnalyze}
    />
  );

  return (
    <div
      data-testid="bots-page"
      onPointerDown={handleFirstInteraction}
      className="mx-auto flex max-w-5xl flex-col gap-4 p-4"
    >
      {isDesktop
        ? renderDesktopLayout(botClock, userClock, board, panel)
        : renderMobileLayout(botClock, userClock, board, panel)}

      {game.outcome !== null && (
        <GameResultDialog
          outcome={game.outcome}
          userColor={BOT_GAME_SETTINGS.userColor}
          open={!dialogDismissed}
          onDismiss={() => setDialogDismissed(true)}
          onNewGame={game.newGame}
          onAnalyze={handleAnalyze}
        />
      )}
    </div>
  );
}
