// @vitest-environment jsdom
/**
 * TrainSolveScreen.test.tsx — Phase 190 Plan 04 Task 2/Task 3 coverage:
 * progress indicator (frozen count, not the remaining-array length),
 * last-move highlight, the in-place "Checking your move…" state (exact-match
 * skips it, non-exact shows it, no board flicker across the transition), the
 * engine-failure fallback, and block-and-retry solve persistence (T-190-12).
 *
 * `ChessBoard` is mocked (mirrors Train.solveLoop.test.tsx's precedent) so
 * tests drive `onPieceDrop` directly and read `position`/`flipped`/`lastMove`
 * back via data attributes. Both `useTrainSession` (against a mocked
 * `trainApi`) and `useTrainGradingEngine` (against a fake global `Worker`) run
 * FOR REAL — this exercises the actual block-and-retry gate rather than a
 * hand-stubbed approximation of it.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor, within, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { useEffect, useState } from 'react';
import type { ReactElement } from 'react';
import { Chess } from 'chess.js';
import { TrainSolveScreen } from '@/components/train/TrainSolveScreen';
import { useMobileBoardControls } from '@/lib/mobileBoardControls';
import { TooltipProvider } from '@/components/ui/tooltip';
import { TRAIN_STEP_HIGHLIGHT, TRAIN_STEP_LIVE_ARROW_MIN_DEPTH } from '@/lib/trainArrows';
import { MOVE_TIER_POINTS, scorePuzzle } from '@/lib/trainScore';
import { SETTINGS_STORAGE_KEYS } from '@/lib/engineSettings';
import {
  MOVE_QUALITY_BLUNDER,
  MOVE_QUALITY_GOOD,
  STOCKFISH_SECONDARY_LINE,
  TRAIN_BEST_MOVE_ARROW,
  TRAIN_FOCUS_ARROW_DIM_OPACITY,
  TRAIN_FOCUS_ARROW_LIT_OPACITY,
  TRAIN_FOCUS_BADGE_DIM_OPACITY,
  TRAIN_FOCUS_BADGE_LIT_OPACITY,
} from '@/lib/theme';
import { buildGameAnalysisUrl } from '@/lib/analysisUrl';
import { animateScrollTop } from '@/lib/animatedScroll';
import { HILDA_ID, introStepCount, WALKTHROUGH_STEP_COUNT } from '@/lib/trainBotCopy';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import { useTrainSession } from '@/hooks/useTrainSession';
import {
  TRAIN_RECHECK_MAX_NODES,
  TRAIN_RECHECK_MOVETIME_MS,
  TRAIN_RECHECK_TIMEOUT_MS,
  useTrainGradingEngine,
} from '@/hooks/useTrainGradingEngine';
import type { GradeResult, TrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import { fenAfterUciMove } from '@/hooks/trainGradingSupport';
import { waitForReveal } from './revealTestUtils';
import { readTrainRevealCache, type CachedTrainReveal } from '@/lib/trainRevealCache';
import type {
  ReviewRequest,
  SolveRequest,
  SolveResponse,
  SolvedResult,
  TrainPuzzle,
  TrainSessionResponse,
  TrainSettingsResponse,
} from '@/types/train';

// ─── ResizeObserver stub ────────────────────────────────────────────────────
// jsdom has no ResizeObserver; TrainSolveScreen's useFitBoardToViewport
// observes its board column with one (same per-file stub precedent as
// Bots.test.tsx / Analysis.test.tsx).

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
  ResizeObserverStub;

// ─── matchMedia stub (Phase 200: TrainReveal's useIsDesktop) ──────────────
// Controllable per test (mirrors Bots.test.tsx L221's jsdom shim precedent,
// but with a settable `matches` instead of a fixed `false`) — defaults to
// the desktop path so the pre-existing hover-spotlight coverage below needs
// no per-test override.
let matchMediaMatches = true;
// WR-02: the reveal action bar is mounted once by breakpoint (`useIsSmUp`, 640px):
// the in-flow bar from `sm` up, the published phone bottom-bar payload below it.
// Kept separate from `matchMediaMatches` (the lg desktop gate) so a phone-width
// bubble/strip test does not also flip the action bar; the probe render sets it false.
let smUpMatches = true;
const SM_UP_QUERY = '(min-width: 640px)';
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: query === SM_UP_QUERY ? smUpMatches : matchMediaMatches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// jsdom has no scrollIntoView; the reveal's move list (HorizontalMoveList)
// scrolls the current token into view.
if (typeof Element.prototype.scrollIntoView !== 'function') {
  Element.prototype.scrollIntoView = vi.fn();
}

// ─── Phase 237 focus-dimming readers (over the ChessBoard mock's attributes) ─

/** Every arrow's explicit opacity, in the order of the mock's data-arrow-ucis
 * (a merged role draws two arrows with the same UCI, so the values stay a
 * list per UCI). Dim, never hide: an unfocused move is present with the DIM
 * opacity, not missing. */
function arrowOpacitiesByUci(boardEl: HTMLElement): Record<string, number[]> {
  const ucis = (boardEl.getAttribute('data-arrow-ucis') ?? '').split(',').filter((u) => u !== '');
  const opacities = (boardEl.getAttribute('data-arrow-opacities') ?? '').split(',');
  const out: Record<string, number[]> = {};
  ucis.forEach((uci, i) => {
    (out[uci] ??= []).push(Number(opacities[i]));
  });
  return out;
}

/** Marker opacities in the order the overlay builder pushed them. */
function markerOpacities(boardEl: HTMLElement): number[] {
  return (boardEl.getAttribute('data-marker-opacities') ?? '')
    .split(',')
    .filter((o) => o !== '')
    .map(Number);
}

/** Phase 237 plan 08: on a phone the verdict is a collapsed strip; open it so the
 * expanded details (verdict line, pills, Your-call feedback) are readable. */
async function openVerdictStrip(): Promise<HTMLElement> {
  await waitForReveal();
  const strip = await screen.findByTestId('train-verdict-strip');
  fireEvent.click(strip);
  return screen.getByTestId('train-verdict-strip-details');
}

/** Asserts exactly `lit` UCIs are drawn lit and every other drawn arrow is DIM
 * (all of its arrows, so a merged pair lights together). */
function expectLitArrows(boardEl: HTMLElement, lit: string[]): void {
  const byUci = arrowOpacitiesByUci(boardEl);
  for (const [uci, opacities] of Object.entries(byUci)) {
    const expected = lit.includes(uci) ? TRAIN_FOCUS_ARROW_LIT_OPACITY : TRAIN_FOCUS_ARROW_DIM_OPACITY;
    expect(opacities, `arrow ${uci}`).toEqual(opacities.map(() => expected));
  }
  for (const uci of lit) expect(Object.keys(byUci), `lit arrow ${uci} is drawn`).toContain(uci);
}

/** Phase 237: the reveal's move list replaced the per-card steppers. Taps the
 * move token at `index` (0 = the first move of the focused chip's line). */
function tapListMove(index = 0): void {
  const tokens = screen.getByTestId('train-move-tree').querySelectorAll('[data-testid^="variation-node-"]');
  const token = tokens[index];
  expect(token, `list move ${index}`).toBeDefined();
  fireEvent.click(token!);
}

// ─── ChessBoard mock ────────────────────────────────────────────────────────

vi.mock('@/components/board/ChessBoard', () => ({
  ChessBoard: ({
    position,
    flipped,
    lastMove,
    lastMoveColor,
    onPieceDrop,
    arrows,
    squareMarkers,
  }: {
    position: string;
    flipped?: boolean;
    lastMove?: { from: string; to: string } | null;
    lastMoveColor?: string;
    onPieceDrop: (source: string, target: string) => boolean;
    arrows?: { startSquare: string; endSquare: string; color: string; opacity?: number }[];
    squareMarkers?: { opacity?: number }[];
  }) => (
    <div
      data-testid="chessboard"
      data-position={position}
      data-flipped={flipped ? 'true' : 'false'}
      data-last-move={lastMove ? `${lastMove.from}${lastMove.to}` : ''}
      data-last-move-color={lastMoveColor ?? ''}
      data-arrows-count={String(arrows?.length ?? 0)}
      // Phase 200 UAT round 5: the free-play best-move arrow is only meaningful
      // as a specific move in a specific hue, so the mock exposes both — a bare
      // count can't tell the blue engine pointer from any other single arrow.
      data-arrow-ucis={(arrows ?? []).map((a) => `${a.startSquare}${a.endSquare}`).join(',')}
      data-arrow-colors={(arrows ?? []).map((a) => a.color).join(',')}
      data-markers-count={String(squareMarkers?.length ?? 0)}
      // Phase 237: the focus dimming is an opacity on each arrow/badge, so the
      // mock exposes them in the same order as data-arrow-ucis (empty string =
      // no explicit opacity).
      data-arrow-opacities={(arrows ?? []).map((a) => (a.opacity === undefined ? '' : String(a.opacity))).join(',')}
      data-marker-opacities={(squareMarkers ?? []).map((m) => (m.opacity === undefined ? '' : String(m.opacity))).join(',')}
    >
      <button data-testid="drop-e2e4" onClick={() => onPieceDrop('e2', 'e4')}>
        e2e4
      </button>
      <button data-testid="drop-d2d4" onClick={() => onPieceDrop('d2', 'd4')}>
        d2d4
      </button>
      {/* Phase 200 (D-12): a black-move drop, needed to prove exploration
          follows the live side to move rather than pinning to white. */}
      <button data-testid="drop-e7e5" onClick={() => onPieceDrop('e7', 'e5')}>
        e7e5
      </button>
      {/* Phase 200 UAT: a SECOND black move, so a test can jump back and play a
          divergent continuation — the fork the analysis move tree must keep. */}
      <button data-testid="drop-d7d5" onClick={() => onPieceDrop('d7', 'd5')}>
        d7d5
      </button>
      {/* Phase 205 (D-04): a THIRD white first move (Nc3), legal from the
          starting position but deliberately outside every mount-search rank
          the ScriptedFenFakeWorker below ever returns (e2e4/d2d4/g1f3/c2c4)
          — needed to exercise the D-04 residual (an unranked root move
          stays on today's cross-oracle path). */}
      <button data-testid="drop-b1c3" onClick={() => onPieceDrop('b1', 'c3')}>
        b1c3
      </button>
      {/* Phase 235 (D-19): the sharp runner-up c2c4 of the re-check tests. */}
      <button data-testid="drop-c2c4" onClick={() => onPieceDrop('c2', 'c4')}>
        c2c4
      </button>
    </div>
  ),
}));

// ─── trainApi mock ──────────────────────────────────────────────────────────

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

const composeOrResumeSession = vi.fn<() => Promise<TrainSessionResponse>>();
const solvePuzzle = vi.fn<(sessionId: number, body: SolveRequest) => Promise<SolveResponse>>();
// Phase 222 (D-12): exposed at module scope so individual tests can override
// `intro_seen_at` — defaults to "already seen" (a past timestamp) so every
// PRE-EXISTING test in this file (none of which expects the intro stepper)
// keeps seeing the regular prompt immediately, matching today's behavior.
const getSettings = vi.fn<() => Promise<TrainSettingsResponse>>();
function makeSettings(overrides: Partial<TrainSettingsResponse> = {}): TrainSettingsResponse {
  return {
    timezone: 'UTC',
    weekday_mask: 127,
    puzzles_per_session: 5,
    reminder_enabled: false,
    reminder_hour: 9,
    reminder_intent_at: null,
    intro_seen_at: '2026-01-01T00:00:00Z',
    reveal_walkthrough_seen_at: '2026-01-01T00:00:00Z',
    sr_explained_at: '2026-01-01T00:00:00Z',
    has_mobile_subscription: false,
    ...overrides,
  };
}

// Phase 222 (D-12): the onboarding stamp mutation's mock — asserted on by the
// intro-stepper tests below.
const stampOnboarding = vi.fn(async () => makeSettings({ intro_seen_at: '2026-06-01T00:00:00Z' }));

// Phase 233 (D-06): every review flush goes through the keepalive transport
// (Next too, since the 233 review fix WR-02). The mock below splits it by the
// body's `exit`: nextFlush is the Next path, exitFlush every non-Next exit. A
// factory without the transport would throw inside the deferred unmount flush.
const exitFlush = vi.fn<(sessionId: number, position: number, body: ReviewRequest) => void>();
const nextFlush = vi.fn<(sessionId: number, position: number, body: ReviewRequest) => void>();

// 190-05/190.1-01: TrainReveal (mounted here once a verdict lands) fires its
// own reveal/game-card/tactic-lines queries. Exposed at module scope (rather
// than inlined in the mock factory) so individual tests can override the
// default fixture via `mockResolvedValueOnce` — e.g. the 190.1-01 game-move-
// box test below needs a non-null `played_in_game_move_uci`.
const revealPuzzle = vi.fn(async () => ({
  game_id: 100,
  ply: 20,
  fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  played_in_game_san: null,
  played_in_game_move_uci: null,
  puzzle_type: 'sharp' as const,
  source: 'sr_item' as const,
  has_tactic_lines: false,
}));

// Mocked to resolve/reject deterministically so this file's pre-existing
// assertions never depend on a real network call (libraryApi.getGame /
// getTacticLines would otherwise hit the real apiClient).
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      composeOrResumeSession: () => composeOrResumeSession(),
      solvePuzzle: (sessionId: number, body: SolveRequest) => solvePuzzle(sessionId, body),
      revealPuzzle: () => revealPuzzle(),
      getSettings: () => getSettings(),
      updateSettings: vi.fn(),
      stampOnboarding: (step: string) => stampOnboarding(step),
    },
    postReviewKeepalive: (sessionId: number, position: number, body: ReviewRequest) =>
      (body.exit === 'next' ? nextFlush : exitFlush)(sessionId, position, body),
    libraryApi: {
      ...actual.libraryApi,
      getGame: vi.fn().mockRejectedValue(new Error('not needed for this test file')),
      getTacticLines: vi.fn().mockRejectedValue(new Error('not needed for this test file')),
    },
  };
});

// ─── sounds mock ────────────────────────────────────────────────────────────

// 190.1 UAT round 4: reveal-line stepping plays sounds and the button row
// carries the shared mute toggle — mocked (same approach as useBotGame.test)
// so jsdom never touches real Audio machinery. `unlockAudio` (Quick 260805-p37)
// added once useAnalysisBoard/useTrainRevealTree started calling it on every
// gesture-driven command — free play on this screen wraps that hook.
const mockSetMuted = vi.fn();
vi.mock('@/lib/animatedScroll', () => ({
  animateScrollTop: vi.fn(),
}));

vi.mock('@/lib/sounds', () => ({
  playSound: vi.fn(),
  unlockAudio: vi.fn(),
  useMuted: () => false,
  setMuted: (muted: boolean) => mockSetMuted(muted),
}));

// ─── Fake Worker ────────────────────────────────────────────────────────────

// 190.1-02: tracks the width from the last `setoption name MultiPV value N`
// message and emits one `info ... multipv K ...` line per requested rank on
// a mount search, still emitting a single rank for width-1 searches (the
// after-move/reveal-time searches).
/** Search depth every FakeWorker reports unless a test overrides it. Kept BELOW
 * TRAIN_STEP_LIVE_ARROW_MIN_DEPTH so stepped positions stay line-arrow-only. */
const FAKE_WORKER_DEFAULT_DEPTH = 10;

class FakeWorker {
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  private width = 1;
  // Phase 200 (EXPLORE-05): public so teardown is directly assertable —
  // flipped true by terminate() below, never reset back to false.
  terminated = false;

  /** `pv` defaults to the bare best move; the 190.1 UAT stepping test hands
   * in a longer line so the reveal stepper has something to step through. */
  constructor(
    private bestMove = 'e2e4',
    private pv = bestMove,
    private depth = FAKE_WORKER_DEFAULT_DEPTH,
  ) {}

  postMessage(msg: string | { progressPort: unknown }): void {
    // Phase 213: useStockfishEngine now also hands the worker a
    // `{ progressPort }` MessageChannel port before the 'uci' handshake —
    // this fake has no progress-reporting to simulate, so it just ignores
    // any non-string payload.
    if (typeof msg !== 'string') return;
    if (msg === 'uci') {
      this.emit('uciok');
    } else if (msg === 'isready') {
      this.emit('readyok');
    } else if (msg.startsWith('setoption name MultiPV value ')) {
      const width = parseInt(msg.slice('setoption name MultiPV value '.length), 10);
      this.width = Number.isFinite(width) && width > 0 ? width : 1;
    } else if (msg.startsWith('go ')) {
      queueMicrotask(() => {
        for (let rank = 1; rank <= this.width; rank++) {
          this.emit(`info depth ${this.depth} multipv ${rank} score cp ${this.cpFor(rank)} nodes 1000 pv ${this.pv}`);
        }
        this.emit(`bestmove ${this.bestMove}`);
      });
    }
  }

  terminate(): void {
    this.terminated = true;
  }

  /** Side-to-move centipawns reported for `rank`; subclasses script other readings. */
  protected cpFor(rank: number): number {
    return 20 - rank;
  }

  private emit(data: string): void {
    this.onmessage?.(new MessageEvent('message', { data }));
  }
}

/**
 * Phase 235 (D-20): a FakeWorker that HOLDS the reply to any disagreement
 * re-check search (`go movetime ${TRAIN_RECHECK_MOVETIME_MS} `) until
 * `release()` is called, so a test can observe the wait or let it time out.
 * Real Stockfish answers a `stop` with a bestmove, so held replies are also
 * released on `stop` (that is how the dispatch queue drains after a timeout).
 */
class GatedRecheckWorker extends FakeWorker {
  private heldGo: string[] = [];

  postMessage(msg: string | { progressPort: unknown }): void {
    if (typeof msg === 'string') {
      if (msg.startsWith(`go movetime ${TRAIN_RECHECK_MOVETIME_MS} `)) {
        this.heldGo.push(msg);
        return;
      }
      if (msg === 'stop') this.release();
    }
    super.postMessage(msg);
  }

  /** Number of re-check searches currently held. */
  get heldCount(): number {
    return this.heldGo.length;
  }

  release(): void {
    const held = this.heldGo;
    this.heldGo = [];
    for (const go of held) super.postMessage(go);
  }
}

/**
 * Phase 236 (D-12, Pitfall 1): a FakeWorker that HOLDS the reply to any search
 * started on `heldFen` until `release()` is called, so a test can observe the
 * instant path while its after-played background search is still running.
 * Matches on the searched FEN, not the movetime (the mount budget equals the
 * grading budget). A `stop` releases held replies first (real Stockfish answers
 * a stop with a bestmove); `stopsWhileHeld` counts the stops that arrived while
 * a search was held, which is exactly what plan 04's serialization must keep at 0.
 */
class HeldPositionWorker extends FakeWorker {
  private lastPosition = '';
  private heldGo: string[] = [];
  stopsWhileHeld = 0;

  constructor(private heldFen: string) {
    super('d7d5', 'd7d5');
  }

  postMessage(msg: string | { progressPort: unknown }): void {
    if (typeof msg === 'string') {
      if (msg.startsWith('position ')) this.lastPosition = msg;
      if (msg.startsWith('go ') && this.lastPosition.includes(this.heldFen)) {
        this.heldGo.push(msg);
        return;
      }
      if (msg === 'stop') {
        if (this.heldGo.length > 0) this.stopsWhileHeld += 1;
        this.release();
      }
    }
    super.postMessage(msg);
  }

  /** Number of searches currently held. */
  get heldCount(): number {
    return this.heldGo.length;
  }

  release(): void {
    const held = this.heldGo;
    this.heldGo = [];
    for (const go of held) super.postMessage(go);
  }
}

/**
 * Phase 237 plan 06 (SOLV-02): a FakeWorker that records every string message it
 * receives, so a test can prove which Workers were (not) asked to search.
 */
class RecordingFakeWorker extends FakeWorker {
  messages: string[] = [];

  postMessage(msg: string | { progressPort: unknown }): void {
    if (typeof msg === 'string') this.messages.push(msg);
    super.postMessage(msg);
  }

  /** Number of `go ...` searches this Worker has been asked to run. */
  get goCount(): number {
    return this.messages.filter((m) => m.startsWith('go ')).length;
  }
}

/** Release every HeldPositionWorker `stubWorker` handed out. */
function releaseHeldWorkers(): void {
  for (const instance of stubbedWorkerInstances) {
    if (instance instanceof HeldPositionWorker) instance.release();
  }
}

/**
 * Quick 261008-ob1: a FakeWorker whose reading depends on the searched position
 * and the search budget. `cpAt` receives the last `position fen ...` and the
 * `go ...` message and returns the side-to-move cp, or null for the default.
 */
class ScriptedCpWorker extends FakeWorker {
  private lastPosition = '';
  private lastGo = '';

  constructor(private cpAt: (position: string, go: string) => number | null) {
    super('d7d5', 'd7d5');
  }

  postMessage(msg: string | { progressPort: unknown }): void {
    if (typeof msg === 'string') {
      if (msg.startsWith('position ')) this.lastPosition = msg;
      if (msg.startsWith('go ')) this.lastGo = msg;
    }
    super.postMessage(msg);
  }

  protected cpFor(rank: number): number {
    return this.cpAt(this.lastPosition, this.lastGo) ?? super.cpFor(rank);
  }
}

/** Never responds to the UCI handshake — isReady never becomes true and the
 * worker never errors either; used only alongside fake timers for the
 * readiness-timeout path. */
class HangingWorker {
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  postMessage(): void {
    /* never responds */
  }
  terminate(): void {}
}

/** Fails the UCI handshake immediately via the Worker's onerror path. */
class FailingWorker {
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  postMessage(msg: string): void {
    if (msg === 'uci') {
      queueMicrotask(() => this.onerror?.(new Event('error')));
    }
  }
  terminate(): void {}
}

interface StubbedWorker {
  onmessage: unknown;
  onerror: unknown;
  postMessage: unknown;
  terminate: unknown;
  /** Phase 200 (EXPLORE-05): present on `FakeWorker`, absent on the
   * `HangingWorker`/`FailingWorker` fixtures that never reach teardown tests. */
  terminated?: boolean;
}

// Phase 200 (EXPLORE-05): every Worker instance `stubWorker`'s factory hands
// out, in construction order — lets a test assert instance COUNT (one
// grading engine vs. a second, distinct exploration engine) and each
// instance's own `terminated` flag. Reset in `beforeEach` below.
let stubbedWorkerInstances: StubbedWorker[] = [];

function stubWorker(factory: () => StubbedWorker): void {
  vi.stubGlobal(
    'Worker',
    vi.fn(function (this: unknown) {
      const instance = factory();
      stubbedWorkerInstances.push(instance);
      return instance;
    }),
  );
}

// ─── Fixtures ───────────────────────────────────────────────────────────────

function makePuzzle(overrides: Partial<TrainPuzzle> = {}): TrainPuzzle {
  return {
    position: 1,
    game_id: 100,
    ply: 20,
    fen: START_FEN,
    side_to_move: 'white',
    last_move_uci: 'd7d5',
    ...overrides,
  };
}

const SOLVE_RESPONSE: SolveResponse = {
  correct_guess: true,
  correct_move: true,
  move_quality: 'good',
  puzzle_type: 'sharp',
  item_status: 'active',
  streak: 1,
  due_date: '2026-07-28',
  session_complete: false,
};

function makeSolvedResult(overrides: Partial<SolvedResult> = {}): SolvedResult {
  return {
    correct_guess: true,
    move_quality: 'good',
    source: 'sr_item',
    item_status: 'active',
    due_date: '2026-07-28',
    ...overrides,
  };
}

function makeSession(overrides: Partial<TrainSessionResponse> = {}): TrainSessionResponse {
  return {
    session_id: 1,
    session_date: '2026-07-25',
    expires_on: '2026-07-26',
    puzzle_count: 5,
    requested_count: 5,
    solved_count: 0,
    blob_pending_count: 0,
    puzzles: [],
    solved_results: [],
    is_warmup: false,
    ...overrides,
  };
}

// ─── Harness: mounts the REAL hooks against the mocked trainApi + fake Worker ─

