/**
 * Bots — the /bots page assembling the clocked bot-play board (Phase 169),
 * plus the Phase 170 localStorage resume gate + silent pending-store drain.
 *
 * Default export (required by React.lazy in App.tsx, mirroring Analysis.tsx's
 * Pitfall 1 divergence from the app's named-export convention).
 *
 * Restructured into an outer `BotsPage` (owner-scope resolution, snapshot
 * detection, pending-store drain — Phase 170 Plan 05) and an inner `BotsGame`
 * (today's game body, unchanged except `BOT_GAME_SETTINGS` swapped for a
 * per-instance `settings` derived from an optional resumed snapshot).
 *
 * D-14 stub: with NO snapshot present, `BotsGame` still gets a hardcoded
 * `BOT_GAME_SETTINGS` and starts immediately — Phase 171 replaces THAT branch
 * (and only that branch) with the real setup screen (ELO/blend/TC/color
 * pickers) and adds the nav entry. With a snapshot present, `BotsGame` mounts
 * immediately too (so its engines warm — D-03 corrected), but `ResumeGate`
 * overlays the board and nothing starts until the user chooses Resume or
 * Discard (D-04).
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
import { ResumeGate } from '@/components/bots/ResumeGate';
import { useBotGame, type BotGameSettings, type UseBotGameState } from '@/hooks/useBotGame';
import { useUserProfile } from '@/hooks/useUserProfile';
import { useDrainPendingStore } from '@/hooks/useStoreBotGame';
import { readSnapshot, clearSnapshot, type BotGameSnapshot } from '@/lib/botGameSnapshot';
import type { MoverColor } from '@/lib/liveFlaw';
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
  userColor: MoverColor;
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
  userColor,
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
          userColor={userColor}
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

interface BotsGameProps {
  /** The snapshot to resume from, or `null` for a fresh D-14 stub game. */
  resume: BotGameSnapshot | null;
  ownerKey: string | null;
  /** Discard-confirmed: clears the snapshot and remounts a fresh game
   * (BotsPage's `handleDiscard`, via the `key`-changed remount). */
  onDiscard: () => void;
}

/**
 * The actual game body — today's page, minus owner-scope/snapshot-detection
 * concerns (now `BotsPage`'s job). `settings` comes from the resumed
 * snapshot when present, else the D-14 stub. `ResumeGate` overlays the board
 * whenever a snapshot is present and the hook has not gone live yet
 * (D-03/D-04): the hook is mounted immediately either way, so its provider
 * bring-up effect warms the engines while the gate is still on screen.
 */
function BotsGame({ resume, ownerKey, onDiscard }: BotsGameProps): ReactElement {
  const navigate = useNavigate();
  const isDesktop = useIsDesktop();
  const muted = useMuted();
  const settings = resume?.settings ?? BOT_GAME_SETTINGS;
  const game = useBotGame(settings, resume ?? undefined, ownerKey);
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

  const botColor = settings.userColor === 'white' ? 'black' : 'white';
  const flipped = settings.userColor === 'black';

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
      remainingMs={settings.userColor === 'white' ? game.whiteClockMs : game.blackClockMs}
      isActive={game.activeColor === settings.userColor}
      isThinking={false}
      testId="clock-user"
    />
  );
  const board = (
    <ChessBoard position={game.position} onPieceDrop={game.attemptMove} flipped={flipped} />
  );
  const panel = (
    <GamePanel
      game={game}
      userColor={settings.userColor}
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

      {resume !== null && !game.live && (
        <ResumeGate
          snapshot={resume}
          plyCount={game.liveGamePly}
          onResume={game.confirmLive}
          onDiscard={onDiscard}
        />
      )}

      {game.outcome !== null && (
        <GameResultDialog
          outcome={game.outcome}
          userColor={settings.userColor}
          open={!dialogDismissed}
          onDismiss={() => setDialogDismissed(true)}
          onNewGame={game.newGame}
          onAnalyze={handleAnalyze}
        />
      )}
    </div>
  );
}

export default function BotsPage(): ReactElement {
  const { data: profile, isLoading } = useUserProfile();
  const ownerKey = profile?.email ?? null;

  const [boot, setBoot] = useState<{ resume: BotGameSnapshot | null; nonce: number } | null>(
    null,
  );

  // Boot effect: read the snapshot only once the profile has settled
  // (`!isLoading`). Reading it earlier would use the `anon` key (T-170-04's
  // ordering trap) and silently miss a logged-in user's resumable game.
  // `boot === null` also gates the FIRST read only — a later `ownerKey`
  // change (e.g. login completing) does not re-trigger this effect, matching
  // "lazy seed, not a live subscription" (useBotGame's `resume` prop is a
  // lazy initializer, read once at first render).
  useEffect(() => {
    if (isLoading) return;
    if (boot !== null) return;
    setBoot({ resume: readSnapshot(ownerKey), nonce: 0 });
  }, [isLoading, ownerKey, boot]);

  // D-13: drain the pending-store queue on mount, before/independently of the
  // gate — fires exactly once, after the profile has settled, regardless of
  // whether a gate is shown. Silent in this phase (no UI); fire-and-forget,
  // `drain()` never rethrows.
  const { drain } = useDrainPendingStore(ownerKey);
  const hasDrainedRef = useRef(false);
  useEffect(() => {
    if (isLoading) return;
    if (hasDrainedRef.current) return;
    hasDrainedRef.current = true;
    void drain();
  }, [isLoading, drain]);

  // D-05: discard clears ONLY the in-progress snapshot (never the
  // pending-store queue — D-12's separate key) and remounts `BotsGame` via a
  // changed `key` with `resume: null`, so the post-discard game gets
  // `BOT_GAME_SETTINGS` (not the discarded game's settings) and is live from
  // mount, exactly today's D-14 stub behavior.
  const handleDiscard = useCallback((): void => {
    clearSnapshot(ownerKey);
    setBoot((prev) => ({ resume: null, nonce: (prev?.nonce ?? 0) + 1 }));
  }, [ownerKey]);

  if (boot === null) {
    return (
      <div data-testid="bots-page-loading" className="p-4 text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  return (
    <BotsGame key={boot.nonce} resume={boot.resume} ownerKey={ownerKey} onDiscard={handleDiscard} />
  );
}
