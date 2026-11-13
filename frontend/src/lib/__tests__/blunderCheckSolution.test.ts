import { describe, expect, it } from 'vitest';
import {
  BLUNDER_CHECK_ALT_MOVE_ARROWS,
  buildSolutionChips,
  buildSolutionOverlay,
  solutionCopy,
  solutionLineUcis,
} from '@/lib/blunderCheckSolution';
import type { TrainEngineLine } from '@/hooks/useTrainGradingEngine';
import type { BlunderSolution, FalseAlarmSolution } from '@/types/blunderCheck';

/** 1. e4 e5 played, white to move: d4 is the key, Nf3 the played blunder. */
const FEN = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2';
const KEY = 'd2d4';
const BLUNDER = 'g1f3';
const OTHER_BETTER = 'b1c3';

function solution(overrides: Partial<BlunderSolution> = {}): BlunderSolution {
  return {
    kind: 'blunder',
    outcome: 'caught',
    is_own: true,
    window_case: 'allowed',
    game_id: 1,
    analysis_ply: 2,
    fen: FEN,
    blunder_uci: BLUNDER,
    key_uci: KEY,
    better_move_uci: KEY,
    better_move_tier: 'good',
    server_graded_moves: [],
    game_info: null,
    window_points: 5,
    safe_points: 0,
    blunder_points: 3,
    better_move_points: 2,
    ...overrides,
  };
}

const LINE: TrainEngineLine = { moves: [KEY, 'e5d4'], evalCp: 30, evalMate: null };

describe('solutionLineUcis', () => {
  it('searches the key first, then the better move, then the played blunder, each once', () => {
    expect(solutionLineUcis(solution({ better_move_uci: OTHER_BETTER }))).toEqual([
      KEY,
      OTHER_BETTER,
      BLUNDER,
    ]);
  });

  it('a better move equal to the key is searched once', () => {
    expect(solutionLineUcis(solution())).toEqual([KEY, BLUNDER]);
  });

  it('a missed blunder has no better move to search', () => {
    expect(solutionLineUcis(solution({ outcome: 'missed', better_move_uci: null }))).toEqual([
      KEY,
      BLUNDER,
    ]);
  });
});

describe('buildSolutionChips', () => {
  it('merges the better move into the Best chip when they coincide, and rates it best', () => {
    const chips = buildSolutionChips(solution(), {});

    expect(chips.map((chip) => chip.key)).toEqual(['your', 'game']);
    expect(chips[0]).toMatchObject({
      roles: ['your', 'best'],
      uci: KEY,
      san: 'd4',
      label: 'Move = Best',
      quality: 'best',
    });
    expect(chips[1]).toMatchObject({
      roles: ['game'],
      uci: BLUNDER,
      san: 'Nf3',
      label: 'Game',
      quality: 'blunder',
    });
  });

  it('keeps three chips for a different better move and rates it by its tier', () => {
    const good = buildSolutionChips(
      solution({ better_move_uci: OTHER_BETTER, better_move_tier: 'good' }),
      {},
    );
    expect(good.map((chip) => chip.key)).toEqual(['your', 'best', 'game']);
    expect(good[0]?.quality).toBe('good');
    expect(good[1]?.quality).toBe('best');

    const inaccuracy = buildSolutionChips(
      solution({ better_move_uci: OTHER_BETTER, better_move_tier: 'inaccuracy' }),
      {},
    );
    expect(inaccuracy[0]?.quality).toBe('inaccuracy');

    const wrong = buildSolutionChips(
      solution({ better_move_uci: OTHER_BETTER, better_move_tier: 'wrong' }),
      {},
    );
    expect(wrong[0]?.quality).toBe('mistake');
  });

  it('a missed blunder has Best and Game chips and no Your chip', () => {
    const chips = buildSolutionChips(solution({ outcome: 'missed', better_move_uci: null }), {});
    expect(chips.map((chip) => chip.key)).toEqual(['best', 'game']);
  });

  it('maps each line state to the chip: waiting and loading, ready, failed', () => {
    const chips = buildSolutionChips(solution({ better_move_uci: OTHER_BETTER }), {
      [KEY]: { status: 'ready', line: LINE },
      [OTHER_BETTER]: { status: 'error' },
    });

    const [your, best, game] = chips;
    expect(your).toMatchObject({ pending: 'failed', line: null });
    expect(best).toMatchObject({ pending: null, line: LINE });
    // No state yet for the blunder: its search has not started.
    expect(game).toMatchObject({ pending: 'loading', line: null });
  });
});