function Harness({
  puzzle,
  restoredSolve = null,
  gradeMoveOverride,
}: {
  puzzle: TrainPuzzle;
  /** Phase 236: replaces the real engine's `gradeMove` (the real engine still
   * drives startGrading and the reveal search), to script background-grade outcomes. */
  gradeMoveOverride?: TrainGradingEngine['gradeMove'];
  /** Phase 205 Task 2 (D-10): pass-through to TrainSolveScreen's own prop,
   * defaulting to today's behavior so every pre-existing test (none of which
   * passes this) is unaffected. */
  restoredSolve?: CachedTrainReveal | null;
}): ReactElement {
  const trainSession = useTrainSession();
  const realEngine = useTrainGradingEngine({ enabled: true });
  const gradingEngine: TrainGradingEngine =
    gradeMoveOverride === undefined ? realEngine : { ...realEngine, gradeMove: gradeMoveOverride };
  const { startSession } = trainSession;
  useEffect(() => {
    startSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <TrainSolveScreen
      puzzle={puzzle}
      trainSession={trainSession}
      gradingEngine={gradingEngine}
      restoredSolve={restoredSolve}
      hasGames={true}
      isGuest={false}
    />
  );
}

// Phase 200 UAT round 7: the same harness, but the SOLVE SCREEN can be
// unmounted and remounted (with the next session's first puzzle) while
// `useTrainSession` — and therefore its solve mutation, holding the last
// verdict — stays alive above it. That is exactly the shape of a dev-clock
// time jump: `Train.tsx`'s `returnToLanding` drops back to the landing screen,
// a NEW session is composed, and pressing Start remounts this component.
// Deliberately does NOT call `resetSolve` on the toggle, so the test pins
// TrainSolveScreen's own mount guard rather than Train.tsx's cleanup.
function RemountHarness({
  puzzle,
  nextPuzzle,
}: {
  puzzle: TrainPuzzle;
  nextPuzzle: TrainPuzzle;
}): ReactElement {
  const trainSession = useTrainSession();
  const gradingEngine = useTrainGradingEngine({ enabled: true });
  const [visible, setVisible] = useState(true);
  const [remounted, setRemounted] = useState(false);
  const { startSession } = trainSession;
  useEffect(() => {
    startSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <>
      <button
        data-testid="toggle-loop"
        onClick={() => {
          setVisible((v) => !v);
          if (visible) setRemounted(true);
        }}
      >
        toggle
      </button>
      {visible && (
        <TrainSolveScreen
          puzzle={remounted ? nextPuzzle : puzzle}
          trainSession={trainSession}
          gradingEngine={gradingEngine}
          hasGames={true}
          isGuest={false}
        />
      )}
    </>
  );
}

async function renderScreen(
  puzzle: TrainPuzzle,
  session: TrainSessionResponse = makeSession(),
  restoredSolve: CachedTrainReveal | null = null,
  gradeMoveOverride?: TrainGradingEngine['gradeMove'],
) {
  composeOrResumeSession.mockResolvedValue(session);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const result = render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <Harness puzzle={puzzle} restoredSolve={restoredSolve} gradeMoveOverride={gradeMoveOverride} />
        </TooltipProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());
  return result;
}

// Quick 260809-g0n: reads the published mobileBoardControls payload (or its
// absence) via testids/buttons, so a test can assert on the store the same
// way MobileBottomBar itself would consume it.
function MobileBoardControlsProbe(): ReactElement {
  const controls = useMobileBoardControls();
  return (
    <div data-testid="mbc-probe" data-published={controls ? 'true' : 'false'}>
      {controls && (
        <>
          <span data-testid="mbc-can-go-back">{String(controls.canGoBack)}</span>
          <span data-testid="mbc-can-go-forward">{String(controls.canGoForward)}</span>
          <span data-testid="mbc-can-reset">{String(controls.canReset)}</span>
          <span data-testid="mbc-has-next">{String(controls.onNext != null)}</span>
          <span data-testid="mbc-analyze-to">{String(controls.analyzeTo)}</span>
          <button data-testid="mbc-btn-next" onClick={controls.onNext}>next</button>
          <button data-testid="mbc-btn-back" onClick={controls.onBack}>back</button>
          <button data-testid="mbc-btn-forward" onClick={controls.onForward}>forward</button>
          <button data-testid="mbc-btn-reset" onClick={controls.onReset}>reset</button>
          <button data-testid="mbc-btn-flip" onClick={controls.onFlip}>flip</button>
        </>
      )}
    </div>
  );
}

// Same MemoryRouter/QueryClientProvider/TooltipProvider/Harness harness as
// `renderScreen`, with the probe mounted alongside — proves the store is
// truly cross-tree (Harness and the probe are siblings, exactly like
// TrainSolveScreen and MobileBottomBar are in the real App tree).
async function renderScreenWithProbe(
  puzzle: TrainPuzzle,
  session: TrainSessionResponse = makeSession(),
) {
  // Below `sm` the fixed phone bar (fed by the published payload) is the only bar.
  smUpMatches = false;
  composeOrResumeSession.mockResolvedValue(session);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const result = render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <MobileBoardControlsProbe />
          <Harness puzzle={puzzle} />
        </TooltipProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());
  return result;
}

