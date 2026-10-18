// @vitest-environment jsdom
/**
 * TrainReveal.test.tsx — the reveal panel's presentational coverage: the guess
 * verdict card and its prose, the mastery banner, the copy, the game
 * footer, the game-move search state reporting, and the chips row
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
import { SETTINGS_STORAGE_KEYS } from '@/lib/engineSettings';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import { verdictCopy } from '@/lib/trainBotCopy';
import { buildChipGroups } from '@/lib/trainRevealLines';
import type { BuildChipGroupsInput, ChipGroup } from '@/lib/trainRevealLines';
import { TOUR_SPOTLIGHT_CLASS } from '@/lib/theme';
import type { GradeResult, TrainEngineLine, TrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import type { PuzzleRevealResponse, SolveResponse, TrainPuzzle } from '@/types/train';
import type { EvalPoint, GameFlawCard } from '@/types/library';

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

// The line steppers play move sounds — mocked so jsdom
// never touches real Audio machinery.
vi.mock('@/lib/sounds', () => ({
  playSound: vi.fn(),
}));

// ─── matchMedia stub (useIsDesktop) ─────────────────────────────
// Controllable per test (Bots.test.tsx L221 jsdom-shim precedent, with a
// settable `matches` instead of a fixed `false`) so both the desktop-hover
// and mobile-tap paths are exercisable in the same file.
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
    // Defaults to 'sr_item' so pre-existing callers that
    // only override `puzzle_type` keep exercising the "own game" branch at
    // all three own-game sites exactly as before this field existed.
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

/** Stub `TrainGradingEngine` — only `startGameMoveSearch` matters
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

/** Minimal `EvalPoint` fixture: every nullable field null unless overridden. */
function makeEvalPoint(overrides: Partial<EvalPoint> = {}): EvalPoint {
  return {
    ply: 20,
    es: null,
    eval_cp: null,
    eval_mate: null,
    clock_seconds: null,
    move_seconds: null,
    best_move: null,
    best_move_tier: null,
    maia_prob: null,
    ...overrides,
  };
}

