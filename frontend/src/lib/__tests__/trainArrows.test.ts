import { describe, it, expect } from 'vitest';
import {
  buildChipFocusOverlay,
  buildTrainLiveAlternativeArrows,
  buildTrainRevealOverlay,
  buildTrainFreePlayArrows,
  buildTrainStepArrows,
  buildTrainStepMarkers,
  buildTrainStepOverlayArrows,
  dropLineMove,
  chipArrowColor,
  classifyTrainMoveQuality,
  trainRootMultiPvFloor,
  vettedMoveForSquares,
  TRAIN_BEST_MOVE_ARROW_WIDTH,
  TRAIN_LIVE_ALT_MIN_DEPTH,
  TRAIN_LIVE_ALT_ROOT_MULTIPV,
  TRAIN_SOFT_TOTAL_ALT_MOVE_ARROWS,
  TRAIN_GOOD_MOVE_ARROW_WIDTH,
  TRAIN_GAME_MOVE_ARROW_WIDTH,
  TRAIN_STEP_HIGHLIGHT,
} from '@/lib/trainArrows';
import type { TrainFineMove, TrainLiveAlternativeContext } from '@/lib/trainArrows';
import { classifyLiveSeverity, evalToExpectedScore } from '@/lib/liveFlaw';
import type { PvLine } from '@/hooks/uciParser';
import { DARK_GREEN } from '@/lib/arrowColor';
import {
  MOVE_HIGHLIGHT_BEST,
  MOVE_HIGHLIGHT_GOOD,
  MOVE_HIGHLIGHT_SQUARE,
  MOVE_QUALITY_BLUNDER,
  MOVE_QUALITY_GOOD,
  MOVE_QUALITY_INACCURACY,
  MOVE_QUALITY_MISTAKE,
  NEXT_MOVE_ARROW,
  STOCKFISH_SECONDARY_LINE,
  TRAIN_BEST_MOVE_ARROW,
  TRAIN_FOCUS_ARROW_DIM_OPACITY,
  TRAIN_FOCUS_ARROW_LIT_OPACITY,
  TRAIN_FOCUS_BADGE_DIM_OPACITY,
  TRAIN_FOCUS_BADGE_LIT_OPACITY,
  TRAIN_FOCUS_LIVE_ALT_DIM_OPACITY,
} from '@/lib/theme';

/** Shorthand: wrap UCIs as clean ('good') fine moves — the pre-260726-fma
 * shape every legacy case in this file exercised. */
function good(...ucis: string[]): TrainFineMove[] {
  return ucis.map((uci) => ({ uci, quality: 'good' as const }));
}