describe('TrainSolveScreen — progress, last move, grading state, engine failure, solve retry', () => {
  beforeEach(() => {
    matchMediaMatches = true; // desktop by default — see the module-scope stub
    smUpMatches = true;
    stubbedWorkerInstances = [];
    stubWorker(() => new FakeWorker());
    composeOrResumeSession.mockReset();
    solvePuzzle.mockReset();
    solvePuzzle.mockResolvedValue(SOLVE_RESPONSE);
    revealPuzzle.mockClear();
    getSettings.mockReset();
    getSettings.mockResolvedValue(makeSettings());
    stampOnboarding.mockClear();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    localStorage.removeItem(SETTINGS_STORAGE_KEYS.sfArrows);
    localStorage.removeItem(SETTINGS_STORAGE_KEYS.sfLines);
  });

  it('progress: shows "i of N" using the FROZEN session puzzle_count, not puzzles.length', async () => {
    // solved_count seeds currentIndex=2 (Pitfall 5); puzzles stays empty on
    // purpose — the denominator must come from puzzle_count (12), never
    // puzzles.length (0 here).
    await renderScreen(makePuzzle(), makeSession({ puzzle_count: 12, solved_count: 2 }));
    expect(screen.getByTestId('train-progress').textContent).toBe('3 of 12');
  });

  it('progress bar: fill width reflects the completed fraction for a mid-session puzzle', async () => {
    await renderScreen(makePuzzle(), makeSession({ puzzle_count: 12, solved_count: 3 }));
    const fill = screen.getByTestId('train-progress-bar').firstElementChild as HTMLElement;
    // i=4, N=12 -> completed fraction (i-1)/N = 3/12 = 25%.
    expect(fill.style.width).toBe('25%');
  });

  it('orientation: flipped for a black-to-move puzzle, not flipped for white', async () => {
    await renderScreen(makePuzzle({ side_to_move: 'black' }));
    expect(screen.getByTestId('chessboard').getAttribute('data-flipped')).toBe('true');
  });

  it('orientation: white-to-move puzzle is not flipped', async () => {
    await renderScreen(makePuzzle({ side_to_move: 'white' }));
    expect(screen.getByTestId('chessboard').getAttribute('data-flipped')).toBe('false');
  });

  it('last-move highlight: derived from the arriving-move UCI', async () => {
    await renderScreen(makePuzzle({ last_move_uci: 'd7d5' }));
    expect(screen.getByTestId('chessboard').getAttribute('data-last-move')).toBe('d7d5');
  });

  it('last-move highlight: a null arriving move renders no highlight', async () => {
    await renderScreen(makePuzzle({ last_move_uci: null }));
    expect(screen.getByTestId('chessboard').getAttribute('data-last-move')).toBe('');
  });

  it('exact-match move never shows the checking indicator', async () => {
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // matches FakeWorker's default bestmove
    });
    await waitForReveal();
    expect(screen.queryByTestId('train-grading-indicator')).toBeNull();
  });

  it('non-exact move shows the checking indicator before the verdict', async () => {
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    fireEvent.click(screen.getByTestId('drop-d2d4')); // does not match bestmove e2e4 -> second search
    await waitFor(() => expect(screen.getByTestId('train-grading-indicator')).not.toBeNull());
    await waitForReveal();
  });

  it('keyed puzzle: grades against the server key and the best arrow names it (Phase 235)', async () => {
    // The phone's own search would answer d7d5 for every position, and every
    // search reads cp 19 (black POV) after a white move, so the after-key and
    // after-e2e4 readings are identical: drop 0, GOOD. The key d2d4 is NOT any
    // move the FakeWorker ever names as bestmove for the root position.
    stubWorker(() => new FakeWorker('d7d5', 'd7d5'));
    await renderScreen(
      makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'soft', runner_up_uci: null }),
    );
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    expect(solvePuzzle.mock.calls[0]?.[1].move_quality).toBe('good');

    // The reveal's best arrow names the server key, in the best-move color.
    const board = () => screen.getByTestId('chessboard');
    await waitFor(() => {
      const ucis = (board().getAttribute('data-arrow-ucis') ?? '').split(',');
      // Colors are rgba(...) strings that contain commas, so split only on commas outside parentheses.
      const colors = (board().getAttribute('data-arrow-colors') ?? '').split(/,(?![^()]*\))/);
      const keyIndex = ucis.indexOf('d2d4');
      expect(keyIndex).toBeGreaterThanOrEqual(0);
      expect(colors[keyIndex]).toBe(TRAIN_BEST_MOVE_ARROW);
    });
  });

  it('keyed puzzle: an off-key move POSTs the 1.5 s phone_grade record (Phase 236 D-01/D-13)', async () => {
    stubWorker(() => new FakeWorker('d7d5', 'd7d5'));
    await renderScreen(
      makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'soft', runner_up_uci: null }),
    );
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    const body = solvePuzzle.mock.calls[0]?.[1];
    expect(body?.phone_grade).toMatchObject({
      v: 1,
      tier: body?.move_quality,
      key_depth: 10,
      played_depth: 10,
    });
    for (const es of [body?.phone_grade?.key_es, body?.phone_grade?.played_es]) {
      expect(typeof es).toBe('number');
      expect(es).toBeGreaterThanOrEqual(0);
      expect(es).toBeLessThanOrEqual(1);
    }
  });

  it('sharp keyed puzzle: an off-key good move is re-checked and the POST carries the record (Phase 235 D-10/D-11/D-17)', async () => {
    // FakeWorker answers every search with the same depth-10 reading, so the
    // 1.5 s pair grades GOOD, the sharp trigger fires, and both 3 s re-check
    // searches answer at depth 10 too (proving they really ran).
    const postSpy = vi.spyOn(FakeWorker.prototype, 'postMessage');
    try {
      stubWorker(() => new FakeWorker('d7d5', 'd7d5'));
      await renderScreen(
        makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'sharp', runner_up_uci: 'c2c4' }),
      );
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitForReveal();

      expect(solvePuzzle).toHaveBeenCalledTimes(1);
      const body = solvePuzzle.mock.calls[0]?.[1];
      expect(body?.move_quality).toBe('good');
      expect(body?.recheck).toMatchObject({
        v: 1,
        outcome: 'confirmed',
        key_depth_recheck: 10,
        played_depth_recheck: 10,
      });

      const recheckGo = `go movetime ${TRAIN_RECHECK_MOVETIME_MS} nodes ${TRAIN_RECHECK_MAX_NODES}`;
      const recheckPosts = postSpy.mock.calls.filter(([msg]) => msg === recheckGo);
      expect(recheckPosts).toHaveLength(2);
    } finally {
      postSpy.mockRestore();
    }
  });

  it('playing the sharp runner-up posts no recheck (D-19)', async () => {
    const postSpy = vi.spyOn(FakeWorker.prototype, 'postMessage');
    try {
      stubWorker(() => new FakeWorker('d7d5', 'd7d5'));
      await renderScreen(
        makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'sharp', runner_up_uci: 'c2c4' }),
      );
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-c2c4'));
      });
      await waitForReveal();

      expect(solvePuzzle).toHaveBeenCalledTimes(1);
      expect(solvePuzzle.mock.calls[0]?.[1]).not.toHaveProperty('recheck');
      expect(
        postSpy.mock.calls.filter(([msg]) => typeof msg === 'string' && msg.includes('movetime 3000')),
      ).toHaveLength(0);
    } finally {
      postSpy.mockRestore();
    }
  });

  it('a soft keyed puzzle posts no recheck (D-10)', async () => {
    stubWorker(() => new FakeWorker('d7d5', 'd7d5'));
    await renderScreen(
      makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'soft', runner_up_uci: 'c2c4' }),
    );
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    expect(solvePuzzle.mock.calls[0]?.[1]).not.toHaveProperty('recheck');
  });

  // Quick 261008-ob1: the 1.5 s search under-reads the played move (black to
  // move after 1.e4 reads +90 for black: a ~0.06 ES drop against the key's +19,
  // an inaccuracy). Every other search, the key and the 3 s searches, reads the
  // default +19 unless `slowPlayedCp` overrides the 3 s played reading.
  const AFTER_E2E4_BOARD = '/4P3/';
  const FAST_PLAYED_CP = 90;
  function underReadPlayedWorker(slowPlayedCp: number | null): ScriptedCpWorker {
    return new ScriptedCpWorker((position, go) => {
      if (!position.includes(AFTER_E2E4_BOARD)) return null;
      return go.startsWith(`go movetime ${TRAIN_RECHECK_MOVETIME_MS} `)
        ? slowPlayedCp
        : FAST_PLAYED_CP;
    });
  }

  it('an off-key inaccuracy on a soft puzzle is re-checked and upgraded to good (quick 261008-ob1)', async () => {
    stubWorker(() => underReadPlayedWorker(null));
    await renderScreen(
      makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'soft', runner_up_uci: null }),
    );
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    const body = solvePuzzle.mock.calls[0]?.[1];
    expect(body?.move_quality).toBe('good');
    expect(body?.recheck).toMatchObject({ v: 1, outcome: 'confirmed' });
    // The 1.5 s pair in the record still reads the inaccuracy that triggered it.
    expect((body?.recheck?.key_es ?? 0) - (body?.recheck?.played_es ?? 0)).toBeGreaterThan(0.05);
  });

  it('an off-key inaccuracy the 3 s pair still reads as inaccuracy stays inaccuracy (quick 261008-ob1)', async () => {
    stubWorker(() => underReadPlayedWorker(FAST_PLAYED_CP));
    await renderScreen(
      makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'soft', runner_up_uci: null }),
    );
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    const body = solvePuzzle.mock.calls[0]?.[1];
    expect(body?.move_quality).toBe('inaccuracy');
    expect(body?.recheck).toMatchObject({ v: 1, outcome: 'resolved' });
  });

  it('keyed puzzle: playing the key POSTs phone_grade good with played == key (Phase 236 D-05)', async () => {
    stubWorker(() => new FakeWorker('d7d5', 'd7d5'));
    await renderScreen(
      makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'soft', runner_up_uci: null }),
    );
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4'));
    });
    await waitForReveal();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    const phoneGrade = solvePuzzle.mock.calls[0]?.[1].phone_grade;
    expect(phoneGrade?.tier).toBe('good');
    expect(phoneGrade?.played_es).toBe(phoneGrade?.key_es);
    expect(phoneGrade?.key_depth).toBe(10);
    expect(phoneGrade?.played_depth).toBe(phoneGrade?.key_depth);
  });

  it('legacy no-key puzzle: the POST carries no phone_grade (Phase 236 D-06)', async () => {
    stubWorker(() => new FakeWorker('d7d5', 'd7d5'));
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    expect(solvePuzzle.mock.calls[0]?.[1]).not.toHaveProperty('phone_grade');
  });

  it('a re-check replaces the grade but phone_grade keeps the 1.5 s reading (Phase 236 D-04)', async () => {
    stubWorker(() => underReadPlayedWorker(null));
    await renderScreen(
      makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'soft', runner_up_uci: null }),
    );
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    const body = solvePuzzle.mock.calls[0]?.[1];
    expect(body?.move_quality).toBe('good');
    expect(body?.recheck?.outcome).toBe('confirmed');
    // The record is the 1.5 s reading, whose tier differs from the final grade.
    expect(body?.phone_grade?.tier).toBe('inaccuracy');
    expect(body?.phone_grade?.key_es).toBe(body?.recheck?.key_es);
    expect(body?.phone_grade?.played_es).toBe(body?.recheck?.played_es);
  });

  it('a retried keyed solve re-sends the identical payload, phone_grade included (Phase 236 D-13)', async () => {
    solvePuzzle.mockRejectedValueOnce(new Error('network down'));
    stubWorker(() => new FakeWorker('d7d5', 'd7d5'));
    await renderScreen(
      makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'soft', runner_up_uci: null }),
    );
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.getByTestId('train-solve-error')).not.toBeNull());

    fireEvent.click(screen.getByTestId('btn-train-solve-retry'));
    await waitForReveal();

    expect(solvePuzzle).toHaveBeenCalledTimes(2);
    const first = solvePuzzle.mock.calls[0]?.[1];
    expect(first?.phone_grade).toBeDefined();
    expect(solvePuzzle.mock.calls[1]?.[1]).toEqual(first);
  });

  it('a server-graded move is never re-checked: no 3 s search, no recheck in the body (Phase 236 D-11)', async () => {
    // The 1.5 s pair reads the played move as an inaccuracy, which would
    // trigger a re-check were e2e4 not in the puzzle's server-graded set.
    const postSpy = vi.spyOn(FakeWorker.prototype, 'postMessage');
    try {
      stubWorker(() => underReadPlayedWorker(null));
      await renderScreen(
        makePuzzle({
          key_move_uci: 'd2d4',
          puzzle_type: 'soft',
          runner_up_uci: null,
          server_graded_moves: [
            { uci: 'd2d4', tier: 'good' },
            { uci: 'e2e4', tier: 'inaccuracy' },
          ],
        }),
      );
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitForReveal();

      expect(solvePuzzle).toHaveBeenCalledTimes(1);
      const body = solvePuzzle.mock.calls[0]?.[1];
      expect(body?.move_quality).toBe('inaccuracy');
      expect(body).not.toHaveProperty('recheck');
      expect(
        postSpy.mock.calls.filter(([msg]) => typeof msg === 'string' && msg.includes('movetime 3000')),
      ).toHaveLength(0);
    } finally {
      postSpy.mockRestore();
    }
  });

  it('a stalled re-check falls back to the 1.5 s grade and posts no recheck (D-20)', async () => {
    let gated: GatedRecheckWorker | null = null;
    stubWorker(() => {
      gated = new GatedRecheckWorker('d7d5', 'd7d5');
      return gated;
    });
    await renderScreen(
      makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'sharp', runner_up_uci: 'c2c4' }),
    );
    // Only timeouts are faked, and only once the screen is up. RTL's waitFor
    // must not be used while they are (its drain step waits on a faked
    // setTimeout); the FakeWorker answers in microtasks, so flushing them is enough.
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
      await vi.advanceTimersByTimeAsync(0);
    });
    // The first re-check search is held: the POST has not happened yet, and the
    // bubble explains the wait (D-12) instead of "Checking your move…".
    expect((gated as GatedRecheckWorker | null)?.heldCount).toBe(1);
    expect(solvePuzzle).not.toHaveBeenCalled();
    expect(screen.getByTestId('train-recheck-indicator').textContent).toBe('Taking a closer look…');
    expect(screen.queryByTestId('train-grading-indicator')).toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(TRAIN_RECHECK_TIMEOUT_MS);
    });
    // D-20 on screen: the wait copy is gone once the stalled re-check times out
    // and the verdict renders from the 1.5 s grade.
    expect(screen.queryByTestId('train-recheck-indicator')).toBeNull();
    expect(screen.queryByTestId('train-grading-indicator')).toBeNull();
    expect(screen.getByTestId('train-reveal')).not.toBeNull();
    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    const body = solvePuzzle.mock.calls[0]?.[1];
    expect(body?.move_quality).toBe('good');
    expect(body).not.toHaveProperty('recheck');
  });

  it('the bubble reads "Taking a closer look…" while the re-check runs, then the verdict replaces it (D-12)', async () => {
    let gated: GatedRecheckWorker | null = null;
    stubWorker(() => {
      gated = new GatedRecheckWorker('d7d5', 'd7d5');
      return gated;
    });
    await renderScreen(
      makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'sharp', runner_up_uci: 'c2c4' }),
    );
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.getByTestId('train-recheck-indicator')).not.toBeNull());
    expect(screen.getByTestId('train-recheck-indicator').textContent).toBe('Taking a closer look…');
    expect(screen.queryByTestId('train-grading-indicator')).toBeNull();
    expect(solvePuzzle).not.toHaveBeenCalled();

    // Each re-check search is held in turn (key, then played); keep releasing
    // until the whole re-check has answered and the verdict is on screen.
    await waitFor(() => {
      (gated as GatedRecheckWorker | null)?.release();
      expect(screen.getByTestId('train-reveal')).not.toBeNull();
    });
    expect(screen.queryByTestId('train-recheck-indicator')).toBeNull();
    expect(solvePuzzle.mock.calls[0]?.[1].recheck).toBeDefined();
  });

  it('a retried solve re-sends the identical payload, recheck included, and never re-runs the re-check (D-17)', async () => {
    const postSpy = vi.spyOn(FakeWorker.prototype, 'postMessage');
    try {
      solvePuzzle.mockRejectedValueOnce(new Error('network down'));
      stubWorker(() => new FakeWorker('d7d5', 'd7d5'));
      await renderScreen(
        makePuzzle({ key_move_uci: 'd2d4', puzzle_type: 'sharp', runner_up_uci: 'c2c4' }),
      );
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitFor(() => expect(screen.getByTestId('train-solve-error')).not.toBeNull());
      const recheckGo = `go movetime ${TRAIN_RECHECK_MOVETIME_MS} nodes ${TRAIN_RECHECK_MAX_NODES}`;
      const recheckPostsBefore = postSpy.mock.calls.filter(([msg]) => msg === recheckGo).length;
      expect(recheckPostsBefore).toBe(2);

      fireEvent.click(screen.getByTestId('btn-train-solve-retry'));
      await waitForReveal();

      expect(solvePuzzle).toHaveBeenCalledTimes(2);
      expect(solvePuzzle.mock.calls[1]?.[1]).toEqual(solvePuzzle.mock.calls[0]?.[1]);
      expect(solvePuzzle.mock.calls[1]?.[1].recheck).toBeDefined();
      expect(postSpy.mock.calls.filter(([msg]) => msg === recheckGo)).toHaveLength(2);
    } finally {
      postSpy.mockRestore();
    }
  });

  it('board holds the played-move position through grading (no flicker/remount), then snaps back to the puzzle position once the reveal opens (190-05 D-08)', async () => {
    const puzzle = makePuzzle();
    // Phase 237: the board now snaps to the puzzle position in the SAME render the
    // verdict lands (it follows the reveal tree), so the played-move position has
    // to be observed while the grading search is held, not in a one-render window.
    stubWorker(() => new HeldPositionWorker(fenAfterUciMove(START_FEN, 'd2d4') ?? ''));
    await renderScreen(puzzle);
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    fireEvent.click(screen.getByTestId('drop-d2d4'));
    await waitFor(() => expect(screen.getByTestId('train-grading-indicator')).not.toBeNull());
    const positionAtIndicator = screen.getByTestId('chessboard').getAttribute('data-position');
    // No flicker/remount during grading itself: still showing the played move.
    expect(positionAtIndicator).not.toBe(puzzle.fen);
    act(() => releaseHeldWorkers());
    await waitForReveal();
    const positionAtVerdict = screen.getByTestId('chessboard').getAttribute('data-position');
    // 190-05 D-08: as the reveal opens, the board snaps BACK to the puzzle
    // position — the played move is reported in the verdict text, not left
    // on the board.
    expect(positionAtVerdict).toBe(puzzle.fen);
  });

  it('engine failure (Worker error): checking indicator is gone, retry affordance present', async () => {
    stubWorker(() => new FailingWorker());
    await renderScreen(makePuzzle());
    await waitFor(() => expect(screen.getByTestId('train-engine-error')).not.toBeNull());
    expect(screen.queryByTestId('train-grading-indicator')).toBeNull();
    expect(screen.queryByTestId('btn-train-guess-critical')).toBeNull();
    expect(screen.getByTestId('btn-train-engine-retry')).not.toBeNull();
  });

  it('retrying after an onerror engine failure lets a subsequent move actually grade instead of hanging forever (WR-01)', async () => {
    let handedOutFailingWorker = false;
    stubWorker(() => {
      if (!handedOutFailingWorker) {
        handedOutFailingWorker = true;
        return new FailingWorker();
      }
      return new FakeWorker();
    });
    await renderScreen(makePuzzle());
    await waitFor(() => expect(screen.getByTestId('train-engine-error')).not.toBeNull());

    fireEvent.click(screen.getByTestId('btn-train-engine-retry'));

    // The restarted (healthy) Worker becomes ready — the guess/move UI must
    // reappear rather than staying stuck on the error fallback.
    await waitFor(() => expect(screen.getByTestId('btn-train-guess-critical')).not.toBeNull());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });

    // Before the WR-01 fix, `handleRetryEngine` called `startGrading`
    // synchronously against the STALE (still-erroring) refs — permanently
    // rejecting this puzzle's grading, so every subsequent move surfaced
    // `train-grading-error` forever instead of ever reaching a verdict.
    await waitForReveal();
    expect(screen.queryByTestId('train-grading-error')).toBeNull();
  });

  it('engine failure (readiness timeout): surfaces the same fallback when the Worker never reports ready', async () => {
    vi.useFakeTimers();
    stubWorker(() => new HangingWorker());
    composeOrResumeSession.mockResolvedValue(makeSession());
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <Harness puzzle={makePuzzle()} />
        </QueryClientProvider>
      </MemoryRouter>,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(20000);
    });
    expect(screen.getByTestId('train-engine-error')).not.toBeNull();
  });

  // ─── Task 3: block-and-retry solve persistence (T-190-12/T-190-15) ────────

  it('a forced solve-POST failure blocks Next and never advances; retry re-submits the identical payload and then enables Next', async () => {
    solvePuzzle.mockRejectedValueOnce(new Error('network down'));
    await renderScreen(makePuzzle());

    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });

    await waitFor(() => expect(screen.getByTestId('train-solve-error')).not.toBeNull());
    expect(screen.getByText("Couldn't save your result.")).not.toBeNull();

    const nextBtn = screen.getByTestId('btn-train-next') as HTMLButtonElement;
    expect(nextBtn.disabled).toBe(true);

    // Pressing Next while disabled must not change the puzzle index — the
    // hook's own gate (not just the disabled attribute) is what's asserted.
    fireEvent.click(nextBtn);
    expect(screen.queryByTestId('train-reveal')).toBeNull();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    const firstAttemptBody = solvePuzzle.mock.calls[0]?.[1];

    // Retry re-submits — this time it resolves (mockResolvedValue default).
    fireEvent.click(screen.getByTestId('btn-train-solve-retry'));

    await waitForReveal();
    expect(screen.queryByTestId('train-solve-error')).toBeNull();

    expect(solvePuzzle).toHaveBeenCalledTimes(2);
    const retryBody = solvePuzzle.mock.calls[1]?.[1];
    expect(retryBody).toEqual(firstAttemptBody);

    const nextBtnAfterRetry = screen.getByTestId('btn-train-next') as HTMLButtonElement;
    expect(nextBtnAfterRetry.disabled).toBe(false);
  });

  // ─── 190.1-01: end-to-end game-move reveal line, real hook + real Worker ──

  it('the game-move chip surfaces a live eval from the REAL grading engine, not a stub, once the reveal lands', async () => {
    // played_in_game_move_uci ('d2d4') is deliberately DISTINCT from the
    // played/best move ('e2e4', FakeWorker's fixed bestmove) — 190.1-03's
    // coincidence-merge rule only skips the reveal-time search (and folds
    // the game move into the You / Best chip) when the game move matches
    // one of the other two; this test exercises the independent search path.
    revealPuzzle.mockResolvedValueOnce({
      game_id: 100,
      ply: 20,
      fen: START_FEN,
      played_in_game_san: 'd4',
      played_in_game_move_uci: 'd2d4',
      puzzle_type: 'sharp',
      source: 'sr_item',
      has_tactic_lines: false,
    });
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.getByTestId('train-chip-game')).not.toBeNull());
    // The eval lands once the reveal-time search resolves (the chip shows a
    // spinner until then).
    await waitFor(() => {
      expect(screen.getByTestId('train-chip-game-eval').textContent).not.toBe('');
    });
  });

  // ─── 190.1-04: reveal-board arrows (D-02) ─────────────────────────────────

  it('the arrows prop handed to the board is empty before the verdict and non-empty afterwards', async () => {
    await renderScreen(makePuzzle());
    expect(screen.getByTestId('chessboard').getAttribute('data-arrows-count')).toBe('0');

    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    // exact-match move (FakeWorker's fixed bestmove e2e4) — still no arrows
    // while grading/solving is in flight.
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();
    await waitFor(() =>
      expect(Number(screen.getByTestId('chessboard').getAttribute('data-arrows-count'))).toBeGreaterThan(0),
    );
  });

  it('quality badges (squareMarkers) land on the board alongside the arrows once the verdict has settled (190.1 UAT)', async () => {
    await renderScreen(makePuzzle());
    expect(screen.getByTestId('chessboard').getAttribute('data-markers-count')).toBe('0');
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // exact match -> played IS best
    });
    await waitFor(() =>
      expect(Number(screen.getByTestId('chessboard').getAttribute('data-markers-count'))).toBeGreaterThan(0),
    );
  });

  // ─── Phase 237 tracer: chips + one move tree on the real reveal ─────────

  it('tracer: tapping the Best chip lights its arrow at the puzzle position and a list tap steps the line', async () => {
    // A three-move PV so the second token of the Best line still has a next move.
    stubWorker(() => new FakeWorker('e2e4', 'e2e4 e7e5 g1f3'));
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4')); // non-best -> separate You / Best chips
    });
    await waitForReveal();
    const board = () => screen.getByTestId('chessboard');

    // The reveal opens with the Move chip active: its arrow lit, the best arrow dimmed.
    await waitFor(() => expect(screen.getByTestId('train-chip-your').getAttribute('data-active')).toBe('true'));
    await waitFor(() => expectLitArrows(board(), ['d2d4']));
    expect(Object.keys(arrowOpacitiesByUci(board()))).toContain('e2e4');

    // D-01: a Best chip tap lights the best arrow; the board stays at the puzzle position.
    fireEvent.click(screen.getByTestId('train-chip-best'));
    await waitFor(() => expectLitArrows(board(), ['e2e4']));
    expect(screen.getByTestId('train-chip-best').getAttribute('data-active')).toBe('true');
    expect(board().getAttribute('data-position')).toBe(START_FEN);

    // D-03: a tap on the SECOND move token of the list steps the board there with
    // the step overlay (one blue next-move arrow).
    fireEvent.click(within(screen.getByTestId('train-move-tree')).getByText('e5'));
    await waitFor(() => expect(board().getAttribute('data-position')).not.toBe(START_FEN));
    expect(board().getAttribute('data-position')).toContain('rnbqkbnr/pppp1ppp/8/4p3/4P3');
    expect(board().getAttribute('data-arrows-count')).toBe('1');
    expect(board().getAttribute('data-arrow-ucis')).toBe('g1f3');
  });

  it('quick 261009-por: a stepped known-line position shows a deep, disagreeing reveal-engine move as a secondary arrow under the line pointer', async () => {
    // First Worker = grading engine (builds the Best line e4 e5 Nf3); later
    // Workers = the reveal engine, which disagrees with the line ('b1c3' vs the
    // line's 'g1f3') at exactly the gate depth.
    let workerCallCount = 0;
    stubWorker(() => {
      workerCallCount += 1;
      return workerCallCount === 1
        ? new FakeWorker('e2e4', 'e2e4 e7e5 g1f3')
        : new FakeWorker('b1c3', 'b1c3', TRAIN_STEP_LIVE_ARROW_MIN_DEPTH);
    });
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4')); // non-best -> separate You / Best chips
    });
    await waitForReveal();
    const board = () => screen.getByTestId('chessboard');
    fireEvent.click(screen.getByTestId('train-chip-best'));
    await waitFor(() => expectLitArrows(board(), ['e2e4']));

    fireEvent.click(within(screen.getByTestId('train-move-tree')).getByText('e5'));
    await waitFor(() => expect(board().getAttribute('data-position')).not.toBe(START_FEN));
    await waitFor(() => expect(board().getAttribute('data-arrows-count')).toBe('2'));
    expect(board().getAttribute('data-arrow-ucis')).toBe('b1c3,g1f3');
    expect(board().getAttribute('data-arrow-colors')).toBe(
      `${STOCKFISH_SECONDARY_LINE},${TRAIN_BEST_MOVE_ARROW}`,
    );
  });

  // ─── 190.1 UAT: reveal-line stepping clears the overlay; Solution restores ─

  it('stepping a reveal line clears the overlay, highlights the stepped move in its quality color with a blue next-move arrow, and Solution restores everything', async () => {
    // A two-move PV so the merged your/best box actually has a next move to
    // point at after the first step.
    stubWorker(() => new FakeWorker('e2e4', 'e2e4 e7e5'));
    await renderScreen(makePuzzle({ last_move_uci: 'd7d5' }));
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // exact match -> played IS best
    });
    await waitFor(() =>
      expect(Number(screen.getByTestId('chessboard').getAttribute('data-markers-count'))).toBeGreaterThan(0),
    );

    // Step to the line's first move (the merged Move = Best chip's first list token).
    tapListMove(0);

    const board = () => screen.getByTestId('chessboard');
    // UAT round 4: the FIRST move of a stepped line keeps exactly its own
    // quality badge (the rest of the solution overlay's markers are cleared).
    await waitFor(() => expect(board().getAttribute('data-markers-count')).toBe('1'));
    // The stepped move is highlighted in its quality color (played IS best ->
    // the engine-blue highlight), and the only arrow is the blue next-move
    // pointer for the rest of the Stockfish line.
    expect(board().getAttribute('data-last-move')).toBe('e2e4');
    expect(board().getAttribute('data-last-move-color')).toBe(TRAIN_STEP_HIGHLIGHT.best);
    expect(board().getAttribute('data-arrows-count')).toBe('1');

    // Deeper into the line (an engine continuation): no quality badge at all.
    tapListMove(1);
    await waitFor(() => expect(board().getAttribute('data-markers-count')).toBe('0'));

    // Solution: board back at the puzzle position, full overlay + the
    // arrival-move highlight restored.
    fireEvent.click(screen.getByTestId('board-btn-reset'));
    await waitFor(() =>
      expect(Number(board().getAttribute('data-markers-count'))).toBeGreaterThan(0),
    );
    expect(board().getAttribute('data-position')).toBe(START_FEN);
    expect(board().getAttribute('data-last-move')).toBe('d7d5');
    expect(board().getAttribute('data-last-move-color')).toBe('');
  });

  // Phase 200 UAT round 3: stepping a line back to its start must restore the
  // FULL solution — both the your-move and best-move arrows. The card being
  // stepped is still spotlit at that moment (the pointer never left it), which
  // used to leave the "restored" board showing that one move alone.
  // Phase 200 UAT round 9: while a line is stepped, clicking ANOTHER card used
  // to move only the card ring — the board stayed at the stepped position, so
  // the clicked card's own move was nowhere on screen. It must snap back to the
  // solution position and show that card's move.
  it('D-01: tapping a chip while stepped into another line returns the board to the puzzle position with that chip\'s arrow lit', async () => {
    stubWorker(() => new FakeWorker('e2e4', 'e2e4 e7e5'));
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4')); // non-best -> separate You / Best chips
    });
    await waitForReveal();

    const board = () => screen.getByTestId('chessboard');
    await waitFor(() =>
      expect(Number(board().getAttribute('data-arrows-count'))).toBeGreaterThan(1),
    );

    // Step into the You line — the board now shows a position no other chip describes.
    tapListMove(0);
    await waitFor(() => expect(board().getAttribute('data-position')).not.toBe(START_FEN));
    expect((screen.getByTestId('board-btn-reset') as HTMLButtonElement).disabled).toBe(false);

    // Tap the Best chip: the board jumps to the puzzle position with its arrow lit.
    fireEvent.click(screen.getByTestId('train-chip-best'));

    await waitFor(() => expect(board().getAttribute('data-position')).toBe(START_FEN));
    // The stepped line is over (rewind is disabled again) and the Best move is LIT
    // (the other move is dimmed, not removed).
    expect((screen.getByTestId('board-btn-reset') as HTMLButtonElement).disabled).toBe(true);
    expect(Number(board().getAttribute('data-arrows-count'))).toBeGreaterThan(1);
    expectLitArrows(board(), ['e2e4']);
    expect(screen.getByTestId('train-chip-best').getAttribute('data-active')).toBe('true');
  });

  it('D-01: tapping the chip whose own line is on the board does not move the board', async () => {
    stubWorker(() => new FakeWorker('e2e4', 'e2e4 e7e5 g1f3'));
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4'));
    });
    await waitForReveal();
    const board = () => screen.getByTestId('chessboard');

    // Walk into the Best line (chip first, so the list shows the Best line), two plies deep.
    fireEvent.click(screen.getByTestId('train-chip-best'));
    tapListMove(1);
    await waitFor(() => expect(board().getAttribute('data-position')).not.toBe(START_FEN));
    const positionInLine = board().getAttribute('data-position');

    // Tapping Best again while on its own line leaves the board exactly where it is.
    fireEvent.click(screen.getByTestId('train-chip-best'));
    expect(board().getAttribute('data-position')).toBe(positionInLine);
    expect(screen.getByTestId('train-chip-best').getAttribute('data-active')).toBe('true');
  });

  it('D-02: playing the best move shows ONE chip labelled "Move = Best" and one lit arrow', async () => {
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // exact match -> played IS best
    });
    await waitForReveal();

    expect(screen.getByTestId('train-chip-your-label').textContent).toBe('Move = Best');
    expect(screen.queryByTestId('train-chip-best')).toBeNull();
    const board = () => screen.getByTestId('chessboard');
    await waitFor(() => expectLitArrows(board(), ['e2e4']));
    expect(Object.keys(arrowOpacitiesByUci(board()))).toEqual(['e2e4']);
  });

  it('tracer: a best-move solve shows the collapsed strip with its total and expands to the full feedback', async () => {
    matchMediaMatches = false; // phone: the verdict is a strip, not a bubble
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // exact match -> played IS the engine's best
    });
    await waitForReveal();

    const strip = await screen.findByTestId('train-verdict-strip');
    expect(strip.getAttribute('aria-expanded')).toBe('false');
    expect(screen.getByTestId('train-verdict-strip-line').textContent).toBe('Right call, best move');
    expect(screen.getByTestId('train-verdict-strip-points').textContent).toBe(
      `+${scorePuzzle(SOLVE_RESPONSE.correct_guess, SOLVE_RESPONSE.move_quality)}`,
    );
    expect(screen.queryByTestId('train-verdict-strip-details')).toBeNull();
    // The old surfaces are gone on a phone: no bubble, no Your-call card.
    expect(screen.queryByTestId('train-bot-bubble')).toBeNull();
    expect(screen.queryByTestId('train-verdict-guess')).toBeNull();

    fireEvent.click(strip);
    expect(strip.getAttribute('aria-expanded')).toBe('true');
    const details = screen.getByTestId('train-verdict-strip-details');
    const verdictLine = within(details).getByTestId('train-bot-verdict-line');
    const guessRow = within(details).getByTestId('train-verdict-guess');
    const guessProse = within(details).getByTestId('train-verdict-guess-prose');
    expect(verdictLine.compareDocumentPosition(guessRow) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(guessRow.compareDocumentPosition(guessProse) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(within(details).queryByTestId('btn-train-analyze')).toBeNull();
  });

  // ─── Phase 200 (LEGEND-02) / Phase 237: chip focus on the shared board, end to end ─

  it('tapping the Best chip lights its own arrow on the shared board and dims the merged Move = Game move; tapping You restores it', async () => {
    // played_in_game_move_uci ('d2d4') coincides with the user's own played
    // move (also 'd2d4', a non-exact-match play against FakeWorker's fixed
    // bestmove 'e2e4') — merges You + Game into one chip and leaves Best as
    // its own chip (train-chip-best), so the focus target and its single arrow
    // are unambiguous.
    revealPuzzle.mockResolvedValueOnce({
      game_id: 100,
      ply: 20,
      fen: START_FEN,
      played_in_game_san: 'd4',
      played_in_game_move_uci: 'd2d4',
      puzzle_type: 'sharp',
      source: 'sr_item',
      has_tactic_lines: false,
    });
    stubWorker(() => new FakeWorker('e2e4', 'e2e4 e7e5'));
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    fireEvent.click(screen.getByTestId('drop-d2d4')); // non-exact -> separate You / Best chips
    await waitForReveal();

    const board = () => screen.getByTestId('chessboard');
    await waitFor(() =>
      expect(Number(board().getAttribute('data-arrows-count'))).toBeGreaterThan(0),
    );
    const fullArrowCount = Number(board().getAttribute('data-arrows-count'));
    expect(fullArrowCount).toBeGreaterThan(1); // a genuinely multi-arrow reveal
    // The reveal opens on the You (= Game) chip.
    await waitFor(() => expectLitArrows(board(), ['d2d4']));

    fireEvent.click(screen.getByTestId('train-chip-best'));
    // Lighting the best move DIMS the merged Move = Game move (both of its
    // arrows), never removes anything.
    await waitFor(() => expectLitArrows(board(), ['e2e4']));
    expect(Number(board().getAttribute('data-arrows-count'))).toBe(fullArrowCount);

    fireEvent.click(screen.getByTestId('train-chip-your'));
    await waitFor(() => expectLitArrows(board(), ['d2d4']));
    expect(Number(board().getAttribute('data-arrows-count'))).toBe(fullArrowCount);
  });

  it('the reveal opens with You lit — three arrows and three badges are drawn, only the You move is lit — and tapping Game then Best moves the light (Phase 237 dim-not-hide)', async () => {
    // A game move distinct from BOTH the user's played move (d2d4) and the
    // engine's best move (e2e4), so it gets its own standalone chip and lands
    // on its own square (f3), keeping all three arrows/badges pairwise
    // distinguishable (d4/e4/f3).
    revealPuzzle.mockResolvedValueOnce({
      game_id: 100,
      ply: 20,
      fen: START_FEN,
      played_in_game_san: 'Nf3',
      played_in_game_move_uci: 'g1f3',
      puzzle_type: 'sharp',
      source: 'sr_item',
      has_tactic_lines: false,
    });
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4')); // non-exact -> your != best
    });
    await waitForReveal();
    // The game chip exists (so its arrow IS available to focus)...
    await waitFor(() => expect(screen.getByTestId('train-chip-game')).not.toBeNull());

    // All THREE arrows and badges are drawn with no tap (260902-qf7). The marker
    // count is asserted inside its own `waitFor` because the game move's own
    // quality badge depends on the reveal-time engine search resolving
    // (`gameMoveLine`), an async gap that lands strictly after the arrow itself.
    const board = () => screen.getByTestId('chessboard');
    await waitFor(() => expect(board().getAttribute('data-arrows-count')).toBe('3'));
    await waitFor(() => expect(board().getAttribute('data-markers-count')).toBe('3'));
    // Phase 237: the Move chip is active, so ONLY its arrow and badge are lit.
    expectLitArrows(board(), ['d2d4']);
    // Badges are pushed played > best > game, i.e. d4, e4, f3.
    expect(markerOpacities(board())).toEqual([
      TRAIN_FOCUS_BADGE_LIT_OPACITY,
      TRAIN_FOCUS_BADGE_DIM_OPACITY,
      TRAIN_FOCUS_BADGE_DIM_OPACITY,
    ]);

    fireEvent.click(screen.getByTestId('train-chip-game'));
    await waitFor(() => expectLitArrows(board(), ['g1f3']));
    expect(board().getAttribute('data-arrows-count')).toBe('3');
    expect(board().getAttribute('data-markers-count')).toBe('3');
    expect(markerOpacities(board())).toEqual([
      TRAIN_FOCUS_BADGE_DIM_OPACITY,
      TRAIN_FOCUS_BADGE_DIM_OPACITY,
      TRAIN_FOCUS_BADGE_LIT_OPACITY,
    ]);

    fireEvent.click(screen.getByTestId('train-chip-best'));
    await waitFor(() => expectLitArrows(board(), ['e2e4']));
    expect(markerOpacities(board())).toEqual([
      TRAIN_FOCUS_BADGE_DIM_OPACITY,
      TRAIN_FOCUS_BADGE_LIT_OPACITY,
      TRAIN_FOCUS_BADGE_DIM_OPACITY,
    ]);
    expect(board().getAttribute('data-arrows-count')).toBe('3');
  });

  it('a puzzle with no played-in-game move shows two chips and draws only the your-move and best-move arrows (filler puzzles are unaffected by 260902-qf7)', async () => {
    // Uses the module-level `revealPuzzle` default fixture
    // (`played_in_game_move_uci: null`) — no Game chip is ever rendered, so the
    // drawn set stays the your/best pair; this guards that the game arrow is
    // scoped to puzzles that actually carry a game move.
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4')); // non-exact -> your != best
    });
    await waitForReveal();
    expect(screen.queryByTestId('train-chip-game')).toBeNull();
    expect(screen.getByTestId('train-chip-your')).not.toBeNull();
    expect(screen.getByTestId('train-chip-best')).not.toBeNull();

    const board = () => screen.getByTestId('chessboard');
    await waitFor(() => expect(board().getAttribute('data-arrows-count')).toBe('2'));
    expect(board().getAttribute('data-markers-count')).toBe('2');
    expectLitArrows(board(), ['d2d4']); // You lit, Best present but dimmed
    expect(Object.keys(arrowOpacitiesByUci(board())).sort()).toEqual(['d2d4', 'e2e4']);
  });

  // ─── Phase 200 (LEGEND-04): the "Also fine" row, end to end ───────────────

  /** A width-aware fake Stockfish worker whose MultiPV mount search returns a
   * DISTINCT move per rank (unlike the module's own `FakeWorker`, which
   * echoes the same move for every rank) — needed to exercise a soft
   * puzzle's multiple `alsoFineMoves` entries. Every rank's score differs by
   * only 1cp, so `deriveFineMoves` classifies every rank 'good' (no
   * meaningful drop) and every rank stays a legal opening move from the
   * shared board's starting position. */
  class MultiRankFakeWorker {
    onmessage: ((e: MessageEvent<string>) => void) | null = null;
    onerror: ((e: unknown) => void) | null = null;
    private width = 1;
    private readonly ranked = ['e2e4', 'd2d4', 'g1f3', 'c2c4'];

    postMessage(msg: string | { progressPort: unknown }): void {
      // Phase 213: ignore the non-string `{ progressPort }` handoff
      // useStockfishEngine now sends before the 'uci' handshake.
      if (typeof msg !== 'string') return;
      if (msg === 'uci') {
        this.emit('uciok');
      } else if (msg === 'isready') {
        this.emit('readyok');
      } else if (msg.startsWith('setoption name MultiPV value ')) {
        const width = parseInt(msg.slice('setoption name MultiPV value '.length), 10);
        this.width = Number.isFinite(width) && width > 0 ? width : 1;
      } else if (msg.startsWith('go ')) {
        queueMicrotask(() => {
          for (let rank = 1; rank <= this.width; rank++) {
            const move = this.ranked[rank - 1] ?? this.ranked[this.ranked.length - 1];
            this.emit(`info depth 10 multipv ${rank} score cp ${20 - rank} nodes 1000 pv ${move}`);
          }
          this.emit(`bestmove ${this.ranked[0]}`);
        });
      }
    }

    terminate(): void {}

    private emit(data: string): void {
      this.onmessage?.(new MessageEvent('message', { data }));
    }
  }

  /**
   * Phase 205 (D-04, Task 1): a Worker fake that branches its response on
   * the LAST position it was told to search (`position fen ...`), modelled
   * on `MultiRankFakeWorker` above. At `puzzleFen` it emits the SAME shape
   * of settled mount search — four near-equal-score, distinct-move ranks,
   * honouring the requested MultiPV width exactly as `MultiRankFakeWorker`
   * does. At any OTHER position (the free-play engine's own post-move
   * search) it emits a single line whose score comes from a constructor-
   * supplied FEN -> WHITE-POV-centipawn map, with a default for any FEN not
   * in the map — so a test can script the free-play "oracle" to disagree
   * with the mount search on purpose (SEED-137 case 2's exact shape).
   *
   * `scoresByFen` values are WHITE-POV (matching every eval convention in
   * this codebase); this class converts to the mover-POV a real UCI engine
   * reports before emitting, using the searched FEN's own side-to-move —
   * the same `whitePovSign` inversion `useTrainGradingEngine.ts`'s
   * `dispatchNow` and `useStockfishEngine.ts`'s `analyze` both apply.
   */
  class ScriptedFenFakeWorker {
    onmessage: ((e: MessageEvent<string>) => void) | null = null;
    onerror: ((e: unknown) => void) | null = null;
    private width = 1;
    private lastPositionFen = '';
    private readonly mountRanks = ['e2e4', 'd2d4', 'g1f3', 'c2c4'];

    constructor(
      private readonly puzzleFen: string,
      private readonly scoresByFen: Record<string, number>,
      private readonly defaultScoreCp = 20,
    ) {}

    postMessage(msg: string | { progressPort: unknown }): void {
      // Phase 213: ignore the non-string `{ progressPort }` handoff
      // useStockfishEngine now sends before the 'uci' handshake.
      if (typeof msg !== 'string') return;
      if (msg === 'uci') {
        this.emit('uciok');
      } else if (msg === 'isready') {
        this.emit('readyok');
      } else if (msg.startsWith('setoption name MultiPV value ')) {
        const width = parseInt(msg.slice('setoption name MultiPV value '.length), 10);
        this.width = Number.isFinite(width) && width > 0 ? width : 1;
      } else if (msg.startsWith('position fen ')) {
        this.lastPositionFen = msg.slice('position fen '.length);
      } else if (msg.startsWith('go ')) {
        const fen = this.lastPositionFen;
        queueMicrotask(() => {
          if (fen === this.puzzleFen) {
            // The settled mount search — near-equal scores (differ by 1cp
            // per rank), a DISTINCT move per rank, honouring the requested
            // width exactly like MultiRankFakeWorker.
            for (let rank = 1; rank <= this.width; rank++) {
              const move = this.mountRanks[rank - 1] ?? this.mountRanks[this.mountRanks.length - 1];
              this.emit(`info depth 10 multipv ${rank} score cp ${20 - rank} nodes 1000 pv ${move}`);
            }
            this.emit(`bestmove ${this.mountRanks[0]}`);
          } else {
            // The free-play engine's own independent post-move search —
            // scripted per-FEN, WHITE-POV converted to this FEN's mover POV.
            const whitePovCp = this.scoresByFen[fen] ?? this.defaultScoreCp;
            const moverSign = fen.split(' ')[1] === 'b' ? -1 : 1;
            this.emit(`info depth 10 multipv 1 score cp ${whitePovCp * moverSign} nodes 1000 pv a7a6`);
            this.emit('bestmove a7a6');
          }
        });
      }
    }

    terminate(): void {}

    private emit(data: string): void {
      this.onmessage?.(new MessageEvent('message', { data }));
    }
  }

  it('a herring puzzle with three drawn alternatives lists all three SANs in the guess card; the alternatives stay DIMMED on the board whichever chip is focused (Phase 237)', async () => {
    stubWorker(() => new MultiRankFakeWorker());
    // Phase 211 (D-01): the alternatives come from the SERVER's vetted_moves
    // on the solve response — the client engine's own ranks no longer feed
    // the overlay. `e2e4` (the best move) is included to prove the overlay
    // still filters it out before drawing alternatives. The puzzle type is
    // HERRING because three alternatives fit only its own cap
    // (TRAIN_HERRING_ALT_MOVE_ARROWS = 4); the soft budget is 1 as of 211-02.
    solvePuzzle.mockResolvedValueOnce({
      ...SOLVE_RESPONSE,
      puzzle_type: 'herring',
      vetted_moves: [
        { uci: 'e2e4', quality: 'good' },
        { uci: 'd2d4', quality: 'good' },
        { uci: 'g1f3', quality: 'good' },
        { uci: 'c2c4', quality: 'good' },
      ],
    });
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-several'));
    // Exact match to the mount search's top move (e2e4): merges into the
    // single blue best arrow. UAT round 4 — the vetted entry equal to the
    // best move no longer consumes an alternative slot, so ALL of
    // d2d4/g1f3/c2c4 draw within the herring cap.
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();

    // UAT round 6: the list lives in the guess card's body.
    const list = await waitFor(() => screen.getByTestId('train-reveal-also-fine'));
    expect(list.textContent).toContain('d4');
    expect(list.textContent).toContain('Nf3');
    expect(list.textContent).toContain('c4');

    // Phase 237 (dim, never hide): the board lights the focused chip (your =
    // best coincide, so one blue arrow) AND draws the three alternatives
    // DIMMED. No chip owns an alternative, so they stay dimmed whichever chip
    // is focused.
    const board = () => screen.getByTestId('chessboard');
    await waitFor(() => expect(board().getAttribute('data-arrows-count')).toBe('4'));
    expectLitArrows(board(), ['e2e4']);
    expect(Object.keys(arrowOpacitiesByUci(board())).sort()).toEqual(['c2c4', 'd2d4', 'e2e4', 'g1f3']);

    fireEvent.click(screen.getByTestId('train-chip-your'));
    await waitFor(() => expectLitArrows(board(), ['e2e4']));
    expect(board().getAttribute('data-arrows-count')).toBe('4');
  });

  // ─── Phase 211 (D-03/D-07): the board badge follows the server's graded ES ─

  it('VETFINE-03: the played-move badge derives from the verdict\'s graded_es_* pair even when the client engine\'s own search implies a blunder (the server override wins on the board)', async () => {
    // b1c3 (Nc3) is legal but OUTSIDE every mount rank (e2e4/d2d4/g1f3/c2c4),
    // so the 190.1 rank-match fast path cannot serve it — the client runs a
    // real after-move search, scripted catastrophic (-900 white-POV), so
    // gradeResult.esBefore/esAfter imply a BLUNDER.
    const afterB1C3 = new Chess(START_FEN);
    afterB1C3.move('Nc3');
    const fenAfterB1C3 = afterB1C3.fen();
    stubWorker(() => new ScriptedFenFakeWorker(START_FEN, { [fenAfterB1C3]: -900 }));
    // The SERVER's verdict: b1c3 is a certified key move, graded good from
    // the stored evals (a sub-inaccuracy ES drop), with g1f3 as a second
    // vetted alternative for the legend row.
    solvePuzzle.mockResolvedValueOnce({
      ...SOLVE_RESPONSE,
      puzzle_type: 'soft',
      move_quality: 'good',
      vetted_moves: [
        { uci: 'b1c3', quality: 'good' },
        { uci: 'g1f3', quality: 'good' },
      ],
      graded_es_before: 0.52,
      graded_es_after: 0.51,
    });

    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-several'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-b1c3')); // off-rank -> real after-move search
    });
    await waitForReveal();

    // (a) The board followed the SERVER, not the client engine: the played
    // arrow is good-green, and no blunder-colored arrow exists anywhere.
    const board = () => screen.getByTestId('chessboard');
    await waitFor(() =>
      expect(board().getAttribute('data-arrow-colors') ?? '').toContain(MOVE_QUALITY_GOOD),
    );
    expect(board().getAttribute('data-arrow-colors') ?? '').not.toContain(MOVE_QUALITY_BLUNDER);

    // (b) The vetted alternative (g1f3, not played, not best) reaches the
    // "Also fine" legend row.
    const list = await waitFor(() => screen.getByTestId('train-reveal-also-fine'));
    expect(list.textContent).toContain('Nf3');
  });

  it('VETFINE-03 (pre-211 cache shape): a verdict with NO vetted_moves key draws zero alternative arrows and nothing throws', async () => {
    // MultiRankFakeWorker still derives client-side ranks 2-4 — if the
    // overlay ever fell back to the client engine's alternatives, this test
    // would see them. SOLVE_RESPONSE carries no vetted_moves key at all (the
    // exact shape a trainRevealCache entry written by a pre-211 bundle
    // restores).
    stubWorker(() => new MultiRankFakeWorker());
    solvePuzzle.mockResolvedValueOnce({ ...SOLVE_RESPONSE, puzzle_type: 'soft' });
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-several'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();

    // No "Also fine" list, and hovering the guess card surfaces no
    // alternative arrows — the pristine single blue best/played arrow stays.
    expect(screen.queryByTestId('train-reveal-also-fine')).toBeNull();
    const board = () => screen.getByTestId('chessboard');
    await waitFor(() => expect(board().getAttribute('data-arrows-count')).toBe('1'));
    fireEvent.pointerEnter(screen.getByTestId('train-verdict-guess'));
    // Deliberately re-assert after the hover settles — still exactly one.
    await waitFor(() => expect(board().getAttribute('data-arrows-count')).toBe('1'));
  });

  // ─── Phase 205 (ORACLE-01/ORACLE-02) → Phase 211 (D-06): free-play root ──
  // grade agrees with the reveal's "Also fine" row — SEED-137 case 2.

  // Re-expressed by Plan 211-03 (unskipped — was the 211-02 Known Transient,
  // WINDOWS.md #6): the guarantee's source is no longer the mount search's
  // own rank lines (dead at width 1, D-05) but the SERVED vetted list on the
  // solve response — the same key the "Also fine" row reads (D-06).
  it('ORACLE-01: playing a served "Also fine" vetted move as the FIRST free-play move is badged with the server\'s own quality, never a fresh (worse) free-play-engine search', async () => {
    // The position reached after white's served alternative (d2d4) —
    // scripted to a CATASTROPHIC white-POV score (-900cp), far below
    // BLUNDER_DROP, so a build that consulted the free-play engine's own
    // search here would badge this move a blunder. The SERVER's key says
    // d2d4 is good; the badge must read the key.
    const afterD2D4 = new Chess(START_FEN);
    afterD2D4.move('d4');
    const fenAfterD2D4 = afterD2D4.fen();
    stubWorker(() => new ScriptedFenFakeWorker(START_FEN, { [fenAfterD2D4]: -900 }));
    solvePuzzle.mockResolvedValueOnce({
      ...SOLVE_RESPONSE,
      puzzle_type: 'soft',
      vetted_moves: [{ uci: 'd2d4', quality: 'good' }],
    });

    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-several'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // rank-1, exact match -> lands the verdict
    });
    await waitForReveal();

    // Post-verdict: the FIRST free-play move, from the root, is the served
    // vetted ("Also fine") move.
    fireEvent.click(screen.getByTestId('drop-d2d4'));
    const board = () => screen.getByTestId('chessboard');
    await waitFor(() => expect(board().getAttribute('data-last-move-color')).not.toBe(''));
    expect(board().getAttribute('data-last-move-color')).toBe(TRAIN_STEP_HIGHLIGHT.good);
    expect(board().getAttribute('data-last-move-color')).not.toBe(TRAIN_STEP_HIGHLIGHT.mistake);
    expect(board().getAttribute('data-last-move-color')).not.toBe(TRAIN_STEP_HIGHLIGHT.blunder);
  });

  it('D-04 residual (deliberate): a FIRST free-play move NOT among the mount ranks still comes from the free-play engine\'s own (worse) search', async () => {
    const afterB1C3 = new Chess(START_FEN);
    afterB1C3.move('Nc3');
    const fenAfterB1C3 = afterB1C3.fen();
    stubWorker(() => new ScriptedFenFakeWorker(START_FEN, { [fenAfterB1C3]: -900 }));

    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // rank-1, exact match -> lands the verdict
    });
    await waitForReveal();

    // b1c3 (Nc3) is legal but outside every mount rank (e2e4/d2d4/g1f3/c2c4)
    // — D-04's accepted residual seam: esBefore stays seeded from the mount
    // search, esAfter still comes from the free-play engine's own search.
    fireEvent.click(screen.getByTestId('drop-b1c3'));
    const board = () => screen.getByTestId('chessboard');
    await waitFor(() =>
      expect(board().getAttribute('data-last-move-color')).toBe(TRAIN_STEP_HIGHLIGHT.blunder),
    );
  });

  // ─── 190.1 UAT round 3 / Phase 237 plan 07: the action bar under the board ──

  it('the action bar appears under the board only once the verdict lands; rewind is disabled at the puzzle position and live after a list step', async () => {
    await renderScreen(makePuzzle({ ply: 20 }));
    expect(screen.queryByTestId('train-reveal-action-bar')).toBeNull();
    expect(screen.queryByTestId('btn-train-analyze')).toBeNull();
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.getByTestId('btn-train-analyze')).not.toBeNull());
    const reset = () => screen.getByTestId('board-btn-reset') as HTMLButtonElement;
    // The pristine reveal sits at the puzzle position: nothing to rewind.
    expect(reset().disabled).toBe(true);

    // Step the merged Move = Best line's first move: the board departs the puzzle
    // position, so rewind now has a job.
    await waitFor(() => expect(screen.getByTestId('train-move-tree')).not.toBeNull());
    tapListMove(0);
    await waitFor(() => expect(reset().disabled).toBe(false));

    const bar = screen.getByTestId('train-reveal-action-bar');
    const analyzeBtn = screen.getByTestId('btn-train-analyze');
    const nextBtn = screen.getByTestId('btn-train-next');
    // The bar owns the controls; the verdict bubble carries copy only.
    expect(bar.contains(analyzeBtn)).toBe(true);
    expect(bar.contains(nextBtn)).toBe(true);
    expect(bar.contains(reset())).toBe(true);
    const bubble = screen.getByTestId('train-verdict-card');
    expect(bubble.contains(analyzeBtn)).toBe(false);
    expect(bubble.contains(nextBtn)).toBe(false);
    // Analyze deep-links one ply BEFORE the mistake (ply 20 -> 19).
    expect(analyzeBtn.getAttribute('href')).toBe(buildGameAnalysisUrl(100, 19));

    // Rewind returns to the puzzle position, which disables it again.
    fireEvent.click(reset());
    await waitFor(() => expect(reset().disabled).toBe(true));
  });

  it('Phase 222 (D-10): the mute toggle is retired — no board-btn-mute renders once the verdict lands', async () => {
    await renderScreen(makePuzzle());
    expect(screen.queryByTestId('board-btn-mute')).toBeNull();
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.getByTestId('btn-train-next')).not.toBeNull());
    expect(screen.queryByTestId('board-btn-mute')).toBeNull();
  });

  it('a live 3-point solve plays the per-puzzle score-full sound and pops the "Points: +3" flash over the board (190.1 UAT round 7, SEED-119 max)', async () => {
    const { playSound } = await import('@/lib/sounds');
    vi.mocked(playSound).mockClear();
    await renderScreen(makePuzzle());
    expect(screen.queryByTestId('train-points-flash')).toBeNull();
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // matches bestmove -> good tier, 2 move points
    });
    await waitFor(() => expect(screen.getByTestId('train-points-flash')).not.toBeNull());
    expect(screen.getByTestId('train-points-flash').textContent).toBe('+3');
    // Sketch 004 (phase 222 UAT): the pop carries the verdict bot's face.
    expect(screen.getByTestId('train-points-flash-avatar')).not.toBeNull();
    // Quick 260814-b: the per-puzzle perfect score has its own clip. It must
    // NOT be 'game-win' — that is reserved for the green session verdict and
    // bot-game wins, and reusing it here made one puzzle sound like the whole
    // session (round 7's earlier verdict, that it is not the Victory fanfare
    // either, still holds — that SoundEvent no longer exists).
    expect(playSound).toHaveBeenCalledWith('score-full');
    expect(playSound).not.toHaveBeenCalledWith('game-win');
  });

  it('a REMOUNT (dev-clock time travel -> new session) replays neither the previous session’s result sound nor its points flash (Phase 200 UAT round 7)', async () => {
    const { playSound } = await import('@/lib/sounds');
    composeOrResumeSession.mockResolvedValue(makeSession());
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            <RemountHarness puzzle={makePuzzle()} nextPuzzle={makePuzzle({ position: 2 })} />
          </TooltipProvider>
        </QueryClientProvider>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());

    // Solve the puzzle so the shared solve mutation holds a landed verdict.
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.getByTestId('train-points-flash')).not.toBeNull());

    // Leave the loop and come back on the next session's first puzzle. The
    // mutation still holds the OLD verdict at this mount — it must stay silent.
    vi.mocked(playSound).mockClear();
    await act(async () => {
      fireEvent.click(screen.getByTestId('toggle-loop'));
    });
    expect(screen.queryByTestId('chessboard')).toBeNull();
    await act(async () => {
      fireEvent.click(screen.getByTestId('toggle-loop'));
    });
    await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());
    expect(playSound).not.toHaveBeenCalled();
    expect(screen.queryByTestId('train-points-flash')).toBeNull();
  });

  // ─── D-09: Analyze hidden (not disabled) when game_id is null (Phase 192) ──

  it('hides the Analyze link when the source game link is null, but the bar still has Next and rewind (Phase 237 plan 07)', async () => {
    await renderScreen(makePuzzle({ game_id: null, ply: 20 }));
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.getByTestId('btn-train-next')).not.toBeNull());
    expect(screen.queryByTestId('btn-train-analyze')).toBeNull();
    expect(screen.getByTestId('train-reveal-action-bar').contains(screen.getByTestId('btn-train-next'))).toBe(true);
    await waitFor(() => expect(screen.getByTestId('train-move-tree')).not.toBeNull());
    tapListMove(0);
    await waitFor(() =>
      expect((screen.getByTestId('board-btn-reset') as HTMLButtonElement).disabled).toBe(false),
    );
    expect(screen.getByTestId('btn-train-next')).not.toBeNull();
  });

  it('renders the Analyze link when the source game is present', async () => {
    await renderScreen(makePuzzle({ game_id: 100, ply: 20 }));
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.getByTestId('btn-train-analyze')).not.toBeNull());
    expect(screen.getByTestId('btn-train-analyze').getAttribute('href')).toBe(
      buildGameAnalysisUrl(100, 19),
    );
  });

  it('btn-train-analyze carries no ply query parameter when puzzle.ply is 0', async () => {
    await renderScreen(makePuzzle({ ply: 0 }));
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.getByTestId('btn-train-analyze')).not.toBeNull());
    const href = screen.getByTestId('btn-train-analyze').getAttribute('href');
    expect(href).toBe(buildGameAnalysisUrl(100, null));
    expect(href).not.toContain('ply=');
  });

  // ─── 190.1 UAT: post-guess move prompt ────────────────────────────────────

  it('committing a guess replaces the guess buttons with the "Now play a move for {color}" prompt, which disappears once the move lands', async () => {
    await renderScreen(makePuzzle({ side_to_move: 'white' }));
    expect(screen.queryByTestId('train-move-prompt')).toBeNull();
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    expect(screen.getByTestId('train-move-prompt').textContent).toBe(
      'Your call: only one good move. Now play a move for white.',
    );
    expect(screen.queryByTestId('btn-train-guess-critical')).toBeNull();
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.queryByTestId('train-move-prompt')).toBeNull());
  });

  it('the move prompt states black for a black-to-move puzzle', async () => {
    await renderScreen(makePuzzle({ side_to_move: 'black' }));
    fireEvent.click(screen.getByTestId('btn-train-guess-several'));
    expect(screen.getByTestId('train-move-prompt').textContent).toBe(
      'Your call: several good moves. Now play a move for black.',
    );
  });

  // ─── 190.1-04: running session score on the progress bar (D-04) ──────────

  it('train-session-score is absent on the first puzzle of a fresh session before any solve', async () => {
    await renderScreen(makePuzzle(), makeSession({ solved_count: 0 }));
    expect(screen.queryByTestId('train-session-score')).toBeNull();
  });

  it('driving one puzzle to a correct-guess good-move verdict shows the accumulated score and a max of one times TRAIN_POINTS_PER_PUZZLE (SEED-119: 3)', async () => {
    await renderScreen(makePuzzle(), makeSession({ solved_count: 0 }));
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // exact match -> guess + good move
    });
    await waitFor(() => expect(screen.getByTestId('train-session-score')).not.toBeNull());
    const text = screen.getByTestId('train-session-score').textContent ?? '';
    expect(text).toContain('3'); // score: correct_guess (1) + good move (2) = 3 points
    expect(text).toContain('3'); // max: 1 puzzle x TRAIN_POINTS_PER_PUZZLE (3) = 3
  });

  it('train-progress, train-progress-bar and train-session-score share one compact row (phase 222 UAT)', async () => {
    // sessionSolvedCount (260728-tgc) derives from solved_results.length, not
    // solved_count — seed one entry so the score row actually renders.
    await renderScreen(
      makePuzzle(),
      makeSession({ solved_count: 1, solved_results: [makeSolvedResult()] }),
    );
    const score = screen.getByTestId('train-session-score');
    const progress = screen.getByTestId('train-progress');
    expect(score.parentElement).toBe(progress.parentElement);
    const bar = screen.getByTestId('train-progress-bar');
    expect(bar.parentElement).toBe(progress.parentElement);
    expect(bar.previousElementSibling).toBe(progress);
    expect(bar.nextElementSibling).toBe(score);
  });

  // ─── Phase 200 (EXPLORE-01/02/04/05, D-12) / Phase 237 plan 06: sidelines fork in place ──

  it('a post-verdict drop forks a sideline in place on the one tree; a further drop extends it; no second grading/solve attempt is ever issued', async () => {
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // the single graded attempt
    });
    await waitForReveal();
    expect(solvePuzzle).toHaveBeenCalledTimes(1);

    const board = () => screen.getByTestId('chessboard');
    // The known lines (played = best = e2e4) carry no Stockfish row.
    expect(screen.queryByTestId('train-sf-row')).toBeNull();

    // Post-verdict drop 1: d2d4 matches no known line, so it FORKS a sideline.
    const afterD4 = new Chess(START_FEN);
    afterD4.move('d4');
    fireEvent.click(screen.getByTestId('drop-d2d4'));
    await waitFor(() => expect(board().getAttribute('data-position')).toBe(afterD4.fen()));
    // Off the known lines: the sideline is listed with its close x, and the
    // Stockfish row appears (D-03).
    expect(
      screen.getByTestId('train-move-tree').querySelector('[data-testid^="btn-delete-line-"]'),
    ).not.toBeNull();
    expect(screen.getByTestId('train-sf-row')).not.toBeNull();

    // Post-verdict drop 2: EXTENDS the sideline (never restarts/resets it).
    const afterD4D5 = new Chess(START_FEN);
    afterD4D5.move('d4');
    afterD4D5.move('d5');
    fireEvent.click(screen.getByTestId('drop-d7d5'));
    await waitFor(() => expect(board().getAttribute('data-position')).toBe(afterD4D5.fen()));

    // Prohibition guard (SOLV-02): neither drop touched the graded/solve path,
    // exactly the ONE solvePuzzle call from the original graded move.
    expect(solvePuzzle).toHaveBeenCalledTimes(1);
  });

  // Phase 205 Task 2 (D-10): a reveal restored from an OLDER bundle's cache
  // (its gradeResult has no rank-lines key at runtime) must grade its root
  // free-play move exactly like today's pre-Phase-205 path — no throw, no
  // silently invented rank match.
  it('D-10: a restored pre-Phase-205 reveal (gradeResult carrying no rank lines) grades its root fork from the reveal engine\'s own path, never throwing', async () => {
    const restoredPuzzle = makePuzzle();
    const afterD2D4 = new Chess(START_FEN);
    afterD2D4.move('d4');
    const fenAfterD2D4 = afterD2D4.fen();
    stubWorker(() => new ScriptedFenFakeWorker(START_FEN, { [fenAfterD2D4]: -900 }));

    // A JSON round trip through `unknown` models exactly what an OLDER
    // bundle actually wrote — `lines` never existed on the wire.
    const restoredCached = JSON.parse(
      JSON.stringify({
        sessionId: 1,
        puzzle: restoredPuzzle,
        verdict: SOLVE_RESPONSE,
        guess: 'critical',
        playedMoveUci: 'e2e4',
        gradeResult: {
          moveTier: 'good',
          bestMoveUci: 'e2e4',
          esBefore: 0.5,
          esAfter: 0.5,
          bestLine: { moves: ['e2e4'], evalCp: 19, evalMate: null },
          playedLine: { moves: ['e2e4'], evalCp: 19, evalMate: null },
        },
      }),
    ) as CachedTrainReveal;

    await renderScreen(restoredPuzzle, makeSession(), restoredCached);
    await waitForReveal();

    expect(() => fireEvent.click(screen.getByTestId('drop-d2d4'))).not.toThrow();
    const board = () => screen.getByTestId('chessboard');
    // Today's pre-Phase-205 behavior: graded from the free-play engine's own
    // (scripted, catastrophic) search — never a silently invented rank
    // match, since the restored gradeResult carries no lines to consult.
    await waitFor(() =>
      expect(board().getAttribute('data-last-move-color')).toBe(TRAIN_STEP_HIGHLIGHT.blunder),
    );
  });

  it('a drop while grading is still pending (verdict not yet landed) is rejected and never forks a sideline', async () => {
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    fireEvent.click(screen.getByTestId('drop-d2d4')); // non-exact -> grading in flight, verdict still null
    // Synchronously, before the FakeWorker's queueMicrotask-deferred result
    // lands, moveApplied is already true but verdict is still null — the
    // exploration branch's own gate must reject this drop.
    fireEvent.click(screen.getByTestId('drop-e2e4'));
    await waitForReveal();
    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    // No sideline was ever forked: rewind stays disabled (the board never left the
    // puzzle position) and there is no sideline close x. If the rejected drop had
    // forked, both would show.
    expect(document.querySelector('[data-testid^="btn-delete-line-"]')).toBeNull();
    expect((screen.getByTestId('board-btn-reset') as HTMLButtonElement).disabled).toBe(true);
  });

  it('Phase 200 (D-12): the side to move follows the sideline, turn order stays fully enforced, and no move is ever auto-played onto the board', async () => {
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();

    const board = () => screen.getByTestId('chessboard');
    const afterD4 = new Chess(START_FEN);
    afterD4.move('d4');
    const afterD4D5 = new Chess(START_FEN);
    afterD4D5.move('d4');
    afterD4D5.move('d5');

    // Fork a sideline with a white drop: now black's turn.
    fireEvent.click(screen.getByTestId('drop-d2d4'));
    await waitFor(() => expect(board().getAttribute('data-position')).toBe(afterD4.fen()));

    // Turn order is still ENFORCED, not bypassed (the Analysis-board rule): a
    // WHITE drop while it's black's turn is rejected — a build that widens
    // the branch by skipping chess.js validation (instead of tracking
    // displayFen) would wrongly accept this.
    fireEvent.click(screen.getByTestId('drop-e2e4'));
    expect(board().getAttribute('data-position')).toBe(afterD4.fen());

    // The side to move FOLLOWS the sideline: a black drop is accepted here.
    // A build that validates against the frozen boardFen instead of
    // displayFen fails this — data-position would stay stuck after-d2d4.
    fireEvent.click(screen.getByTestId('drop-d7d5'));
    await waitFor(() => expect(board().getAttribute('data-position')).toBe(afterD4D5.fen()));
    expect(board().getAttribute('data-position')?.split(' ')[1]).toBe('w');

    // No auto-reply: the position stays byte-identical after flushing
    // pending microtasks/timers — one user drop appends exactly one move,
    // and no engine result ever plays a move onto the board.
    await act(async () => {
      await Promise.resolve();
    });
    expect(board().getAttribute('data-position')).toBe(afterD4D5.fen());
  });

  // ─── Phase 200 (EXPLORE-05) / Phase 237 plan 06: ONE reveal engine ────────
  //
  // After the verdict there are exactly two Workers: [0] the session-scoped
  // grading engine (idle once the verdict has landed) and [1] the reveal tree's
  // one engine, which follows the shown position (eval bar, Stockfish row, board
  // arrows and the sideline grader all read it). A fork never adds a third.

  /** Verdict landed (played = best = e2e4), then ONE fork from the puzzle
   * position (d2d4, a move no known line carries) so the board sits on a user
   * sideline. Returns board accessors. */
  async function startSideline() {
    await renderScreen(makePuzzle());
    return forkFromVerdict();
  }

  async function forkFromVerdict() {
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // the single graded attempt
    });
    await waitForReveal();
    fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
    await waitFor(() => expect(screen.getByTestId('train-sf-row')).not.toBeNull());
    return {
      board: () => screen.getByTestId('chessboard'),
      moveList: () => screen.getByTestId('train-move-tree'),
    };
  }

  it('exactly two Workers exist once the verdict lands (grading + the reveal engine), and still exactly two after a fork', async () => {
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();
    await waitFor(() => expect(stubbedWorkerInstances.length).toBe(2)); // grading + reveal engine

    fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
    await waitFor(() => expect(screen.getByTestId('train-sf-row')).not.toBeNull());
    await act(async () => {
      await Promise.resolve();
    });
    expect(stubbedWorkerInstances.length).toBe(2);
    expect(stubbedWorkerInstances[0]).not.toBe(stubbedWorkerInstances[1]);
    expect(stubbedWorkerInstances[0]!.terminated).not.toBe(true);
    expect(stubbedWorkerInstances[1]!.terminated).not.toBe(true);
  });

  it('SOLV-02: two post-verdict forks never reach grading or the solve POST: solvePuzzle runs once and the grading Worker is asked for no further search', async () => {
    stubWorker(() => new RecordingFakeWorker());
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();
    await waitFor(() => expect(stubbedWorkerInstances.length).toBe(2));
    const gradingWorker = stubbedWorkerInstances[0] as RecordingFakeWorker;
    const gradingSearchesAtVerdict = gradingWorker.goCount;
    expect(solvePuzzle).toHaveBeenCalledTimes(1);

    const board = () => screen.getByTestId('chessboard');
    fireEvent.click(screen.getByTestId('drop-d2d4')); // fork 1
    await waitFor(() => expect(board().getAttribute('data-position')).toContain('3P4'));
    fireEvent.click(screen.getByTestId('drop-d7d5')); // extends the sideline
    await waitFor(() => expect(board().getAttribute('data-position')).toContain('3p4'));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 250));
    });

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    expect(gradingWorker.goCount).toBe(gradingSearchesAtVerdict);
    expect(stubbedWorkerInstances.length).toBe(2);
  });

  it('a puzzle transition from a sideline tears down the reveal engine Worker, and the next puzzle opens at the root with no sidelines', async () => {
    composeOrResumeSession.mockResolvedValue(makeSession());
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const puzzle1 = makePuzzle({ position: 1 });
    const { rerender } = render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            <Harness puzzle={puzzle1} />
          </TooltipProvider>
        </QueryClientProvider>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());

    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();
    await waitFor(() => expect(stubbedWorkerInstances.length).toBe(2)); // grading + reveal engine
    fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
    await waitFor(() => expect(screen.getByTestId('train-sf-row')).not.toBeNull());
    const revealWorker = stubbedWorkerInstances[1]!;
    expect(revealWorker.terminated).not.toBe(true);

    // Transition to a new puzzle (Train.tsx hands TrainSolveScreen a new
    // `puzzle` prop on the SAME component instance, never a remount). The
    // per-puzzle reset is keyed on puzzle.fen, so the fixture needs a genuinely
    // DIFFERENT fen, not just a different position/ply.
    const puzzle2 = makePuzzle({
      position: 2,
      ply: 30,
      fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
    });
    rerender(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            <Harness puzzle={puzzle2} />
          </TooltipProvider>
        </QueryClientProvider>
      </MemoryRouter>,
    );

    await waitFor(() => expect(revealWorker.terminated).toBe(true));
    // The new puzzle renders the pristine pre-verdict screen: no move list, no
    // sideline carried forward, no action bar, no Stockfish row.
    expect(screen.queryByTestId('train-move-tree')).toBeNull();
    expect(document.querySelector('[data-testid^="btn-delete-line-"]')).toBeNull();
    expect(screen.queryByTestId('train-sf-row')).toBeNull();
    expect(screen.queryByTestId('train-reveal-action-bar')).toBeNull();
  });

  it("off the known lines the board carries exactly the reveal engine's blue best-move arrow, and the reveal arrows return after Solution", async () => {
    // Second Worker = the reveal engine; its PV must be a LEGAL move from the
    // sideline position (after 1.d4, black to move), so 'e7e5'.
    let workerCallCount = 0;
    stubWorker(() => {
      workerCallCount += 1;
      return workerCallCount === 1 ? new FakeWorker() : new FakeWorker('e7e5', 'e7e5');
    });
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() =>
      expect(Number(screen.getByTestId('chessboard').getAttribute('data-arrows-count'))).toBeGreaterThan(
        0,
      ),
    );
    const revealArrowCount = Number(screen.getByTestId('chessboard').getAttribute('data-arrows-count'));
    const revealMarkerCount = Number(screen.getByTestId('chessboard').getAttribute('data-markers-count'));
    expect(revealMarkerCount).toBeGreaterThan(0);

    fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
    // Phase 200 UAT round 5: off the known lines the engine's top move is a blue
    // arrow, exactly like the analysis board. Exactly ONE arrow: the reveal
    // overlay (your/best/game/alternatives) stays off.
    const board = () => screen.getByTestId('chessboard');
    await waitFor(() => expect(board().getAttribute('data-arrows-count')).toBe('1'));
    expect(board().getAttribute('data-arrow-ucis')).toBe('e7e5');
    expect(board().getAttribute('data-arrow-colors')).toBe(TRAIN_BEST_MOVE_ARROW);
    // The freely played move carries its own live quality badge, and the seeded
    // parent eval makes the FIRST one resolve without waiting on the engine.
    await waitFor(() => expect(board().getAttribute('data-markers-count')).toBe('1'));

    fireEvent.click(screen.getByTestId('board-btn-reset'));
    await waitFor(() =>
      expect(Number(screen.getByTestId('chessboard').getAttribute('data-arrows-count'))).toBe(
        revealArrowCount,
      ),
    );
    expect(Number(screen.getByTestId('chessboard').getAttribute('data-markers-count'))).toBe(
      revealMarkerCount,
    );
  });

  it('Stockfish arrows 0 (Phase 228 D-13): a sideline draws no live arrow, yet the reveal legend arrows still draw and return after Solution', async () => {
    localStorage.setItem(SETTINGS_STORAGE_KEYS.sfArrows, '0');
    let workerCallCount = 0;
    stubWorker(() => {
      workerCallCount += 1;
      return workerCallCount === 1 ? new FakeWorker() : new FakeWorker('e7e5', 'e7e5');
    });
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    // The setting must NOT touch the reveal legend arrows (blue best, green
    // also-fine, game-move): the pristine reveal still draws them.
    await waitFor(() =>
      expect(Number(screen.getByTestId('chessboard').getAttribute('data-arrows-count'))).toBeGreaterThan(0),
    );
    const revealArrowCount = Number(screen.getByTestId('chessboard').getAttribute('data-arrows-count'));

    fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
    const board = () => screen.getByTestId('chessboard');
    await waitFor(() => expect(board().getAttribute('data-markers-count')).toBe('1'));
    expect(board().getAttribute('data-arrows-count')).toBe('0');

    fireEvent.click(screen.getByTestId('board-btn-reset'));
    await waitFor(() =>
      expect(Number(board().getAttribute('data-arrows-count'))).toBe(revealArrowCount),
    );
  });

  it('the Analyze link href is unchanged on a sideline (EXPLORE-06)', async () => {
    await renderScreen(makePuzzle({ game_id: 100, ply: 20 }));
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.getByTestId('btn-train-analyze')).not.toBeNull());
    const hrefBefore = screen.getByTestId('btn-train-analyze').getAttribute('href');
    expect(hrefBefore).toBe(buildGameAnalysisUrl(100, 19));

    fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
    await waitFor(() =>
      expect((screen.getByTestId('board-btn-reset') as HTMLButtonElement).disabled).toBe(false),
    );
    expect(screen.getByTestId('btn-train-analyze').getAttribute('href')).toBe(hrefBefore);
  });

  // ─── Phase 237 plan 06 (D-03): the Stockfish row off the known lines ───────

  it('a sideline shows the Stockfish row; clicking a move in it plays it into the sideline as one engine-line move', async () => {
    let workerCallCount = 0;
    stubWorker(() => {
      workerCallCount += 1;
      // First Worker = the session-scoped grading engine. Second = the reveal
      // engine, whose PV must be LEGAL from the sideline position (after 1.d4,
      // black to move), so 'e7e5'.
      return workerCallCount === 1 ? new FakeWorker() : new FakeWorker('e7e5', 'e7e5');
    });

    const { board, moveList } = await startSideline();
    // The move list is the one tree: the user's fork is already in it.
    expect(within(moveList()).getByText('d4')).not.toBeNull();
    // On the known lines the row is absent; here it is present.
    expect(screen.getByTestId('train-sf-row')).not.toBeNull();

    await waitFor(() => expect(screen.getByTestId('engine-line-0-move-0')).not.toBeNull());
    const positionBeforeClick = board().getAttribute('data-position');
    fireEvent.click(screen.getByTestId('engine-line-0-move-0'));
    await waitFor(() => expect(board().getAttribute('data-position')).not.toBe(positionBeforeClick));
    expect(within(moveList()).getByText('e5')).not.toBeNull();
  });

  it('the Stockfish row is absent on the known lines and again after a tap back onto one', async () => {
    const { board } = await startSideline();
    expect(screen.getByTestId('train-sf-row')).not.toBeNull();

    // Solution rewinds to the puzzle position: a known line (and the root).
    fireEvent.click(screen.getByTestId('board-btn-reset'));
    await waitFor(() => expect(board().getAttribute('data-position')).toBe(START_FEN));
    expect(screen.queryByTestId('train-sf-row')).toBeNull();

    // Stepping into the played/best line (e2e4) keeps the row away.
    fireEvent.click(screen.getByTestId('drop-e2e4'));
    await waitFor(() => expect(board().getAttribute('data-position')).not.toBe(START_FEN));
    expect(screen.queryByTestId('train-sf-row')).toBeNull();
  });

  // Phase 237 UAT: the row follows the analysis board's layout. It was capped at
  // two lines whatever the setting, behind a row toggle beside each line's chevron.
  it('on desktop the Stockfish row shows every configured line, wrapping (no sideways scroll)', async () => {
    localStorage.setItem(SETTINGS_STORAGE_KEYS.sfLines, '3');
    await startSideline();
    await waitFor(() => expect(screen.getByTestId('engine-line-2-move-0')).not.toBeNull());
    expect(screen.getByTestId('engine-line-0-move-0').closest('.overflow-x-auto')).toBeNull();
  });

  it('on mobile the Stockfish row shows every configured line, each scrolling sideways', async () => {
    localStorage.setItem(SETTINGS_STORAGE_KEYS.sfLines, '3');
    matchMediaMatches = false;
    await startSideline();
    await waitFor(() => expect(screen.getByTestId('engine-line-2-move-0')).not.toBeNull());
    expect(screen.getByTestId('engine-line-0-move-0').closest('.overflow-x-auto')).not.toBeNull();
  });

  // ─── Phase 200 UAT: sidelines + move quality ──────────────────────────────

  it('a move played from a jumped-back position FORKS a sideline instead of truncating it: both continuations stay in the move list', async () => {
    const { moveList } = await startSideline(); // 1. d4 (root fork)
    fireEvent.click(screen.getByTestId('drop-e7e5')); // 1... e5
    await waitFor(() => expect(within(moveList()).getByText('e5')).not.toBeNull());

    // Jump back to the position after 1.d4 and play a DIFFERENT black move.
    fireEvent.click(within(moveList()).getByText('d4'));
    fireEvent.click(screen.getByTestId('drop-d7d5')); // 1... d5

    // The analysis board's fork semantics: e5 survives alongside d5.
    await waitFor(() => expect(within(moveList()).getByText('d5')).not.toBeNull());
    expect(within(moveList()).getByText('e5')).not.toBeNull();
  });

  it('the sideline move list badges the played move with its quality: never a gem/great glyph, since Train runs no Maia', async () => {
    let workerCallCount = 0;
    stubWorker(() => {
      workerCallCount += 1;
      // The reveal engine's top move after 1.d4 is e7e5 (legal for black).
      return workerCallCount === 1 ? new FakeWorker() : new FakeWorker('e7e5', 'e7e5');
    });
    const { moveList } = await startSideline();
    // Wait for the reveal engine to have searched the d4 position, so playing
    // its top move grades 'best' against the cached parent.
    await waitFor(() => expect(screen.getByTestId('engine-line-0-move-0')).not.toBeNull());
    fireEvent.click(screen.getByTestId('drop-e7e5'));
    await waitFor(() => expect(within(moveList()).getByText('e5')).not.toBeNull());

    // The badge icons carry an SVG <title> as their accessible name.
    const badgeTitles = (): string[] =>
      [...moveList().querySelectorAll('svg > title')].map((t) => t.textContent ?? '');
    await waitFor(() => expect(badgeTitles()).toContain('Best move'));
    expect(badgeTitles()).not.toContain('Gem move');
    expect(badgeTitles()).not.toContain('Great move');
  });

  // Phase 205 (D-04, ORACLE-02): the root-only boundary. The served vetted list
  // describes the PUZZLE position only: consulting it at a DEEPER ply would grade
  // a move against a key for a DIFFERENT position, exactly the failure mode this
  // test exists to catch.
  it('ORACLE-02: a served vetted move replayed at ply 3 (not the root) is graded from the engine\'s own parent/child pair: a scripted bad score still badges it worse', async () => {
    const afterSequence = new Chess(START_FEN);
    afterSequence.move('d4');
    afterSequence.move('d5');
    afterSequence.move('c4'); // a SERVED vetted move, replayed at ply 3
    const fenAfterSequence = afterSequence.fen();
    stubWorker(() => new ScriptedFenFakeWorker(START_FEN, { [fenAfterSequence]: -900 }));
    solvePuzzle.mockResolvedValueOnce({
      ...SOLVE_RESPONSE,
      puzzle_type: 'soft',
      vetted_moves: [{ uci: 'c2c4', quality: 'good' }],
    });

    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4')); // graded move -> lands the verdict
    });
    await waitForReveal();

    const moveList = () => screen.getByTestId('train-move-tree');
    fireEvent.click(screen.getByTestId('drop-d2d4')); // ply 1 (root fork)
    await waitFor(() => expect(within(moveList()).getByText('d4')).not.toBeNull());
    fireEvent.click(screen.getByTestId('drop-d7d5')); // ply 2: a reply
    await waitFor(() => expect(within(moveList()).getByText('d5')).not.toBeNull());
    // Let ply 2's own position finish its reveal-engine search (debounce +
    // microtask-deferred response) BEFORE playing ply 3: otherwise React's effect
    // cleanup cancels ply 2's pending debounce the instant ply 3's FEN changes,
    // and its eval never lands in the cache.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 250));
    });

    // ply 3: the served vetted move (c2c4) at a DEEPER ply. A build that widened
    // the root-only gate to every ply would wrongly consult the served list by
    // squares alone and badge this 'good'; the correct build grades it from THIS
    // ply's own parent/child pair (the engine's scripted, catastrophic score).
    fireEvent.click(screen.getByTestId('drop-c2c4'));
    const board = () => screen.getByTestId('chessboard');
    await waitFor(() =>
      expect(board().getAttribute('data-last-move-color')).toBe(TRAIN_STEP_HIGHLIGHT.blunder),
    );
  });

  // ─── Sideline stepping through the published phone bottom bar ─────────────
  //
  // Back/forward/rewind/flip are published to the phone bottom bar for the whole
  // reveal (plan 07); these tests drive them off a sideline.

  async function startSidelineWithProbe() {
    await renderScreenWithProbe(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();
    fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
    await waitFor(() =>
      expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true'),
    );
    return {
      board: () => screen.getByTestId('chessboard'),
      moveList: () => screen.getByTestId('train-move-tree'),
    };
  }

  it('the published controls step back and forward through the sideline, and Reset returns to the puzzle position while the sideline stays listed', async () => {
    const { board, moveList } = await startSidelineWithProbe();
    const afterD4 = board().getAttribute('data-position');
    fireEvent.click(screen.getByTestId('drop-e7e5'));
    await waitFor(() => expect(within(moveList()).getByText('e5')).not.toBeNull());
    const afterD4E5 = board().getAttribute('data-position');

    fireEvent.click(screen.getByTestId('mbc-btn-back'));
    await waitFor(() => expect(board().getAttribute('data-position')).toBe(afterD4));
    fireEvent.click(screen.getByTestId('mbc-btn-forward'));
    await waitFor(() => expect(board().getAttribute('data-position')).toBe(afterD4E5));

    // Reset lands on the puzzle position but keeps the tree: the sideline is
    // still listed.
    fireEvent.click(screen.getByTestId('mbc-btn-reset'));
    await waitFor(() => expect(board().getAttribute('data-position')).toBe(START_FEN));
    expect(within(moveList()).getByText('e5')).not.toBeNull();
    expect(within(moveList()).getByText('d4')).not.toBeNull();
  });

  it('at the tip of the sideline Forward is disabled and Back and Reset are live; at the puzzle position Reset is disabled but the bar stays published', async () => {
    const { board } = await startSidelineWithProbe();
    expect(screen.getByTestId('mbc-can-go-forward').textContent).toBe('false');
    expect(screen.getByTestId('mbc-can-go-back').textContent).toBe('true');
    expect(screen.getByTestId('mbc-can-reset').textContent).toBe('true');

    fireEvent.click(screen.getByTestId('mbc-btn-reset'));
    await waitFor(() => expect(board().getAttribute('data-position')).toBe(START_FEN));
    // Published for the whole reveal: the bar stays, with Reset disabled at the root.
    expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true');
    expect(screen.getByTestId('mbc-can-reset').textContent).toBe('false');
  });

  it('the published flip toggles board orientation, and a puzzle transition restores the solver-color default', async () => {
    smUpMatches = false; // phone: only the published bottom-bar payload exists
    composeOrResumeSession.mockResolvedValue(makeSession());
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const renderTree = (puzzle: TrainPuzzle): ReactElement => (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            <MobileBoardControlsProbe />
            <Harness puzzle={puzzle} />
          </TooltipProvider>
        </QueryClientProvider>
      </MemoryRouter>
    );
    const { rerender } = render(renderTree(makePuzzle({ position: 1 })));
    await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());

    const board = () => screen.getByTestId('chessboard');
    expect(board().getAttribute('data-flipped')).toBe('false'); // white to move
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();
    fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
    await waitFor(() =>
      expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true'),
    );

    fireEvent.click(screen.getByTestId('mbc-btn-flip'));
    await waitFor(() => expect(board().getAttribute('data-flipped')).toBe('true'));

    // Orientation is a per-position affordance, not a session preference: the
    // next puzzle starts at its own solver-color default again.
    rerender(
      renderTree(
        makePuzzle({
          position: 2,
          ply: 30,
          fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
        }),
      ),
    );
    await waitFor(() => expect(board().getAttribute('data-flipped')).toBe('false'));
  });

  // ─── Phase 237 plan 06 (D-04): a move no chip owns deselects every chip ────

  it('D-04: a hand-played move that matches a line lights that chip without creating a sideline; a move that matches none deselects every chip and lists only the user line', async () => {
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4')); // played d4 against the best e4 -> separate chips
    });
    await waitForReveal();
    await waitFor(() => expect(screen.getByTestId('train-chip-best')).not.toBeNull());
    const pressed = (testId: string) => screen.getByTestId(testId).getAttribute('aria-pressed');
    expect(pressed('train-chip-your')).toBe('true');

    // Playing the best move by hand from the root lights the Best chip and is a
    // board move along the known line, not a fork.
    fireEvent.click(screen.getByTestId('drop-e2e4'));
    await waitFor(() => expect(pressed('train-chip-best')).toBe('true'));
    expect(pressed('train-chip-your')).toBe('false');
    expect(document.querySelector('[data-testid^="btn-delete-line-"]')).toBeNull();
    expect(screen.queryByTestId('train-sf-row')).toBeNull();

    // Back at the puzzle position, a move that matches no line forks.
    fireEvent.click(screen.getByTestId('board-btn-reset'));
    await waitFor(() =>
      expect(screen.getByTestId('chessboard').getAttribute('data-position')).toBe(START_FEN),
    );
    fireEvent.click(screen.getByTestId('drop-b1c3'));
    await waitFor(() => expect(screen.getByTestId('train-sf-row')).not.toBeNull());
    expect(pressed('train-chip-your')).toBe('false');
    expect(pressed('train-chip-best')).toBe('false');
    const list = screen.getByTestId('train-move-tree');
    expect(within(list).getByText('Nc3')).not.toBeNull();
    // Only the user's own line is listed: neither known line shows.
    expect(within(list).queryByText('d4')).toBeNull();
    expect(within(list).queryByText('e4')).toBeNull();
  });

  // ─── Phase 237 plan 06 (D-14): Umami events for sideline forks ────────────

  describe('sideline feature events (D-14)', () => {
    const track = vi.fn();
    const trackedTargets = (target: string): unknown[][] =>
      track.mock.calls.filter((call) => (call[1] as { target?: string } | undefined)?.target === target);

    beforeEach(() => {
      track.mockClear();
      window.umami = { track, identify: vi.fn() };
      window.history.pushState({}, '', '/train');
    });

    afterEach(() => {
      delete window.umami;
      window.history.pushState({}, '', '/');
    });

    async function landVerdict(): Promise<void> {
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitForReveal();
    }

    it('the FIRST fork per puzzle sends exactly one train-sideline-fork action; a second fork and a hand-played known-line move send nothing', async () => {
      await renderScreen(makePuzzle());
      await landVerdict();
      expect(trackedTargets('train-sideline-fork')).toHaveLength(0);

      // A hand-played move along the known line (played = best = e2e4) is a
      // board move, not a fork: no event.
      fireEvent.click(screen.getByTestId('drop-e2e4'));
      await waitFor(() =>
        expect(screen.getByTestId('chessboard').getAttribute('data-position')).not.toBe(START_FEN),
      );
      expect(trackedTargets('train-sideline-fork')).toHaveLength(0);

      fireEvent.click(screen.getByTestId('board-btn-reset'));
      await waitFor(() =>
        expect(screen.getByTestId('chessboard').getAttribute('data-position')).toBe(START_FEN),
      );
      fireEvent.click(screen.getByTestId('drop-d2d4')); // the first fork
      await waitFor(() => expect(screen.getByTestId('train-sf-row')).not.toBeNull());
      expect(trackedTargets('train-sideline-fork')).toHaveLength(1);
      expect(trackedTargets('train-sideline-fork')[0]).toEqual([
        'action',
        { page: 'train', target: 'train-sideline-fork' },
      ]);

      fireEvent.click(screen.getByTestId('drop-d7d5')); // extends it: a second fork
      await waitFor(() =>
        expect(screen.getByTestId('chessboard').getAttribute('data-position')).toContain('3p4'),
      );
      expect(trackedTargets('train-sideline-fork')).toHaveLength(1);
    });

    it('rewind sends exactly one train-solution action per press and nothing on render (D-14)', async () => {
      await renderScreen(makePuzzle());
      await landVerdict();
      expect(trackedTargets('train-solution')).toHaveLength(0);

      fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
      await waitFor(() =>
        expect((screen.getByTestId('board-btn-reset') as HTMLButtonElement).disabled).toBe(false),
      );
      expect(trackedTargets('train-solution')).toHaveLength(0);

      fireEvent.click(screen.getByTestId('board-btn-reset'));
      await waitFor(() =>
        expect(screen.getByTestId('chessboard').getAttribute('data-position')).toBe(START_FEN),
      );
      expect(trackedTargets('train-solution')).toHaveLength(1);
      expect(trackedTargets('train-solution')[0]).toEqual([
        'action',
        { page: 'train', target: 'train-solution' },
      ]);
    });

    it('closing a sideline with its x sends the existing board-tool line-delete event', async () => {
      await renderScreen(makePuzzle());
      await landVerdict();
      fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
      await waitFor(() => expect(screen.getByTestId('train-sf-row')).not.toBeNull());
      const close = screen
        .getByTestId('train-move-tree')
        .querySelector('[data-testid^="btn-delete-line-"]');
      expect(close).not.toBeNull();

      fireEvent.click(close!);

      expect(trackedTargets('line-delete')).toEqual([
        ['board-tool', { page: 'train', target: 'line-delete' }],
      ]);
      expect(screen.queryByTestId('train-sf-row')).toBeNull();
    });

    it('mounting a restored reveal sends no sideline event', async () => {
      const restoredPuzzle = makePuzzle();
      const restoredCached = JSON.parse(
        JSON.stringify({
          sessionId: 1,
          puzzle: restoredPuzzle,
          verdict: SOLVE_RESPONSE,
          guess: 'critical',
          playedMoveUci: 'e2e4',
          gradeResult: {
            moveTier: 'good',
            bestMoveUci: 'e2e4',
            esBefore: 0.5,
            esAfter: 0.5,
            bestLine: { moves: ['e2e4'], evalCp: 19, evalMate: null },
            playedLine: { moves: ['e2e4'], evalCp: 19, evalMate: null },
          },
        }),
      ) as CachedTrainReveal;

      await renderScreen(restoredPuzzle, makeSession(), restoredCached);
      await waitForReveal();
      await act(async () => {
        await Promise.resolve();
      });

      expect(trackedTargets('train-sideline-fork')).toHaveLength(0);
    });
  });

  // ─── Quick 260803-iv6 (Task 1): live Stockfish eval bar beside the board ──

  describe('live Stockfish eval bar', () => {
    it('is absent while the guess buttons are on screen and while grading is in flight, and present with a real evaluation once the reveal opens', async () => {
      await renderScreen(makePuzzle());
      expect(screen.queryByTestId('train-eval-bar')).toBeNull();
      // Phase 222 UAT round 3: an empty frame fills the slot until the reveal.
      expect(screen.getByTestId('train-eval-bar-placeholder')).not.toBeNull();

      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      expect(screen.queryByTestId('train-eval-bar')).toBeNull(); // T-iv6-01: guess committed, no move yet

      // Non-exact move -> a second grading search runs. Checked SYNCHRONOUSLY
      // (no intervening `await`/`waitFor`) — the FakeWorker's response is
      // already microtask-queued by the time `fireEvent.click` returns, so an
      // `await` here would let it drain before this assertion runs.
      fireEvent.click(screen.getByTestId('drop-d2d4'));
      expect(screen.getByTestId('train-grading-indicator')).not.toBeNull();
      expect(screen.queryByTestId('train-eval-bar')).toBeNull(); // T-iv6-01: verdict not landed yet

      await waitForReveal();
      await waitFor(() => expect(screen.getByTestId('train-eval-bar')).not.toBeNull());
      expect(screen.queryByTestId('train-eval-bar-placeholder')).toBeNull();
      // aria-label reflects a real engine evaluation, not the 0.00 neutral
      // reading a still-idle bar would show.
      await waitFor(() => {
        const label = screen.getByTestId('train-eval-bar').getAttribute('aria-label') ?? '';
        expect(label).not.toBe('Engine evaluation: 0.00');
      });
    });

    it('follows the board through reveal-line stepping — the SAME FEN the ChessBoard renders drives the bar', async () => {
      stubWorker(() => new FakeWorker('e2e4', 'e2e4 e7e5'));
      await renderScreen(makePuzzle({ last_move_uci: 'd7d5' }));
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4')); // exact match -> played IS best
      });
      await waitFor(() => expect(screen.getByTestId('train-eval-bar')).not.toBeNull());

      const board = () => screen.getByTestId('chessboard');
      const positionAtSolution = board().getAttribute('data-position');

      // Step into the merged your/best box's line — the board moves off the
      // puzzle position, and the bar must stay mounted and keep tracking it
      // (never disappear just because the position is no longer the puzzle's).
      tapListMove(0);
      await waitFor(() => expect(board().getAttribute('data-position')).not.toBe(positionAtSolution));
      expect(screen.getByTestId('train-eval-bar')).not.toBeNull();
      await waitFor(() => {
        const label = screen.getByTestId('train-eval-bar').getAttribute('aria-label') ?? '';
        expect(label).not.toBe('Engine evaluation: 0.00');
      });
    });

    it('on a sideline the bar reads the one reveal engine: no second concurrent search, and the bar keeps a real evaluation', async () => {
      let workerCallCount = 0;
      stubWorker(() => {
        workerCallCount += 1;
        // [0] grading, [1] the reveal engine (it follows the shown position, so
        // its PV must be legal from the sideline position too: black to move).
        return workerCallCount <= 1 ? new FakeWorker() : new FakeWorker('e7e5', 'e7e5');
      });
      await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitFor(() => expect(screen.getByTestId('train-eval-bar')).not.toBeNull());
      await waitFor(() => expect(stubbedWorkerInstances.length).toBe(2)); // grading + reveal engine

      fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
      await waitFor(() => expect(screen.getByTestId('train-sf-row')).not.toBeNull());
      await act(async () => {
        await Promise.resolve();
      });
      // No second engine: the same two Workers, neither torn down.
      expect(stubbedWorkerInstances.length).toBe(2);
      expect(stubbedWorkerInstances[1]!.terminated).not.toBe(true);
      // The bar keeps rendering, fed by the reveal engine's reading of the sideline.
      expect(screen.getByTestId('train-eval-bar')).not.toBeNull();
      await waitFor(() => {
        const label = screen.getByTestId('train-eval-bar').getAttribute('aria-label') ?? '';
        expect(label).not.toBe('Engine evaluation: 0.00');
      });
    });
  });

  // ─── Phase 237 plan 07: desktop keyboard (ArrowLeft / ArrowRight / Home) ──────
  describe('desktop keyboard navigation', () => {
    const position = () => screen.getByTestId('chessboard').getAttribute('data-position');

    async function landVerdictOnYourLine(): Promise<void> {
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitForReveal();
    }

    it('does nothing before the verdict lands', async () => {
      await renderScreen(makePuzzle());
      expect(position()).toBe(START_FEN);
      // Inert: the hook never attaches a container, so the key is not even
      // default-prevented (fireEvent returns false when it was).
      expect(fireEvent.keyDown(window, { key: 'ArrowRight' })).toBe(true);
      expect(fireEvent.keyDown(window, { key: 'Home' })).toBe(true);
      expect(position()).toBe(START_FEN);
    });

    it('ArrowRight steps into the focused chip\'s line, ArrowLeft returns, Home returns from deeper in the line', async () => {
      await renderScreen(makePuzzle());
      await landVerdictOnYourLine();
      expect(position()).toBe(START_FEN);

      fireEvent.keyDown(window, { key: 'ArrowRight' });
      await waitFor(() => expect(position()).not.toBe(START_FEN));
      const afterFirst = position();

      fireEvent.keyDown(window, { key: 'ArrowLeft' });
      await waitFor(() => expect(position()).toBe(START_FEN));

      // Go in again, then deeper (a hand-played reply), then Home straight back.
      fireEvent.keyDown(window, { key: 'ArrowRight' });
      await waitFor(() => expect(position()).toBe(afterFirst));
      fireEvent.click(screen.getByTestId('drop-e7e5'));
      await waitFor(() => expect(position()).not.toBe(afterFirst));
      fireEvent.keyDown(window, { key: 'Home' });
      await waitFor(() => expect(position()).toBe(START_FEN));
    });
  });

  // ─── Quick 260809-g0n / Phase 237 plan 06: publishes mobileBoardControls while
  // the board is off the puzzle position, for MobileBottomBar's footer swap ──
  describe('mobileBoardControls publishing', () => {
    it('publishes nothing before a verdict lands', async () => {
      await renderScreenWithProbe(makePuzzle());
      expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('false');
    });

    it('publishes for the whole reveal once the verdict lands, also at the puzzle position, with Next and the Analyze URL', async () => {
      await renderScreenWithProbe(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitForReveal();
      await waitFor(() =>
        expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true'),
      );
      // At the puzzle position: nothing to rewind or step back into, but the bar is there.
      expect(screen.getByTestId('mbc-can-reset').textContent).toBe('false');
      expect(screen.getByTestId('mbc-can-go-back').textContent).toBe('false');
      expect(screen.getByTestId('mbc-has-next').textContent).toBe('true');
      // Below `sm` the in-flow Analyze link is not mounted (WR-02), so the payload's
      // URL is checked against the builder, not a DOM href.
      expect(screen.getByTestId('mbc-analyze-to').textContent).toBe(buildGameAnalysisUrl(100, 19));
      expect(screen.queryByTestId('btn-train-analyze')).toBeNull();
    });

    it('a puzzle without a source game publishes analyzeTo null', async () => {
      await renderScreenWithProbe(makePuzzle({ game_id: null }));
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitFor(() =>
        expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true'),
      );
      expect(screen.getByTestId('mbc-analyze-to').textContent).toBe('null');
    });

    it('the published onNext leaves the reveal like the in-flow Next (review flushed once with exit next)', async () => {
      nextFlush.mockClear();
      await renderScreenWithProbe(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitFor(() =>
        expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true'),
      );
      fireEvent.click(screen.getByTestId('mbc-btn-next'));
      await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    });

    it("the published bar's Next walks the tour to its last step without flushing", async () => {
      getSettings.mockResolvedValue(makeSettings({ reveal_walkthrough_seen_at: null }));
      await renderScreenWithProbe(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitFor(() => expect(screen.getByTestId('train-bot-walkthrough')).not.toBeNull());
      // Phase 237 UAT (G-01): the published bar's Next walks the tour.
      for (let click = 0; click < WALKTHROUGH_STEP_COUNT - 1; click += 1) {
        fireEvent.click(screen.getByTestId('mbc-btn-next'));
      }
      await waitFor(() =>
        expect(screen.getByTestId('train-tour-step-count').textContent).toBe(
          `${WALKTHROUGH_STEP_COUNT} / ${WALKTHROUGH_STEP_COUNT}`,
        ),
      );
      expect(nextFlush).not.toHaveBeenCalled();
    });

    it('forking a sideline publishes a payload mirroring the tree: back and reset live, forward disabled at the tip', async () => {
      await renderScreenWithProbe(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4')); // the graded attempt
      });
      await waitForReveal();

      fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline

      await waitFor(() =>
        expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true'),
      );
      // One move in: at the tip (nothing to advance into) but back/reset are live.
      expect(screen.getByTestId('mbc-can-go-back').textContent).toBe('true');
      expect(screen.getByTestId('mbc-can-go-forward').textContent).toBe('false');
      expect(screen.getByTestId('mbc-can-reset').textContent).toBe('true');
    });

    it('rewinding (back on the puzzle position) keeps the payload published with reset disabled', async () => {
      await renderScreenWithProbe(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitForReveal();
      fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
      await waitFor(() =>
        expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true'),
      );

      fireEvent.click(screen.getByTestId('mbc-btn-reset'));
      await waitFor(() => expect(screen.getByTestId('mbc-can-reset').textContent).toBe('false'));
      expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true');
    });

    it('unmounting the solve screen clears the published payload', async () => {
      const { unmount } = await renderScreenWithProbe(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitForReveal();
      fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
      await waitFor(() =>
        expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true'),
      );

      unmount();
      // The probe unmounted too (same tree), so re-render a fresh one to read
      // the store's post-unmount state.
      render(
        <MemoryRouter>
          <TooltipProvider>
            <MobileBoardControlsProbe />
          </TooltipProvider>
        </MemoryRouter>,
      );
      expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('false');
    });

    it('invoking the published onReset returns the board to the puzzle position while the sideline stays listed', async () => {
      await renderScreenWithProbe(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitForReveal();
      fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
      await waitFor(() =>
        expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true'),
      );

      const board = () => screen.getByTestId('chessboard');
      fireEvent.click(screen.getByTestId('mbc-btn-reset'));
      await waitFor(() => expect(board().getAttribute('data-position')).toBe(START_FEN));
      expect(within(screen.getByTestId('train-move-tree')).getByText('d4')).not.toBeNull();
    });

    it('invoking the published onFlip flips the shared board', async () => {
      await renderScreenWithProbe(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitForReveal();
      fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
      await waitFor(() =>
        expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true'),
      );

      const board = () => screen.getByTestId('chessboard');
      expect(board().getAttribute('data-flipped')).toBe('false'); // white to move
      fireEvent.click(screen.getByTestId('mbc-btn-flip'));
      await waitFor(() => expect(board().getAttribute('data-flipped')).toBe('true'));
    });

    it('a flip survives a rewind (flip is a permanent bar control now)', async () => {
      await renderScreenWithProbe(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitForReveal();
      fireEvent.click(screen.getByTestId('drop-d2d4')); // forks a sideline
      await waitFor(() =>
        expect(screen.getByTestId('mbc-probe').getAttribute('data-published')).toBe('true'),
      );

      const board = () => screen.getByTestId('chessboard');
      fireEvent.click(screen.getByTestId('mbc-btn-flip'));
      await waitFor(() => expect(board().getAttribute('data-flipped')).toBe('true'));

      // Rewind returns to the puzzle position and leaves the orientation alone.
      fireEvent.click(screen.getByTestId('mbc-btn-reset'));
      await waitFor(() => expect(screen.getByTestId('mbc-can-reset').textContent).toBe('false'));
      expect(board().getAttribute('data-flipped')).toBe('true');
    });
  });

  describe('Phase 222: first-session intro stepper (D-05/D-12/D-22)', () => {
    it('renders Hilda\'s welcome with a Next control and no guess buttons when intro_seen_at is null', async () => {
      getSettings.mockResolvedValue(makeSettings({ intro_seen_at: null }));
      await renderScreen(makePuzzle());
      expect(screen.getByTestId('train-bot-name').textContent).toBe('Hilda the Hippo');
      expect(screen.getByTestId('train-bot-copy').textContent).toContain('Welcome to FlawChess Train!');
      expect(screen.queryByTestId('btn-train-guess-critical')).toBeNull();
      expect(screen.queryByTestId('btn-train-guess-several')).toBeNull();
      expect(screen.getByTestId('btn-train-bot-step-next')).not.toBeNull();
    });

    // Plan 06 UAT: short steps instead of three long ones, so nothing scrolls
    // inside the phone bubble — four Next clicks reach the guess buttons on a
    // regular session. Phase 237 UAT: Hilda hosts every step, the welcome too.
    it('advances through the Hilda steps, showing the guess buttons only on the closing step', async () => {
      getSettings.mockResolvedValue(makeSettings({ intro_seen_at: null }));
      await renderScreen(makePuzzle());
      await waitFor(() =>
        expect(screen.getByTestId('train-bot-copy').textContent).toContain('Welcome to FlawChess Train!'),
      );
      expect(screen.getByTestId('train-bot-name').textContent).toBe('Hilda the Hippo');
      fireEvent.click(screen.getByTestId('btn-train-bot-step-next'));
      await waitFor(() =>
        expect(screen.getByTestId('train-bot-copy').textContent).not.toContain('Welcome'),
      );
      expect(screen.getByTestId('train-bot-name').textContent).toBe('Hilda the Hippo');
      expect(screen.queryByTestId('btn-train-guess-critical')).toBeNull();
      for (let click = 0; click < introStepCount(false, { hasGames: true, isGuest: false }) - 2; click += 1) {
        expect(screen.queryByTestId('btn-train-guess-critical')).toBeNull();
        fireEvent.click(screen.getByTestId('btn-train-bot-step-next'));
      }
      await waitFor(() => expect(screen.getByTestId('btn-train-guess-critical')).not.toBeNull());
      expect(screen.getByTestId('train-bot-name').textContent).toBe('Hilda the Hippo');
      expect(screen.getByTestId('btn-train-guess-several')).not.toBeNull();
      expect(screen.queryByTestId('btn-train-bot-step-next')).toBeNull();
      expect(screen.getByTestId('train-bot-copy').textContent).not.toContain('warm-up');
    });

    // Phase 222 UAT round 3: a warm-up first session gets the "still
    // analyzing" step right before the closing guess step.
    it('a warm-up session shows the "still analyzing" step right before the guess buttons', async () => {
      getSettings.mockResolvedValue(makeSettings({ intro_seen_at: null }));
      await renderScreen(makePuzzle(), makeSession({ is_warmup: true }));
      await waitFor(() => expect(screen.getByTestId('btn-train-bot-step-next')).not.toBeNull());
      for (let click = 0; click < introStepCount(true, { hasGames: true, isGuest: false }) - 2; click += 1) {
        fireEvent.click(screen.getByTestId('btn-train-bot-step-next'));
      }
      await waitFor(() =>
        expect(screen.getByTestId('train-bot-copy').textContent).toContain(
          'still analyzing your games',
        ),
      );
      expect(screen.queryByTestId('btn-train-guess-critical')).toBeNull();
      fireEvent.click(screen.getByTestId('btn-train-bot-step-next'));
      await waitFor(() => expect(screen.getByTestId('btn-train-guess-critical')).not.toBeNull());
    });

    it('stamps intro exactly once on the closing-step guess click and commits the guess', async () => {
      getSettings.mockResolvedValue(makeSettings({ intro_seen_at: null }));
      await renderScreen(makePuzzle());
      for (let click = 0; click < introStepCount(false, { hasGames: true, isGuest: false }) - 1; click += 1) {
        fireEvent.click(screen.getByTestId('btn-train-bot-step-next'));
      }
      await waitFor(() => expect(screen.getByTestId('btn-train-guess-critical')).not.toBeNull());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await waitFor(() => expect(stampOnboarding).toHaveBeenCalledTimes(1));
      expect(stampOnboarding).toHaveBeenCalledWith('intro');
      // The guess itself committed too — the bubble moves to the move prompt.
      await waitFor(() => expect(screen.getByTestId('train-move-prompt')).not.toBeNull());
    });

    it('does not stamp when the component unmounts mid-stepper (step 3)', async () => {
      getSettings.mockResolvedValue(makeSettings({ intro_seen_at: null }));
      const { unmount } = await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-bot-step-next'));
      fireEvent.click(screen.getByTestId('btn-train-bot-step-next'));
      await waitFor(() =>
        expect(screen.getByTestId('train-bot-name').textContent).toBe('Hilda the Hippo'),
      );
      unmount();
      expect(stampOnboarding).not.toHaveBeenCalled();
    });

    it('renders no copy and no guess buttons while settings is still loading (cold cache)', async () => {
      let resolveSettings: (value: TrainSettingsResponse) => void = () => {};
      getSettings.mockReturnValue(
        new Promise((resolve) => {
          resolveSettings = resolve;
        }),
      );
      composeOrResumeSession.mockResolvedValue(makeSession());
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <TooltipProvider>
              <Harness puzzle={makePuzzle()} />
            </TooltipProvider>
          </QueryClientProvider>
        </MemoryRouter>,
      );
      await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());
      expect(screen.queryByTestId('train-bot-bubble')).toBeNull();
      expect(screen.queryByTestId('train-guess-prompt')).toBeNull();
      expect(screen.queryByTestId('btn-train-guess-critical')).toBeNull();
      resolveSettings(makeSettings({ intro_seen_at: null }));
      await waitFor(() =>
        expect(screen.getByTestId('train-bot-copy').textContent).toContain('Welcome to FlawChess Train!'),
      );
    });

    // Phase 222 code review CR-01: a settings fetch that FAILS (not merely
    // pending) must not hide the guess prompt on the session's first puzzle.
    it('a failed settings fetch on the first puzzle degrades to the regular prompt, not a blank slot', async () => {
      getSettings.mockRejectedValue(new Error('settings 500'));
      await renderScreen(makePuzzle());
      await waitFor(() => expect(screen.getByTestId('train-guess-prompt')).not.toBeNull());
      expect(screen.getByTestId('btn-train-guess-critical')).not.toBeNull();
      expect(screen.queryByTestId('btn-train-bot-step-next')).toBeNull();
    });

    it('a user who has already completed the intro sees the regular prompt immediately', async () => {
      getSettings.mockResolvedValue(makeSettings({ intro_seen_at: '2026-01-01T00:00:00Z' }));
      await renderScreen(makePuzzle());
      expect(screen.getByTestId('train-guess-prompt')).not.toBeNull();
      expect(screen.getByTestId('btn-train-guess-critical')).not.toBeNull();
    });

    it('the intro does not render on a later puzzle even though intro_seen_at is still null', async () => {
      getSettings.mockResolvedValue(makeSettings({ intro_seen_at: null }));
      const session = makeSession({ solved_count: 1, puzzle_count: 5 });
      await renderScreen(makePuzzle({ position: 2 }), session);
      expect(screen.getByTestId('train-guess-prompt')).not.toBeNull();
      expect(screen.queryByTestId('btn-train-bot-step-next')).toBeNull();
    });
  });

  describe('Phase 222: drop-before-guess nudge (D-08)', () => {
    it('a drop before the guess snaps back and swaps the bubble copy to the nudge line', async () => {
      await renderScreen(makePuzzle());
      const board = () => screen.getByTestId('chessboard');
      fireEvent.click(screen.getByTestId('drop-e2e4'));
      await waitFor(() =>
        expect(screen.getByTestId('train-bot-bubble').getAttribute('data-nudge')).toBe('true'),
      );
      expect(board().getAttribute('data-position')).toBe(START_FEN); // piece snapped back
      expect(screen.getByTestId('train-guess-prompt').textContent).toContain('Decide first');
      // The guess buttons remain visible — the user still needs to answer.
      expect(screen.getByTestId('btn-train-guess-critical')).not.toBeNull();
    });

    it('a second drop while still unguessed replays the nudge — the bubble content remounts', async () => {
      await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('drop-e2e4'));
      await waitFor(() =>
        expect(screen.getByTestId('train-bot-bubble').getAttribute('data-nudge')).toBe('true'),
      );
      const firstNode = screen.getByTestId('train-bot-copy');
      fireEvent.click(screen.getByTestId('drop-d2d4'));
      await waitFor(() => expect(screen.getByTestId('train-bot-copy')).not.toBe(firstNode));
      expect(screen.getByTestId('train-bot-bubble').getAttribute('data-nudge')).toBe('true');
    });

    it('committing a guess clears the nudge — the bubble moves to the move prompt', async () => {
      await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('drop-e2e4'));
      await waitFor(() =>
        expect(screen.getByTestId('train-bot-bubble').getAttribute('data-nudge')).toBe('true'),
      );
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await waitFor(() => expect(screen.getByTestId('train-move-prompt')).not.toBeNull());
      expect(screen.getByTestId('train-bot-bubble').getAttribute('data-nudge')).toBeNull();
    });
  });

  describe('Phase 222: verdict bubble (D-03/D-10/D-15/D-16/D-23)', () => {
    it('a 0-point verdict is spoken by the narrating bot and shows the look-closer line + both pills', async () => {
      matchMediaMatches = false; // phone: the expanded strip
      solvePuzzle.mockResolvedValue({
        correct_guess: false,
        correct_move: false,
        move_quality: 'wrong',
        puzzle_type: 'sharp',
        source: 'sr_item',
        item_status: 'active',
        streak: 0,
        due_date: '2026-07-28',
        session_complete: false,
      });
      await renderScreen(makePuzzle());
      const narrator = screen.getByTestId('train-bot-name').textContent;
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await openVerdictStrip();
      // Phase 237 UAT: the bot that asked for the move also gives the feedback.
      expect(screen.getByTestId('train-verdict-strip-avatar').getAttribute('data-persona-name')).toBe(
        narrator,
      );
      expect(screen.getByTestId('train-bot-pill-guess').textContent).toBe('+0');
      expect(screen.getByTestId('train-bot-pill-move').textContent).toBe('+0');
      expect(screen.getByTestId('train-bot-look-closer')).not.toBeNull();
    });

    it('a 3-point verdict is spoken by the narrating bot with no look-closer line', async () => {
      matchMediaMatches = false; // phone: the expanded strip
      solvePuzzle.mockResolvedValue({
        correct_guess: true,
        correct_move: true,
        move_quality: 'good',
        puzzle_type: 'sharp',
        source: 'sr_item',
        item_status: 'active',
        streak: 1,
        due_date: '2026-07-28',
        session_complete: false,
      });
      await renderScreen(makePuzzle());
      const narrator = screen.getByTestId('train-bot-name').textContent;
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await openVerdictStrip();
      // Phase 237 UAT: the bot that asked for the move also gives the feedback.
      expect(screen.getByTestId('train-verdict-strip-avatar').getAttribute('data-persona-name')).toBe(
        narrator,
      );
      expect(screen.getByTestId('train-bot-pill-guess').textContent).toBe('+1');
      expect(screen.getByTestId('train-bot-pill-move').textContent).toBe('+2');
      expect(screen.queryByTestId('train-bot-look-closer')).toBeNull();
    });

    // Phase 237 UAT: Hilda narrates the first-reveal tour, so she never hosts a
    // puzzle while that tour is pending, even on a draw that lands on her slot.
    it('Hilda never hosts the puzzle while the first-reveal tour is pending', async () => {
      getSettings.mockResolvedValue(makeSettings({ reveal_walkthrough_seen_at: null }));
      const all = Object.values(PERSONA_REGISTRY);
      const hildaSlot = all.findIndex((p) => p.id === HILDA_ID);
      const random = vi.spyOn(Math, 'random').mockReturnValue((hildaSlot + 0.5) / all.length);
      await renderScreen(makePuzzle());
      expect(screen.getByTestId('train-bot-name').textContent).not.toBe('Hilda the Hippo');
      random.mockRestore();
    });

    // Phase 222 UAT round 4: `verdictCopy` draws a random opener; drawing it
    // on every render flipped "Good job!"/"Clean." on each board interaction
    // and twitched the layout. The draw is memoised per verdict.
    it('the verdict opener stays fixed across re-renders (no per-render random draw)', async () => {
      matchMediaMatches = false; // phone: the expanded strip
      solvePuzzle.mockResolvedValue({
        correct_guess: true,
        correct_move: true,
        move_quality: 'good',
        puzzle_type: 'sharp',
        source: 'sr_item',
        item_status: 'active',
        streak: 1,
        due_date: '2026-07-28',
        session_complete: false,
      });
      const random = vi.spyOn(Math, 'random').mockReturnValue(0);
      await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      const details = await openVerdictStrip();
      expect(within(details).getByTestId('train-bot-verdict-line').textContent).toMatch(/^Good job!/);
      // Every later draw would pick the OTHER opener — a re-render must not draw.
      random.mockReturnValue(0.999);
      await waitFor(() => expect(screen.getByTestId('train-move-tree')).not.toBeNull());
      tapListMove(0);
      await waitFor(() =>
        expect(screen.getByTestId('chessboard').getAttribute('data-position')).not.toBe(START_FEN),
      );
      expect(screen.getByTestId('train-bot-verdict-line').textContent).toMatch(/^Good job!/);
      random.mockRestore();
    });

    // Phase 222 UAT round 4: the reveal restored after the Analyze round trip
    // shows the SAME bot that spoke the verdict before leaving.
    it('a restored reveal keeps the verdict bot recorded in the reveal cache', async () => {
      matchMediaMatches = false; // phone: the bot is the strip's avatar
      const restoredPuzzle = makePuzzle();
      const restoredCached: CachedTrainReveal = {
        sessionId: 1,
        puzzle: restoredPuzzle,
        verdict: SOLVE_RESPONSE,
        verdictBotId: 'wall-1800',
        guess: 'critical',
        playedMoveUci: 'e2e4',
        gradeResult: {
          moveTier: 'good',
          bestMoveUci: 'e2e4',
          esBefore: 0.5,
          esAfter: 0.5,
          bestLine: { moves: ['e2e4'], evalCp: 19, evalMate: null },
          playedLine: { moves: ['e2e4'], evalCp: 19, evalMate: null },
          lines: [],
        },
      };
      await renderScreen(restoredPuzzle, makeSession(), restoredCached);
      await waitForReveal();
      const strip = await screen.findByTestId('train-verdict-strip');
      // D-08: a restored reveal starts collapsed too, whatever the score.
      expect(strip.getAttribute('aria-expanded')).toBe('false');
      expect(screen.getByTestId('train-verdict-strip-avatar').getAttribute('data-persona-name')).toBe(
        PERSONA_REGISTRY['wall-1800'].name,
      );
    });

    it('desktop: the verdict is the full bubble at the top of the reveal column, details visible, no strip', async () => {
      await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      const reveal = await waitForReveal();
      const bubble = within(reveal).getByTestId('train-verdict-card');
      expect(reveal.firstElementChild).toBe(bubble);
      // Phase 237 UAT: the avatar sits inside the card, with no name label.
      expect(within(bubble).getByTestId('train-verdict-card-avatar')).not.toBeNull();
      expect(within(bubble).queryByTestId('train-bot-name')).toBeNull();
      expect(within(bubble).getByTestId('train-bot-verdict-line').textContent).toContain('best move');
      expect(within(bubble).getByTestId('train-verdict-guess-prose')).not.toBeNull();
      expect(screen.queryByTestId('train-verdict-strip')).toBeNull();
      // The left slot no longer speaks the verdict.
      expect(screen.queryByTestId('train-bot-bubble')).toBeNull();
    });

    it('D-08: the strip is collapsed again on the next puzzle\'s reveal, even after the user opened it', async () => {
      matchMediaMatches = false;
      const { rerender } = await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await openVerdictStrip();
      expect(screen.getByTestId('train-verdict-strip').getAttribute('aria-expanded')).toBe('true');

      // The next puzzle on the SAME screen instance (what Next does in the page).
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      });
      rerender(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <TooltipProvider>
              <Harness
                puzzle={makePuzzle({
                  position: 2,
                  ply: 30,
                  fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
                })}
              />
            </TooltipProvider>
          </QueryClientProvider>
        </MemoryRouter>,
      );
      await waitFor(() => expect(screen.queryByTestId('train-reveal')).toBeNull());
      fireEvent.click(await screen.findByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-d2d4'));
      });
      await waitForReveal();
      const strip = await screen.findByTestId('train-verdict-strip');
      expect(strip.getAttribute('aria-expanded')).toBe('false');
      expect(screen.queryByTestId('train-verdict-strip-details')).toBeNull();
    });

    it('the mastered tail renders even when the stale due_date compares as "next session" (status-before-date)', async () => {
      const session = makeSession({ session_date: '2026-09-13', expires_on: '2026-09-14' });
      solvePuzzle.mockResolvedValue({
        correct_guess: true,
        correct_move: true,
        move_quality: 'good',
        puzzle_type: 'sharp',
        source: 'sr_item',
        item_status: 'mastered',
        streak: 3,
        due_date: '2026-09-01',
        session_complete: false,
      });
      await renderScreen(makePuzzle(), session);
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      const verdictLine = await waitFor(() => screen.getByTestId('train-bot-verdict-line'));
      // D-16: the mastered tail EXPLAINS why it won't return — it is not
      // itself a return promise, so it never carries `train-bot-return-tail`.
      expect(verdictLine.textContent).toContain("won't come back");
      expect(screen.queryByTestId('train-bot-return-tail')).toBeNull();
    });

    it('a sharp_filler verdict renders no return-tail element', async () => {
      solvePuzzle.mockResolvedValue({
        correct_guess: true,
        correct_move: true,
        move_quality: 'good',
        puzzle_type: 'sharp',
        source: 'sharp_filler',
        item_status: null,
        streak: null,
        due_date: null,
        session_complete: false,
      });
      await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitFor(() => expect(screen.getByTestId('train-bot-verdict-line')).not.toBeNull());
      expect(screen.queryByTestId('train-bot-return-tail')).toBeNull();
    });

    // Quick 260915-sht: warm-up is a SESSION property. A herring solved in a
    // regular session (the user has SR items) must not be called a warm-up.
    it.each([
      { is_warmup: false, expectWarmup: false },
      { is_warmup: true, expectWarmup: true },
    ])(
      'a red_herring verdict says "warm-up" only when the session is a warm-up (is_warmup=$is_warmup)',
      async ({ is_warmup, expectWarmup }) => {
        solvePuzzle.mockResolvedValue({
          correct_guess: true,
          correct_move: true,
          move_quality: 'good',
          puzzle_type: 'herring',
          source: 'red_herring',
          item_status: null,
          streak: null,
          due_date: null,
          session_complete: false,
        });
        await renderScreen(makePuzzle(), makeSession({ is_warmup }));
        fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
        await act(async () => {
          fireEvent.click(screen.getByTestId('drop-e2e4'));
        });
        const verdictLine = await waitFor(() => screen.getByTestId('train-bot-verdict-line'));
        expect(verdictLine.textContent).toContain("won't come back");
        expect(verdictLine.textContent?.includes('warm-up')).toBe(expectWarmup);
        expect(screen.queryByTestId('train-bot-return-tail')).toBeNull();
      },
    );

    it('a verdict object missing source renders without throwing and without a return tail', async () => {
      solvePuzzle.mockResolvedValue({
        correct_guess: true,
        correct_move: true,
        move_quality: 'good',
        puzzle_type: 'sharp',
        item_status: 'active',
        streak: 1,
        due_date: '2026-07-28',
        session_complete: false,
      } as SolveResponse);
      await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitFor(() => expect(screen.getByTestId('train-bot-verdict-line')).not.toBeNull());
      expect(screen.queryByTestId('train-bot-return-tail')).toBeNull();
    });

    it('the verdict bubble renders no buttons (the actions live in the reveal bar) and the mute toggle is gone', async () => {
      await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitFor(() => expect(screen.getByTestId('btn-train-next')).not.toBeNull());
      const bubble = screen.getByTestId('train-verdict-card');
      expect(bubble.querySelector('button')).toBeNull();
      expect(bubble.contains(screen.getByTestId('btn-train-next'))).toBe(false);
      const bar = screen.getByTestId('train-reveal-action-bar');
      expect(bar.contains(screen.getByTestId('btn-train-next'))).toBe(true);
      expect(bar.contains(screen.getByTestId('btn-train-analyze'))).toBe(true);
      expect(screen.queryByTestId('board-btn-mute')).toBeNull();
    });
  });

  describe('Phase 222: first-reveal walkthrough (D-24/D-12/TRAINBOT-10)', () => {
    /** Opens a first reveal (tour active) on the current viewport. */
    async function openFirstReveal(): Promise<ReturnType<typeof render>> {
      getSettings.mockResolvedValue(makeSettings({ reveal_walkthrough_seen_at: null }));
      const rendered = await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitFor(() => expect(screen.getByTestId('train-bot-walkthrough')).not.toBeNull());
      return rendered;
    }
    // Phase 237 UAT (G-01): the reveal bar's Next is the tour's only Next.
    const clickWalkthroughNext = (): void => {
      fireEvent.click(screen.getByTestId('btn-train-next'));
    };
    const walkthroughCopyText = (): string =>
      screen.getByTestId('train-bot-walkthrough').textContent ?? '';
    const overlayShown = (): boolean => screen.queryByTestId('train-tour-overlay') !== null;
    const badgeShown = (): boolean => screen.queryByTestId('btn-train-tour-reopen') !== null;

    it('tracer: on a phone Hilda speaks from an overlay on the board and the strip is ringed', async () => {
      matchMediaMatches = false; // below lg: the strip is the verdict surface, the tour an overlay
      await openFirstReveal();
      const overlay = screen.getByTestId('train-tour-overlay');
      // G-01: the tour copy sits on the board, not in the reveal column.
      expect(screen.getByTestId('train-pinned-board').contains(overlay)).toBe(true);
      expect(within(screen.getByTestId('train-reveal')).queryByTestId('train-bot-walkthrough')).toBeNull();
      expect(overlay.className).toContain('pointer-events-none');
      expect(screen.getByTestId('train-verdict-strip').getAttribute('aria-expanded')).toBe('false');
      expect(screen.getByTestId('train-verdict-strip-root').className).toContain('ring-2');
      expect(walkthroughCopyText()).toContain('Tap it');
      expect(within(overlay).getByTestId('train-tour-step-count').textContent).toBe(`1 / ${WALKTHROUGH_STEP_COUNT}`);
      // One Next on screen: the bar's.
      expect(screen.queryByTestId('btn-train-bot-walkthrough-next')).toBeNull();
      expect(screen.getAllByTestId('btn-train-next')).toHaveLength(1);
      expect(screen.queryByTestId('train-bot-verdict-line')).toBeNull();
    });

    it('on desktop Hilda also speaks from the board overlay, and the verdict bubble is ringed', async () => {
      matchMediaMatches = true;
      await openFirstReveal();
      const overlay = screen.getByTestId('train-tour-overlay');
      // Phase 237 UAT: no second bot bubble stacked over the verdict bubble.
      expect(screen.getByTestId('train-pinned-board').contains(overlay)).toBe(true);
      const reveal = screen.getByTestId('train-reveal');
      expect(within(reveal).queryByTestId('train-bot-walkthrough')).toBeNull();
      expect(within(reveal).queryByTestId('train-bot-bubble')).toBeNull();
      expect(within(reveal).getByTestId('train-verdict-card').className).toContain('ring-2');
      expect(within(overlay).getByTestId('train-tour-step-count').textContent).toBe(
        `1 / ${WALKTHROUGH_STEP_COUNT}`,
      );
      expect(walkthroughCopyText()).not.toContain('Tap it');
      expect(screen.queryByTestId('btn-train-bot-walkthrough-next')).toBeNull();
      expect(within(reveal).queryByTestId('train-verdict-strip')).toBeNull();
    });

    it('the bar Next moves the tour to the chips step and off the strip, and never rings the chips row', async () => {
      matchMediaMatches = false;
      await openFirstReveal();
      clickWalkthroughNext();
      await waitFor(() => expect(walkthroughCopyText()).toContain('Tap one to focus it'));
      expect(screen.getByTestId('train-verdict-strip-root').className).not.toContain('ring-2');
      expect(screen.getByTestId('train-line-chips').className).not.toContain('ring-2');
      expect(screen.getByTestId('train-tour-step-count').textContent).toBe(`2 / ${WALKTHROUGH_STEP_COUNT}`);
    });

    it('the ring follows the target: list, board row, list, then nothing on the bar step', async () => {
      matchMediaMatches = false;
      await openFirstReveal();
      const treeRinged = (): boolean =>
        screen.getByTestId('train-tree-tour-ring').className.includes('ring-2');
      const boardRinged = (): boolean =>
        screen.getByTestId('chessboard').closest('[class*="ring-2"]') !== null;
      // Step 1: the chips (the active chip's own ring only).
      clickWalkthroughNext();
      expect([treeRinged(), boardRinged()]).toEqual([false, false]);
      // Step 2: the move list.
      clickWalkthroughNext();
      expect([treeRinged(), boardRinged()]).toEqual([true, false]);
      // Step 3: the board row.
      clickWalkthroughNext();
      expect([treeRinged(), boardRinged()]).toEqual([false, true]);
      // Step 4: chips and list together (the list carries the ring).
      clickWalkthroughNext();
      expect([treeRinged(), boardRinged()]).toEqual([true, false]);
      // Step 5: the action bar step rings nothing (Phase 237 UAT: the bar ring
      // was clipped in the fixed mobile bottom bar, so the bubble points alone).
      clickWalkthroughNext();
      await waitFor(() =>
        expect(screen.getByTestId('train-tour-step-count').textContent).toBe(
          `${WALKTHROUGH_STEP_COUNT} / ${WALKTHROUGH_STEP_COUNT}`,
        ),
      );
      expect(screen.getByTestId('train-reveal-action-bar').className).not.toContain('ring-2');
      expect([treeRinged(), boardRinged()]).toEqual([false, false]);
      expect(screen.getByTestId('train-line-chips').className).not.toContain('ring-2');
    });

    it('the bar Next walks the tour without leaving the puzzle; on the last step it leaves and stamps once', async () => {
      await openFirstReveal();
      for (let click = 0; click < WALKTHROUGH_STEP_COUNT - 1; click += 1) {
        clickWalkthroughNext();
        // The puzzle stays: the reveal is still on screen and nothing is stamped or flushed.
        expect(screen.getByTestId('train-reveal')).not.toBeNull();
      }
      expect(nextFlush).not.toHaveBeenCalled();
      expect(stampOnboarding).not.toHaveBeenCalled();
      clickWalkthroughNext();
      await waitFor(() => expect(stampOnboarding).toHaveBeenCalledTimes(1));
      expect(stampOnboarding).toHaveBeenCalledWith('reveal_walkthrough');
      await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    });

    it('unmounting on the last step (before leaving through Next) fires no stamp — an abandoned stepper replays', async () => {
      const { unmount } = await openFirstReveal();
      for (let click = 0; click < WALKTHROUGH_STEP_COUNT - 1; click += 1) clickWalkthroughNext();
      await waitFor(() =>
        expect(screen.getByTestId('train-tour-step-count').textContent).toBe(
          `${WALKTHROUGH_STEP_COUNT} / ${WALKTHROUGH_STEP_COUNT}`,
        ),
      );
      unmount();
      expect(stampOnboarding).not.toHaveBeenCalled();
    });

    it('step 2 explains the Move = Best chip only when the played move is the best move', async () => {
      matchMediaMatches = false;
      await openFirstReveal();
      clickWalkthroughNext();
      const merged = screen.queryByTestId('train-chip-your')?.textContent?.includes('Best') ?? false;
      expect(walkthroughCopyText().includes('"Move = Best"')).toBe(merged);
    });

    it('the bar copy shows the bar icons, not glyphs', async () => {
      matchMediaMatches = false;
      await openFirstReveal();
      clickWalkthroughNext();
      clickWalkthroughNext();
      expect(screen.getByTestId('train-tour-icon-back')).not.toBeNull();
      expect(screen.getByTestId('train-tour-icon-forward')).not.toBeNull();
      clickWalkthroughNext();
      expect(screen.getByTestId('train-tour-icon-rewind')).not.toBeNull();
      expect(walkthroughCopyText()).not.toContain('{');
    });

    // Phase 237 UAT (G-01): an interaction hides the phone overlay but never
    // moves the tour; the next bar Next shows the overlay with the next step.
    it('on a phone, a chip tap hides the overlay without advancing; Next shows the next step', async () => {
      matchMediaMatches = false;
      await openFirstReveal();
      clickWalkthroughNext();
      expect(overlayShown()).toBe(true);
      fireEvent.click(screen.getByTestId('train-chip-your'));
      await waitFor(() => expect(overlayShown()).toBe(false));
      expect(badgeShown()).toBe(true);
      clickWalkthroughNext();
      await waitFor(() => expect(overlayShown()).toBe(true));
      expect(walkthroughCopyText()).toContain('Step through the focused line');
      expect(badgeShown()).toBe(false);
    });

    it("on a phone, Hilda's badge brings the current step back", async () => {
      matchMediaMatches = false;
      await openFirstReveal();
      clickWalkthroughNext();
      clickWalkthroughNext();
      tapListMove(0);
      await waitFor(() => expect(badgeShown()).toBe(true));
      fireEvent.click(screen.getByTestId('btn-train-tour-reopen'));
      expect(overlayShown()).toBe(true);
      expect(walkthroughCopyText()).toContain('Step through the focused line');
    });

    it('on a phone, a touch on the board hides the overlay', async () => {
      matchMediaMatches = false;
      await openFirstReveal();
      fireEvent.pointerDown(screen.getByTestId('chessboard'));
      await waitFor(() => expect(badgeShown()).toBe(true));
      expect(overlayShown()).toBe(false);
    });

    it('on a phone, expanding the strip hides the overlay and leaves the tour on the result step', async () => {
      matchMediaMatches = false;
      await openFirstReveal();
      fireEvent.click(screen.getByTestId('train-verdict-strip'));
      await waitFor(() => expect(badgeShown()).toBe(true));
      fireEvent.click(screen.getByTestId('btn-train-tour-reopen'));
      expect(walkthroughCopyText()).toContain('Tap it');
    });

    it('a fork hides the overlay and leaves the tour on its step', async () => {
      matchMediaMatches = false;
      await openFirstReveal();
      clickWalkthroughNext();
      clickWalkthroughNext();
      clickWalkthroughNext();
      expect(walkthroughCopyText()).toContain('Move a piece');
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-d2d4'));
      });
      await waitFor(() => expect(badgeShown()).toBe(true));
      fireEvent.click(screen.getByTestId('btn-train-tour-reopen'));
      expect(walkthroughCopyText()).toContain('Move a piece');
    });

    it('on desktop an interaction hides the tour overlay behind the badge but never moves the tour', async () => {
      matchMediaMatches = true;
      await openFirstReveal();
      clickWalkthroughNext();
      fireEvent.click(screen.getByTestId('train-chip-your'));
      // Phase 237 UAT: the overlay covers the board on desktop too, so it hides.
      expect(overlayShown()).toBe(false);
      expect(badgeShown()).toBe(true);
      fireEvent.click(screen.getByTestId('btn-train-tour-reopen'));
      expect(walkthroughCopyText()).toContain('Tap one to focus it');
    });

    async function openOnPhoneAndMockLayout(rects: {
      pinned: Partial<DOMRect>;
      chips: Partial<DOMRect>;
    }): Promise<void> {
      matchMediaMatches = false;
      const scrollTween = vi.mocked(animateScrollTop);
      scrollTween.mockClear();
      await openFirstReveal();
      await waitFor(() => expect(screen.getByTestId('train-line-chips')).not.toBeNull());
      vi.spyOn(screen.getByTestId('train-pinned-board'), 'getBoundingClientRect').mockReturnValue(
        rects.pinned as DOMRect,
      );
      // The scroll target is the chips wrapper (`data-tour-target="chips"`).
      const chipsAnchor = screen.getByTestId('train-reveal').querySelector('[data-tour-target="chips"]');
      expect(chipsAnchor).not.toBeNull();
      vi.spyOn(chipsAnchor as Element, 'getBoundingClientRect').mockReturnValue(rects.chips as DOMRect);
      expect(scrollTween).not.toHaveBeenCalled();
      clickWalkthroughNext();
    }

    it('on a phone, chips already on screen need no scroll', async () => {
      // jsdom's viewport is 768px tall and no fixed bar is mounted from sm up.
      await openOnPhoneAndMockLayout({
        pinned: { top: 0, bottom: 300, height: 300 },
        chips: { top: 400, bottom: 480, height: 80 },
      });
      await waitFor(() => expect(walkthroughCopyText()).toContain('Tap one to focus it'));
      expect(vi.mocked(animateScrollTop)).not.toHaveBeenCalled();
    });

    it('on a phone, chips below the fold scroll up just enough to clear the bottom edge', async () => {
      await openOnPhoneAndMockLayout({
        pinned: { top: 0, bottom: 300, height: 300 },
        chips: { top: 700, bottom: 780, height: 80 },
      });
      const scrollTween = vi.mocked(animateScrollTop);
      await waitFor(() => expect(scrollTween).toHaveBeenCalledTimes(1));
      // 780 (chips bottom) + 12 (gap) - 768 (viewport bottom), over the 700ms tween.
      expect(scrollTween).toHaveBeenCalledWith(document.documentElement, 24, 700);
    });

    it('on a phone, a target taller than the gap never scrolls its top behind the pinned block', async () => {
      await openOnPhoneAndMockLayout({
        pinned: { top: 0, bottom: 300, height: 300 },
        chips: { top: 350, bottom: 1200, height: 850 },
      });
      const scrollTween = vi.mocked(animateScrollTop);
      await waitFor(() => expect(scrollTween).toHaveBeenCalledTimes(1));
      // Capped at 350 (chips top) - 300 (pinned height) - 12 (gap).
      expect(scrollTween).toHaveBeenCalledWith(document.documentElement, 38, 700);
    });

    it('with reveal_walkthrough_seen_at already stamped, no walkthrough renders and the verdict shows immediately', async () => {
      getSettings.mockResolvedValue(
        makeSettings({ reveal_walkthrough_seen_at: '2026-01-01T00:00:00Z' }),
      );
      await renderScreen(makePuzzle());
      fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('drop-e2e4'));
      });
      await waitFor(() => expect(screen.getByTestId('train-bot-verdict-line')).not.toBeNull());
      expect(screen.queryByTestId('train-bot-walkthrough')).toBeNull();
    });

    it('the board arrow set is identical across all walkthrough steps — the chip focus is never touched', async () => {
      await openFirstReveal();
      const board = screen.getByTestId('chessboard');
      const step0Arrows = board.getAttribute('data-arrow-ucis');
      expect(step0Arrows).not.toBe('');
      for (let click = 0; click < WALKTHROUGH_STEP_COUNT - 1; click += 1) {
        clickWalkthroughNext();
        expect(board.getAttribute('data-arrow-ucis')).toBe(step0Arrows);
      }
      await waitFor(() => expect(screen.getByTestId('btn-train-next')).not.toBeNull());
      expect(board.getAttribute('data-arrow-ucis')).toBe(step0Arrows);
    });
  });
});

