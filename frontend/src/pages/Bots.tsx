/**
 * Bots — the /bots page assembling the clocked bot-play board (Phase 169),
 * the Phase 170 localStorage resume gate + silent pending-store drain, and
 * the Phase 171 setup screen (D-09/D-11/D-13).
 *
 * Default export (required by React.lazy in App.tsx, mirroring Analysis.tsx's
 * Pitfall 1 divergence from the app's named-export convention).
 *
 * Restructured into an outer `BotsPage` (owner-scope resolution, snapshot
 * detection, pending-store drain, and now the setup/game phase switch — Phase
 * 170 Plan 05 + Phase 171 Plan 06) and an inner `BotsGame` (today's game
 * body, now taking its `settings` as a required prop instead of falling back
 * to a hardcoded stub).
 *
 * SETUP AS THE SINGLE ENTRY POINT (Phase 171, replacing the old D-14 stub
 * branch): with NO snapshot present, `BotsPage` renders `SetupScreen` and
 * `BotsGame` is not mounted at all until Start fires. With a snapshot
 * present, `BotsGame` mounts immediately (so its engines warm — D-03
 * corrected) and `ResumeGate` overlays the board; nothing starts until the
 * user chooses Resume or Discard (D-04) — this precedence is UNCHANGED by
 * this plan. Discard and both result-surface "New game" actions all fall
 * through to the setup screen (D-11/D-13) rather than auto-starting a fresh
 * game — there is no second start path.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactElement } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChessBoard } from '@/components/board/ChessBoard';
import { BoardControls } from '@/components/board/BoardControls';
import { ClockDisplay } from '@/components/bots/ClockDisplay';
import { MoveListPanel } from '@/components/bots/MoveListPanel';
import { GameControls } from '@/components/bots/GameControls';
import { GameResultDialog } from '@/components/bots/GameResultDialog';
import { GameResultStrip } from '@/components/bots/GameResultStrip';
import { ResumeGate } from '@/components/bots/ResumeGate';
import { SetupScreen } from '@/components/bots/SetupScreen';
import { useBotGame, type BotGameSettings, type UseBotGameState } from '@/hooks/useBotGame';
import { useUserProfile } from '@/hooks/useUserProfile';
import { useDrainPendingStore, useStoreBotGame, toStoreRequest } from '@/hooks/useStoreBotGame';
import { useTier1EnqueueForGame } from '@/hooks/useEnqueueGame';
import { readSnapshot, clearSnapshot, type BotGameSnapshot } from '@/lib/botGameSnapshot';
import { removePendingStore } from '@/lib/botPendingStore';
import type { MoverColor } from '@/lib/liveFlaw';
import { resolvePlayerName } from '@/lib/playerName';
import { setMuted, unlockAudio, useMuted } from '@/lib/sounds';
import { buildAnalysisLineUrl, buildGameAnalysisUrl } from '@/lib/analysisUrl';

/** Matches the app's existing `lg` Tailwind breakpoint (1024px) — below this,
 * clocks/move-list/controls stack around the board (mobile: bot clock above,
 * user clock below, per lichess convention); at/above it they move into a
 * side column beside the board (desktop), per the UI-SPEC layout. */
const DESKTOP_BREAKPOINT_PX = 1024;

/** Max rendered width of the bot-game board, in px. Shared between the
 * `ChessBoard maxWidth` prop and the single-column stack's `max-width` so the
 * clock strips / board controls are ALWAYS exactly the board's width: capping
 * the column at this value means the container never exceeds the board, so the
 * board (sized to `min(container, this)`) fills the column edge-to-edge. */
const BOT_BOARD_MAX_WIDTH_PX = 400;

/** Fixed width of the desktop right column (clocks + move list + controls). */
const DESKTOP_SIDE_COLUMN_PX = 320;

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
  /** D-11: returns to the setup screen (unmounting BotsGame) — NOT
   * `game.newGame()`, which would restart in place with the same settings. */
  onNewGame: () => void;
  /** D-21: true only once the finish-time store mutation has CONFIRMED
   * (`useStoreBotGame().isSuccess`) — gates the "Saved to your Library" row
   * on the result strip. Never true on idle/pending/error. */
  storeSucceeded: boolean;
  /** SC4: guests additionally see the not-auto-analyzed caveat alongside the
   * save confirmation. */
  isGuest: boolean;
  /** Quick 260714-rj5: threaded to GameResultStrip's Analyze button — see
   * GameResultDialog's analyzeBusy doc comment. */
  analyzeBusy: boolean;
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
  onNewGame,
  storeSucceeded,
  isGuest,
  analyzeBusy,
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
          onNewGame={onNewGame}
          onAnalyze={onAnalyze}
          storeSucceeded={storeSucceeded}
          isGuest={isGuest}
          analyzeBusy={analyzeBusy}
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