describe('buildTrainRevealOverlay', () => {
  it('returns an empty overlay when the verdict has not landed, even with a full good-moves list, a played move and a game move supplied', () => {
    const overlay = buildTrainRevealOverlay(
      'soft',
      good('e2e4', 'd2d4', 'g1f3', 'c2c4'),
      'e2e4',
      { uci: 'e2e4', quality: 'best' },
      { uci: 'd2d4', quality: 'good' },
      false,
    );
    expect(overlay.arrows).toEqual([]);
    expect(overlay.markers).toEqual([]);
    expect(overlay.alsoFineMoves).toEqual([]);
  });

  it('a sharp puzzle with four good moves returns exactly one arrow — the BLUE best move — with a best badge on its target square (190.1 UAT); alsoFineMoves is empty (D-03)', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4', 'd2d4', 'g1f3', 'c2c4'),
      'e2e4',
      null,
      null,
      true,
    );
    expect(overlay.arrows).toHaveLength(1);
    expect(overlay.arrows[0]).toMatchObject({
      startSquare: 'e2',
      endSquare: 'e4',
      color: TRAIN_BEST_MOVE_ARROW,
    });
    expect(overlay.markers).toEqual([{ square: 'e4', best: true }]);
    expect(overlay.alsoFineMoves).toEqual([]);
  });

  it('a soft puzzle draws exactly ONE alternative when BOTH served entries survive the filter (client best and played move match neither) — the soft cap of 1 truncates to the FIRST entry, which best-first server order makes the STRONGEST new fine move (D-01 amendment)', () => {
    const overlay = buildTrainRevealOverlay(
      'soft',
      [
        { uci: 'd2d4', quality: 'best' }, // the deep best, served first
        { uci: 'g1f3', quality: 'good' }, // the deep second-best (su)
      ],
      'e2e4', // the client engine disagrees with the deep best
      { uci: 'a2a3', quality: 'blunder' }, // off-key played move
      null,
      true,
    );
    // Blue client-best arrow + played arrow + exactly ONE green alternative:
    // the deep best, never the truncated su.
    expect(overlay.arrows.map((a) => `${a.startSquare}${a.endSquare}`)).toEqual([
      'a2a3',
      'e2e4',
      'd2d4',
    ]);
    expect(overlay.arrows[1]!.color).toBe(TRAIN_BEST_MOVE_ARROW);
    expect(overlay.arrows[2]!.color).toBe(DARK_GREEN);
    // The su (g1f3) is beyond TRAIN_SOFT_ALT_MOVE_ARROWS and must never leak
    // into the sidebar row either — the LEGEND-04 1:1 invariant.
    expect(overlay.arrows.some((a) => `${a.startSquare}${a.endSquare}` === 'g1f3')).toBe(false);
    expect(overlay.alsoFineMoves).toEqual([{ uci: 'd2d4', quality: 'best' }]);
  });

  it("the operator's Task 3 round-2 scenario: the served su coincides with the client's best AND played move, so the deep-best entry is what keeps the \"Also fine\" row non-empty (D-01 amendment)", () => {
    // Before the amendment the served list was [d1a4] alone; the filter below
    // absorbed it (== bestMoveUci AND == playedMove.uci) and the row rendered
    // EMPTY under the "several fine moves" copy. The deep best (d1e2 — Be2 in
    // the operator's screenshot) is genuinely new information and must
    // survive as the row's single entry.
    const overlay = buildTrainRevealOverlay(
      'soft',
      [
        { uci: 'd1e2', quality: 'best' },
        { uci: 'd1a4', quality: 'good' },
      ],
      'd1a4', // client engine's best…
      { uci: 'd1a4', quality: 'best' }, // …which the user also played
      null,
      true,
    );
    expect(overlay.alsoFineMoves).toEqual([{ uci: 'd1e2', quality: 'best' }]);
    const alt = overlay.arrows.find((a) => a.layerKey === 'good-0');
    expect(alt).toMatchObject({ startSquare: 'd1', endSquare: 'e2', color: DARK_GREEN });
    // The deep engine's endorsement is real information: the alternative
    // keeps its 'best' badge (blue star) on the green arrow's target square.
    expect(overlay.markers).toContainEqual({ square: 'e2', best: true });
  });

  it('an inaccuracy-level fine move renders the SAME dark-green arrow and good badge as a clean alternative — the D-05 collapse applies to alternatives too', () => {
    const overlay = buildTrainRevealOverlay(
      'herring',
      [
        { uci: 'e2e4', quality: 'good' },
        { uci: 'd2d4', quality: 'good' },
        { uci: 'g1f3', quality: 'inaccuracy' },
      ],
      'e2e4',
      null,
      null,
      true,
    );
    expect(overlay.arrows).toHaveLength(3);
    const greenAlt = overlay.arrows.find((a) => a.endSquare === 'd4');
    const collapsedAlt = overlay.arrows.find((a) => a.endSquare === 'f3');
    expect(greenAlt).toMatchObject({ color: DARK_GREEN, width: TRAIN_GOOD_MOVE_ARROW_WIDTH });
    expect(collapsedAlt).toMatchObject({
      color: DARK_GREEN,
      width: TRAIN_GOOD_MOVE_ARROW_WIDTH,
    });
    expect(overlay.markers).toEqual([
      { square: 'e4', best: true },
      { square: 'd4', good: true },
      { square: 'f3', good: true },
    ]);
    // alsoFineMoves keeps the fine move's OWN classified quality (the
    // collapse is a drawing decision only, never a data mutation) — and
    // equals exactly the drawn alternatives (LEGEND-04).
    expect(overlay.alsoFineMoves).toEqual([
      { uci: 'd2d4', quality: 'good' },
      { uci: 'g1f3', quality: 'inaccuracy' },
    ]);
  });

  it('a herring puzzle draws up to FOUR alternatives from a five-entry vetted list (Phase 211 D-01: the ladder minus its top entry) — its own budget, no longer the soft cap', () => {
    // Mutation guard (RESEARCH Pitfall 6): collapsing alternativeArrowCap
    // back to a two-way sharp/non-sharp branch caps this at the soft budget
    // (1) and turns the two assertions below red.
    const overlay = buildTrainRevealOverlay(
      'herring',
      good('e2e4', 'd2d4', 'g1f3', 'c2c4', 'b1c3'),
      'e2e4',
      null,
      null,
      true,
    );
    expect(overlay.arrows).toHaveLength(5); // blue best + four green
    // The legend row equals exactly the drawn alternatives (LEGEND-04).
    expect(overlay.alsoFineMoves).toEqual([
      { uci: 'd2d4', quality: 'good' },
      { uci: 'g1f3', quality: 'good' },
      { uci: 'c2c4', quality: 'good' },
      { uci: 'b1c3', quality: 'good' },
    ]);
  });

  it('a blundered played move gets a blunder-colored arrow and a blunder severity badge, alongside the blue best arrow', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4'),
      'e2e4',
      { uci: 'd2d4', quality: 'blunder' },
      null,
      true,
    );
    expect(overlay.arrows).toHaveLength(2);
    const played = overlay.arrows.find((a) => a.layerKey === 'played');
    const best = overlay.arrows.find((a) => a.layerKey === 'best');
    expect(played).toMatchObject({ startSquare: 'd2', endSquare: 'd4', color: MOVE_QUALITY_BLUNDER });
    expect(best).toMatchObject({ startSquare: 'e2', endSquare: 'e4', color: TRAIN_BEST_MOVE_ARROW });
    expect(overlay.markers).toEqual([
      { square: 'd4', severity: 'blunder' },
      { square: 'e4', best: true },
    ]);
  });

  it('a played move that IS the best move merges into the single blue arrow with one best badge — never two arrows for one move', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4'),
      'e2e4',
      { uci: 'e2e4', quality: 'best' },
      null,
      true,
    );
    expect(overlay.arrows).toHaveLength(1);
    expect(overlay.arrows[0]!.color).toBe(TRAIN_BEST_MOVE_ARROW);
    expect(overlay.markers).toEqual([{ square: 'e4', best: true }]);
  });

  it('a played move matching a green alternative replaces that green arrow with the quality-colored played arrow, and is skipped from alsoFineMoves too', () => {
    const overlay = buildTrainRevealOverlay(
      'soft',
      good('e2e4', 'd2d4', 'g1f3'),
      'e2e4',
      { uci: 'd2d4', quality: 'good' },
      null,
      true,
    );
    // best (blue) + played (good, light green) + one remaining alternative
    // (the played entry was filtered BEFORE the soft slice, so g1f3 still
    // fits the 1-alternative budget).
    expect(overlay.arrows).toHaveLength(3);
    const d4Arrows = overlay.arrows.filter((a) => a.endSquare === 'd4');
    expect(d4Arrows).toHaveLength(1);
    expect(d4Arrows[0]!.color).toBe(MOVE_QUALITY_GOOD);
    // d2d4 is skipped from alsoFineMoves exactly as it is from the arrows —
    // only g1f3 (the one remaining drawn alternative) survives (LEGEND-04).
    expect(overlay.alsoFineMoves).toEqual([{ uci: 'g1f3', quality: 'good' }]);
  });

  // UAT round 4 regression (recast on the herring budget in Phase 211): the
  // best move and the played alternative are filtered out BEFORE the slice,
  // so neither consumes an alternative slot — all three remaining vetted
  // entries draw and list.
  it('a played fine alternative does not consume an alternative slot — the remaining alternatives all still draw and all list (UAT round 4)', () => {
    const overlay = buildTrainRevealOverlay(
      'herring',
      good('e2e4', 'd2d4', 'g1f3', 'c2c4', 'b1c3'),
      'e2e4',
      { uci: 'd2d4', quality: 'good' },
      null,
      true,
    );
    // best (blue) + played d2d4 (good) + g1f3 + c2c4 + b1c3 (all green).
    expect(overlay.arrows).toHaveLength(5);
    expect(overlay.arrows.filter((a) => a.layerKey?.startsWith('good-'))).toHaveLength(3);
    // The legend row equals exactly the drawn alternatives (LEGEND-04).
    expect(overlay.alsoFineMoves).toEqual([
      { uci: 'g1f3', quality: 'good' },
      { uci: 'c2c4', quality: 'good' },
      { uci: 'b1c3', quality: 'good' },
    ]);
  });

  it('a sharp puzzle still draws ZERO alternatives even when the user played a fine one — the deep answer key outranks the live search (UAT round 4)', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4', 'd2d4', 'g1f3', 'c2c4'),
      'e2e4',
      { uci: 'd2d4', quality: 'good' },
      null,
      true,
    );
    // Only the blue best arrow and the user's own played arrow — never green
    // alternatives.
    expect(overlay.arrows.filter((a) => a.layerKey?.startsWith('good-'))).toHaveLength(0);
    expect(overlay.arrows).toHaveLength(2);
    expect(overlay.alsoFineMoves).toEqual([]);
  });

  it("alsoFineMoves.length always equals the number of arrows whose layerKey starts with 'good-' (D-03 1:1 invariant)", () => {
    const overlay = buildTrainRevealOverlay(
      'soft',
      good('e2e4', 'd2d4', 'g1f3', 'c2c4', 'b1c3'),
      'e2e4',
      null,
      null,
      true,
    );
    const goodArrowCount = overlay.arrows.filter((a) => a.layerKey?.startsWith('good-')).length;
    expect(overlay.alsoFineMoves.length).toBe(goodArrowCount);
  });

  it('played mistake and played blunder each keep their own arrow color and a severity marker — never collapsed like inaccuracy (prohibition 2)', () => {
    const mistakeOverlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4'),
      'e2e4',
      { uci: 'g1f3', quality: 'mistake' },
      null,
      true,
    );
    const mistakePlayed = mistakeOverlay.arrows.find((a) => a.layerKey === 'played');
    expect(mistakePlayed).toMatchObject({ color: MOVE_QUALITY_MISTAKE });
    expect(mistakeOverlay.markers).toContainEqual({ square: 'f3', severity: 'mistake' });

    const blunderOverlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4'),
      'e2e4',
      { uci: 'd2d4', quality: 'blunder' },
      null,
      true,
    );
    const blunderPlayed = blunderOverlay.arrows.find((a) => a.layerKey === 'played');
    expect(blunderPlayed).toMatchObject({ color: MOVE_QUALITY_BLUNDER });
    expect(blunderOverlay.markers).toContainEqual({ square: 'd4', severity: 'blunder' });
  });

  it('the game-move arrow carries NEXT_MOVE_ARROW, onTop true, a width strictly smaller than the good-move width, and its quality badge', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      [],
      null,
      null,
      { uci: 'g1f3', quality: 'mistake' },
      true,
    );
    expect(overlay.arrows).toHaveLength(1);
    const gameArrow = overlay.arrows[0]!;
    expect(gameArrow.color).toBe(NEXT_MOVE_ARROW);
    expect(gameArrow.onTop).toBe(true);
    expect(gameArrow.width).toBe(TRAIN_GAME_MOVE_ARROW_WIDTH);
    expect(gameArrow.width).toBeLessThan(TRAIN_GOOD_MOVE_ARROW_WIDTH);
    expect(overlay.markers).toEqual([{ square: 'f3', severity: 'mistake' }]);
  });

  it('a game move with null quality (search pending/failed) draws its arrow but no badge', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      [],
      null,
      null,
      { uci: 'g1f3', quality: null },
      true,
    );
    expect(overlay.arrows).toHaveLength(1);
    expect(overlay.markers).toEqual([]);
  });

  it('badges dedupe by target square with the played move winning (played and best land on the same square from different origins); the played inaccuracy keeps its own severity badge (quick 261008-opg)', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4'),
      'e2e4',
      { uci: 'd3e4', quality: 'inaccuracy' },
      null,
      true,
    );
    const e4Markers = overlay.markers.filter((m) => m.square === 'e4');
    expect(e4Markers).toEqual([{ square: 'e4', severity: 'inaccuracy' }]);
  });

  it('a played inaccuracy draws the inaccuracy-yellow arrow, not the good green (quick 261008-opg)', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4'),
      'e2e4',
      { uci: 'd2d4', quality: 'inaccuracy' },
      null,
      true,
    );
    const played = overlay.arrows.find((a) => a.layerKey === 'played');
    expect(played?.color).toBe(MOVE_QUALITY_INACCURACY);
  });

  it('a coincident from-to pair across played, best and game moves keeps distinct layerKeys so concentric arrows survive dedupe', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4'),
      'e2e4',
      { uci: 'd2d4', quality: 'mistake' },
      { uci: 'd2d4', quality: 'mistake' },
      true,
    );
    const layerKeys = overlay.arrows.map((a) => a.layerKey);
    expect(new Set(layerKeys).size).toBe(overlay.arrows.length);
  });

  it('a three-character UCI and an empty string each contribute no arrow and do not throw', () => {
    expect(() =>
      buildTrainRevealOverlay('sharp', good('e2e'), '', { uci: '', quality: 'good' }, { uci: '', quality: null }, true),
    ).not.toThrow();
    const overlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e'),
      '',
      { uci: '', quality: 'good' },
      { uci: '', quality: null },
      true,
    );
    expect(overlay.arrows).toEqual([]);
    expect(overlay.markers).toEqual([]);
  });
});