describe('TrainSolveScreen — per-puzzle telemetry (Phase 233)', () => {
  beforeEach(() => {
    matchMediaMatches = true;
    stubbedWorkerInstances = [];
    stubWorker(() => new FakeWorker());
    composeOrResumeSession.mockReset();
    solvePuzzle.mockReset();
    solvePuzzle.mockResolvedValue(SOLVE_RESPONSE);
    revealPuzzle.mockClear();
    getSettings.mockReset();
    getSettings.mockResolvedValue(makeSettings());
    stampOnboarding.mockClear();
    nextFlush.mockClear();
    exitFlush.mockClear();
    // The think-timer resume marker lives in sessionStorage; start every test fresh.
    sessionStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    sessionStorage.clear();
  });

  async function guessAndDrop(): Promise<void> {
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitForReveal();
  }

  it('telemetry: the solve POST carries v, client, guess_ms, move_ms, think_hidden_ms and resumed', async () => {
    await renderScreen(makePuzzle());
    await guessAndDrop();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    const telemetry = solvePuzzle.mock.calls[0]?.[1].telemetry;
    expect(telemetry).toMatchObject({ v: 1, client: 'desktop', think_hidden_ms: 0, resumed: false });
    expect(Number.isInteger(telemetry.guess_ms)).toBe(true);
    expect(telemetry.guess_ms).toBeGreaterThanOrEqual(0);
    expect(Number.isInteger(telemetry.move_ms)).toBe(true);
    expect(telemetry.move_ms).toBeGreaterThanOrEqual(0);
  });

  it('telemetry: Next flushes the review once with exit next for this position', async () => {
    const puzzle = makePuzzle();
    await renderScreen(puzzle);
    await guessAndDrop();
    expect(nextFlush).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('btn-train-next'));

    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    const [sessionId, position, body] = nextFlush.mock.calls[0]!;
    expect(sessionId).toBe(makeSession().session_id);
    expect(position).toBe(puzzle.position);
    expect(body).toMatchObject({ v: 2, exit: 'next' });
    expect(Number.isInteger(body.review_ms)).toBe(true);
    expect(body.review_ms).toBeGreaterThanOrEqual(0);
  });

  it('telemetry: leaving an open reveal (unmount) sends one keepalive flush with exit pagehide for this position', async () => {
    const puzzle = makePuzzle();
    const { unmount } = await renderScreen(puzzle);
    await guessAndDrop();
    expect(exitFlush).not.toHaveBeenCalled();

    unmount();
    await act(async () => {});

    expect(exitFlush).toHaveBeenCalledTimes(1);
    expect(exitFlush).toHaveBeenCalledWith(
      makeSession().session_id,
      puzzle.position,
      expect.objectContaining({ exit: 'pagehide' }),
    );
    expect(nextFlush).not.toHaveBeenCalled();
  });

  it('telemetry: Next then unmount sends no keepalive flush', async () => {
    const { unmount } = await renderScreen(makePuzzle());
    await guessAndDrop();
    fireEvent.click(screen.getByTestId('btn-train-next'));
    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));

    unmount();
    await act(async () => {});

    expect(exitFlush).not.toHaveBeenCalled();
  });

  it('telemetry: Analyze saves the review snapshot into the reveal cache', async () => {
    await renderScreen(makePuzzle());
    await guessAndDrop();
    await waitFor(() => expect(screen.getByTestId('btn-train-analyze')).not.toBeNull());

    fireEvent.click(screen.getByTestId('btn-train-analyze'));

    const visibleMs = readTrainRevealCache()?.reviewTelemetry?.visibleMs;
    expect(typeof visibleMs).toBe('number');
    expect(visibleMs).toBeGreaterThanOrEqual(0);
  });

  it('telemetry: a list step and an active walkthrough reach the Next flush', async () => {
    getSettings.mockResolvedValue(makeSettings({ reveal_walkthrough_seen_at: null }));
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-e2e4'));
    });
    await waitFor(() => expect(screen.getByTestId('train-bot-walkthrough')).not.toBeNull());
    await waitFor(() => expect(screen.getByTestId('train-move-tree')).not.toBeNull());
    tapListMove(0);
    // Walk the walkthrough with the bar's Next (Phase 237 UAT G-01); on its last
    // step the same Next leaves the puzzle.
    for (let click = 0; click < WALKTHROUGH_STEP_COUNT; click += 1) {
      fireEvent.click(screen.getByTestId('btn-train-next'));
    }

    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    expect(nextFlush.mock.calls[0]![2]).toMatchObject({
      exit: 'next',
      review_line_steps: 1,
      review_walkthrough: true,
      review_explored: false,
      review_analyze_opened: false,
    });
  });

  it('telemetry: board moves and engine-line clicks split into review_board_moves and review_explore_moves', async () => {
    let workerCallCount = 0;
    stubWorker(() => {
      workerCallCount += 1;
      // Grading engine first, then the reveal engine whose PV (e7e5) is legal after 1.d4.
      return workerCallCount === 1 ? new FakeWorker() : new FakeWorker('e7e5', 'e7e5');
    });
    await renderScreen(makePuzzle());
    await guessAndDrop();

    // The mocked board's drop buttons call onPieceDrop, the one entry point for
    // desktop drag AND mobile tap-to-move in the real ChessBoard.
    fireEvent.click(screen.getByTestId('drop-d2d4')); // board move 1, forks a sideline
    await waitFor(() => expect(screen.getByTestId('engine-line-0-move-0')).not.toBeNull());
    fireEvent.click(screen.getByTestId('engine-line-0-move-0')); // engine-line click (1...e5)
    await waitFor(() => expect(screen.getByTestId('chessboard').getAttribute('data-position')).toContain('4p3'));
    fireEvent.click(screen.getByTestId('drop-e2e4')); // board move 2

    fireEvent.click(screen.getByTestId('btn-train-next'));
    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    expect(nextFlush.mock.calls[0]![2]).toMatchObject({
      review_explored: true,
      review_explore_moves: 3,
      review_board_moves: 2,
    });
  });

  it('telemetry (D-13): a hand-played known-line move counts as a board move, not a fork', async () => {
    await renderScreen(makePuzzle());
    await guessAndDrop(); // played = best = e2e4

    fireEvent.click(screen.getByTestId('drop-e2e4')); // along the known line
    fireEvent.click(screen.getByTestId('btn-train-next'));
    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    expect(nextFlush.mock.calls[0]![2]).toMatchObject({
      review_explore_moves: 1,
      review_board_moves: 1,
      // D-13: a move along a known line is not a fork, and the merged Move = Best
      // chip is the default chip, so nothing counts as selected either.
      review_explored: false,
      review_chips_selected: 0,
    });
  });

  it('tracer: a chip tap, a strip expand and a fork ride the v2 Next flush', async () => {
    matchMediaMatches = false; // phone: the strip exists
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4')); // non-best -> separate You / Best chips
    });
    await waitForReveal();
    const chipsShown = screen.getAllByTestId(/^train-chip-(your|best|game)$/).length;
    expect(chipsShown).toBeGreaterThanOrEqual(2);

    fireEvent.click(screen.getByTestId('train-chip-best')); // 1 chip selected beyond You
    fireEvent.click(await screen.findByTestId('train-verdict-strip')); // strip expanded
    fireEvent.click(screen.getByTestId('drop-c2c4')); // fork from the root: matches no chip line
    fireEvent.click(screen.getByTestId('btn-train-next'));

    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    const body = nextFlush.mock.calls[0]![2];
    expect(body).toMatchObject({
      v: 2,
      exit: 'next',
      review_chips_selected: 1,
      review_chips_total: chipsShown,
      review_strip_expanded: true,
      review_explored: true,
    });
    expect(Object.keys(body).filter((key) => key.startsWith('review_cards_'))).toEqual([]);
  });

  it('telemetry (D-12): re-tapping the default You chip and never opening the strip sends zero chips and a closed strip', async () => {
    matchMediaMatches = false;
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4'));
    });
    await waitForReveal();

    fireEvent.click(screen.getByTestId('train-chip-your'));
    fireEvent.click(screen.getByTestId('btn-train-next'));

    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    expect(nextFlush.mock.calls[0]![2]).toMatchObject({
      review_chips_selected: 0,
      review_strip_expanded: false,
      review_explored: false,
    });
  });

  it('telemetry: a remount of the same unsolved puzzle sends resumed: true', async () => {
    const first = await renderScreen(makePuzzle());
    first.unmount();
    await renderScreen(makePuzzle());
    await guessAndDrop();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    expect(solvePuzzle.mock.calls[0]?.[1].telemetry.resumed).toBe(true);
  });
});