/** Mobile / single column: bot clock above the board, board, user clock below
 * (lichess convention), then the board controls, then the move list +
 * controls/strip. The whole stack is capped at the board's max width and
 * centered, so the clock strips and board controls always match the board's
 * width exactly (they never stretch past it on wider single-column widths). */
function renderMobileLayout(
  botClock: ReactElement,
  userClock: ReactElement,
  board: ReactElement,
  boardControls: ReactElement,
  panel: ReactElement,
): ReactElement {
  return (
    <div
      className="mx-auto flex w-full flex-col gap-3"
      style={{ maxWidth: BOT_BOARD_MAX_WIDTH_PX }}
    >
      {botClock}
      {board}
      {userClock}
      {boardControls}
      {panel}
    </div>
  );
}

/** Desktop: the board (with its controls directly below) and a fixed-width side
 * column (both clocks, then the move list + controls/strip) sit as one centered
 * group with NO gap between the two columns. Each column is its own fixed width
 * so removing the gap actually butts them together (a `flex-1 justify-center`
 * board would instead reintroduce whitespace between the centered board and the
 * side column). */
function renderDesktopLayout(
  botClock: ReactElement,
  userClock: ReactElement,
  board: ReactElement,
  boardControls: ReactElement,
  panel: ReactElement,
): ReactElement {
  return (
    <div className="flex flex-row justify-center gap-2">
      <div
        className="flex w-full flex-col gap-3"
        style={{ maxWidth: BOT_BOARD_MAX_WIDTH_PX }}
      >
        {board}
        {boardControls}
      </div>
      <div
        className="flex shrink-0 flex-col gap-3"
        style={{ width: DESKTOP_SIDE_COLUMN_PX }}
      >
        {botClock}
        {userClock}
        {panel}
      </div>
    </div>
  );
}

interface BotsGameProps {
  /** The snapshot to resume from, or `null` for a fresh setup-started game. */
  resume: BotGameSnapshot | null;
  ownerKey: string | null;
  /** The settings this instance plays with — from the resumed snapshot, or
   * from the setup screen's Start. REQUIRED, no fallback: `BotsGame` is never
   * mounted with placeholder settings (T-171-06-02). */
  settings: BotGameSettings;
  /** SC4: threaded down to the result surfaces' guest caveat — sourced from
   * `BotsPage`'s own `useUserProfile()` call, not a second hook call here. */
  isGuest: boolean;
  /** quick-260714-pnk: the player-side clock caption — resolved by
   * `BotsPage` from its own `useUserProfile()` call (lichess_username ->
   * chess_com_username -> "You"), never a second hook call here. */
  playerName: string;
  /** Discard-confirmed: clears the snapshot and remounts a fresh game
   * (BotsPage's `handleDiscard`, via the `key`-changed remount). */
  onDiscard: () => void;
  /** D-11: "New game" from either result surface returns to the setup
   * screen (unmounting this component) — it does NOT call `game.newGame()`. */
  onNewGame: () => void;
}

/**
 * The actual game body — today's page, minus owner-scope/snapshot-detection
 * concerns (now `BotsPage`'s job). `settings` is supplied by the caller
 * (resumed snapshot or setup screen). `ResumeGate` overlays the board
 * whenever a snapshot is present and the hook has not gone live yet
 * (D-03/D-04): the hook is mounted immediately either way, so its provider
 * bring-up effect warms the engines while the gate is still on screen.
 */
