import { describe, expect, it } from 'vitest';
import {
  BLUNDER_CHECK_ALT_MOVE_ARROWS,
  buildSolutionChips,
  buildSolutionOverlay,
  solutionCopy,
  solutionLineUcis,
} from '@/lib/blunderCheckSolution';
import { gameBlunderSentence } from '@/lib/gameBlunderSentence';
import { sanFromUci } from '@/lib/trainRevealLines';
import type { TrainEngineLine } from '@/hooks/useTrainGradingEngine';
import type {
  BlunderFeedback,
  BlunderSolution,
  FalseAlarmSolution,
  HerringSolution,
} from '@/types/blunderCheck';

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
    feedback: null,
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

describe('facepalm blunder badge (Phase 261 UAT)', () => {
  const scored = (score: number): BlunderSolution =>
    solution({ feedback: { score, type_line: null, hard_to_catch: false } });
  const gameMarker = (s: BlunderSolution) =>
    buildSolutionOverlay(s).markers.find((marker) => marker.square === 'f3');
  const gameChip = (s: BlunderSolution) =>
    buildSolutionChips(s, {}).find((chip) => chip.key === 'game');

  it('marks the game move "???" on the board and the Game chip from 70% up', () => {
    expect(gameMarker(scored(0.7))).toEqual({ square: 'f3', severity: 'blunder', facepalm: true });
    expect(gameChip(scored(0.7))).toMatchObject({ quality: 'blunder', facepalm: true });
  });

  it('keeps the plain "??" below 70% and for a window with no feedback', () => {
    expect(gameMarker(scored(0.699))).toEqual({ square: 'f3', severity: 'blunder' });
    expect(gameChip(scored(0.699))?.facepalm).toBe(false);
    expect(gameMarker(solution({ feedback: null }))).toEqual({ square: 'f3', severity: 'blunder' });
    const legacy: Partial<BlunderSolution> = solution();
    delete legacy.feedback;
    expect(gameChip(legacy as BlunderSolution)?.facepalm).toBe(false);
  });

  it("never flags the Best chip or the user's own better move", () => {
    const caught: BlunderSolution = {
      ...scored(0.95),
      better_move_uci: OTHER_BETTER,
      better_move_tier: 'wrong',
    };
    for (const chip of buildSolutionChips(caught, {}).filter((c) => c.key !== 'game')) {
      expect(chip.facepalm).toBeUndefined();
    }
    expect(buildSolutionOverlay(caught).markers).toEqual(
      expect.arrayContaining([
        { square: 'd4', best: true },
        { square: 'c3', severity: 'mistake' },
        { square: 'f3', severity: 'blunder', facepalm: true },
      ]),
    );
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
    expect(copy).toBe('Your call was right +3 and you played a mistake, Nc3 +0. Best was d4.');
  });

  it('does not repeat the best move when the user found it, and adds the earlier calls', () => {
    const copy = sentence(solution({ safe_points: 2, window_points: 7 }));
    expect(copy).toBe(
      'Your call was right +3 and you found the best move, d4 +2. Your earlier calls earned +2.',
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
    expect(copy).toBe('Your call was wrong +0. Best was d4.');
  });
});

describe('solutionCopy feedback (Phase 261 D-03 to D-09)', () => {
  function feedbackOf(overrides: Partial<BlunderFeedback>): BlunderFeedback {
    return { score: 0.5, facepalm_type: 'allowed_loss', type_line: null, hard_to_catch: false, ...overrides };
  }

  // Phase 264 D-16: the four type sentences left this paragraph for the shared "Game move:"
  // line below the divider; only the hard-to-catch line is still feedback.
  it.each<[BlunderFeedback['type_line'] & string, string]>([
    // D-25: the snapshot score (0.5 here) follows as its own sentence.
    ['allowed_material', 'Game move: loses material. Fairly easy to spot (facepalm score 50%).'],
    ['allowed_mate', 'Game move: allows checkmate. Fairly easy to spot (facepalm score 50%).'],
    ['missed_material', 'Game move: missed a chance to win material. Fairly easy to spot (facepalm score 50%).'],
    ['missed_mate', 'Game move: missed checkmate. Fairly easy to spot (facepalm score 50%).'],
  ])('type line %s is the game-move line "%s", not a feedback sentence', (typeLine, sentence) => {
    const copy = solutionCopy(solution({ feedback: feedbackOf({ type_line: typeLine }) }));
    expect(copy.feedback).toBeNull();
    expect(gameBlunderSentence(copy.gameMove)).toBe(sentence);
  });

  it('a null type line with no tag and no hard-to-catch line: no paragraph, the line says the score (D-23)', () => {
    const copy = solutionCopy(solution({ feedback: feedbackOf({ score: 0.237, type_line: null }) }));
    expect(copy.feedback).toBeNull();
    expect(gameBlunderSentence(copy.gameMove)).toBe('Game move: hard to spot (facepalm score 23%).');
    // With the hard-to-catch line above the divider the band word is not said twice.
    const hard = solutionCopy(solution({ feedback: feedbackOf({ score: 0.237, type_line: null, hard_to_catch: true }) }));
    expect(hard.feedback?.lines).toHaveLength(1);
    expect(gameBlunderSentence(hard.gameMove)).toBe('Game move: facepalm score 23%.');
    // A pre-phase window has no snapshot, so no score: nothing known, no line.
    expect(solutionCopy(solution({ feedback: null })).gameMove).toEqual([]);
  });

  it('after a tag or a type part the snapshot score follows as its own sentence (D-25)', () => {
    const typed = solutionCopy(solution({ feedback: feedbackOf({ score: 0.237, type_line: 'allowed_material' }) }));
    expect(gameBlunderSentence(typed.gameMove)).toBe('Game move: loses material. Hard to spot (facepalm score 23%).');
  });

  it('the hard-to-catch line differs after a catch and after a miss, and is absent when false', () => {
    const hard = feedbackOf({ hard_to_catch: true });
    expect(solutionCopy(solution({ outcome: 'caught', feedback: hard })).feedback?.lines).toEqual([
      'Well spotted! This was one of the tough ones we mix in on purpose.',
    ]);
    expect(solutionCopy(solution({ outcome: 'missed', feedback: hard })).feedback?.lines).toEqual([
      'This one was hard to catch. We mix in a few tough ones on purpose.',
    ]);
    expect(solutionCopy(solution({ feedback: feedbackOf({ type_line: 'allowed_mate' }) })).feedback).toBeNull();
  });

  it('keeps the hard-to-catch line in the paragraph next to a type line, and carries no score', () => {
    const copy = solutionCopy(
      solution({
        outcome: 'missed',
        feedback: { score: 0.437, type_line: 'missed_mate', hard_to_catch: true },
      }),
    );
    expect(copy.feedback).toEqual({
      lines: ['This one was hard to catch. We mix in a few tough ones on purpose.'],
    });
    // Hard to catch: the band word is not said twice.
    expect(gameBlunderSentence(copy.gameMove)).toBe('Game move: missed checkmate. Facepalm score 43%.');
  });

  it('the game-move line carries the solution\'s tags before the type part (C12, C13)', () => {
    const tagged = { allowed_tactic: { motif: 'fork', depth: 1 }, missed_tactic: null };
    const withType = solutionCopy(solution({ ...tagged, feedback: feedbackOf({ type_line: 'allowed_material' }) }));
    expect(gameBlunderSentence(withType.gameMove)).toBe(
      'Game move: allowed fork in 2, loses material. Fairly easy to spot (facepalm score 50%).',
    );
    // A pre-phase window has no feedback, and still gets its tag.
    const tagOnly = solutionCopy(solution({ ...tagged, feedback: null }));
    expect(gameBlunderSentence(tagOnly.gameMove)).toBe('Game move: allowed fork in 2.');
  });

  it('the line\'s subject is the blunder\'s SAN with "??", or "???" from a 70% score', () => {
    const plain = solutionCopy(solution({ feedback: feedbackOf({ score: 0.5, type_line: 'allowed_material' }) }));
    expect(plain.gameMoveHead).toEqual({
      san: sanFromUci(FEN, BLUNDER),
      quality: 'blunder',
      facepalmScore: 0.5,
      facepalmType: 'allowed_loss',
      byOther: false,
    });
    const foreign = solutionCopy(solution({ is_own: false, feedback: feedbackOf({ score: 0.7, facepalm_type: 'missed_win' }) }));
    expect(foreign.gameMoveHead).toMatchObject({ facepalmScore: 0.7, facepalmType: 'missed_win', byOther: true });
    // A solution cached before facepalm_type existed: the score alone, so a plain glyph.
    const cached = solutionCopy(solution({ feedback: { score: 0.7, type_line: null, hard_to_catch: false } }));
    expect(cached.gameMoveHead).toMatchObject({ facepalmScore: 0.7, facepalmType: null });
    expect(gameBlunderSentence(plain.gameMove, plain.gameMoveHead.san)).toBe(
      `${sanFromUci(FEN, BLUNDER)}: loses material. Fairly easy to spot (facepalm score 50%).`,
    );
  });

  it('a timed-out blunder is not called a wrong call (review fix)', () => {
    const base = { outcome: 'missed', blunder_points: 0, better_move_uci: null, better_move_tier: null, better_move_points: null } as const;
    const text = (s: BlunderSolution): string =>
      solutionCopy(s).parts.map((part) => (typeof part === 'string' ? part : `+${part.points}`)).join('');
    expect(text(solution({ ...base, timed_out: true }))).toContain('Time ran out before your call +0.');
    expect(text(solution({ ...base, timed_out: false }))).toContain('Your call was wrong +0.');
    // A solution cached before the release has no such field: the plain wording.
    expect(text(solution(base))).toContain('Your call was wrong +0.');
  });

  it('a solution cached before the release (no tag fields) gets its type part alone', () => {
    const legacy: Partial<BlunderSolution> = solution({ feedback: feedbackOf({ type_line: 'allowed_material' }) });
    delete legacy.allowed_tactic;
    delete legacy.missed_tactic;
    expect(gameBlunderSentence(solutionCopy(legacy as BlunderSolution).gameMove)).toBe(
      'Game move: loses material. Fairly easy to spot (facepalm score 50%).',
    );
  });

  it('gives no feedback for a null feedback or a cached solution with no feedback field', () => {
    expect(solutionCopy(solution({ feedback: null })).feedback).toBeNull();
    // A solution cached in sessionStorage before the release has no such key at all.
    const legacy: Partial<BlunderSolution> = solution();
    delete legacy.feedback;
    expect(solutionCopy(legacy as BlunderSolution).feedback).toBeNull();
  });

  it('does not change the verdict sentence', () => {
    const plain = solutionCopy(solution({ feedback: null })).parts;
    const withFeedback = solutionCopy(
      solution({ feedback: { score: 0.9, type_line: 'allowed_mate', hard_to_catch: true } }),
    ).parts;
    expect(withFeedback).toEqual(plain);
  });

  it('a false alarm and a herring carry no feedback (D-05)', () => {
    const falseAlarm: FalseAlarmSolution = {
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
    };
    const herring: HerringSolution = {
      kind: 'herring',
      outcome: 'cleared',
      is_own: true,
      game_id: 1,
      analysis_ply: 2,
      fen: FEN,
      sequence_ucis: [],
      game_info: null,
      window_points: 3,
    };
    expect(solutionCopy(falseAlarm).feedback).toBeNull();
    expect(solutionCopy(herring).feedback).toBeNull();
    // D-16: neither gets a "Game move:" line.
    expect(solutionCopy(falseAlarm).gameMove).toEqual([]);
    expect(solutionCopy(herring).gameMove).toEqual([]);
  });
});
