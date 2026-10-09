// @vitest-environment jsdom
/**
 * TrainReveal.test.tsx — the reveal panel's presentational coverage: the guess
 * verdict card and its prose, the mastery banner, D-11/D-12 copy, the game
 * footer, the game-move search state reporting, and (Phase 237) the chips row
 * plus the move-list slot that replaced the three line cards. The chip/tree
 * behavior itself is covered by TrainLineChips / TrainMoveTreeList /
 * useTrainRevealTree tests and, end to end, by TrainSolveScreen.test.tsx.
 * The Solution/Analyze/Next row lives in TrainSolveScreen (tested there).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import type { ComponentProps } from 'react';
import { TrainReveal } from '@/components/train/TrainReveal';
import { TooltipProvider } from '@/components/ui/tooltip';
import { formatDateWithYear } from '@/lib/utils';
import { buildGameAnalysisUrl } from '@/lib/analysisUrl';
import { SETTINGS_STORAGE_KEYS } from '@/lib/engineSettings';
import { guessFeedbackProse } from '@/lib/trainGuessLabels';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import { verdictCopy } from '@/lib/trainBotCopy';
import { buildChipGroups } from '@/lib/trainRevealLines';
import type { BuildChipGroupsInput, ChipGroup } from '@/lib/trainRevealLines';
import type { GradeResult, TrainEngineLine, TrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import type { PuzzleRevealResponse, SolveResponse, TrainPuzzle } from '@/types/train';
import type { GameFlawCard } from '@/types/library';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

// ─── api/client mock ────────────────────────────────────────────────────────

const revealPuzzle = vi.fn<(sessionId: number, position: number) => Promise<PuzzleRevealResponse>>();
const getGame = vi.fn();

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      ...actual.trainApi,
      revealPuzzle: (sessionId: number, position: number) => revealPuzzle(sessionId, position),
    },
    libraryApi: {
      ...actual.libraryApi,
      getGame: (gameId: number) => getGame(gameId),
    },
  };
});

// 190.1 UAT round 4: the line steppers play move sounds — mocked so jsdom
// never touches real Audio machinery.
vi.mock('@/lib/sounds', () => ({
  playSound: vi.fn(),
}));

// ─── matchMedia stub (Phase 200: useIsDesktop) ─────────────────────────────
// Controllable per test (Bots.test.tsx L221 jsdom-shim precedent, with a
// settable `matches` instead of a fixed `false`) so both the desktop-hover
// (D-06) and mobile-tap (D-08) paths are exercisable in the same file.
let matchMediaMatches = true;
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: matchMediaMatches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// ─── Fixtures ───────────────────────────────────────────────────────────────

function makePuzzle(overrides: Partial<TrainPuzzle> = {}): TrainPuzzle {
  return {
    position: 5,
    game_id: 100,
    ply: 20,
    fen: START_FEN,
    side_to_move: 'white',
    last_move_uci: 'd7d5',
    ...overrides,
  };
}

function makeVerdict(overrides: Partial<SolveResponse> = {}): SolveResponse {
  return {
    correct_guess: true,
    correct_move: true,
    move_quality: 'good',
    puzzle_type: 'sharp',
    // Phase 206 (D-19): defaults to 'sr_item' so pre-existing callers that
    // only override `puzzle_type` keep exercising the "own game" branch at
    // all three D-19 sites exactly as before this field existed.
    source: 'sr_item',
    item_status: 'active',
    streak: 1,
    due_date: '2026-08-01',
    session_complete: false,
    ...overrides,
  };
}

function makeReveal(overrides: Partial<PuzzleRevealResponse> = {}): PuzzleRevealResponse {
  return {
    game_id: 100,
    ply: 20,
    fen: START_FEN,
    played_in_game_san: null,
    played_in_game_move_uci: null,
    puzzle_type: 'sharp',
    source: 'sr_item',
    has_tactic_lines: false,
    motif: null,
    ...overrides,
  };
}

function makeEngineLine(overrides: Partial<TrainEngineLine> = {}): TrainEngineLine {
  return { moves: ['e2e4'], evalCp: 50, evalMate: null, ...overrides };
}

function makeGradeResult(overrides: Partial<GradeResult> = {}): GradeResult {
  return {
    correctMove: true,
    bestMoveUci: 'e2e4',
    esBefore: 0.5,
    esAfter: 0.5,
    bestLine: makeEngineLine(),
    playedLine: makeEngineLine(),
    ...overrides,
  };
}

/** Stub `TrainGradingEngine` (190.1-01) — only `startGameMoveSearch` matters
 * to TrainReveal; the other members are never called from this component. */
function makeGradingEngine(overrides: Partial<TrainGradingEngine> = {}): TrainGradingEngine {
  return {
    isReady: true,
    hasError: false,
    startGrading: vi.fn(),
    abortGrading: vi.fn(),
    restartEngine: vi.fn(),
    gradeMove: vi.fn(),
    recheckMove: vi.fn(),
    startGameMoveSearch: vi.fn<(puzzleFen: string, gameMoveUci: string) => Promise<TrainEngineLine>>()
      .mockResolvedValue({ moves: [], evalCp: null, evalMate: null }),
    ...overrides,
  };
}

/** Minimal `GameFlawCard` fixture (Task 2's footer only reads
 * user_color/white_username/black_username/played_at). */
function makeGame(overrides: Partial<GameFlawCard> = {}): GameFlawCard {
  return {
    game_id: 100,
    user_result: 'win',
    played_at: '2026-07-20T12:00:00Z',
    time_control_bucket: 'blitz',
    platform: 'lichess',
    platform_url: null,
    white_username: 'alice',
    black_username: 'bob',
    white_rating: 1500,
    black_rating: 1500,
    opening_name: null,
    opening_eco: null,
    user_color: 'white',
    ply_count: 40,
    termination: 'checkmate',
    time_control_str: '5+0',
    result_fen: null,
    severity_counts: null,
    white_accuracy: null,
    black_accuracy: null,
    chips: [],
    analysis_state: 'no_engine_analysis',
    eval_series: null,
    flaw_markers: null,
    phase_transitions: null,
    moves: null,
    active_eval_status: null,
    opening_ply_count: 0,
    ...overrides,
  };
}

/** The chips the board owner would hand down: the REAL `buildChipGroups` over
 * the same inputs TrainSolveScreen feeds it (TrainReveal itself is presentational
 * about chips since Phase 237). Defaults to a played d4 against the best e4. */
function makeChips(overrides: Partial<BuildChipGroupsInput> = {}): ChipGroup[] {
  return buildChipGroups({
    puzzleFen: START_FEN,
    playedMoveUci: 'd2d4',
    gradeResult: makeGradeResult({
      bestLine: makeEngineLine({ moves: ['e2e4'], evalCp: 50 }),
      playedLine: makeEngineLine({ moves: ['d2d4'], evalCp: 10 }),
    }),
    instantGrade: null,
    gameMoveUci: null,
    gameMoveLine: { status: 'idle' },
    playedMoveQuality: 'good',
    gameMoveQuality: null,
    ...overrides,
  });
}