function BotsGame({
  resume,
  ownerKey,
  settings,
  isGuest,
  playerName,
  onDiscard,
  onNewGame,
}: BotsGameProps): ReactElement {
  const navigate = useNavigate();
  const isDesktop = useIsDesktop();
  const muted = useMuted();
  // D-11: `game.newGame` (a public hook API) is intentionally left UNCALLED
  // from this UI — both result surfaces below use `onNewGame` (returns to the
  // setup screen) instead.
  //
  // Correction (Phase 171 code review, WR-03): this comment used to claim
  // "`npm run knip` is the arbiter of whether `newGame` stays exported from
  // the hook". That was FALSE and worth naming: `newGame` is a PROPERTY of the
  // object `useBotGame` returns, not a module export, so knip cannot see it
  // and CI will never flag it. Nothing enforces its removal, and it currently
  // has NO production caller — it is retained as hook API (with its own
  // `useBotGame.test.ts` coverage: book reset, uuid re-mint, live reset,
  // pending-store non-clobber) for a future in-place "rematch" caller. The
  // invariant that this UI never calls it IS enforced, but by Bots.test.tsx
  // (`expect(fakeGame.newGame).not.toHaveBeenCalled()` on both result
  // surfaces), not by a linter.
  const game = useBotGame(settings, resume ?? undefined, ownerKey);
  const [dialogDismissed, setDialogDismissed] = useState(false);
  const hasUnlockedAudioRef = useRef(false);

  // D-21 (the CONTEXT amendment): store the finished game ON FINISH, not
  // deferred to the next `/bots` mount.
  //
  // WHY this exists: `finalizeGame` (useBotGame.ts) only ENQUEUES the
  // finished game into localStorage — the actual POST used to wait for the
  // NEXT `/bots` mount's `useDrainPendingStore` drain (BotsPage, below), so
  // D-20's "Saved to your Library" row had no signal to gate on while the
  // user was still looking at THIS result screen (171-RESEARCH.md
  // Pitfall 3).
  //
  // WHY `useStoreBotGame()` and not `useDrainPendingStore()`: only the
  // former returns a full `UseMutationResult` whose `isSuccess` the result
  // surfaces below can read — the drain hook exposes no per-entry status to
  // its caller.
  //
  // WHY the localStorage queue still exists: it is the offline / 401-retry
  // durability fallback (Phase 170). This effect is an ADDITIONAL store
  // trigger, not a replacement (D-21) — `finalizeGame` remains the ONLY
  // `enqueuePendingStore` call site (170 D-12/SC2 is structural; do not add
  // a second one here).
  //
  // WHY `removePendingStore` on success: it is the double-POST fix. Without
  // it, the next mount's drain would re-POST a game already stored. The
  // server is idempotent on `game_uuid` (167 D-11), so a stray double-POST
  // would be harmless — but harmless is not the bar; D-21 requires it not to
  // happen, and a call-count test pins it (171-07 Task 3, V-15).
  const store = useStoreBotGame();
  const storedGameUuidRef = useRef<string | null>(null);
  useEffect(() => {
    if (game.outcome === null) return;
    if (game.pgn === null) return;
    if (storedGameUuidRef.current === game.gameUuid) return;
    // Latch FIRST, before the async mutate call: a re-render while the
    // mutation is in flight must not double-fire for the same gameUuid.
    storedGameUuidRef.current = game.gameUuid;
    store.mutate(
      toStoreRequest({
        gameUuid: game.gameUuid,
        pgn: game.pgn,
        settings,
        enqueuedAt: Date.now(),
      }),
      { onSuccess: () => removePendingStore(ownerKey, game.gameUuid) },
    );
    // Deliberately depends on `store.mutate` (a stable TanStack Query
    // reference), not the whole `store` object — depending on `store` would
    // re-run this effect on every mutation status transition (pending ->
    // success), which the `storedGameUuidRef` latch guards against anyway
    // but is needless churn.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [game.outcome, game.pgn, game.gameUuid, ownerKey, settings, store.mutate]);

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

  // D-21 RETIRED (Quick 260714-rj5): Analyze now needs the server-assigned
  // game_id from the finish-time store (`store`, above) to enqueue tier-1
  // analysis and land on the game-mode board directly, so it's gated on the
  // store settling — see GameResultDialog/GameResultStrip's analyzeBusy doc
  // comments for the full rationale (this replaces the old "never gated"
  // Phase 169 D-20/D-21 invariant).
  const enqueueTier1 = useTier1EnqueueForGame();
  const storedGameId = store.data?.game_id ?? null;
  // Busy while the store mutation hasn't settled either way yet, OR the
  // tier-1 enqueue triggered by clicking Analyze is itself in flight.
  const analyzeBusy = (!store.isSuccess && !store.isError) || enqueueTier1.isPending;

  const handleAnalyze = useCallback((): void => {
    if (storedGameId === null) {
      // Store exhausted MAX_STORE_RETRIES (see useStoreBotGame.ts) — fall
      // back to the free-play ?line= URL so the user is never stranded
      // without a way to review the game (D-08).
      navigate(buildAnalysisLineUrl(game.moveHistory, settings.userColor));
      return;
    }
    // onSettled (not onSuccess) is deliberate: an enqueue failure still opens
    // the game-mode board with its move list, which beats stranding the user
    // on the result screen. The global MutationCache.onError already reports
    // the failure to Sentry — no second capture here.
    enqueueTier1.mutate(storedGameId, {
      onSettled: () => navigate(buildGameAnalysisUrl(storedGameId)),
    });
  }, [storedGameId, enqueueTier1, navigate, game.moveHistory, settings.userColor]);

  const botColor = settings.userColor === 'white' ? 'black' : 'white';
  // Board orientation defaults to the user's own side facing them, but is now a
  // manual toggle driven by the flip board control (a live-game convenience —
  // it never affects the game itself, only which way the board is drawn).
  const [flipped, setFlipped] = useState(settings.userColor === 'black');
  const handleFlip = useCallback((): void => setFlipped((f) => !f), []);

  // Board-control navigation drives the hook's view-only `viewedPly` cursor
  // (never the live game): reset jumps to the start, back/forward step one ply.
  const { viewedPly, liveGamePly, viewPly } = game;
  const handleBack = useCallback(
    (): void => viewPly(Math.max(0, viewedPly - 1)),
    [viewPly, viewedPly],
  );
  const handleForward = useCallback(
    (): void => viewPly(Math.min(liveGamePly, viewedPly + 1)),
    [viewPly, viewedPly, liveGamePly],
  );
  const handleResetView = useCallback((): void => viewPly(0), [viewPly]);

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
      sideLabel={playerName}
      remainingMs={settings.userColor === 'white' ? game.whiteClockMs : game.blackClockMs}
      isActive={game.activeColor === settings.userColor}
      isThinking={false}
      testId="clock-user"
    />
  );
  const board = (
    <ChessBoard
      position={game.position}
      onPieceDrop={game.attemptMove}
      flipped={flipped}
      lastMove={game.lastMove}
      maxWidth={BOT_BOARD_MAX_WIDTH_PX}
    />
  );
  const boardControls = (
    <BoardControls
      onBack={handleBack}
      onForward={handleForward}
      onReset={handleResetView}
      onFlip={handleFlip}
      canGoBack={viewedPly > 0}
      canGoForward={viewedPly < liveGamePly}
    />
  );
  const panel = (
    <GamePanel
      game={game}
      userColor={settings.userColor}
      muted={muted}
      dialogDismissed={dialogDismissed}
      onToggleMute={handleToggleMute}
      onAnalyze={handleAnalyze}
      onNewGame={onNewGame}
      storeSucceeded={store.isSuccess}
      isGuest={isGuest}
      analyzeBusy={analyzeBusy}
    />
  );

  return (
    <div
      data-testid="bots-page"
      onPointerDown={handleFirstInteraction}
      // Bottom-nav clearance (171 UAT gap 3, Task 1) — same pb-20 sm:pb-4
      // pattern as SetupScreen.tsx's root; see that comment for the full
      // clearance arithmetic.
      className="mx-auto flex max-w-5xl flex-col gap-4 p-4 pb-20 sm:pb-4"
    >
      {isDesktop
        ? renderDesktopLayout(botClock, userClock, board, boardControls, panel)
        : renderMobileLayout(botClock, userClock, board, boardControls, panel)}

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
          onNewGame={onNewGame}
          onAnalyze={handleAnalyze}
          storeSucceeded={store.isSuccess}
          isGuest={isGuest}
          analyzeBusy={analyzeBusy}
        />
      )}
    </div>
  );
}