// ─── Phase 237 plan 09: Analyze -> Back restores the reveal tree ─────────────

describe('TrainSolveScreen — restored reveal tree (Phase 237 plan 09)', () => {
  const track = vi.fn();

  beforeEach(() => {
    matchMediaMatches = true;
    stubbedWorkerInstances = [];
    // A three-move Best line so the second token still has a next move.
    stubWorker(() => new FakeWorker('e2e4', 'e2e4 e7e5 g1f3'));
    composeOrResumeSession.mockReset();
    solvePuzzle.mockReset();
    solvePuzzle.mockResolvedValue(SOLVE_RESPONSE);
    revealPuzzle.mockClear();
    getSettings.mockReset();
    getSettings.mockResolvedValue(makeSettings());
    stampOnboarding.mockClear();
    nextFlush.mockClear();
    exitFlush.mockClear();
    track.mockClear();
    sessionStorage.clear();
    window.history.pushState({}, '', '/train');
  });

  afterEach(() => {
    cleanup();
    delete window.umami;
    vi.unstubAllGlobals();
    sessionStorage.clear();
    window.history.pushState({}, '', '/');
  });

  /** Solve with a non-best move, tap Best, step to its 2nd move, fork Nc3 there, click Analyze. */
  async function solveForkAndAnalyze(): Promise<{ forkedPosition: string }> {
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4')); // non-best -> separate You / Best chips
    });
    await waitForReveal();
    fireEvent.click(screen.getByTestId('train-chip-best'));
    fireEvent.click(within(screen.getByTestId('train-move-tree')).getByText('e5'));
    await waitFor(() => expect(screen.getByTestId('chessboard').getAttribute('data-position')).not.toBe(START_FEN));
    fireEvent.click(screen.getByTestId('drop-b1c3')); // fork off the Best line
    await waitFor(() => expect(within(screen.getByTestId('train-move-tree')).queryByText('Nc3')).not.toBeNull());
    const forkedPosition = screen.getByTestId('chessboard').getAttribute('data-position') ?? '';
    fireEvent.click(screen.getByTestId('btn-train-analyze'));
    return { forkedPosition };
  }

  it('Analyze saves the focused chip, the forked node as currentPath and the sideline in the cache entry', async () => {
    await solveForkAndAnalyze();

    const tree = readTrainRevealCache()?.revealTree;
    expect(tree?.rootFocus).toBe('best');
    expect(tree?.currentPath).toEqual(['e2e4', 'e7e5', 'b1c3']);
    expect(tree?.sidelinePaths).toEqual([['e2e4', 'e7e5', 'b1c3']]);
  });

  it('remounting with that entry shows the Best chip active, the board on the forked node and the sideline listed, silently', async () => {
    const { forkedPosition } = await solveForkAndAnalyze();
    const cached = readTrainRevealCache();
    expect(cached).not.toBeNull();
    cleanup();
    await act(async () => {});
    // The unmount flush mirrors the review totals into the entry; the tree survives that.
    expect(readTrainRevealCache()?.revealTree).toEqual(cached?.revealTree);

    const { playSound } = await import('@/lib/sounds');
    vi.mocked(playSound).mockClear();
    window.umami = { track, identify: vi.fn() };
    track.mockClear();
    await renderScreen(makePuzzle(), makeSession(), readTrainRevealCache());
    await waitForReveal();

    await waitFor(() => expect(screen.getByTestId('chessboard').getAttribute('data-position')).toBe(forkedPosition));
    expect(screen.getByTestId('train-chip-best').getAttribute('data-active')).toBe('true');
    expect(within(screen.getByTestId('train-move-tree')).queryByText('Nc3')).not.toBeNull();
    expect(playSound).not.toHaveBeenCalled();
    expect(track).not.toHaveBeenCalled();
  });

  it('remounting with an entry that has no revealTree opens at the puzzle position with You active', async () => {
    await solveForkAndAnalyze();
    const entry = { ...readTrainRevealCache()! };
    delete entry.revealTree;
    cleanup();
    await act(async () => {});

    await renderScreen(makePuzzle(), makeSession(), entry);
    await waitForReveal();

    expect(screen.getByTestId('chessboard').getAttribute('data-position')).toBe(START_FEN);
    expect(screen.getByTestId('train-chip-your').getAttribute('data-active')).toBe('true');
    expect(within(screen.getByTestId('train-move-tree')).queryByText('Nc3')).toBeNull();
  });

  it('a restored reveal continues the cumulative v2 counters (chips, strip, fork) into the Next flush', async () => {
    matchMediaMatches = false; // phone: the strip exists
    await renderScreen(makePuzzle());
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('drop-d2d4'));
    });
    await waitForReveal();
    fireEvent.click(screen.getByTestId('train-chip-best'));
    fireEvent.click(await screen.findByTestId('train-verdict-strip'));
    fireEvent.click(screen.getByTestId('drop-c2c4')); // fork from the root
    fireEvent.click(screen.getByTestId('btn-train-analyze'));
    const entry = readTrainRevealCache();
    cleanup();
    await act(async () => {});
    nextFlush.mockClear();

    await renderScreen(makePuzzle(), makeSession(), entry);
    await waitForReveal();
    fireEvent.click(screen.getByTestId('btn-train-next'));

    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    expect(nextFlush.mock.calls[0]![2]).toMatchObject({
      v: 2,
      review_chips_selected: 1,
      review_strip_expanded: true,
      review_explored: true,
      review_analyze_opened: true,
    });
  });
});