// Phase 211 (Plan 03, D-06): the free-play root ply's key lookup. These four
// cases carry forward, in substance, the behavior contract of the deleted
// squares-only rank matcher (formerly in uciParser.ts, deleted in 211-03):
// empty-list null, no-match null, promotion tolerance, array-order ties.
describe('vettedMoveForSquares (Phase 211 D-06)', () => {
  it('returns null for an empty vetted list', () => {
    expect(vettedMoveForSquares([], 'e2', 'e4')).toBeNull();
  });

  it("returns null when no entry's UCI starts with the given squares", () => {
    const moves = good('e2e4', 'd2d4');
    expect(vettedMoveForSquares(moves, 'g1', 'f3')).toBeNull();
  });

  it('matches an entry whose UCI carries a promotion suffix — the promotion-tolerance contract (MoveNode stores no promotion piece)', () => {
    const moves = good('e7e8q', 'd2d4');
    const result = vettedMoveForSquares(moves, 'e7', 'e8');
    expect(result?.uci).toBe('e7e8q');
  });

  it('two entries naming the same squares (a promotion-variant pair): the EARLIER entry wins — array order is the server\'s own best-first order, the tie rule', () => {
    const moves: TrainFineMove[] = [
      { uci: 'e7e8q', quality: 'good' },
      { uci: 'e7e8n', quality: 'inaccuracy' },
    ];
    const result = vettedMoveForSquares(moves, 'e7', 'e8');
    expect(result?.uci).toBe('e7e8q');
    expect(result?.quality).toBe('good');
  });

  it('a malformed/short UCI never matches and never throws', () => {
    const moves: TrainFineMove[] = [{ uci: 'e2', quality: 'good' }];
    expect(vettedMoveForSquares(moves, 'e2', 'e4')).toBeNull();
  });
});

