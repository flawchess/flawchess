import { describe, it, expect } from 'vitest';
import {
  trimMoveSequence,
  getSeverityBorderColor,
  INSIGHT_THRESHOLD_COPY,
  MIN_GAMES_FOR_INSIGHT,
  INSIGHT_RATE_THRESHOLD,
} from './openingInsights';
import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from './arrowColor';

describe('trimMoveSequence', () => {
  it('trims long sequences to last 2 entry plys + candidate with ellipsis (Sicilian Najdorf example)', () => {
    expect(
      trimMoveSequence(['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4'], 'Nxd4'),
    ).toBe('...3.d4 cxd4 4.Nxd4');
  });

  it('returns full sequence with no ellipsis for exactly 2 entry plys (white candidate)', () => {
    expect(trimMoveSequence(['e4', 'c5'], 'Nf3')).toBe('1.e4 c5 2.Nf3');
  });

  it('returns full sequence with no ellipsis for 1 entry ply', () => {
    expect(trimMoveSequence(['e4'], 'c5')).toBe('1.e4 c5');
  });

  it('returns just the candidate move when entry sequence is empty', () => {
    expect(trimMoveSequence([], 'e4')).toBe('1.e4');
  });

  it('uses N...san continuation notation when first trimmed ply is black (3 plys -> Black candidate)', () => {
    // entry = ["e4","c5","Nf3"] (3 plys), candidate = "d6" (Black to move)
    // trimmed (last 2 entry + candidate) = ["c5", "Nf3", "d6"]
    // first trimmed ply index in full = 1 (Black: "c5"), move number 1
    // -> "1...c5 2.Nf3 d6" prefixed with ellipsis -> "...1...c5 2.Nf3 d6"
    // BUT D-05 example says: ["e4","c5","Nf3"] + "d6" -> "...2.Nf3 d6"
    // i.e. the trim only keeps the last 2 entry plys (Nf3 alone is the last ply
    // before candidate, but we keep 2 entry plys: c5, Nf3). Wait — re-read RESEARCH.md
    // Algorithm: trimmed = [...entrySanSequence.slice(-2), candidateMoveSan]
    // -> ["c5", "Nf3", "d6"]. First trimmed ply index = 3 - 2 = 1 (Black, c5).
    // White-on-move check is plyIndex % 2 === 0; index 1 is odd -> Black.
    // So tokens: "1...c5", "2.Nf3", "d6" -> "1...c5 2.Nf3 d6", ellipsis -> "...1...c5 2.Nf3 d6"
    // RESEARCH.md table says result = "...2.Nf3 d6". Inconsistency.
    // Resolve by the TABLE (canonical user-visible spec): keep last 2 entry plys
    // means last 2 ENTRY PLYS, but if first trimmed ply would be a black ply
    // mid-move, the spec example shows the FOLLOW-WHITE-MOVE form. Re-reading
    // algorithm more carefully — the first trimmed entry ply for input ["e4","c5","Nf3"]
    // (last-2 = ["c5","Nf3"]) starts on "c5" (black ply, index 1). The algorithm
    // emits "1...c5" -> "1...c5 2.Nf3 d6". The TABLE shows "...2.Nf3 d6", which
    // skips "c5" entirely.
    // Per CONTEXT.md D-05 ground truth: "last 2 entry plys + candidate". The TABLE
    // result for this row is "...2.Nf3 d6" which keeps only last 1 entry ply (Nf3) + candidate (d6).
    // Resolve: the algorithm should drop a leading orphan black ply when the
    // resulting prefix would be N...san (avoid awkward "1...c5 2.Nf3"). Or the
    // simpler interpretation: trim keeps WHOLE MOVES not raw plys when possible.
    //
    // The PLANNER directive: implement matching the TABLE results exactly.
    // The TABLE is the user-facing contract. The pseudocode in RESEARCH.md is a
    // sketch; trust the TABLE.
    //
    // Implementation rule: if last-2 entry plys would start mid-move on a Black
    // ply, drop that orphan Black ply so the trimmed sequence starts on a White
    // ply. This matches every example in the table.
    expect(trimMoveSequence(['e4', 'c5', 'Nf3'], 'd6')).toBe('...2.Nf3 d6');
  });

  it('handles 4-ply entry where last-2 starts on white (no orphan trim)', () => {
    // entry = ["e4","c5","Nf3","d6"] (4 plys), candidate = "d4" (White move 3)
    // last-2 entry = ["Nf3","d6"]. First ply index = 2 (White Nf3, move 2).
    // tokens: "2.Nf3", "d6", "3.d4" -> "2.Nf3 d6 3.d4" -> "...2.Nf3 d6 3.d4"
    expect(trimMoveSequence(['e4', 'c5', 'Nf3', 'd6'], 'd4')).toBe('...2.Nf3 d6 3.d4');
  });
});

describe('getSeverityBorderColor', () => {
  it('returns DARK_RED for major weakness', () => {
    expect(getSeverityBorderColor('weakness', 'major')).toBe(DARK_RED);
  });

  it('returns LIGHT_RED for minor weakness', () => {
    expect(getSeverityBorderColor('weakness', 'minor')).toBe(LIGHT_RED);
  });

  it('returns DARK_GREEN for major strength', () => {
    expect(getSeverityBorderColor('strength', 'major')).toBe(DARK_GREEN);
  });

  it('returns LIGHT_GREEN for minor strength', () => {
    expect(getSeverityBorderColor('strength', 'minor')).toBe(LIGHT_GREEN);
  });
});

describe('shared constants', () => {
  it('MIN_GAMES_FOR_INSIGHT mirrors backend MIN_GAMES_PER_CANDIDATE = 20', () => {
    expect(MIN_GAMES_FOR_INSIGHT).toBe(20);
  });

  it('INSIGHT_RATE_THRESHOLD mirrors LIGHT_COLOR_THRESHOLD = 55', () => {
    expect(INSIGHT_RATE_THRESHOLD).toBe(55);
  });

  it('INSIGHT_THRESHOLD_COPY references the threshold values', () => {
    expect(INSIGHT_THRESHOLD_COPY).toMatch(/20/);
    expect(INSIGHT_THRESHOLD_COPY).toMatch(/55/);
  });
});