function renderReveal(
  props: Partial<ComponentProps<typeof TrainReveal>> = {},
  queryClient?: QueryClient,
) {
  const client = queryClient ?? new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const fullProps: ComponentProps<typeof TrainReveal> = {
    puzzle: makePuzzle(),
    sessionId: 1,
    verdict: makeVerdict(),
    isSolveError: false,
    onRetrySolve: vi.fn(),
    onNext: vi.fn(),
    gradingEngine: makeGradingEngine(),
    guess: null,
    playedMoveUci: null,
    gradeResult: null,
    chips: [],
    activeChip: null,
    onChipSelect: vi.fn(),
    treeList: null,
    verdictBot: PERSONA_REGISTRY['wall-1800'],
    verdictOpening: verdictCopy(2, true, 'good', false, () => 0),
    isBest: false,
    isWarmup: false,
    audience: { hasGames: true, isGuest: false },
    ...props,
  };
  const result = render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <TooltipProvider>
          <TrainReveal {...fullProps} />
        </TooltipProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
  return { ...result, client, props: fullProps };
}

describe('TrainReveal', () => {
  beforeEach(() => {
    matchMediaMatches = true; // desktop by default — see the module-scope stub
    revealPuzzle.mockReset();
    getGame.mockReset();
    revealPuzzle.mockResolvedValue(makeReveal());
    getGame.mockResolvedValue(makeGame());
  });

  afterEach(() => {
    cleanup();
    localStorage.removeItem(SETTINGS_STORAGE_KEYS.sfLines);
  });

  // ─── Phase 237 plan 08: the verdict surface (strip on phones, bubble on desktop) ──

  it('desktop: the verdict bubble leads the reveal column with the full details visible and no strip', () => {
    renderReveal({ guess: 'critical', isBest: true });
    const reveal = screen.getByTestId('train-reveal');
    const bubble = within(reveal).getByTestId('train-verdict-card');
    expect(within(bubble).getByTestId('train-verdict-card-avatar')).not.toBeNull();
    expect(within(bubble).getByTestId('train-bot-verdict-line').textContent).toContain('best move');
    expect(within(bubble).getByTestId('train-verdict-guess')).not.toBeNull();
    expect(screen.queryByTestId('train-verdict-strip')).toBeNull();
    // The bubble is the FIRST thing in the column.
    expect(reveal.firstElementChild).toBe(bubble);
  });

  it('phone: the strip replaces the bubble and the Your-call card, collapsed, with the isBest wording', () => {
    matchMediaMatches = false;
    renderReveal({ guess: 'critical', isBest: true });
    const strip = screen.getByTestId('train-verdict-strip');
    expect(strip.getAttribute('aria-expanded')).toBe('false');
    expect(screen.getByTestId('train-verdict-strip-line').textContent).toBe('Right call, best move');
    expect(screen.queryByTestId('train-verdict-card')).toBeNull();
    expect(screen.queryByTestId('train-verdict-guess')).toBeNull();
    fireEvent.click(strip);
    expect(screen.getByTestId('train-verdict-guess')).not.toBeNull();
  });

  it('phone: without isBest the same verdict reads "good move"', () => {
    matchMediaMatches = false;
    renderReveal({ guess: 'critical', isBest: false });
    expect(screen.getByTestId('train-verdict-strip-line').textContent).toBe('Right call, good move');
  });

  // ─── Verdict rows (190.1-03 D-03) ─────────────────────────────────────────

  // Phase 200 UAT round 3: the ✓/✗ marks became score chips stating the
  // points actually earned (guess: 1 or 0).
  it('verdict-guess row states the spelled-out critical-option wording and a +0 chip for a wrong critical guess', () => {
    renderReveal({ guess: 'critical', verdict: makeVerdict({ correct_guess: false }) });
    const text = screen.getByTestId('train-verdict-guess').textContent ?? '';
    expect(text).toContain('only one good move');
    expect(text).not.toContain('✗');
    expect(screen.getByTestId('train-bot-pill-guess').textContent).toBe('+0');
  });

  it('verdict-guess row states the spelled-out several-fine wording with a +1 chip for a correct guess', () => {
    renderReveal({ guess: 'several', verdict: makeVerdict({ correct_guess: true }) });
    const text = screen.getByTestId('train-verdict-guess').textContent ?? '';
    expect(text).toContain('several good moves');
    expect(text).not.toContain('✓');
    expect(screen.getByTestId('train-bot-pill-guess').textContent).toBe('+1');
  });

  // Phase 200 UAT round 3: the chip reads the three-way scoring tier, so an
  // inaccuracy scores +1 — the boolean correct_move could not express that.
  // Phase 200 UAT round 8: the Your-move box leads the whole panel, above the
  // guess card, on both viewports (one component serves both).
  // ─── Outcome copy — fully retired (Phase 200 UAT round 7) ─────────────────
  // Round 3 retired the miss sentence; round 7 retired the last one standing,
  // the herring "You handled this well in the game" line. The guess card's
  // body now holds the Also fine list or nothing at all.

  it('a herring renders no outcome sentence — the herring sentence is retired too', async () => {
    renderReveal({
      verdict: makeVerdict({
        correct_move: false,
        puzzle_type: 'herring',
        source: 'red_herring',
        item_status: null,
        due_date: null,
        streak: null,
      }),
    });
    await waitFor(() => expect(getGame).toHaveBeenCalled());
    expect(screen.queryByTestId('train-outcome-copy')).toBeNull();
  });

  it('a genuine miss (non-herring) renders no outcome sentence at all — the miss sentence is retired', async () => {
    renderReveal({ verdict: makeVerdict({ correct_move: false, puzzle_type: 'sharp' }) });
    await waitFor(() => expect(getGame).toHaveBeenCalled());
    expect(screen.queryByTestId('train-outcome-copy')).toBeNull();
  });

  it('a correct, non-herring solve renders no outcome sentence at all', async () => {
    renderReveal({ verdict: makeVerdict({ correct_move: true, puzzle_type: 'sharp' }) });
    await waitFor(() => expect(getGame).toHaveBeenCalled());
    expect(screen.queryByTestId('train-outcome-copy')).toBeNull();
  });

  // ─── Flaw fixed banner (PROG-03/D-14, Phase 191 Plan 03 — supersedes the
  // D-12 plain "Mastered — retired." comeback hint) ─────────────────────────

  it('item_status "mastered" renders the flaw-fixed banner', () => {
    renderReveal({ verdict: makeVerdict({ item_status: 'mastered', due_date: null }) });
    expect(screen.getByTestId('train-flaw-fixed-banner')).not.toBeNull();
  });

  // Quick 260803-iv6 (Task 2): the banner is the FIRST card in the panel —
  // above both the Your-move box and the guess card — on a mastered,
  // non-herring verdict. Asserted via `compareDocumentPosition`, not index
  // into a hand-built list, so a reordering elsewhere in the panel can't
  // accidentally make this pass for the wrong reason.
  it('the flaw-fixed banner follows the verdict surface and sits above the chips row', async () => {
    renderReveal({
      guess: 'critical',
      playedMoveUci: 'd2d4',
      chips: makeChips(),
      activeChip: 'your',
      verdict: makeVerdict({ item_status: 'mastered', due_date: null }),
    });
    const banner = screen.getByTestId('train-flaw-fixed-banner');
    const yourBox = await waitFor(() => screen.getByTestId('train-line-chips'));
    // Phase 237 plan 08 (ROADMAP item 6): the verdict bubble (desktop) leads the
    // column, then the banner, then the chips.
    const verdictSurface = screen.getByTestId('train-verdict-card');
    expect(
      verdictSurface.compareDocumentPosition(banner) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      banner.compareDocumentPosition(yourBox) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it('item_status "active" renders neither the banner nor a comeback line', () => {
    renderReveal({ verdict: makeVerdict({ item_status: 'active', due_date: '2026-07-28' }) });
    expect(screen.queryByTestId('train-flaw-fixed-banner')).toBeNull();
    expect(screen.queryByTestId('train-comeback-hint')).toBeNull();
  });

  it('item_status "parked" renders neither the banner nor a comeback line', () => {
    renderReveal({ verdict: makeVerdict({ item_status: 'parked', due_date: '2026-07-28' }) });
    expect(screen.queryByTestId('train-flaw-fixed-banner')).toBeNull();
    expect(screen.queryByTestId('train-comeback-hint')).toBeNull();
  });

  it('a herring (item_status null) renders neither the banner nor a comeback line', () => {
    renderReveal({
      verdict: makeVerdict({
        puzzle_type: 'herring',
        source: 'red_herring',
        item_status: null,
        due_date: null,
        streak: null,
      }),
    });
    expect(screen.queryByTestId('train-flaw-fixed-banner')).toBeNull();
    expect(screen.queryByTestId('train-comeback-hint')).toBeNull();
  });

  it('two mastered reveals in sequence (a new puzzle each time) each render their own single, un-pluralized banner', () => {
    const { rerender, client, props } = renderReveal({
      verdict: makeVerdict({ item_status: 'mastered', due_date: null }),
    });
    expect(screen.getAllByTestId('train-flaw-fixed-banner')).toHaveLength(1);
    expect(screen.getByText('Flaw fixed!')).not.toBeNull();

    rerender(
      <MemoryRouter>
        <QueryClientProvider client={client}>
          <TooltipProvider>
            <TrainReveal
              {...props}
              puzzle={makePuzzle({ position: 6 })}
              verdict={makeVerdict({ item_status: 'mastered', due_date: null })}
            />
          </TooltipProvider>
        </QueryClientProvider>
      </MemoryRouter>,
    );
    // Still exactly one banner with the same singular heading — a second
    // mastery in the SAME session never batches into a "2 fixed" count.
    expect(screen.getAllByTestId('train-flaw-fixed-banner')).toHaveLength(1);
    expect(screen.getByText('Flaw fixed!')).not.toBeNull();
  });

  // ─── Chips row + move list slot (Phase 237 D-01..D-03) ─────────────────────

  it('an empty chips list renders no chip row', async () => {
    revealPuzzle.mockResolvedValue(makeReveal());
    renderReveal();
    await waitFor(() => expect(getGame).toHaveBeenCalled());
    expect(screen.queryByTestId('train-line-chips')).toBeNull();
    expect(screen.queryByTestId('train-move-tree-slot')).toBeNull();
  });

  it('renders the chips row and the treeList slot, and a chip tap reaches onChipSelect with its role key', async () => {
    const onChipSelect = vi.fn();
    renderReveal({
      guess: 'critical',
      playedMoveUci: 'd2d4',
      chips: makeChips(),
      activeChip: 'your',
      onChipSelect,
      treeList: <div data-testid="train-move-tree-slot" />,
    });
    expect(screen.getByTestId('train-line-chips')).not.toBeNull();
    expect(screen.getByTestId('train-chip-your').getAttribute('data-active')).toBe('true');
    expect(screen.getByTestId('train-move-tree-slot')).not.toBeNull();
    fireEvent.click(screen.getByTestId('train-chip-best'));
    expect(onChipSelect).toHaveBeenCalledWith('best');
    await waitFor(() => expect(getGame).toHaveBeenCalled());
  });

  it('a game move with a SAN but no UCI renders a non-interactive game chip', async () => {
    revealPuzzle.mockResolvedValue(makeReveal({ played_in_game_san: 'Nf3', played_in_game_move_uci: null }));
    renderReveal({ guess: 'critical', playedMoveUci: 'd2d4', chips: makeChips(), activeChip: 'your' });
    const gameChip = await waitFor(() => screen.getByTestId('train-chip-game'));
    expect(gameChip.getAttribute('data-interactive')).toBe('false');
    expect(gameChip.textContent).toContain('Nf3');
  });

  it('while the verdict is absent no chip row and no tree slot render', () => {
    renderReveal({
      verdict: null,
      chips: [],
      treeList: <div data-testid="train-move-tree-slot" />,
    });
    expect(screen.queryByTestId('train-line-chips')).toBeNull();
    expect(screen.queryByTestId('train-move-tree-slot')).toBeNull();
  });

  describe('Phase 237 plan 10: first-reveal tour rings and bubble slot (D-10)', () => {
    const TREE_SLOT = <div data-testid="train-move-tree-slot" />;
    const renderWithTarget = async (
      walkthroughTarget: ComponentProps<typeof TrainReveal>['walkthroughTarget'],
    ): Promise<void> => {
      renderReveal({
        guess: 'critical',
        playedMoveUci: 'd2d4',
        chips: makeChips(),
        activeChip: 'your',
        treeList: TREE_SLOT,
        walkthroughTarget,
      });
      await waitFor(() => screen.getByTestId('train-line-chips'));
    };
    const chipsRinged = (): boolean => screen.getByTestId('train-line-chips').className.includes('ring-2');
    const treeRinged = (): boolean =>
      screen.getByTestId('train-tree-tour-ring').className.includes('ring-2');

    // Phase 237 UAT: the chips row is never ringed as a row (the active chip's
    // own ring already marks it).
    it('chips rings nothing: the active chip carries its own ring', async () => {
      await renderWithTarget('chips');
      expect(chipsRinged()).toBe(false);
      expect(treeRinged()).toBe(false);
      expect(screen.getByTestId('train-chip-your').className).toContain('ring-2');
    });

    it('tree rings the move list only', async () => {
      await renderWithTarget('tree');
      expect(chipsRinged()).toBe(false);
      expect(treeRinged()).toBe(true);
    });

    it('lines rings the move list (never the chips row)', async () => {
      await renderWithTarget('lines');
      expect(chipsRinged()).toBe(false);
      expect(treeRinged()).toBe(true);
    });

    it.each(['verdict', 'board', 'bar'] as const)('%s rings neither the chips row nor the list', async (target) => {
      await renderWithTarget(target);
      expect(chipsRinged()).toBe(false);
      expect(treeRinged()).toBe(false);
    });

    it('no target (null) rings nothing', async () => {
      await renderWithTarget(null);
      expect(chipsRinged()).toBe(false);
      expect(treeRinged()).toBe(false);
    });

    it('the chips row and the list sit inside their tour-target wrappers', async () => {
      await renderWithTarget(null);
      const chips = screen.getByTestId('train-line-chips');
      expect(chips.closest('[data-tour-target="chips"]')).not.toBeNull();
      expect(screen.getByTestId('train-move-tree-slot').closest('[data-tour-target="tree"]')).not.toBeNull();
    });

    it('on desktop the verdict target rings the verdict card', () => {
      renderReveal({ walkthroughTarget: 'verdict' });
      expect(screen.getByTestId('train-verdict-card').className).toContain('ring-2');
    });

    it('on a phone the verdict target rings the strip', () => {
      matchMediaMatches = false;
      renderReveal({ walkthroughTarget: 'verdict' });
      expect(screen.getByTestId('train-verdict-strip-root').className).toContain('ring-2');
    });
  });

  it('game move equals best move dispatches no reveal-time search', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ played_in_game_san: 'e4', played_in_game_move_uci: 'e2e4' }),
    );
    const gradeResult = makeGradeResult({
      bestLine: makeEngineLine({ moves: ['e2e4'], evalCp: 50, evalMate: null }),
      playedLine: makeEngineLine({ moves: ['d2d4'], evalCp: 10, evalMate: null }),
    });
    const startGameMoveSearch = vi.fn();
    const onGameMoveUciChange = vi.fn();
    renderReveal({
      guess: 'critical',
      playedMoveUci: 'd2d4',
      gradeResult,
      gradingEngine: makeGradingEngine({ startGameMoveSearch }),
      onGameMoveUciChange,
    });
    // The reveal GET resolves asynchronously: wait for the game move to be known
    // before asserting that nothing was searched.
    await waitFor(() => expect(onGameMoveUciChange).toHaveBeenCalledWith('e2e4'));
    expect(startGameMoveSearch).not.toHaveBeenCalled();
  });

  it('game move equals played move dispatches no reveal-time search', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ played_in_game_san: 'd4', played_in_game_move_uci: 'd2d4' }),
    );
    const gradeResult = makeGradeResult({
      bestLine: makeEngineLine({ moves: ['e2e4'], evalCp: 50, evalMate: null }),
      playedLine: makeEngineLine({ moves: ['d2d4'], evalCp: 10, evalMate: null }),
    });
    const startGameMoveSearch = vi.fn();
    const onGameMoveUciChange = vi.fn();
    renderReveal({
      guess: 'critical',
      playedMoveUci: 'd2d4',
      gradeResult,
      gradingEngine: makeGradingEngine({ startGameMoveSearch }),
      onGameMoveUciChange,
    });
    await waitFor(() => expect(onGameMoveUciChange).toHaveBeenCalledWith('d2d4'));
    expect(startGameMoveSearch).not.toHaveBeenCalled();
  });

  it('onGameMoveUciChange reports the resolved game-move UCI, and null on unmount (190.1-04)', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ played_in_game_san: 'e4', played_in_game_move_uci: 'e2e4' }),
    );
    const onGameMoveUciChange = vi.fn();
    const { unmount } = renderReveal({
      gradingEngine: makeGradingEngine({ startGameMoveSearch: vi.fn().mockResolvedValue(makeEngineLine()) }),
      onGameMoveUciChange,
    });
    await waitFor(() => expect(onGameMoveUciChange).toHaveBeenCalledWith('e2e4'));
    unmount();
    expect(onGameMoveUciChange).toHaveBeenLastCalledWith(null);
  });

  it('onGameMoveLineStateChange reports loading, then the searched line, and idle on unmount (Phase 237)', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ played_in_game_san: 'e4', played_in_game_move_uci: 'e2e4' }),
    );
    const searchedLine = makeEngineLine({ moves: ['e2e4', 'e7e5'], evalCp: -120 });
    const onGameMoveLineStateChange = vi.fn();
    const { unmount } = renderReveal({
      gradingEngine: makeGradingEngine({
        startGameMoveSearch: vi.fn().mockResolvedValue(searchedLine),
      }),
      onGameMoveLineStateChange,
    });
    await waitFor(() =>
      expect(onGameMoveLineStateChange).toHaveBeenCalledWith({ status: 'ready', line: searchedLine }),
    );
    const statuses = onGameMoveLineStateChange.mock.calls.map(([state]) => state.status);
    expect(statuses.indexOf('loading')).toBeGreaterThanOrEqual(0);
    expect(statuses.indexOf('loading')).toBeLessThan(statuses.indexOf('ready'));
    unmount();
    expect(onGameMoveLineStateChange).toHaveBeenLastCalledWith({ status: 'idle' });
  });

  it('a non-null played_in_game_move_uci dispatches the reveal-time search on the puzzle fen', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ played_in_game_san: 'e4', played_in_game_move_uci: 'e2e4' }),
    );
    const startGameMoveSearch = vi
      .fn()
      .mockResolvedValue({ moves: ['e2e4', 'e7e5'], evalCp: 35, evalMate: null });
    const onGameMoveLineStateChange = vi.fn();
    renderReveal({
      gradingEngine: makeGradingEngine({ startGameMoveSearch }),
      onGameMoveLineStateChange,
    });
    await waitFor(() =>
      expect(onGameMoveLineStateChange).toHaveBeenCalledWith({
        status: 'ready',
        line: { moves: ['e2e4', 'e7e5'], evalCp: 35, evalMate: null },
      }),
    );
    expect(startGameMoveSearch).toHaveBeenCalledWith(START_FEN, 'e2e4');
  });

  it('a game-move search that never settles stays in the loading state, and the verdict rows still render (190.1-01 Task 2)', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ played_in_game_san: 'e4', played_in_game_move_uci: 'e2e4' }),
    );
    const startGameMoveSearch = vi.fn().mockReturnValue(new Promise(() => {})); // never settles
    const onGameMoveLineStateChange = vi.fn();
    renderReveal({ gradingEngine: makeGradingEngine({ startGameMoveSearch }), onGameMoveLineStateChange });
    await waitFor(() => expect(onGameMoveLineStateChange).toHaveBeenCalledWith({ status: 'loading' }));
    expect(onGameMoveLineStateChange).not.toHaveBeenCalledWith(expect.objectContaining({ status: 'ready' }));
    expect(onGameMoveLineStateChange).not.toHaveBeenCalledWith({ status: 'error' });
    expect(screen.getByTestId('train-verdict-guess')).not.toBeNull();
  });

  it('a rejecting game-move search reports the error state, and the other reveal blocks still render (190.1-01 Task 2)', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ played_in_game_san: 'e4', played_in_game_move_uci: 'e2e4' }),
    );
    const startGameMoveSearch = vi.fn().mockRejectedValue(new Error('search failed'));
    // bestLine deliberately distinct from BOTH the played move and the game
    // move ('e2e4') — otherwise the coincidence-merge guard would skip the
    // reveal-time search this test exists to exercise.
    // bestMoveUci must agree with bestLine: since WR-01 the Best chip reads
    // bestMoveUci, and the default 'e2e4' would coincide with the game move.
    const gradeResult = makeGradeResult({
      bestMoveUci: 'g1f3',
      bestLine: makeEngineLine({ moves: ['g1f3'] }),
      playedLine: makeEngineLine({ moves: ['d2d4'] }),
    });
    const onGameMoveLineStateChange = vi.fn();
    renderReveal({
      playedMoveUci: 'd2d4',
      gradeResult,
      gradingEngine: makeGradingEngine({ startGameMoveSearch }),
      chips: makeChips({ gradeResult, gameMoveUci: 'e2e4', gameMoveLine: { status: 'error' } }),
      activeChip: 'your',
      onGameMoveLineStateChange,
    });
    await waitFor(() => expect(onGameMoveLineStateChange).toHaveBeenCalledWith({ status: 'error' }));
    // The other reveal blocks (verdict rows, the chips row) still render normally.
    expect(screen.getByTestId('train-verdict-guess')).not.toBeNull();
    expect(screen.getByTestId('train-chip-your')).not.toBeNull();
    expect(screen.getByTestId('train-chip-game').getAttribute('data-line-status')).toBe('failed');
  });

  // ─── Tactic opt-in (SOLV-06) — REMOVED per 190.1 UAT round 4 ──────────────

  it('a tactic-tagged reveal renders NO tactic opt-in trigger (removed, UAT round 4)', async () => {
    revealPuzzle.mockResolvedValue(makeReveal({ has_tactic_lines: true }));
    renderReveal();
    await waitFor(() => expect(getGame).toHaveBeenCalled());
    expect(screen.queryByTestId('btn-train-tactic-step')).toBeNull();
  });

  // ─── Sharp filler motif line (Phase 206, D-20) ────────────────────────────

  it('a non-null motif renders exactly one Motif row inside the guess card', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ source: 'sharp_filler', puzzle_type: 'sharp', motif: 'Fork' }),
    );
    renderReveal({ verdict: makeVerdict({ puzzle_type: 'sharp', source: 'sharp_filler' }) });
    await waitFor(() => expect(screen.getByTestId('train-reveal-motif')).not.toBeNull());
    expect(screen.getByTestId('train-reveal-motif').textContent).toBe('Motif: Fork');
    expect(screen.getAllByTestId('train-reveal-motif')).toHaveLength(1);
  });

  it('a null motif (the normal SR/herring case) renders no Motif row, no placeholder, no dash', async () => {
    revealPuzzle.mockResolvedValue(makeReveal({ motif: null }));
    // guess set (-> non-null guessProse) so the guess CardBody itself
    // renders regardless of motif — otherwise this test would trivially
    // pass whenever the whole card is absent, never actually exercising
    // the motif row's own null guard.
    renderReveal({ guess: 'several' });
    await waitFor(() => expect(getGame).toHaveBeenCalled());
    expect(screen.getByTestId('train-verdict-guess-prose')).not.toBeNull();
    expect(screen.queryByTestId('train-reveal-motif')).toBeNull();
  });

  it('the motif row text size is text-sm, never text-xs', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ source: 'sharp_filler', puzzle_type: 'sharp', motif: 'Skewer' }),
    );
    renderReveal({ verdict: makeVerdict({ puzzle_type: 'sharp', source: 'sharp_filler' }) });
    const motifRow = await screen.findByTestId('train-reveal-motif');
    expect(motifRow.className).toContain('text-sm');
    expect(motifRow.className).not.toContain('text-xs');
  });

  // ─── Opponent-and-date footer (190.1-03 D-03, Task 2) ─────────────────────

  it('the game-card query is disabled while the solve response is absent, and enabled once it is present', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { rerender, props } = renderReveal({ verdict: null, isSolveError: false }, client);
    expect(getGame).not.toHaveBeenCalled();

    rerender(
      <MemoryRouter>
        <QueryClientProvider client={client}>
          <TooltipProvider>
            <TrainReveal {...props} verdict={makeVerdict()} />
          </TooltipProvider>
        </QueryClientProvider>
      </MemoryRouter>,
    );
    await waitFor(() => expect(getGame).toHaveBeenCalledTimes(1));
  });

  it('footer reads "Game: TC · vs OPPONENT (elo) · date" with the BLACK side as opponent for a user_color: white fixture', async () => {
    getGame.mockResolvedValue(
      makeGame({
        user_color: 'white',
        black_username: 'bob',
        black_rating: 1622,
        time_control_bucket: 'blitz',
        time_control_str: '300',
        played_at: '2026-07-20T12:00:00Z',
      }),
    );
    renderReveal();
    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
    const text = screen.getByTestId('train-reveal-footer').textContent ?? '';
    expect(text).toContain('Game:');
    expect(text).toContain('blitz');
    expect(text).toContain('vs bob (1622)');
    expect(text).toContain(formatDateWithYear('2026-07-20T12:00:00Z'));
  });

  it('footer names the WHITE username and rating for a user_color: black fixture', async () => {
    getGame.mockResolvedValue(
      makeGame({ user_color: 'black', white_username: 'alice', white_rating: 1480 }),
    );
    renderReveal();
    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
    expect(screen.getByTestId('train-reveal-footer').textContent).toContain('vs alice (1480)');
  });

  it('the footer analyze link opens the source game at the puzzle ply and fires onAnalyzeClick', async () => {
    getGame.mockResolvedValue(makeGame({ user_color: 'white' }));
    const onAnalyzeClick = vi.fn();
    renderReveal({ puzzle: makePuzzle({ game_id: 100, ply: 20 }), onAnalyzeClick });

    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
    const link = screen.getByTestId('train-reveal-footer-analyze');
    // ply - 1: the board wants the position BEFORE the move the user had to
    // find. Asserted against buildGameAnalysisUrl rather than a literal so
    // this cannot drift from the board's own Analyze button.
    expect(link.getAttribute('href')).toBe(buildGameAnalysisUrl(100, 19));

    // The cache-save handler must fire, or a Back from /analysis drops the
    // reveal. A link that navigated correctly but skipped this would look
    // identical in every other assertion.
    fireEvent.click(link);
    expect(onAnalyzeClick).toHaveBeenCalledTimes(1);
  });

  it('the footer analyze link omits the ply for a ply-0 puzzle rather than emitting ply=-1', async () => {
    getGame.mockResolvedValue(makeGame({ user_color: 'white' }));
    renderReveal({ puzzle: makePuzzle({ game_id: 100, ply: 0 }) });

    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
    expect(screen.getByTestId('train-reveal-footer-analyze').getAttribute('href')).toBe(
      buildGameAnalysisUrl(100, null),
    );
  });

  it('the game fetch failing renders train-gamecard-error while the rest of the reveal still renders', async () => {
    getGame.mockRejectedValue(new Error('boom'));
    renderReveal();
    await waitFor(() => expect(screen.getByTestId('train-gamecard-error')).not.toBeNull());
    expect(screen.getByTestId('train-verdict-guess')).not.toBeNull();
  });

  // ─── D-07: herring reveal omits the game info line entirely (Phase 192) ──

  it('renders no game footer for a herring reveal', async () => {
    getGame.mockResolvedValue(makeGame());
    const { client } = renderReveal({
      verdict: makeVerdict({
        puzzle_type: 'herring',
        source: 'red_herring',
        item_status: null,
        due_date: null,
        streak: null,
      }),
    });
    // Waits for the game query to actually SETTLE (not just be dispatched) —
    // otherwise this test would pass trivially before the success branch
    // ever had a chance to render the footer.
    await waitFor(() =>
      expect(client.getQueryState(['library-game', 100])?.status).toBe('success'),
    );
    expect(screen.queryByTestId('train-reveal-footer')).toBeNull();
  });

  it('renders no game-load error for a herring reveal', async () => {
    getGame.mockRejectedValue(new Error('boom'));
    const { client } = renderReveal({
      verdict: makeVerdict({
        puzzle_type: 'herring',
        source: 'red_herring',
        item_status: null,
        due_date: null,
        streak: null,
      }),
    });
    // T-192-12: a herring's game query can still reject (game_id non-null,
    // per D-08 — the in-game move survives independently of the game row's
    // existence) — the error branch must be gated on the SAME puzzle_type
    // condition as the success branch, not just the success branch.
    await waitFor(() =>
      expect(client.getQueryState(['library-game', 100])?.status).toBe('error'),
    );
    expect(screen.queryByTestId('train-gamecard-error')).toBeNull();
  });

  it('still renders the game footer for an SR reveal (positive control)', async () => {
    getGame.mockResolvedValue(makeGame());
    renderReveal({ verdict: makeVerdict({ puzzle_type: 'sharp' }) });
    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
  });

  // ─── Phase 206 D-19: source === 'sr_item' replaces puzzle_type !== 'herring' ──

  it('a sharp_filler verdict (puzzle_type "sharp", same as a real SR puzzle) suppresses the mastery banner, the game footer, and the own-game guess prose all together', async () => {
    getGame.mockResolvedValue(makeGame());
    const { client } = renderReveal({
      guess: 'several',
      verdict: makeVerdict({
        puzzle_type: 'sharp',
        source: 'sharp_filler',
        correct_guess: true,
        item_status: null,
        due_date: null,
        streak: null,
      }),
    });
    // No mastery banner (item_status is null anyway, but the source gate
    // must ALSO suppress it independently of item_status).
    expect(screen.queryByTestId('train-flaw-fixed-banner')).toBeNull();
    // The non-own-game guess prose renders — same sentence a herring gets —
    // never the SR "not the one you played in the game" variant.
    expect(screen.getByTestId('train-verdict-guess-prose').textContent).toBe(
      'Indeed, several moves are fine here.',
    );
    // No game footer, and no game-load error either — a sharp filler has no
    // game at all (game_id is structurally null server-side).
    await waitFor(() =>
      expect(client.getQueryState(['library-game', 100])?.status).toBe('success'),
    );
    expect(screen.queryByTestId('train-reveal-footer')).toBeNull();
  });

  it('an sr_item verdict with puzzle_type "sharp" (the exact literal a sharp_filler also carries) still renders all three D-19 sites — proves the predicate reads source, not puzzle_type', async () => {
    getGame.mockResolvedValue(makeGame());
    renderReveal({
      guess: 'several',
      verdict: makeVerdict({
        puzzle_type: 'sharp',
        source: 'sr_item',
        correct_guess: true,
        item_status: 'mastered',
        due_date: null,
      }),
    });
    expect(screen.getByTestId('train-flaw-fixed-banner')).not.toBeNull();
    expect(screen.getByTestId('train-verdict-guess-prose').textContent).toBe(
      'Several moves are fine here, but not the one you played in the game.',
    );
    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
  });

  // ─── Also fine, inside the guess card (Phase 200 LEGEND-04/D-02/D-03; UAT
  // round 6 folded the standalone row into the guess card) ──────────────────

  it('renders no Also fine list when alsoFineMoves is empty (the default)', () => {
    renderReveal();
    expect(screen.queryByTestId('train-reveal-also-fine')).toBeNull();
  });

  it('renders the Also fine list in the guess card body, listing the SAN of every entry, with no button in the card', () => {
    renderReveal({
      alsoFineMoves: [
        { uci: 'd2d4', quality: 'good' },
        { uci: 'g1f3', quality: 'inaccuracy' },
      ],
    });
    const card = screen.getByTestId('train-verdict-guess');
    const list = within(card).getByTestId('train-reveal-also-fine');
    expect(list.textContent).toContain('d4');
    expect(list.textContent).toContain('Nf3');
    // Phase 237: the card is inert (the Also fine arrows stay on the board,
    // dimmed, whichever chip is focused): no button anywhere in it.
    expect(within(card).queryAllByRole('button')).toHaveLength(0);
  });

  it('the guess card keeps the verdict and its score chip in the header, and only the Also fine list in the body (round 7: the herring sentence is gone)', async () => {
    renderReveal({
      verdict: makeVerdict({
        correct_guess: true,
        correct_move: false,
        puzzle_type: 'herring',
        source: 'red_herring',
        item_status: null,
        due_date: null,
        streak: null,
      }),
      alsoFineMoves: [{ uci: 'd2d4', quality: 'good' }],
    });
    const card = screen.getByTestId('train-verdict-guess');
    expect(card.textContent).toContain('Your call:');
    expect(within(card).queryByTestId('train-verdict-guess-points')).toBeNull();
    await waitFor(() => expect(getGame).toHaveBeenCalled());
    expect(within(card).queryByTestId('train-outcome-copy')).toBeNull();
    expect(within(card).getByTestId('train-reveal-also-fine').textContent).toContain('d4');
  });

  // ─── Phase 233 (D-11/D-12): card engagement reaches the telemetry callbacks ──

  it('TrainReveal refactor: one instance renders verdict null, then a verdict, then null with no hook-order error', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const { rerender, client, props } = renderReveal({ verdict: null, isSolveError: true });
    expect(screen.getByTestId('train-solve-error')).not.toBeNull();

    revealPuzzle.mockResolvedValue(makeReveal({ played_in_game_san: 'Nf3', played_in_game_move_uci: 'g1f3' }));
    const verdictProps: ComponentProps<typeof TrainReveal> = {
      ...props,
      verdict: makeVerdict(),
      isSolveError: false,
      guess: 'critical',
      playedMoveUci: 'd2d4',
      chips: makeChips({ gameMoveUci: 'g1f3', gameMoveLine: { status: 'ready', line: makeEngineLine({ moves: ['g1f3'], evalCp: -20, evalMate: null }) } }),
      activeChip: 'your',
      gradeResult: makeGradeResult({
        bestLine: makeEngineLine({ moves: ['e2e4'], evalCp: 50, evalMate: null }),
        playedLine: makeEngineLine({ moves: ['d2d4'], evalCp: 10, evalMate: null }),
      }),
      gradingEngine: makeGradingEngine({
        startGameMoveSearch: vi
          .fn()
          .mockResolvedValue(makeEngineLine({ moves: ['g1f3'], evalCp: -20, evalMate: null })),
      }),
    };
    const renderTree = (treeProps: ComponentProps<typeof TrainReveal>) => (
      <MemoryRouter>
        <QueryClientProvider client={client}>
          <TooltipProvider>
            <TrainReveal {...treeProps} />
          </TooltipProvider>
        </QueryClientProvider>
      </MemoryRouter>
    );
    rerender(renderTree(verdictProps));
    await waitFor(() => expect(screen.getByTestId('train-chip-game')).not.toBeNull());
    expect(screen.getByTestId('train-chip-your')).not.toBeNull();
    expect(screen.getByTestId('train-chip-best')).not.toBeNull();

    rerender(renderTree({ ...props, verdict: null, isSolveError: true }));
    expect(screen.getByTestId('train-solve-error')).not.toBeNull();

    const hookOrderErrors = consoleError.mock.calls.filter(
      (call) => typeof call[0] === 'string' && /order of Hooks|Rendered (more|fewer) hooks/.test(call[0]),
    );
    expect(hookOrderErrors).toEqual([]);
  });

  // ─── Guess-feedback prose (Quick 260803-iv6, Task 3) ──────────────────────
  // One prose sentence stating what the guess verdict MEANS, in the guess
  // card body above the Also fine line. The six combinations are LOCKED
  // wording — exact string equality, never a substring/regex match.

  describe('guessFeedbackProse', () => {
    it('critical + wrong guess + herring, regardless of the move played', () => {
      expect(guessFeedbackProse('critical', false, false, 'wrong', false, null)).toBe(
        'Several moves are fine here.',
      );
      expect(guessFeedbackProse('critical', false, false, 'good', false, null)).toBe(
        'Several moves are fine here.',
      );
    });

    // Same fix as the correct-`several` soft branch below, one branch over: a
    // bare "Several moves are fine here." read as "nothing happened here" at
    // one of the user's own blunders. Both guesses share the sentence — the
    // position fact is independent of what the user guessed about it.
    it('critical + wrong guess + one of the user own blunders (soft)', () => {
      expect(guessFeedbackProse('critical', false, true, 'wrong', false, null)).toBe(
        'Several moves are fine here, but not the one you played in the game.',
      );
      expect(guessFeedbackProse('critical', false, true, 'good', false, null)).toBe(
        'Several moves are fine here, but not the one you played in the game.',
      );
    });

    // The 2026-08-03 fix: a correct `critical` guess no longer claims the user
    // PLAYED the critical move — only a `good` move earns the praise clause.
    it('critical + correct + a good move', () => {
      expect(guessFeedbackProse('critical', true, true, 'good', false, null)).toBe(
        'Right, and you found it: only one move works here.',
      );
    });

    it('critical + correct + a non-good move never claims the move was found', () => {
      expect(guessFeedbackProse('critical', true, true, 'inaccuracy', false, null)).toBe(
        "Right, only one move works here, but that wasn't it.",
      );
      expect(guessFeedbackProse('critical', true, true, 'wrong', false, null)).toBe(
        "Right, only one move works here, but that wasn't it.",
      );
    });

    it('several + wrong', () => {
      expect(guessFeedbackProse('several', false, true, 'wrong', false, null)).toBe(
        'One move is clearly better than the alternatives.',
      );
    });

    it('several + correct + NOT one of the user own blunders (herring)', () => {
      expect(guessFeedbackProse('several', true, false, 'good', false, null)).toBe(
        'Indeed, several moves are fine here.',
      );
    });

    // The other 2026-08-03 fix: this branch is reachable ONLY on a `soft`
    // puzzle, i.e. one of the user's own blunders — it used to congratulate
    // them ("You handled this fine in your game.") at the exact position where
    // they blundered.
    it('several + correct + one of the user own blunders (soft)', () => {
      expect(guessFeedbackProse('several', true, true, 'good', false, null)).toBe(
        'Several moves are fine here, but not the one you played in the game.',
      );
    });

    // Phase 235 (D-15): a server-confirmed disagreement outranks every "only
    // one move works" branch, for BOTH guesses and whatever else is true.
    it('a confirmed disagreement names the key for both guesses, whatever the other inputs (D-15)', () => {
      const line = "Qh4 is the engine's first choice, but your move holds up too.";
      expect(guessFeedbackProse('critical', false, true, 'good', true, 'Qh4')).toBe(line);
      expect(guessFeedbackProse('critical', true, true, 'good', true, 'Qh4')).toBe(line);
      expect(guessFeedbackProse('several', true, false, 'good', true, 'Qh4')).toBe(line);
      expect(guessFeedbackProse('several', false, false, 'wrong', true, 'Qh4')).toBe(line);
    });

    it('a disagreement without a key SAN falls through to the existing chain (D-15)', () => {
      expect(guessFeedbackProse('critical', true, true, 'good', true, null)).toBe(
        'Right, and you found it: only one move works here.',
      );
      expect(guessFeedbackProse('several', false, true, 'wrong', true, null)).toBe(
        'One move is clearly better than the alternatives.',
      );
    });
  });

  it('a server-confirmed disagreement renders the D-15 line naming the key SAN on the guess card (D-15)', () => {
    renderReveal({
      guess: 'several',
      verdict: makeVerdict({ correct_guess: true, move_quality: 'good', disagreement: true }),
      gradeResult: makeGradeResult({ bestMoveUci: 'd2d4' }),
    });
    const prose = within(screen.getByTestId('train-verdict-guess')).getByTestId('train-verdict-guess-prose');
    expect(prose.textContent).toBe("d4 is the engine's first choice, but your move holds up too.");
  });

  it('a verdict without the disagreement field keeps the old copy even when a key is known (D-15)', () => {
    renderReveal({
      guess: 'critical',
      verdict: makeVerdict({ correct_guess: true, move_quality: 'good' }),
      gradeResult: makeGradeResult({ bestMoveUci: 'd2d4' }),
    });
    const prose = within(screen.getByTestId('train-verdict-guess')).getByTestId('train-verdict-guess-prose');
    expect(prose.textContent).toBe('Right, and you found it: only one move works here.');
  });

  it('renders the exact locked prose sentence in the guess card body, above the Also fine line', () => {
    renderReveal({
      guess: 'critical',
      verdict: makeVerdict({ correct_guess: true, puzzle_type: 'sharp', move_quality: 'good' }),
      alsoFineMoves: [{ uci: 'd2d4', quality: 'good' }],
    });
    const card = screen.getByTestId('train-verdict-guess');
    const prose = within(card).getByTestId('train-verdict-guess-prose');
    expect(prose.textContent).toBe('Right, and you found it: only one move works here.');
    const alsoFine = within(card).getByTestId('train-reveal-also-fine');
    expect(
      prose.compareDocumentPosition(alsoFine) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it('several + correct + herring (not a played game) renders the "Indeed" sentence', () => {
    renderReveal({
      guess: 'several',
      verdict: makeVerdict({
        correct_guess: true,
        puzzle_type: 'herring',
        source: 'red_herring',
        item_status: null,
        due_date: null,
        streak: null,
      }),
    });
    expect(screen.getByTestId('train-verdict-guess-prose').textContent).toBe(
      'Indeed, several moves are fine here.',
    );
  });

  it('several + correct + soft (one of the user own blunders) renders the "not the one you played" sentence', () => {
    renderReveal({
      guess: 'several',
      verdict: makeVerdict({ correct_guess: true, puzzle_type: 'soft' }),
    });
    expect(screen.getByTestId('train-verdict-guess-prose').textContent).toBe(
      'Several moves are fine here, but not the one you played in the game.',
    );
  });

  // The reported bug, end to end: guessed "One critical move" correctly but
  // played a losing move. The prose used to read "You identified the one
  // critical move.", contradicting the zero-point Your-move chip above it.
  it('a correct critical guess with a wrong move never claims the move was identified', () => {
    renderReveal({
      guess: 'critical',
      verdict: makeVerdict({
        correct_guess: true,
        correct_move: false,
        move_quality: 'wrong',
        puzzle_type: 'sharp',
      }),
    });
    const prose = screen.getByTestId('train-verdict-guess-prose');
    expect(prose.textContent).toBe("Right, only one move works here, but that wasn't it.");
  });

  it('several + wrong renders the "one move is clearly better" sentence', () => {
    renderReveal({
      guess: 'several',
      verdict: makeVerdict({ correct_guess: false, puzzle_type: 'sharp' }),
    });
    expect(screen.getByTestId('train-verdict-guess-prose').textContent).toBe(
      'One move is clearly better than the alternatives.',
    );
  });

  // Both fixtures below are server-consistent: a missed `critical` guess means
  // the puzzle was NOT sharp (`_compute_correct_guess`), so only herring/soft
  // can reach this prose — the pair that `fromOwnBlunder` splits.
  it('critical + wrong + herring renders the bare "several moves are fine" sentence', () => {
    renderReveal({
      guess: 'critical',
      verdict: makeVerdict({
        correct_guess: false,
        puzzle_type: 'herring',
        source: 'red_herring',
        item_status: null,
        due_date: null,
        streak: null,
      }),
    });
    expect(screen.getByTestId('train-verdict-guess-prose').textContent).toBe(
      'Several moves are fine here.',
    );
  });

  it('critical + wrong + soft renders the "not the one you played" sentence', () => {
    renderReveal({
      guess: 'critical',
      verdict: makeVerdict({ correct_guess: false, puzzle_type: 'soft' }),
    });
    expect(screen.getByTestId('train-verdict-guess-prose').textContent).toBe(
      'Several moves are fine here, but not the one you played in the game.',
    );
  });

  it('renders no prose element when guess is null', () => {
    renderReveal({ guess: null });
    expect(screen.queryByTestId('train-verdict-guess-prose')).toBeNull();
  });

  it('the guess card body still mounts (for the prose alone) even with no Also fine alternatives', () => {
    renderReveal({
      guess: 'critical',
      verdict: makeVerdict({ correct_guess: true, puzzle_type: 'sharp' }),
      alsoFineMoves: [],
    });
    expect(screen.getByTestId('train-verdict-guess-prose').textContent).toBe(
      'Right, and you found it: only one move works here.',
    );
    expect(screen.queryByTestId('train-reveal-also-fine')).toBeNull();
  });

  // Quick 260803-iv6 / Phase 237: the guess card is inert — it never carries a
  // cursor-pointer affordance, with or without prose.
  it('a prose-only guess card (no Also fine) carries no cursor-pointer class', () => {
    renderReveal({
      guess: 'critical',
      verdict: makeVerdict({ correct_guess: true, puzzle_type: 'sharp' }),
      alsoFineMoves: [],
    });
    const card = screen.getByTestId('train-verdict-guess');
    expect(card.className).not.toContain('cursor-pointer');
  });

  // ─── Plan 06: free play is gone, so nothing on the reveal is ever swapped out ──

  it('the guess card, the Also fine list, the chips and the move list slot render together (a sideline forks in place, nothing swaps)', async () => {
    renderReveal({
      guess: 'critical',
      chips: makeChips(),
      activeChip: 'your',
      treeList: <div data-testid="train-move-tree-slot" />,
      alsoFineMoves: [{ uci: 'd2d4', quality: 'good' }],
    });
    expect(screen.getByTestId('train-verdict-guess')).not.toBeNull();
    expect(screen.getByTestId('train-reveal-also-fine')).not.toBeNull();
    expect(screen.getByTestId('train-line-chips')).not.toBeNull();
    expect(screen.getByTestId('train-move-tree-slot')).not.toBeNull();
    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
  });
});

// Phase 236 (D-14/D-15): the instant path opens the reveal on the server verdict
// before the phone grade exists. `gradeResult` is null and `instantGrade`
// carries the key (and, once the anchor settled, the key line).
describe('instant-path game-move search (Phase 236)', () => {
  beforeEach(() => {
    matchMediaMatches = true;
    revealPuzzle.mockReset();
    getGame.mockReset();
    revealPuzzle.mockResolvedValue(makeReveal());
    getGame.mockResolvedValue(makeGame());
  });

  afterEach(() => {
    cleanup();
  });

  const KEY_LINE: TrainEngineLine = { moves: ['d2d4', 'd7d5'], evalCp: 30, evalMate: null };
  const soft = { puzzle_type: 'soft' as const, move_quality: 'good' as const };

  it('the grade landing with the same best UCI does not re-dispatch the game-move search (RESEARCH Pitfall 5)', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ played_in_game_move_uci: 'g1f3', played_in_game_san: 'Nf3' }),
    );
    const startGameMoveSearch = vi
      .fn<(puzzleFen: string, gameMoveUci: string) => Promise<TrainEngineLine>>()
      .mockResolvedValue({ moves: ['g1f3'], evalCp: 10, evalMate: null });
    const gradingEngine = makeGradingEngine({ startGameMoveSearch });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const base: ComponentProps<typeof TrainReveal> = {
      puzzle: makePuzzle(),
      sessionId: 1,
      verdict: makeVerdict(soft),
      isSolveError: false,
      onRetrySolve: vi.fn(),
      onNext: vi.fn(),
      gradingEngine,
      guess: 'critical',
      playedMoveUci: 'e2e4',
      gradeResult: null,
      instantGrade: { status: 'pending', keyUci: 'd2d4', keyLine: KEY_LINE },
      chips: [],
      activeChip: null,
      onChipSelect: vi.fn(),
      treeList: null,
      verdictBot: PERSONA_REGISTRY['wall-1800'],
      verdictOpening: verdictCopy(2, true, 'good', false, () => 0),
      isBest: false,
      isWarmup: false,
      audience: { hasGames: true, isGuest: false },
    };
    const tree = (props: ComponentProps<typeof TrainReveal>) => (
      <MemoryRouter>
        <QueryClientProvider client={client}>
          <TooltipProvider>
            <TrainReveal {...props} />
          </TooltipProvider>
        </QueryClientProvider>
      </MemoryRouter>
    );
    const { rerender } = render(tree(base));
    await waitFor(() => expect(startGameMoveSearch).toHaveBeenCalledTimes(1));
    expect(startGameMoveSearch).toHaveBeenCalledWith(START_FEN, 'g1f3');

    rerender(
      tree({
        ...base,
        instantGrade: null,
        gradeResult: makeGradeResult({
          bestMoveUci: 'd2d4',
          bestLine: KEY_LINE,
          playedLine: makeEngineLine({ moves: ['e2e4', 'e7e5'] }),
        }),
      }),
    );
    // Let the re-render's effects and the search promise settle before asserting
    // that the grade landing did not re-dispatch the game-move search.
    await waitFor(() => expect(getGame).toHaveBeenCalled());
    await act(async () => {
      await Promise.resolve();
    });
    expect(startGameMoveSearch).toHaveBeenCalledTimes(1);
  });
});

// Phase 229 (D-12): feature events reach window.umami.track through the real
// analytics module. The exploration exit is gone (plan 06) and the first
// sideline fork is tracked by the board owner (TrainSolveScreen); the post-miss
// Retry re-submits the solve to the backend (useTrainSession
// retrySolve), so it is DB-known and stays un-evented.
describe('TrainReveal feature events (Phase 229)', () => {
  const track = vi.fn();

  beforeEach(() => {
    matchMediaMatches = true;
    revealPuzzle.mockReset();
    getGame.mockReset();
    revealPuzzle.mockResolvedValue(makeReveal());
    getGame.mockResolvedValue(makeGame());
    track.mockClear();
    window.umami = { track, identify: vi.fn() };
    window.history.pushState({}, '', '/train');
  });

  afterEach(() => {
    cleanup();
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  it('the post-miss Retry calls onRetrySolve and sends nothing (it writes to the backend)', () => {
    const onRetrySolve = vi.fn();
    renderReveal({ verdict: null, isSolveError: true, onRetrySolve });
    fireEvent.click(screen.getByTestId('btn-train-solve-retry'));
    expect(onRetrySolve).toHaveBeenCalledTimes(1);
    expect(track).not.toHaveBeenCalled();
  });
});