describe('classifyTrainMoveQuality', () => {
  it('the best move is always best regardless of expected scores', () => {
    expect(classifyTrainMoveQuality(0.9, 0.1, true)).toBe('best');
  });

  it('no meaningful drop classifies as good', () => {
    expect(classifyTrainMoveQuality(0.5, 0.5, false)).toBe('good');
  });

  it('a large drop classifies as blunder', () => {
    expect(classifyTrainMoveQuality(0.9, 0.1, false)).toBe('blunder');
  });
});

describe('buildTrainStepArrows (190.1 UAT stepping)', () => {
  it('returns a single blue engine-hue arrow for the next move', () => {
    const arrows = buildTrainStepArrows('g1f3');
    expect(arrows).toHaveLength(1);
    expect(arrows[0]).toMatchObject({
      startSquare: 'g1',
      endSquare: 'f3',
      color: TRAIN_BEST_MOVE_ARROW,
    });
  });

  it('returns no arrow for a null or malformed next move (end of the line)', () => {
    expect(buildTrainStepArrows(null)).toEqual([]);
    expect(buildTrainStepArrows('e2')).toEqual([]);
  });
});

describe('buildTrainFreePlayArrows (Phase 200 UAT round 5, Phase 228 D-13/D-15)', () => {
  const pv = (multipv: number, firstMove: string): PvLine => ({
    multipv,
    depth: 12,
    moves: [firstMove, 'a7a6'],
    evalCp: 10,
    evalMate: null,
  });

  it("count 1 returns a single blue engine-hue arrow for the free-play engine's top move (the default)", () => {
    const arrows = buildTrainFreePlayArrows([pv(1, 'e7e5'), pv(2, 'c7c5')], 1);
    expect(arrows).toHaveLength(1);
    expect(arrows[0]).toMatchObject({
      startSquare: 'e7',
      endSquare: 'e5',
      color: TRAIN_BEST_MOVE_ARROW,
    });
  });

  it('count 3 returns three distinct arrows: rank 0 solid blue, ranks 1-2 translucent, one shared width, rank 0 last', () => {
    const arrows = buildTrainFreePlayArrows([pv(1, 'e7e5'), pv(2, 'c7c5'), pv(3, 'g8f6')], 3);
    expect(arrows).toHaveLength(3);
    const byKey = (key: string) => arrows.find((a) => a.layerKey === key);
    expect(byKey('free-0')?.color).toBe(TRAIN_BEST_MOVE_ARROW);
    expect(byKey('free-1')?.color).toBe(STOCKFISH_SECONDARY_LINE);
    expect(byKey('free-2')?.color).toBe(STOCKFISH_SECONDARY_LINE);
    expect(new Set(arrows.map((a) => a.width))).toEqual(new Set([TRAIN_BEST_MOVE_ARROW_WIDTH]));
    expect(new Set(arrows.map((a) => `${a.startSquare}${a.endSquare}`)).size).toBe(3);
    // Primary pushed last so it paints on top within its width tier.
    expect(arrows[arrows.length - 1]?.layerKey).toBe('free-0');
  });

  it('count 0 returns no arrows (the Stockfish arrows setting 0 hides the live arrows)', () => {
    expect(buildTrainFreePlayArrows([pv(1, 'e7e5')], 0)).toEqual([]);
  });

  it('returns no arrow while the engine has no lines for the shown position, and skips a malformed UCI', () => {
    expect(buildTrainFreePlayArrows([], 3)).toEqual([]);
    expect(buildTrainFreePlayArrows([pv(1, 'e7')], 1)).toEqual([]);
    const arrows = buildTrainFreePlayArrows([pv(1, 'e7e5'), pv(2, 'zz'), pv(3, 'g8f6')], 3);
    expect(arrows.map((a) => a.layerKey).sort()).toEqual(['free-0', 'free-2']);
  });

  it('a count above the available lines yields only the available arrows', () => {
    expect(buildTrainFreePlayArrows([pv(1, 'e7e5')], 3)).toHaveLength(1);
  });

  it("uses its own layerKey, so a free-play arrow never collides with the stepper's", () => {
    const free = buildTrainFreePlayArrows([pv(1, 'e7e5')], 1)[0];
    const step = buildTrainStepArrows('e7e5')[0];
    expect(free?.layerKey).not.toBe(step?.layerKey);
  });
});