describe('buildSolutionOverlay', () => {
  const uciOf = (arrow: { startSquare: string; endSquare: string }): string =>
    `${arrow.startSquare}${arrow.endSquare}`;

  it('badges the best move, the better move by its tier and the played blunder', () => {
    const overlay = buildSolutionOverlay(
      solution({ better_move_uci: OTHER_BETTER, better_move_tier: 'inaccuracy' }),
    );

    expect(new Set(overlay.arrows.map(uciOf))).toEqual(new Set([KEY, OTHER_BETTER, BLUNDER]));
    expect(overlay.markers).toEqual(
      expect.arrayContaining([
        { square: 'd4', best: true },
        { square: 'c3', severity: 'inaccuracy' },
        { square: 'f3', severity: 'blunder' },
      ]),
    );
  });

  it('a better move that is the key is one best arrow, not a second one', () => {
    const overlay = buildSolutionOverlay(solution({ better_move_uci: KEY }));

    expect(overlay.arrows.filter((arrow) => uciOf(arrow) === KEY)).toHaveLength(1);
    expect(overlay.markers).toContainEqual({ square: 'd4', best: true });
  });

  it('draws only the server good-tier moves as also good, never the key or the blunder', () => {
    const overlay = buildSolutionOverlay(
      solution({
        better_move_uci: null,
        better_move_tier: null,
        server_graded_moves: [
          { uci: KEY, tier: 'good' },
          { uci: OTHER_BETTER, tier: 'good' },
          { uci: 'f1c4', tier: 'inaccuracy' },
          { uci: 'd1h5', tier: 'wrong' },
          { uci: BLUNDER, tier: 'good' },
        ],
      }),
    );

    expect(overlay.alsoFineMoves.map((move) => move.uci)).toEqual([OTHER_BETTER]);
    expect(overlay.markers).toContainEqual({ square: 'c3', good: true });
    expect(overlay.arrows.map(uciOf)).not.toContain('f1c4');
    expect(overlay.arrows.map(uciOf)).not.toContain('d1h5');
  });

  it('caps the also-good arrows', () => {
    const many = ['b1c3', 'f1c4', 'd2d3', 'c2c3', 'a2a3'];
    const overlay = buildSolutionOverlay(
      solution({
        better_move_uci: null,
        better_move_tier: null,
        server_graded_moves: many.map((uci) => ({ uci, tier: 'good' as const })),
      }),
    );

    expect(overlay.alsoFineMoves.map((move) => move.uci)).toEqual(
      many.slice(0, BLUNDER_CHECK_ALT_MOVE_ARROWS),
    );
  });
});

describe('false alarm', () => {
  function falseAlarm(overrides: Partial<FalseAlarmSolution> = {}): FalseAlarmSolution {
    return {
      kind: 'false_alarm',
      outcome: 'false_alarm',
      is_own: true,
      game_id: 1,
      analysis_ply: 2,
      flagged_uci: BLUNDER,
      fen: FEN,
      key_uci: KEY,
      game_info: null,
      window_points: 0,
      ...overrides,
    };
  }

  it('shows Best and the flagged move as a good Game chip', () => {
    const chips = buildSolutionChips(falseAlarm(), {});

    expect(solutionLineUcis(falseAlarm())).toEqual([KEY, BLUNDER]);
    expect(chips.map((chip) => [chip.label, chip.uci, chip.quality])).toEqual([
      ['Best', KEY, 'best'],
      ['Game', BLUNDER, 'good'],
    ]);
  });

  it('merges the chips when the flagged move was the best move', () => {
    const chips = buildSolutionChips(falseAlarm({ key_uci: BLUNDER }), {});

    expect(chips.map((chip) => [chip.label, chip.quality])).toEqual([['Best = Game', 'best']]);
  });

  it('shows only the Game chip when no best move is stored', () => {
    const solution = falseAlarm({ key_uci: null });

    expect(solutionLineUcis(solution)).toEqual([BLUNDER]);
    expect(buildSolutionChips(solution, {}).map((chip) => chip.label)).toEqual(['Game']);
    expect(buildSolutionOverlay(solution).arrows).toHaveLength(1);
  });
});

describe('solutionCopy', () => {
  /** The sentence as it reads, each point badge as "+N". */
  function sentence(source: Parameters<typeof solutionCopy>[0]): string {
    return solutionCopy(source)
      .parts.map((part) => (typeof part === 'string' ? part : `+${part.points}`))
      .join('');
  }

  it('names a weak better move by its own quality, apart from the game blunder', () => {
    // Phase 249 UAT: "Nf3 was a blunder" alone read as a verdict on the better move.
    const copy = sentence(
      solution({
        better_move_uci: OTHER_BETTER,
        better_move_tier: 'wrong',
        better_move_points: 0,
        window_points: 3,
      }),
    );
    expect(copy).toBe('Nf3 was a blunder. You called it +3 and played a mistake, Nc3 +0. Best was d4.');
  });

  it('does not repeat the best move when the user found it, and adds the earlier calls', () => {
    const copy = sentence(solution({ safe_points: 2, window_points: 7 }));
    expect(copy).toBe(
      'Nf3 was a blunder. You called it +3 and found the best move, d4 +2. Your earlier calls earned +2.',
    );
  });

  it('a missed blunder scores nothing', () => {
    const copy = sentence(
      solution({
        outcome: 'missed',
        better_move_uci: null,
        better_move_tier: null,
        better_move_points: null,
        blunder_points: 0,
        window_points: 0,
      }),
    );
    expect(copy).toBe('Nf3 was a blunder. You missed it +0. Best was d4.');
  });
});