/** Minimal `GameFlawCard` fixture (the footer only reads
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
 * about chips). Defaults to a played d4 against the best e4. */
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
    playedMoveUci: null,
    gradeResult: null,
    chips: [],
    activeChip: null,
    onChipSelect: vi.fn(),
    treeList: null,
    verdictBot: PERSONA_REGISTRY['wall-1800'],
    verdictOpening: verdictCopy(2, () => 0),
    isBest: false,
    isWarmup: false,
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

  // ─── The verdict surface (strip on phones, bubble on desktop) ──

  it('desktop: the verdict bubble leads the reveal column with the full details visible and no strip', () => {
    renderReveal({ isBest: true, alsoFineMoves: [{ uci: 'd2d4', quality: 'good' }] });
    const reveal = screen.getByTestId('train-reveal');
    const bubble = within(reveal).getByTestId('train-verdict-card');
    expect(within(bubble).getByTestId('train-verdict-card-avatar')).not.toBeNull();
    expect(within(bubble).getByTestId('train-bot-verdict-line').textContent).toContain('found it');
    expect(within(bubble).getByTestId('train-verdict-extras')).not.toBeNull();
    expect(screen.queryByTestId('train-verdict-strip')).toBeNull();
    // The bubble is the FIRST thing in the column.
    expect(reveal.firstElementChild).toBe(bubble);
  });

  it('phone: the strip replaces the card, collapsed, and its tap opens the full verdict', () => {
    matchMediaMatches = false;
    renderReveal({ isBest: true });
    const strip = screen.getByTestId('train-verdict-strip');
    expect(strip.getAttribute('aria-expanded')).toBe('false');
    expect(screen.getByTestId('train-verdict-strip-line').textContent).toBe('Called it, found it');
    expect(screen.queryByTestId('train-verdict-card')).toBeNull();
    expect(screen.queryByTestId('train-bot-verdict-line')).toBeNull();
    fireEvent.click(strip);
    expect(screen.getByTestId('train-bot-verdict-line')).not.toBeNull();
  });

  it('phone: on a several-move puzzle isBest selects "best move" vs "good move"', () => {
    matchMediaMatches = false;
    const verdict = makeVerdict({ puzzle_type: 'soft' });
    const { unmount } = renderReveal({ verdict, isBest: true });
    expect(screen.getByTestId('train-verdict-strip-line').textContent).toBe('Called it, best move');
    unmount();
    renderReveal({ verdict, isBest: false });
    expect(screen.getByTestId('train-verdict-strip-line').textContent).toBe('Called it, good move');
  });

  // ─── Verdict rows ─────────────────────────────────────────

  // The ✓/✗ marks are score chips stating the
  // points actually earned (guess: 1 or 0).
  it('a wrong call reads "Wrong call" with a +0 guess pill', () => {
    renderReveal({ verdict: makeVerdict({ correct_guess: false }) });
    expect(screen.getByTestId('train-bot-verdict-line').textContent).toContain('Wrong call');
    expect(screen.getByTestId('train-bot-pill-guess').textContent).toBe('+0');
  });

  it('a correct call reads "You called it" with a +1 guess pill', () => {
    renderReveal({ verdict: makeVerdict({ correct_guess: true }) });
    expect(screen.getByTestId('train-bot-verdict-line').textContent).toContain('You called it');
    expect(screen.getByTestId('train-bot-pill-guess').textContent).toBe('+1');
  });

  // The chip reads the three-way scoring tier, so an
  // inaccuracy scores +1 — the boolean correct_move could not express that.
  // The Your-move box leads the whole panel, above the
  // guess card, on both viewports (one component serves both).
  // ─── Outcome copy — fully retired ─────────────────
  // Neither the miss sentence nor the herring "You handled this well in the
  // game" line exists any more. The guess card's
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

  // ─── Flaw fixed banner (replaces the plain "Mastered — retired."
  // comeback hint) ─────────────────────────

  it('item_status "mastered" renders the flaw-fixed banner', () => {
    renderReveal({ verdict: makeVerdict({ item_status: 'mastered', due_date: null }) });
    expect(screen.getByTestId('train-flaw-fixed-banner')).not.toBeNull();
  });

  // The banner is the FIRST card in the panel —
  // above both the Your-move box and the guess card — on a mastered,
  // non-herring verdict. Asserted via `compareDocumentPosition`, not index
  // into a hand-built list, so a reordering elsewhere in the panel can't
  // accidentally make this pass for the wrong reason.
  it('the flaw-fixed banner follows the verdict surface and sits above the chips row', async () => {
    renderReveal({
      playedMoveUci: 'd2d4',
      chips: makeChips(),
      activeChip: 'your',
      verdict: makeVerdict({ item_status: 'mastered', due_date: null }),
    });
    const banner = screen.getByTestId('train-flaw-fixed-banner');
    const yourBox = await waitFor(() => screen.getByTestId('train-line-chips'));
    // The verdict bubble (desktop) leads the
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

  // ─── Chips row + move list slot ─────────────────────

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
    renderReveal({ playedMoveUci: 'd2d4', chips: makeChips(), activeChip: 'your' });
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

  describe('reveal tour spotlights and bubble slot', () => {
    const TREE_SLOT = <div data-testid="train-move-tree-slot" />;
    const renderWithTarget = async (
      tourTarget: ComponentProps<typeof TrainReveal>['tourTarget'],
    ): Promise<void> => {
      renderReveal({
        playedMoveUci: 'd2d4',
        chips: makeChips(),
        activeChip: 'your',
        treeList: TREE_SLOT,
        tourTarget,
      });
      await waitFor(() => screen.getByTestId('train-line-chips'));
    };
    const spotlit = (element: Element | null): boolean =>
      element !== null && element.classList.contains(TOUR_SPOTLIGHT_CLASS);
    const chipsSpotlit = (): boolean =>
      spotlit(screen.getByTestId('train-line-chips').closest('[data-tour-target="chips"]'));
    const treeSpotlit = (): boolean => spotlit(screen.getByTestId('train-tree-tour-ring'));
    const linesSpotlit = (): boolean => spotlit(screen.getByTestId('train-lines-tour-target'));

    // The chips row is spotlit as a row, and the active chip keeps
    // its own selection ring.
    it('chips spotlights the chips row only; the active chip keeps its own ring', async () => {
      await renderWithTarget('chips');
      expect(chipsSpotlit()).toBe(true);
      expect(treeSpotlit()).toBe(false);
      expect(linesSpotlit()).toBe(false);
      expect(screen.getByTestId('train-chip-your').className).toContain('ring-2');
    });

    it('tree spotlights the move list only', async () => {
      await renderWithTarget('tree');
      expect(chipsSpotlit()).toBe(false);
      expect(treeSpotlit()).toBe(true);
      expect(linesSpotlit()).toBe(false);
    });

    it('lines spotlights the one wrapper around the chips row and the list, not the parts', async () => {
      await renderWithTarget('lines');
      expect(linesSpotlit()).toBe(true);
      expect(chipsSpotlit()).toBe(false);
      expect(treeSpotlit()).toBe(false);
      const wrapper = screen.getByTestId('train-lines-tour-target');
      expect(wrapper.contains(screen.getByTestId('train-line-chips'))).toBe(true);
      expect(wrapper.contains(screen.getByTestId('train-move-tree-slot'))).toBe(true);
    });

    it.each(['verdict', 'board', 'bar'] as const)('%s spotlights neither the chips row nor the list', async (target) => {
      await renderWithTarget(target);
      expect(chipsSpotlit()).toBe(false);
      expect(treeSpotlit()).toBe(false);
      expect(linesSpotlit()).toBe(false);
    });

    it('no target (null) spotlights nothing', async () => {
      await renderWithTarget(null);
      expect(chipsSpotlit()).toBe(false);
      expect(treeSpotlit()).toBe(false);
      expect(linesSpotlit()).toBe(false);
    });

    it('the chips row and the list sit inside their tour-target wrappers', async () => {
      await renderWithTarget(null);
      const chips = screen.getByTestId('train-line-chips');
      expect(chips.closest('[data-tour-target="chips"]')).not.toBeNull();
      expect(screen.getByTestId('train-move-tree-slot').closest('[data-tour-target="tree"]')).not.toBeNull();
    });

    it('on desktop the verdict target spotlights the verdict card', () => {
      renderReveal({ tourTarget: 'verdict' });
      expect(spotlit(screen.getByTestId('train-verdict-card'))).toBe(true);
    });

    it('on a phone the verdict target spotlights the strip', () => {
      matchMediaMatches = false;
      renderReveal({ tourTarget: 'verdict' });
      expect(spotlit(screen.getByTestId('train-verdict-strip-root'))).toBe(true);
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
      playedMoveUci: 'd2d4',
      gradeResult,
      gradingEngine: makeGradingEngine({ startGameMoveSearch }),
      onGameMoveUciChange,
    });
    await waitFor(() => expect(onGameMoveUciChange).toHaveBeenCalledWith('d2d4'));
    expect(startGameMoveSearch).not.toHaveBeenCalled();
  });

  it('onGameMoveUciChange reports the resolved game-move UCI, and null on unmount', async () => {
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

  it('onGameMoveLineStateChange reports loading, then the searched line, and idle on unmount', async () => {
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

  it('a game-move search that never settles stays in the loading state, and the verdict rows still render', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ played_in_game_san: 'e4', played_in_game_move_uci: 'e2e4' }),
    );
    const startGameMoveSearch = vi.fn().mockReturnValue(new Promise(() => {})); // never settles
    const onGameMoveLineStateChange = vi.fn();
    renderReveal({ gradingEngine: makeGradingEngine({ startGameMoveSearch }), onGameMoveLineStateChange });
    await waitFor(() => expect(onGameMoveLineStateChange).toHaveBeenCalledWith({ status: 'loading' }));
    expect(onGameMoveLineStateChange).not.toHaveBeenCalledWith(expect.objectContaining({ status: 'ready' }));
    expect(onGameMoveLineStateChange).not.toHaveBeenCalledWith({ status: 'error' });
    expect(screen.getByTestId('train-bot-verdict-line')).not.toBeNull();
  });

  it('a rejecting game-move search reports the error state, and the other reveal blocks still render', async () => {
    revealPuzzle.mockResolvedValue(
      makeReveal({ played_in_game_san: 'e4', played_in_game_move_uci: 'e2e4' }),
    );
    const startGameMoveSearch = vi.fn().mockRejectedValue(new Error('search failed'));
    // bestLine deliberately distinct from BOTH the played move and the game
    // move ('e2e4') — otherwise the coincidence-merge guard would skip the
    // reveal-time search this test exists to exercise.
    // bestMoveUci must agree with bestLine: the Best chip reads
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
    expect(screen.getByTestId('train-bot-verdict-line')).not.toBeNull();
    expect(screen.getByTestId('train-chip-your')).not.toBeNull();
    expect(screen.getByTestId('train-chip-game').getAttribute('data-line-status')).toBe('failed');
  });

  // ─── Tactic opt-in — removed ──────────────

  it('a tactic-tagged reveal renders NO tactic opt-in trigger', async () => {
    revealPuzzle.mockResolvedValue(makeReveal({ has_tactic_lines: true }));
    renderReveal();
    await waitFor(() => expect(getGame).toHaveBeenCalled());
    expect(screen.queryByTestId('btn-train-tactic-step')).toBeNull();
  });

  // ─── Sharp filler motif line ────────────────────────────

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
    renderReveal();
    await waitFor(() => expect(getGame).toHaveBeenCalled());
    expect(screen.getByTestId('train-bot-fact')).not.toBeNull();
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

  // ─── Opponent-and-date footer ─────────────────────

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

  it('the game fetch failing renders train-gamecard-error while the rest of the reveal still renders', async () => {
    getGame.mockRejectedValue(new Error('boom'));
    renderReveal();
    await waitFor(() => expect(screen.getByTestId('train-gamecard-error')).not.toBeNull());
    expect(screen.getByTestId('train-bot-verdict-line')).not.toBeNull();
  });

  it('clock line reads "Played after 13s, with 3:56 left." as its own element under the footer', async () => {
    getGame.mockResolvedValue(
      makeGame({
        analysis_state: 'analyzed',
        eval_series: [
          makeEvalPoint({ ply: 19, clock_seconds: 250, move_seconds: 4 }),
          makeEvalPoint({ ply: 20, clock_seconds: 236.9, move_seconds: 13.0 }),
        ],
      }),
    );
    renderReveal();
    await waitFor(() => expect(screen.getByTestId('train-reveal-clock-line')).not.toBeNull());
    expect(screen.getByTestId('train-reveal-clock-line').textContent).toBe(
      'Played after 13s, with 3:56 left.',
    );
    const footerText = screen.getByTestId('train-reveal-footer').textContent ?? '';
    expect(footerText).toContain('vs bob');
    expect(footerText).not.toContain('Played');
  });

  it('clock line is absent when the game has no eval series', async () => {
    getGame.mockResolvedValue(makeGame());
    renderReveal();
    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
    expect(screen.queryByTestId('train-reveal-clock-line')).toBeNull();
  });

  it('clock line is absent when the flaw-ply point has no clock data', async () => {
    getGame.mockResolvedValue(
      makeGame({ analysis_state: 'analyzed', eval_series: [makeEvalPoint({ ply: 20 })] }),
    );
    renderReveal();
    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
    expect(screen.queryByTestId('train-reveal-clock-line')).toBeNull();
  });

  it('clock line keys on puzzle.ply: a point at another ply is ignored', async () => {
    getGame.mockResolvedValue(
      makeGame({
        analysis_state: 'analyzed',
        eval_series: [makeEvalPoint({ ply: 21, clock_seconds: 236, move_seconds: 13 })],
      }),
    );
    renderReveal();
    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
    expect(screen.queryByTestId('train-reveal-clock-line')).toBeNull();
  });

  it('clock line falls back to "Played with 3:56 left." when think time is unknown', async () => {
    getGame.mockResolvedValue(
      makeGame({
        analysis_state: 'analyzed',
        eval_series: [makeEvalPoint({ ply: 20, clock_seconds: 236, move_seconds: null })],
      }),
    );
    renderReveal();
    await waitFor(() => expect(screen.getByTestId('train-reveal-clock-line')).not.toBeNull());
    expect(screen.getByTestId('train-reveal-clock-line').textContent).toBe(
      'Played with 3:56 left.',
    );
  });

  it('clock line is absent for a herring reveal even with clock data on the flaw ply', async () => {
    getGame.mockResolvedValue(
      makeGame({
        analysis_state: 'analyzed',
        eval_series: [makeEvalPoint({ ply: 20, clock_seconds: 236, move_seconds: 13 })],
      }),
    );
    const { client } = renderReveal({
      verdict: makeVerdict({
        puzzle_type: 'herring',
        source: 'red_herring',
        item_status: null,
        due_date: null,
        streak: null,
      }),
    });
    await waitFor(() =>
      expect(client.getQueryState(['library-game', 100])?.status).toBe('success'),
    );
    expect(screen.queryByTestId('train-reveal-clock-line')).toBeNull();
  });

  // ─── Herring reveal omits the game info line entirely ──

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
    // A herring's game query can still reject (game_id non-null;
    // the in-game move survives independently of the game row's
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

  // ─── The own-game predicate reads source === 'sr_item', not puzzle_type ──

  it('a sharp_filler verdict (puzzle_type "sharp", same as a real SR puzzle) suppresses the mastery banner, the game footer, and the own-game guess prose all together', async () => {
    getGame.mockResolvedValue(makeGame());
    const { client } = renderReveal({
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
    // A sharp filler is a sharp position: the plain sharp fact, never the
    // SR "just not your game move" variant.
    expect(screen.getByTestId('train-bot-fact').textContent).toBe('Only one move works here.');
    // No game footer, and no game-load error either — a sharp filler has no
    // game at all (game_id is structurally null server-side).
    await waitFor(() =>
      expect(client.getQueryState(['library-game', 100])?.status).toBe('success'),
    );
    expect(screen.queryByTestId('train-reveal-footer')).toBeNull();
  });

  it('an sr_item verdict with puzzle_type "sharp" (the exact literal a sharp_filler also carries) still renders all three own-game sites — proves the predicate reads source, not puzzle_type', async () => {
    getGame.mockResolvedValue(makeGame());
    renderReveal({
      verdict: makeVerdict({
        puzzle_type: 'sharp',
        source: 'sr_item',
        correct_guess: true,
        item_status: 'mastered',
        due_date: null,
      }),
    });
    expect(screen.getByTestId('train-flaw-fixed-banner')).not.toBeNull();
    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
  });

  // ─── Also fine, inside the guess card ──────────────────

  it('renders no Also fine list when alsoFineMoves is empty (the default)', () => {
    renderReveal();
    expect(screen.queryByTestId('train-reveal-also-fine')).toBeNull();
  });

  it('renders the Also fine list in the extras line, listing the SAN of every entry, with no button in it', () => {
    renderReveal({
      alsoFineMoves: [
        { uci: 'd2d4', quality: 'good' },
        { uci: 'g1f3', quality: 'inaccuracy' },
      ],
    });
    const card = screen.getByTestId('train-verdict-extras');
    const list = within(card).getByTestId('train-reveal-also-fine');
    expect(list.textContent).toContain('d4');
    expect(list.textContent).toContain('Nf3');
    // The card is inert (the Also fine arrows stay on the board,
    // dimmed, whichever chip is focused): no button anywhere in it.
    expect(within(card).queryAllByRole('button')).toHaveLength(0);
  });

  it('motif and Also fine share one extras line, motif first', async () => {
    revealPuzzle.mockResolvedValue(makeReveal({ motif: 'Fork' }));
    renderReveal({ alsoFineMoves: [{ uci: 'd2d4', quality: 'good' }] });
    await waitFor(() => expect(screen.getByTestId('train-reveal-motif')).not.toBeNull());
    expect(screen.getByTestId('train-verdict-extras').textContent).toBe('Motif: Fork · Also fine, e.g. d4');
  });

  // ─── Card engagement reaches the telemetry callbacks ──

  it('TrainReveal refactor: one instance renders verdict null, then a verdict, then null with no hook-order error', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const { rerender, client, props } = renderReveal({ verdict: null, isSolveError: true });
    expect(screen.getByTestId('train-solve-error')).not.toBeNull();

    revealPuzzle.mockResolvedValue(makeReveal({ played_in_game_san: 'Nf3', played_in_game_move_uci: 'g1f3' }));
    const verdictProps: ComponentProps<typeof TrainReveal> = {
      ...props,
      verdict: makeVerdict(),
      isSolveError: false,
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

  // ─── The verdict sentence ──────────────────────
  // The full copy matrix is unit-tested on `verdictClauseParts`
  // (trainBotCopy.test.ts); these render tests prove the reveal feeds it the
  // right server fields.

  const verdictLine = (): string => screen.getByTestId('train-bot-verdict-line').textContent ?? '';

  it('a sharp puzzle, correct call, key move: one sentence states the fact and both pills', () => {
    renderReveal({ verdict: makeVerdict({ correct_guess: true, puzzle_type: 'sharp', move_quality: 'good' }) });
    expect(screen.getByTestId('train-bot-fact').textContent).toBe('Only one move works here.');
    expect(verdictLine()).toContain('You called it +1 and found it +2.');
  });

  it('a correct call with a wrong move never claims the move was found', () => {
    renderReveal({
      verdict: makeVerdict({ correct_guess: true, correct_move: false, move_quality: 'wrong', puzzle_type: 'sharp' }),
    });
    expect(verdictLine()).toContain('You called it +1, but missed it +0.');
  });

  it('a soft puzzle (one of the user own blunders) names the game move in the fact', () => {
    renderReveal({ verdict: makeVerdict({ correct_guess: false, puzzle_type: 'soft' }) });
    expect(screen.getByTestId('train-bot-fact').textContent).toBe(
      'Several moves work here, just not your game move.',
    );
  });

  it('an sr_item with puzzle_type "sharp" gets the sharp fact (the source gate only splits several-move facts)', () => {
    renderReveal({ verdict: makeVerdict({ correct_guess: false, puzzle_type: 'sharp', source: 'sr_item' }) });
    expect(screen.getByTestId('train-bot-fact').textContent).toBe('Only one move works here.');
    expect(verdictLine()).toContain('Wrong call +0, but you found it +2.');
  });

  it('a herring fact carries no game-move clause', () => {
    renderReveal({
      verdict: makeVerdict({
        correct_guess: true,
        puzzle_type: 'herring',
        source: 'red_herring',
        item_status: null,
        due_date: null,
        streak: null,
      }),
    });
    expect(screen.getByTestId('train-bot-fact').textContent).toBe('Several moves work here.');
  });

  it('a server-confirmed disagreement names the key SAN and credits either call', () => {
    renderReveal({
      verdict: makeVerdict({ correct_guess: true, move_quality: 'good', disagreement: true }),
      gradeResult: makeGradeResult({ bestMoveUci: 'd2d4' }),
    });
    expect(screen.getByTestId('train-bot-fact').textContent).toBe(
      "d4 is the engine's pick, but not the only good move.",
    );
    expect(verdictLine()).toContain('Either call counts +1, and your move holds up +2.');
  });

  it('a verdict without the disagreement field keeps the sharp copy even when a key is known', () => {
    renderReveal({
      verdict: makeVerdict({ correct_guess: true, move_quality: 'good' }),
      gradeResult: makeGradeResult({ bestMoveUci: 'd2d4' }),
    });
    expect(screen.getByTestId('train-bot-fact').textContent).toBe('Only one move works here.');
  });

  it('the return tail sits on its own line after the verdict sentence', () => {
    renderReveal({ sessionDate: '2026-07-20', expiresOn: '2026-07-21' });
    const tail = screen.getByTestId('train-bot-return-tail');
    expect(tail.textContent).toBe('Back in 12 days.');
    expect(screen.getByTestId('train-bot-verdict-line').contains(tail)).toBe(false);
  });

  it('no motif and no Also fine renders no extras line at all', () => {
    renderReveal({ alsoFineMoves: [] });
    expect(screen.queryByTestId('train-verdict-extras')).toBeNull();
  });

  // ─── Free play is gone, so nothing on the reveal is ever swapped out ──

  it('the guess card, the Also fine list, the chips and the move list slot render together (a sideline forks in place, nothing swaps)', async () => {
    renderReveal({
      chips: makeChips(),
      activeChip: 'your',
      treeList: <div data-testid="train-move-tree-slot" />,
      alsoFineMoves: [{ uci: 'd2d4', quality: 'good' }],
    });
    expect(screen.getByTestId('train-bot-verdict-line')).not.toBeNull();
    expect(screen.getByTestId('train-reveal-also-fine')).not.toBeNull();
    expect(screen.getByTestId('train-line-chips')).not.toBeNull();
    expect(screen.getByTestId('train-move-tree-slot')).not.toBeNull();
    await waitFor(() => expect(screen.getByTestId('train-reveal-footer')).not.toBeNull());
  });
});

// The instant path opens the reveal on the server verdict
// before the phone grade exists. `gradeResult` is null and `instantGrade`
// carries the key (and, once the anchor settled, the key line).
describe('instant-path game-move search', () => {
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

  it('the grade landing with the same best UCI does not re-dispatch the game-move search', async () => {
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
      playedMoveUci: 'e2e4',
      gradeResult: null,
      instantGrade: { status: 'pending', keyUci: 'd2d4', keyLine: KEY_LINE },
      chips: [],
      activeChip: null,
      onChipSelect: vi.fn(),
      treeList: null,
      verdictBot: PERSONA_REGISTRY['wall-1800'],
      verdictOpening: verdictCopy(2, () => 0),
      isBest: false,
      isWarmup: false,
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

// Feature events reach window.umami.track through the real
// analytics module. The exploration exit is gone and the first
// sideline fork is tracked by the board owner (TrainSolveScreen); the post-miss
// Retry re-submits the solve to the backend (useTrainSession
// retrySolve), so it is DB-known and stays un-evented.
describe('TrainReveal feature events', () => {
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