describe('buildTrainStepOverlayArrows (quick 261009-por)', () => {
  const pv = (multipv: number, firstMove: string, depth: number = 12): PvLine => ({
    multipv,
    depth,
    moves: [firstMove, 'a7a6'],
    evalCp: 10,
    evalMate: null,
  });

  it('engine agrees with the line: exactly the single blue line arrow', () => {
    const arrows = buildTrainStepOverlayArrows('g1f3', [pv(1, 'g1f3')], 1);
    expect(arrows).toHaveLength(1);
    expect(arrows[0]).toMatchObject({ layerKey: 'step-next', color: TRAIN_BEST_MOVE_ARROW });
  });

  it('a disagreeing engine move draws a secondary under the line arrow, even at depth 1 (no gate)', () => {
    const arrows = buildTrainStepOverlayArrows('g1f3', [pv(1, 'b1c3', 1)], 1);
    expect(arrows).toHaveLength(2);
    expect(arrows[0]).toMatchObject({
      startSquare: 'b1',
      endSquare: 'c3',
      color: STOCKFISH_SECONDARY_LINE,
      width: TRAIN_BEST_MOVE_ARROW_WIDTH,
    });
    expect(arrows[arrows.length - 1]).toMatchObject({
      layerKey: 'step-next',
      color: TRAIN_BEST_MOVE_ARROW,
    });
  });

  it('setting 0 draws only the line arrow', () => {
    const arrows = buildTrainStepOverlayArrows('g1f3', [pv(1, 'b1c3')], 0);
    expect(arrows.map((a) => a.layerKey)).toEqual(['step-next']);
  });

  it('empty pvLines (engine not at the shown position yet) draws only the line arrow', () => {
    const arrows = buildTrainStepOverlayArrows('g1f3', [], 3);
    expect(arrows.map((a) => a.layerKey)).toEqual(['step-next']);
  });

  it('count 3: disagreeing ranks all draw as unique secondaries, line arrow last', () => {
    const arrows = buildTrainStepOverlayArrows(
      'g1f3',
      [pv(1, 'g1f3'), pv(2, 'b1c3'), pv(3, 'd2d4')],
      3,
    );
    expect(arrows).toHaveLength(3);
    expect(arrows[arrows.length - 1]?.layerKey).toBe('step-next');
    const live = arrows.slice(0, -1);
    expect(live.map((a) => a.color)).toEqual([STOCKFISH_SECONDARY_LINE, STOCKFISH_SECONDARY_LINE]);
    const keys = arrows.map((a) => a.layerKey);
    expect(new Set(keys).size).toBe(keys.length);
    for (const a of live) {
      expect(a.layerKey).not.toBe('step-next');
      expect(a.layerKey?.startsWith('free-')).toBe(false);
    }
  });

  it('dedupes by from-to squares only (an under-promotion on the same squares is hidden)', () => {
    const arrows = buildTrainStepOverlayArrows('e7e8q', [pv(1, 'e7e8n')], 1);
    expect(arrows.map((a) => a.layerKey)).toEqual(['step-next']);
  });

  it('skips a malformed live UCI without throwing', () => {
    const arrows = buildTrainStepOverlayArrows('g1f3', [pv(1, 'zz'), pv(2, 'b1c3')], 2);
    expect(arrows.map((a) => `${a.startSquare}${a.endSquare}`)).toEqual(['b1c3', 'g1f3']);
  });

  it('end of the line (null next move): live moves draw as secondaries with no primary', () => {
    const arrows = buildTrainStepOverlayArrows(null, [pv(1, 'b1c3')], 1);
    expect(arrows).toHaveLength(1);
    expect(arrows[0]).toMatchObject({ color: STOCKFISH_SECONDARY_LINE });
    expect(arrows.some((a) => a.layerKey === 'step-next')).toBe(false);
  });

  it('a count above the available lines yields only the available arrows', () => {
    const arrows = buildTrainStepOverlayArrows('g1f3', [pv(1, 'b1c3')], 3);
    expect(arrows).toHaveLength(2);
  });
});

describe('dropLineMove (quick 261009-por)', () => {
  const pv = (multipv: number, firstMove: string): PvLine => ({
    multipv,
    depth: 12,
    moves: [firstMove],
    evalCp: 10,
    evalMate: null,
  });

  it("drops the live line that repeats the known line's next move, keeping rank order", () => {
    const lines = [pv(1, 'g1f3'), pv(2, 'b1c3'), pv(3, 'd2d4')];
    expect(dropLineMove(lines, 'g1f3').map((l) => l.moves[0])).toEqual(['b1c3', 'd2d4']);
  });

  it('compares from-to squares only (a promotion suffix does not matter)', () => {
    expect(dropLineMove([pv(1, 'e7e8n')], 'e7e8q')).toEqual([]);
  });

  it('keeps every line when the engine disagrees or at the end of the line', () => {
    const lines = [pv(1, 'b1c3'), pv(2, 'd2d4')];
    expect(dropLineMove(lines, 'g1f3')).toEqual(lines);
    expect(dropLineMove(lines, null)).toEqual(lines);
  });
});

describe('buildTrainStepMarkers (190.1 UAT round 4)', () => {
  it('returns the quality badge on the moved-to square for the FIRST move only', () => {
    expect(buildTrainStepMarkers('e2e4', 'best', true)).toEqual([{ square: 'e4', best: true }]);
    expect(buildTrainStepMarkers('e2e4', 'blunder', true)).toEqual([
      { square: 'e4', severity: 'blunder' },
    ]);
  });

  it('returns nothing for deeper steps, unknown quality, or a malformed UCI', () => {
    expect(buildTrainStepMarkers('e2e4', 'good', false)).toEqual([]);
    expect(buildTrainStepMarkers('e2e4', null, true)).toEqual([]);
    expect(buildTrainStepMarkers('e2', 'good', true)).toEqual([]);
  });
});

describe('TRAIN_STEP_HIGHLIGHT (190.1 UAT stepping)', () => {
  it('maps best to the engine-blue highlight and inaccuracy to the shared yellow, not good (quick 261008-opg)', () => {
    expect(TRAIN_STEP_HIGHLIGHT.best).toBe(MOVE_HIGHLIGHT_BEST);
    expect(TRAIN_STEP_HIGHLIGHT.inaccuracy).toBe(MOVE_HIGHLIGHT_SQUARE);
    expect(TRAIN_STEP_HIGHLIGHT.inaccuracy).not.toBe(MOVE_HIGHLIGHT_GOOD);
  });

  it('mistake and blunder keep their own distinct highlight values — never collapsed', () => {
    expect(TRAIN_STEP_HIGHLIGHT.mistake).not.toBe(TRAIN_STEP_HIGHLIGHT.good);
    expect(TRAIN_STEP_HIGHLIGHT.blunder).not.toBe(TRAIN_STEP_HIGHLIGHT.good);
    expect(TRAIN_STEP_HIGHLIGHT.mistake).not.toBe(TRAIN_STEP_HIGHLIGHT.blunder);
  });
});