export default function BotsPage(): ReactElement {
  // WR-08: `isError` is read, not just `isLoading`. A failed profile fetch
  // SETTLES the query (isLoading false, data undefined), so without this the
  // page booted normally with `ownerKey = null` and silently degraded to the
  // shared `…:anon` localStorage bucket: a logged-in user's in-progress
  // resumable game became invisible, and the new game's snapshot + setup
  // settings were written into the anon bucket where the NEXT user of the same
  // browser would find them. The ELO default also silently fell back to 1500,
  // indistinguishable from "no anchor". None of it surfaced to the user.
  const { data: profile, isLoading, isError } = useUserProfile();
  const ownerKey = profile?.email ?? null;
  // SC4: passed down to BotsGame's guest caveat — reads `useUserProfile()`
  // once here rather than a second call in BotsGame.
  const isGuest = profile?.is_guest ?? false;
  // quick-260714-pnk: the player-side clock caption, resolved once here from
  // the single `useUserProfile()` call above (never a second hook call in
  // BotsGame) — lichess_username -> chess_com_username -> "You".
  const playerName = resolvePlayerName(profile);

  const [boot, setBoot] = useState<{ resume: BotGameSnapshot | null; nonce: number } | null>(
    null,
  );
  // Settings chosen at setup (Start) or prefilled after a "New game" reset.
  // `null` means "no started game yet — show the setup screen" whenever
  // `boot.resume` is also null (D-09/D-13: the setup screen is the single
  // entry point for every new game; a snapshot still wins over it, D-04).
  const [startedSettings, setStartedSettings] = useState<BotGameSettings | null>(null);

  // Boot effect: read the snapshot only once the profile has settled
  // (`!isLoading`). Reading it earlier would use the `anon` key (T-170-04's
  // ordering trap) and silently miss a logged-in user's resumable game.
  // `boot === null` also gates the FIRST read only — a later `ownerKey`
  // change (e.g. login completing) does not re-trigger this effect, matching
  // "lazy seed, not a live subscription" (useBotGame's `resume` prop is a
  // lazy initializer, read once at first render).
  // WR-08: `isError` gates this too — booting on a failed profile fetch is
  // exactly the "read the snapshot under the WRONG owner key" trap this effect
  // already guards against for `isLoading`.
  useEffect(() => {
    if (isLoading || isError) return;
    if (boot !== null) return;
    setBoot({ resume: readSnapshot(ownerKey), nonce: 0 });
  }, [isLoading, isError, ownerKey, boot]);

  // D-13: drain the pending-store queue on mount, before/independently of the
  // gate — fires exactly once, after the profile has settled, regardless of
  // whether a gate is shown. Silent in this phase (no UI); fire-and-forget,
  // `drain()` never rethrows.
  const { drain } = useDrainPendingStore(ownerKey);
  const hasDrainedRef = useRef(false);
  useEffect(() => {
    // WR-08: never drain under a fallback `anon` key produced by a failed
    // profile fetch — that would POST (or fail to find) the wrong user's queue.
    if (isLoading || isError) return;
    if (hasDrainedRef.current) return;
    hasDrainedRef.current = true;
    void drain();
  }, [isLoading, isError, drain]);

  // Start (from the setup screen): remembers the chosen settings and bumps
  // `nonce` for a fresh `BotsGame` mount — `useBotGame` initializes with
  // exactly these settings, never with placeholders (T-171-06-02).
  const handleStart = useCallback((settings: BotGameSettings): void => {
    setStartedSettings(settings);
    setBoot((prev) => ({ resume: null, nonce: (prev?.nonce ?? 0) + 1 }));
  }, []);

  // D-11: "New game" from either result surface unmounts `BotsGame` and
  // returns to the setup screen (prefilled from the D-10 key that Start
  // already wrote) — it does NOT restart in place with the same settings.
  const handleNewGame = useCallback((): void => {
    setStartedSettings(null);
    setBoot((prev) => ({ resume: null, nonce: (prev?.nonce ?? 0) + 1 }));
  }, []);

  // D-05: discard clears ONLY the in-progress snapshot (never the
  // pending-store queue — D-12's separate key) and falls through to the
  // setup screen (D-13) rather than auto-starting a fresh game.
  const handleDiscard = useCallback((): void => {
    clearSnapshot(ownerKey);
    setStartedSettings(null);
    setBoot((prev) => ({ resume: null, nonce: (prev?.nonce ?? 0) + 1 }));
  }, [ownerKey]);

  // WR-08: BEFORE the `boot === null` loading branch — on a profile error the
  // boot effect deliberately never runs, so `boot` stays null and this page
  // would otherwise sit on "Loading…" forever. Standard CLAUDE.md error copy.
  if (isError) {
    return (
      <div data-testid="bots-page-error" className="p-4 text-sm text-muted-foreground">
        Failed to load your profile. Something went wrong. Please try again in a moment.
      </div>
    );
  }

  if (boot === null) {
    return (
      <div data-testid="bots-page-loading" className="p-4 text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  // Snapshot beats setup (170 D-04, unchanged): a resumed game always mounts
  // `BotsGame` immediately, with `ResumeGate` overlaid.
  if (boot.resume !== null) {
    return (
      <BotsGame
        key={boot.nonce}
        resume={boot.resume}
        settings={boot.resume.settings}
        ownerKey={ownerKey}
        isGuest={isGuest}
        playerName={playerName}
        onDiscard={handleDiscard}
        onNewGame={handleNewGame}
      />
    );
  }

  if (startedSettings === null) {
    return (
      <SetupScreen
        ownerKey={ownerKey}
        normalizedRating={profile?.lichess_blitz_equivalent_rating ?? null}
        onStart={handleStart}
      />
    );
  }

  return (
    <BotsGame
      key={boot.nonce}
      resume={null}
      settings={startedSettings}
      ownerKey={ownerKey}
      isGuest={isGuest}
      playerName={playerName}
      onDiscard={handleDiscard}
      onNewGame={handleNewGame}
    />
  );
}