// ─── Phase 236: the instant server-graded path (D-09 .. D-16) ───────────────

describe('TrainSolveScreen — instant server-graded path (Phase 236)', () => {
  const AFTER_E2E4_FEN = fenAfterUciMove(START_FEN, 'e2e4') ?? '';
  const INSTANT_PUZZLE = {
    key_move_uci: 'd2d4',
    puzzle_type: 'soft' as const,
    server_graded_moves: [
      { uci: 'd2d4', tier: 'good' as const },
      { uci: 'e2e4', tier: 'good' as const },
    ],
  };

  beforeEach(() => {
    matchMediaMatches = true;
    stubbedWorkerInstances = [];
    stubWorker(() => new FakeWorker());
    composeOrResumeSession.mockReset();
    solvePuzzle.mockReset();
    solvePuzzle.mockResolvedValue(SOLVE_RESPONSE);
    revealPuzzle.mockClear();
    getSettings.mockReset();
    getSettings.mockResolvedValue(makeSettings());
    stampOnboarding.mockClear();
    nextFlush.mockClear();
    exitFlush.mockClear();
    sessionStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    sessionStorage.clear();
  });

  function heldWorker(): HeldPositionWorker {
    const held = stubbedWorkerInstances.find((i) => i instanceof HeldPositionWorker);
    expect(held).toBeDefined();
    return held as HeldPositionWorker;
  }

  /** The "grade landed" signal: the Move chip is present and not in a loading state. */
  async function waitForYourMoveLine(): Promise<void> {
    await waitFor(() => {
      const chip = screen.queryByTestId('train-chip-your');
      expect(chip).not.toBeNull();
      expect(screen.queryByTestId('train-chip-your-loading')).toBeNull();
    });
  }

  async function guessAndDrop(dropTestId: string): Promise<void> {
    fireEvent.click(screen.getByTestId('btn-train-guess-critical'));
    await act(async () => {
      fireEvent.click(screen.getByTestId(dropTestId));
    });
  }

  it('instant path: a played server-graded move POSTs at once with the payload tier, and its late reading rides the Next flush (Phase 236 D-09/D-10/D-12/D-16)', async () => {
    stubWorker(() => new HeldPositionWorker(AFTER_E2E4_FEN));
    await renderScreen(makePuzzle(INSTANT_PUZZLE));
    await guessAndDrop('drop-e2e4');
    // D-16: no grading copy right after the drop either.
    expect(screen.queryByTestId('train-grading-indicator')).toBeNull();
    await waitForReveal();

    // The after-played search is STILL held: the verdict did not wait for it.
    expect(heldWorker().heldCount).toBe(1);
    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    const body = solvePuzzle.mock.calls[0]?.[1];
    expect(body?.move_quality).toBe('good');
    expect(body).not.toHaveProperty('phone_grade');
    expect(body).not.toHaveProperty('recheck');
    expect(screen.queryByTestId('train-grading-indicator')).toBeNull();

    act(() => releaseHeldWorkers());
    await waitForYourMoveLine();

    fireEvent.click(screen.getByTestId('btn-train-next'));
    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    expect(nextFlush.mock.calls[0]?.[2].phone_grade).toEqual({
      v: 1,
      tier: 'good',
      key_depth: 10,
      played_depth: 10,
      key_es: expect.any(Number),
      played_es: expect.any(Number),
    });
  });

  it('instant path: playing the key keeps the graded path and its POST record (D-05/D-13)', async () => {
    stubWorker(() => new FakeWorker('d7d5', 'd7d5'));
    await renderScreen(makePuzzle(INSTANT_PUZZLE));
    await guessAndDrop('drop-d2d4');
    await waitForReveal();

    expect(solvePuzzle).toHaveBeenCalledTimes(1);
    const phoneGrade = solvePuzzle.mock.calls[0]?.[1].phone_grade;
    expect(phoneGrade).toBeDefined();
    expect(phoneGrade?.played_depth).toBe(phoneGrade?.key_depth);
  });

  it('instant path: the Best chip shows the key line at once and the Move chip loads, then fills (Phase 236 D-14)', async () => {
    stubWorker(() => new HeldPositionWorker(AFTER_E2E4_FEN));
    await renderScreen(makePuzzle(INSTANT_PUZZLE));
    await guessAndDrop('drop-e2e4');
    await waitForReveal();

    // The played-move search is held: the Move chip is loading, while the
    // anchor (key line) settled, so the Best chip is already filled.
    expect(heldWorker().heldCount).toBe(1);
    await waitFor(() => expect(screen.getByTestId('train-chip-best-eval')).not.toBeNull());
    expect(screen.queryByTestId('train-chip-best-loading')).toBeNull();
    expect(screen.getByTestId('train-chip-your-loading')).not.toBeNull();
    expect(screen.getByTestId('train-chip-your').getAttribute('data-line-status')).toBe('loading');

    act(() => releaseHeldWorkers());
    await waitForYourMoveLine();
    expect(screen.queryByTestId('train-chip-your-loading')).toBeNull();
    expect(screen.getByTestId('train-chip-your-eval')).not.toBeNull();
  });

  it('D-16: the instant POST round trip shows a copy-less spinner, never "Checking your move…"', async () => {
    let resolveSolve: (value: SolveResponse) => void = () => {};
    solvePuzzle.mockImplementationOnce(
      () => new Promise<SolveResponse>((resolve) => (resolveSolve = resolve)),
    );
    await renderScreen(makePuzzle(INSTANT_PUZZLE));
    await guessAndDrop('drop-e2e4');

    expect(screen.getByTestId('train-submitting-indicator')).not.toBeNull();
    expect(screen.queryByTestId('train-grading-indicator')).toBeNull();
    expect(screen.queryByTestId('train-recheck-indicator')).toBeNull();
    expect(screen.getByTestId('train-submitting-indicator').textContent).toBe('');

    await act(async () => {
      resolveSolve(SOLVE_RESPONSE);
    });
    await waitForReveal();
    expect(screen.queryByTestId('train-submitting-indicator')).toBeNull();
  });

  it('D-16: before the phone grade lands the board follows the server pair and the key (never an Also fine arrow); the eval bar waits for the grade', async () => {
    stubWorker(() => new HeldPositionWorker(AFTER_E2E4_FEN));
    solvePuzzle.mockResolvedValueOnce({
      ...SOLVE_RESPONSE,
      puzzle_type: 'soft',
      vetted_moves: [
        { uci: 'd2d4', quality: 'good' },
        { uci: 'e2e4', quality: 'good' },
      ],
      graded_es_before: 0.6,
      graded_es_after: 0.59,
    });
    await renderScreen(makePuzzle(INSTANT_PUZZLE));
    await guessAndDrop('drop-e2e4');
    await waitForReveal();
    expect(heldWorker().heldCount).toBe(1);

    const board = () => screen.getByTestId('chessboard');
    // The played badge (server pair) and the best arrow (the key) are both drawn.
    await waitFor(() => {
      const ucis = (board().getAttribute('data-arrow-ucis') ?? '').split(',');
      expect(ucis).toContain('e2e4');
      expect(ucis).toContain('d2d4');
    });
    expect(board().getAttribute('data-arrow-colors') ?? '').toContain(MOVE_QUALITY_GOOD);

    // The eval bar's own Worker would compete with the held background search.
    expect(screen.getByTestId('train-eval-bar-placeholder')).not.toBeNull();
    expect(screen.queryByTestId('train-eval-bar')).toBeNull();

    act(() => releaseHeldWorkers());
    await waitForYourMoveLine();
    await waitFor(() => expect(screen.getByTestId('train-eval-bar')).not.toBeNull());
    expect(screen.queryByTestId('train-eval-bar-placeholder')).toBeNull();
    // The key is still the best arrow, not an Also fine one, once the grade landed.
    expect((board().getAttribute('data-arrow-ucis') ?? '').split(',')).toContain('d2d4');
  });

  it('D-09: every verdict surface renders the SolveResponse, never the payload tier', async () => {
    matchMediaMatches = false; // phone: the strip total plus its expanded details
    stubWorker(() => new HeldPositionWorker(AFTER_E2E4_FEN));
    // The payload says inaccuracy for the played move; the server answers good.
    await renderScreen(
      makePuzzle({
        ...INSTANT_PUZZLE,
        server_graded_moves: [
          { uci: 'd2d4', tier: 'good' },
          { uci: 'e2e4', tier: 'inaccuracy' },
        ],
      }),
    );
    await guessAndDrop('drop-e2e4');
    await waitForReveal();

    expect(solvePuzzle.mock.calls[0]?.[1].move_quality).toBe('inaccuracy');
    const expectedPoints = scorePuzzle(SOLVE_RESPONSE.correct_guess, SOLVE_RESPONSE.move_quality);
    await waitFor(() => expect(screen.getByTestId('train-points-flash')).not.toBeNull());
    expect(screen.getByTestId('train-points-flash').textContent).toBe(`+${expectedPoints}`);
    // The strip total and the expanded move pill state the SERVER's points, not the payload tier's.
    expect(screen.getByTestId('train-verdict-strip-points').textContent).toBe(`+${expectedPoints}`);
    act(() => releaseHeldWorkers());
    await waitForYourMoveLine();
    await openVerdictStrip();
    expect(screen.getByTestId('train-bot-pill-move').textContent).toContain(
      String(MOVE_TIER_POINTS[SOLVE_RESPONSE.move_quality]),
    );
  });

  it('Pitfall 1: the reveal game-move search queues behind the background grade, never stopping it', async () => {
    revealPuzzle.mockResolvedValueOnce({
      game_id: 100,
      ply: 20,
      fen: START_FEN,
      played_in_game_san: 'Nf3',
      played_in_game_move_uci: 'g1f3',
      puzzle_type: 'sharp' as const,
      source: 'sr_item' as const,
      has_tactic_lines: false,
    });
    stubWorker(() => new HeldPositionWorker(AFTER_E2E4_FEN));
    await renderScreen(makePuzzle(INSTANT_PUZZLE));
    await guessAndDrop('drop-e2e4');
    await waitForReveal();
    // The reveal query resolved and the game-move search was requested.
    await waitFor(() => expect(revealPuzzle).toHaveBeenCalled());
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    // The played search is still held and nothing stopped it.
    expect(heldWorker().heldCount).toBe(1);
    expect(heldWorker().stopsWhileHeld).toBe(0);

    act(() => releaseHeldWorkers());
    await waitForYourMoveLine();
    await waitFor(() => expect(screen.getByTestId('train-chip-game')).not.toBeNull());
    await waitFor(() => expect(screen.queryByTestId('train-chip-game-loading')).toBeNull());
    expect(screen.getByTestId('train-chip-game').getAttribute('data-line-status')).toBeNull();

    fireEvent.click(screen.getByTestId('btn-train-next'));
    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    expect(nextFlush.mock.calls[0]?.[2].phone_grade).toBeDefined();
  });

  it('D-15: a rejecting background grade leaves the verdict open, no grading error and no phone_grade', async () => {
    const gradeMove = vi.fn<TrainGradingEngine['gradeMove']>().mockRejectedValue(new Error('grading timed out'));
    await renderScreen(makePuzzle(INSTANT_PUZZLE), makeSession(), null, gradeMove);
    await guessAndDrop('drop-e2e4');
    await waitForReveal();
    await waitFor(() => expect(gradeMove).toHaveBeenCalledTimes(1));
    await act(async () => {});

    expect(screen.queryByTestId('train-grading-error')).toBeNull();
    expect(screen.queryByTestId('train-grading-indicator')).toBeNull();
    expect(screen.getByTestId('train-reveal')).not.toBeNull();
    // Phase 236 D-15: the Move chip shows its SAN and mark only: no loading, no eval, no error copy.
    const yourChip = screen.getByTestId('train-chip-your');
    expect(yourChip.getAttribute('data-line-status')).toBe('failed');
    expect(screen.queryByTestId('train-chip-your-loading')).toBeNull();
    expect(screen.queryByTestId('train-chip-your-eval')).toBeNull();
    expect(screen.getByTestId('train-chip-your-san').textContent).toBe('e4');

    fireEvent.click(screen.getByTestId('btn-train-next'));
    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    expect(nextFlush.mock.calls[0]?.[2]).not.toHaveProperty('phone_grade');
  });

  it('WR-01/D-15: a grading Worker error after the instant verdict keeps the verdict bubble and its Next button', async () => {
    stubWorker(() => new HeldPositionWorker(AFTER_E2E4_FEN));
    await renderScreen(makePuzzle(INSTANT_PUZZLE));
    await guessAndDrop('drop-e2e4');
    await waitForReveal();
    // The background search is held: the verdict is on screen while the Worker still works.
    expect(heldWorker().heldCount).toBe(1);

    // The Worker dies mid-search (e.g. a wasm out-of-memory crash on a phone):
    // the hook's own worker.onerror flips hasError and rejects the pending grade.
    await act(async () => {
      (heldWorker().onerror as (e: unknown) => void)(new Event('error'));
    });

    // The engine-error branch must not displace the landed verdict (D-15).
    expect(screen.queryByTestId('train-engine-error')).toBeNull();
    expect(screen.queryByTestId('btn-train-engine-retry')).toBeNull();
    expect(screen.getByTestId('train-reveal')).not.toBeNull();
    expect(screen.getByTestId('btn-train-next')).not.toBeNull();
  });

  it('WR-02: Analyze pressed before the background grade lands still caches the solved reveal from the server pair', async () => {
    stubWorker(() => new HeldPositionWorker(AFTER_E2E4_FEN));
    solvePuzzle.mockResolvedValueOnce({
      ...SOLVE_RESPONSE,
      puzzle_type: 'soft',
      graded_es_before: 0.6,
      graded_es_after: 0.59,
    });
    await renderScreen(makePuzzle(INSTANT_PUZZLE));
    await guessAndDrop('drop-e2e4');
    await waitForReveal();
    // The played-move search is still held: gradeResult is null when Analyze is pressed.
    expect(heldWorker().heldCount).toBe(1);

    fireEvent.click(screen.getByTestId('btn-train-analyze'));

    const cached = readTrainRevealCache();
    expect(cached).not.toBeNull();
    expect(cached?.playedMoveUci).toBe('e2e4');
    // Real server numbers, the key as the best move, and no played-move line to restore.
    expect(cached?.gradeResult.bestMoveUci).toBe('d2d4');
    expect(cached?.gradeResult.esBefore).toBe(0.6);
    expect(cached?.gradeResult.esAfter).toBe(0.59);
    expect(cached?.gradeResult.playedLine.moves).toEqual([]);
    expect(cached?.gradeResult.phoneReading).toBeNull();

    // Browser Back: the stand-in restores a solved reveal (verdict plus key card), no crash.
    cleanup();
    stubbedWorkerInstances = [];
    stubWorker(() => new FakeWorker());
    await renderScreen(makePuzzle(INSTANT_PUZZLE), makeSession(), readTrainRevealCache());
    await waitForReveal();
    await waitFor(() => expect(screen.getByTestId('train-chip-best')).not.toBeNull());
    expect(screen.queryByTestId('train-grading-error')).toBeNull();
  });

  it('WR-02: without a server pair on the verdict there is nothing real to cache, so Analyze caches no reveal', async () => {
    stubWorker(() => new HeldPositionWorker(AFTER_E2E4_FEN));
    await renderScreen(makePuzzle(INSTANT_PUZZLE));
    await guessAndDrop('drop-e2e4');
    await waitForReveal();
    expect(heldWorker().heldCount).toBe(1);

    fireEvent.click(screen.getByTestId('btn-train-analyze'));

    expect(readTrainRevealCache()).toBeNull();
  });

  it('Pitfall 4: a background grade settling after the user moved on never lands on the next puzzle', async () => {
    const lateGrade: GradeResult = {
      moveTier: 'good',
      bestMoveUci: 'd2d4',
      esBefore: 0.5,
      esAfter: 0.5,
      bestLine: { moves: ['d2d4'], evalCp: 20, evalMate: null },
      playedLine: { moves: ['e2e4'], evalCp: 20, evalMate: null },
      phoneReading: { tier: 'good', keyEs: 0.5, playedEs: 0.5, keyDepth: 10, playedDepth: 10 },
    };
    const resolvers: Array<(grade: GradeResult) => void> = [];
    const gradeMove = vi.fn<TrainGradingEngine['gradeMove']>(
      () => new Promise<GradeResult>((resolve) => resolvers.push(resolve)),
    );
    const puzzleA = makePuzzle(INSTANT_PUZZLE);
    const { rerender } = await renderScreen(puzzleA, makeSession(), null, gradeMove);
    await guessAndDrop('drop-e2e4');
    await waitForReveal();
    expect(resolvers).toHaveLength(1);

    // Puzzle B (a different fen and position) on the SAME component instance, also instant.
    const puzzleB = makePuzzle({
      position: 2,
      ply: 30,
      fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
      key_move_uci: 'g1f3',
      puzzle_type: 'soft',
      server_graded_moves: [
        { uci: 'g1f3', tier: 'good' },
        { uci: 'd2d4', tier: 'good' },
      ],
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    rerender(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            <Harness puzzle={puzzleB} gradeMoveOverride={gradeMove} />
          </TooltipProvider>
        </QueryClientProvider>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.queryByTestId('train-reveal')).toBeNull());
    await guessAndDrop('drop-d2d4');
    await waitForReveal();
    expect(solvePuzzle).toHaveBeenCalledTimes(2);
    expect(resolvers).toHaveLength(2);
    // Phase 236 D-14: B's You chip is in its loading state, B's own grade has not landed.
    expect(screen.queryByTestId('train-chip-your-loading')).not.toBeNull();

    // A's grade settles now, while B is on screen: it must not fill B's card.
    await act(async () => {
      resolvers[0]?.(lateGrade);
    });
    await act(async () => {});
    expect(screen.queryByTestId('train-chip-your-loading')).not.toBeNull();

    fireEvent.click(screen.getByTestId('btn-train-next'));
    await waitFor(() => expect(nextFlush).toHaveBeenCalledTimes(1));
    expect(nextFlush.mock.calls[0]?.[1]).toBe(puzzleB.position);
    expect(nextFlush.mock.calls[0]?.[2]).not.toHaveProperty('phone_grade');
  });
});