describe('buildChipFocusOverlay (Phase 237)', () => {
  const squaresOf = (a: { startSquare: string; endSquare: string }): string =>
    `${a.startSquare}${a.endSquare}`;

  it('keeps every arrow (dim, never filter): the count equals the input, the active move is lit and onTop, the rest dimmed and not onTop', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4'),
      'e2e4',
      { uci: 'd2d4', quality: 'mistake' },
      { uci: 'g1f3', quality: 'good' },
      true,
    );
    expect(overlay.arrows).toHaveLength(3); // played + best + game
    const focused = buildChipFocusOverlay(overlay, ['d2d4']);

    expect(focused.arrows).toHaveLength(overlay.arrows.length);
    const byMove = Object.fromEntries(focused.arrows.map((a) => [squaresOf(a), a]));
    expect(byMove['d2d4']).toMatchObject({ opacity: TRAIN_FOCUS_ARROW_LIT_OPACITY, onTop: true });
    expect(byMove['e2e4']).toMatchObject({ opacity: TRAIN_FOCUS_ARROW_DIM_OPACITY, onTop: false });
    // The game arrow is built onTop: true; while dimmed it must NOT paint over the lit one.
    expect(byMove['g1f3']).toMatchObject({ opacity: TRAIN_FOCUS_ARROW_DIM_OPACITY, onTop: false });
  });

  it('lights BOTH arrows of a merged role (quality-colored + thin white game arrow on the same squares) and dims the unrelated best arrow', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4'),
      'e2e4',
      { uci: 'd2d4', quality: 'mistake' },
      { uci: 'd2d4', quality: 'mistake' },
      true,
    );
    expect(overlay.arrows).toHaveLength(3); // played + best + game, distinct layerKeys
    const focused = buildChipFocusOverlay(overlay, ['d2d4']);

    const merged = focused.arrows.filter((a) => squaresOf(a) === 'd2d4');
    expect(new Set(merged.map((a) => a.layerKey))).toEqual(new Set(['played', 'game']));
    expect(merged.every((a) => a.opacity === TRAIN_FOCUS_ARROW_LIT_OPACITY && a.onTop === true)).toBe(true);
    const best = focused.arrows.find((a) => squaresOf(a) === 'e2e4');
    expect(best).toMatchObject({ opacity: TRAIN_FOCUS_ARROW_DIM_OPACITY, onTop: false });
  });

  it('lights a badge only when its markerOwners entry is active; the other badges dim but stay', () => {
    const overlay = buildTrainRevealOverlay(
      'sharp',
      good('e2e4'),
      'e2e4',
      { uci: 'd2d4', quality: 'mistake' },
      { uci: 'g1f3', quality: 'good' },
      true,
    );
    expect(overlay.markers.map((m) => m.square).sort()).toEqual(['d4', 'e4', 'f3']);
    const focused = buildChipFocusOverlay(overlay, ['g1f3']);

    expect(focused.markers).toHaveLength(overlay.markers.length);
    const opacityBySquare = Object.fromEntries(focused.markers.map((m) => [m.square, m.opacity]));
    expect(opacityBySquare).toEqual({
      f3: TRAIN_FOCUS_BADGE_LIT_OPACITY,
      d4: TRAIN_FOCUS_BADGE_DIM_OPACITY,
      e4: TRAIN_FOCUS_BADGE_DIM_OPACITY,
    });
  });

  // WR-02 regression. Two candidate moves can land on the SAME target square
  // (here c4d5 as the best move and e4d5 as a fine alternative). `pushMarker`
  // dedups badges by end square under precedence played > best > fine > game,
  // so only the blue best badge on d5 survives the build. Lighting markers by
  // end-square membership would hand that blue badge to the focused move,
  // including the green alternative that owns no badge at all.
  it('does not light another move’s badge when two candidate moves share a target square (WR-02)', () => {
    const overlay = buildTrainRevealOverlay('soft', good('e4d5'), 'c4d5', null, null, true);

    // One badge total, on the shared square, owned by the BEST move.
    expect(overlay.markers).toEqual([{ square: 'd5', best: true }]);
    expect(overlay.markerOwners['d5']).toBe('c4d5');

    // Focusing the alternative: its arrow is lit, the best badge it does not own stays dim.
    const alternative = buildChipFocusOverlay(overlay, ['e4d5']);
    expect(alternative.arrows.find((a) => squaresOf(a) === 'e4d5')?.opacity).toBe(TRAIN_FOCUS_ARROW_LIT_OPACITY);
    expect(alternative.markers).toEqual([
      { square: 'd5', best: true, opacity: TRAIN_FOCUS_BADGE_DIM_OPACITY },
    ]);

    // Focusing the best move lights the badge it actually owns.
    const best = buildChipFocusOverlay(overlay, ['c4d5']);
    expect(best.markers).toEqual([
      { square: 'd5', best: true, opacity: TRAIN_FOCUS_BADGE_LIT_OPACITY },
    ]);
  });

  it.each([
    ['null', null],
    ['empty', []],
  ] as const)('a %s active set dims every arrow and badge (D-04: no active move)', (_label, active) => {
    const overlay = buildTrainRevealOverlay(
      'soft',
      good('e2e4', 'd2d4'),
      'e2e4',
      { uci: 'g1f3', quality: 'good' },
      null,
      true,
    );
    const focused = buildChipFocusOverlay(overlay, active);
    expect(focused.arrows).toHaveLength(overlay.arrows.length);
    expect(focused.markers).toHaveLength(overlay.markers.length);
    expect(focused.arrows.every((a) => a.opacity === TRAIN_FOCUS_ARROW_DIM_OPACITY && a.onTop === false)).toBe(true);
    expect(focused.markers.every((m) => m.opacity === TRAIN_FOCUS_BADGE_DIM_OPACITY)).toBe(true);
  });

  it('an empty overlay stays empty', () => {
    const overlay = buildTrainRevealOverlay('sharp', good('e2e4'), 'e2e4', null, null, false);
    const focused = buildChipFocusOverlay(overlay, ['e2e4']);
    expect(focused.arrows).toEqual([]);
    expect(focused.markers).toEqual([]);
  });

  it('a malformed (< 4 char) UCI contributes no match and does not throw: everything dims', () => {
    const overlay = buildTrainRevealOverlay('sharp', good('e2e4'), 'e2e4', null, null, true);
    expect(() => buildChipFocusOverlay(overlay, ['e2e'])).not.toThrow();
    const focused = buildChipFocusOverlay(overlay, ['e2e']);
    expect(focused.arrows.every((a) => a.opacity === TRAIN_FOCUS_ARROW_DIM_OPACITY)).toBe(true);
    expect(focused.markers.every((m) => m.opacity === TRAIN_FOCUS_BADGE_DIM_OPACITY)).toBe(true);
  });

  it('passes alsoFineMoves and markerOwners through unchanged (Phase 200 LEGEND-04: the sidebar row is never emptied by the board focus)', () => {
    const overlay = buildTrainRevealOverlay(
      'soft',
      good('e2e4', 'd2d4', 'g1f3'),
      'e2e4',
      null,
      null,
      true,
    );
    const focused = buildChipFocusOverlay(overlay, ['e2e4']);
    expect(focused.alsoFineMoves).toBe(overlay.alsoFineMoves);
    expect(focused.markerOwners).toBe(overlay.markerOwners);
  });

  it('does not mutate the source overlay', () => {
    const overlay = buildTrainRevealOverlay('sharp', good('e2e4'), 'e2e4', null, null, true);
    buildChipFocusOverlay(overlay, ['e2e4']);
    expect(overlay.arrows.every((a) => a.opacity === undefined)).toBe(true);
    expect(overlay.markers.every((m) => m.opacity === undefined)).toBe(true);
  });

  describe('liveArrows (quick 261010-e5l)', () => {
    const liveArrow = (uci: string, index: number) => ({
      startSquare: uci.slice(0, 2),
      endSquare: uci.slice(2, 4),
      color: STOCKFISH_SECONDARY_LINE,
      width: TRAIN_BEST_MOVE_ARROW_WIDTH,
      layerKey: `live-alt-${index}`,
    });
    const rootOverlay = () =>
      buildTrainRevealOverlay(
        'soft',
        good('e2e4'),
        'e2e4',
        { uci: 'e2e4', quality: 'best' },
        { uci: 'c2c4', quality: 'good' },
        true,
      );

    it('dims a non-matching live arrow to the live-alt level (not onTop) and lights one that shares the focused squares', () => {
      const focused = buildChipFocusOverlay(
        rootOverlay(),
        ['c2c4'],
        [liveArrow('d2d4', 1), liveArrow('c2c4', 2)],
      );
      const live = focused.arrows.filter((a) => a.layerKey?.startsWith('live-alt-'));
      const d2d4 = live.find((a) => squaresOf(a) === 'd2d4');
      const c2c4 = live.find((a) => squaresOf(a) === 'c2c4');
      expect(d2d4).toMatchObject({ opacity: TRAIN_FOCUS_LIVE_ALT_DIM_OPACITY, onTop: false });
      expect(c2c4).toMatchObject({ opacity: TRAIN_FOCUS_ARROW_LIT_OPACITY, onTop: true });
    });

    it('returns the live arrows first, then the overlay arrows, and passes markers, alsoFineMoves and markerOwners through', () => {
      const overlay = rootOverlay();
      const focused = buildChipFocusOverlay(overlay, ['e2e4'], [liveArrow('d2d4', 1)]);
      expect(focused.arrows).toHaveLength(overlay.arrows.length + 1);
      expect(focused.arrows[0]?.layerKey).toBe('live-alt-1');
      expect(focused.alsoFineMoves).toEqual(overlay.alsoFineMoves);
      expect(focused.markerOwners).toEqual(overlay.markerOwners);
      expect(focused.markers.map((m) => m.square)).toEqual(overlay.markers.map((m) => m.square));
    });

    it('omitting the parameter is identical to the two-argument call and to an empty list', () => {
      const overlay = rootOverlay();
      expect(buildChipFocusOverlay(overlay, ['e2e4'], [])).toEqual(
        buildChipFocusOverlay(overlay, ['e2e4']),
      );
    });
  });
});

describe('chipArrowColor (Phase 237 UAT)', () => {
  it('matches the board arrow each chip focuses', () => {
    expect(chipArrowColor(['your', 'best'], 'best')).toBe(TRAIN_BEST_MOVE_ARROW);
    expect(chipArrowColor(['best', 'game'], 'best')).toBe(TRAIN_BEST_MOVE_ARROW);
    expect(chipArrowColor(['your'], 'blunder')).toBe(MOVE_QUALITY_BLUNDER);
    expect(chipArrowColor(['your', 'game'], 'mistake')).toBe(MOVE_QUALITY_MISTAKE);
    expect(chipArrowColor(['your'], null)).toBe(MOVE_QUALITY_GOOD);
    expect(chipArrowColor(['game'], 'inaccuracy')).toBe(NEXT_MOVE_ARROW);
  });
});

describe('trainRootMultiPvFloor (quick 261010-e5l)', () => {
  it('widens only a soft root to best + every alternative slot', () => {
    expect(TRAIN_LIVE_ALT_ROOT_MULTIPV).toBe(TRAIN_SOFT_TOTAL_ALT_MOVE_ARROWS + 1);
    expect(trainRootMultiPvFloor('soft')).toBe(TRAIN_LIVE_ALT_ROOT_MULTIPV);
    expect(trainRootMultiPvFloor('sharp')).toBe(0);
    expect(trainRootMultiPvFloor('herring')).toBe(0);
  });
});

describe('buildTrainLiveAlternativeArrows (quick 261010-e5l)', () => {
  const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  const BLACK_TO_MOVE_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';
  // White-POV cp of the top line; candidates are scored relative to it.
  const TOP_CP = 20;
  const GOOD_CP = 15;
  const INACCURACY_CP = -50;
  const MISTAKE_CP = -100;
  const BLUNDER_CP = -250;
  const TOP_MOVE = 'e2e4';
  const GOOD_MOVES = ['d2d4', 'g1f3', 'c2c4', 'b1c3', 'a2a3'];

  function line(multipv: number, firstMove: string, evalCp: number | null, depth = TRAIN_LIVE_ALT_MIN_DEPTH): PvLine {
    return { multipv, depth, moves: [firstMove], evalCp, evalMate: null };
  }
  function context(overrides: Partial<TrainLiveAlternativeContext> = {}): TrainLiveAlternativeContext {
    return {
      puzzleType: 'soft',
      puzzleFen: START_FEN,
      bestMoveUci: TOP_MOVE,
      playedMoveUci: null,
      drawnAlternatives: [],
      ...overrides,
    };
  }
  function goodLines(count: number): PvLine[] {
    return [
      line(1, TOP_MOVE, TOP_CP),
      ...GOOD_MOVES.slice(0, count - 1).map((move, i) => line(i + 2, move, GOOD_CP)),
    ];
  }
  /** Classification of a white-POV candidate against the top, white to move. */
  function severityOf(candidateCp: number) {
    return classifyLiveSeverity(
      evalToExpectedScore(TOP_CP, null, 'white'),
      evalToExpectedScore(candidateCp, null, 'white'),
    );
  }
  const ucisOf = (arrows: { startSquare: string; endSquare: string }[]) =>
    arrows.map((a) => `${a.startSquare}${a.endSquare}`);

  it('draws a good rank-1 line as a translucent secondary with the live layerKey', () => {
    expect(severityOf(GOOD_CP)).toBeNull();
    const arrows = buildTrainLiveAlternativeArrows(context(), goodLines(2));
    expect(arrows).toEqual([
      {
        startSquare: 'd2',
        endSquare: 'd4',
        color: STOCKFISH_SECONDARY_LINE,
        width: TRAIN_BEST_MOVE_ARROW_WIDTH,
        layerKey: 'live-alt-1',
      },
    ]);
  });

  it('never draws an inaccuracy, mistake or blunder and lets a later good line take the slot', () => {
    expect(severityOf(INACCURACY_CP)).toBe('inaccuracy');
    expect(severityOf(MISTAKE_CP)).toBe('mistake');
    expect(severityOf(BLUNDER_CP)).toBe('blunder');
    const lines = [
      line(1, TOP_MOVE, TOP_CP),
      line(2, 'd2d4', INACCURACY_CP),
      line(3, 'g1f3', MISTAKE_CP),
      line(4, 'c2c4', BLUNDER_CP),
    ];
    expect(buildTrainLiveAlternativeArrows(context(), lines)).toEqual([]);
    const withGood = [...lines.slice(0, 2), line(3, 'g1f3', GOOD_CP), line(4, 'c2c4', BLUNDER_CP)];
    expect(ucisOf(buildTrainLiveAlternativeArrows(context(), withGood))).toEqual(['g1f3']);
  });

  it('gates on depth inclusively, for the candidate and for the top line', () => {
    const shallow = TRAIN_LIVE_ALT_MIN_DEPTH - 1;
    const lines = [
      line(1, TOP_MOVE, TOP_CP),
      line(2, 'd2d4', GOOD_CP, shallow),
      line(3, 'g1f3', GOOD_CP, TRAIN_LIVE_ALT_MIN_DEPTH),
    ];
    expect(ucisOf(buildTrainLiveAlternativeArrows(context(), lines))).toEqual(['g1f3']);
    const shallowTop = [line(1, TOP_MOVE, TOP_CP, shallow), ...lines.slice(1)];
    expect(buildTrainLiveAlternativeArrows(context(), shallowTop)).toEqual([]);
    expect(buildTrainLiveAlternativeArrows(context(), goodLines(3))).toHaveLength(2);
  });

  it('caps the total at TRAIN_SOFT_TOTAL_ALT_MOVE_ARROWS including drawn server alternatives', () => {
    const lines = goodLines(GOOD_MOVES.length + 1);
    const none = buildTrainLiveAlternativeArrows(context(), lines);
    expect(none).toHaveLength(TRAIN_SOFT_TOTAL_ALT_MOVE_ARROWS);
    expect(ucisOf(none)).toEqual(GOOD_MOVES.slice(0, TRAIN_SOFT_TOTAL_ALT_MOVE_ARROWS));
    const withServer = buildTrainLiveAlternativeArrows(
      context({ drawnAlternatives: [{ uci: 'h2h3', quality: 'good' }] }),
      lines,
    );
    expect(withServer).toHaveLength(TRAIN_SOFT_TOTAL_ALT_MOVE_ARROWS - 1);
  });

  it('skips moves equal to best, played, a drawn server alternative or an earlier live line without consuming a slot', () => {
    const lines = [
      line(1, 'a2a3', TOP_CP),
      line(2, 'e2e4', GOOD_CP), // best
      line(3, 'd2d4q', GOOD_CP), // played, promotion-suffix variant of the same squares
      line(4, 'g1f3', GOOD_CP), // drawn server alternative
      line(5, 'c2c4', GOOD_CP),
      line(6, 'c2c4q', GOOD_CP), // same squares as the earlier live line
      line(7, 'b1c3', GOOD_CP),
    ];
    const arrows = buildTrainLiveAlternativeArrows(
      context({
        bestMoveUci: 'e2e4',
        playedMoveUci: 'd2d4',
        drawnAlternatives: [{ uci: 'g1f3', quality: 'good' }],
      }),
      lines,
    );
    expect(ucisOf(arrows)).toEqual(['c2c4', 'b1c3']);
  });

  it('draws nothing for sharp and herring puzzles', () => {
    expect(buildTrainLiveAlternativeArrows(context({ puzzleType: 'sharp' }), goodLines(4))).toEqual([]);
    expect(buildTrainLiveAlternativeArrows(context({ puzzleType: 'herring' }), goodLines(4))).toEqual([]);
  });

  it('never throws on empty, unscored or malformed input', () => {
    expect(buildTrainLiveAlternativeArrows(context(), [])).toEqual([]);
    expect(buildTrainLiveAlternativeArrows(context(), [line(1, TOP_MOVE, null)])).toEqual([]);
    const unscoredCandidate = [line(1, TOP_MOVE, TOP_CP), line(2, 'd2d4', null)];
    expect(buildTrainLiveAlternativeArrows(context(), unscoredCandidate)).toEqual([]);
    const malformed = [line(1, TOP_MOVE, TOP_CP), line(2, 'd2', GOOD_CP), { ...line(3, 'x', GOOD_CP), moves: [] }];
    expect(buildTrainLiveAlternativeArrows(context(), malformed)).toEqual([]);
  });

  it('judges candidates from the mover point of view (black to move)', () => {
    const blackTop = -TOP_CP; // white-POV: good for black
    const badForBlack = 100; // white-POV +cp is bad for black
    const nearEqual = blackTop + 5;
    const esTop = evalToExpectedScore(blackTop, null, 'black');
    expect(classifyLiveSeverity(esTop, evalToExpectedScore(badForBlack, null, 'black'))).not.toBeNull();
    expect(classifyLiveSeverity(esTop, evalToExpectedScore(nearEqual, null, 'black'))).toBeNull();
    const lines = [
      line(1, 'e7e5', blackTop),
      line(2, 'd7d5', badForBlack),
      line(3, 'c7c5', nearEqual),
    ];
    const arrows = buildTrainLiveAlternativeArrows(
      context({ puzzleFen: BLACK_TO_MOVE_FEN, bestMoveUci: 'e7e5' }),
      lines,
    );
    expect(ucisOf(arrows)).toEqual(['c7c5']);
  });
});
