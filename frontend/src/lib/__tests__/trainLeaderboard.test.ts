// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  DEFAULT_LEADERBOARD_MODE,
  DEFAULT_LEADERBOARD_TAB,
  LEADERBOARD_MODE_STORAGE_KEY,
  LEADERBOARD_TAB_STORAGE_KEY,
  ACCURACY_NOT_ENTERED_LINE,
  BLUNDER_CHECK_NOT_YET_QUALIFIED_DIVIDER_COPY,
  BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS,
  boardCountLabel,
  boardKindFor,
  boardValueLabel,
  firstUnrankedRowIndex,
  parseLeaderboardMode,
  parseLeaderboardTab,
  qualifyDividerCopy,
  readLeaderboardMode,
  sequenceCountLabel,
  writeLeaderboardMode,
  formatCountdown,
  NOT_YET_QUALIFIED_DIVIDER_COPY,
  puzzleCountLabel,
  rankLineCopy,
  remainingSeconds,
  readLeaderboardTab,
  scoreRankLines,
  viewerHint,
  writeLeaderboardTab,
} from '@/lib/trainLeaderboard';
import * as leaderboardLib from '@/lib/trainLeaderboard';
import type {
  LeaderboardBoard,
  LeaderboardRow,
  LeaderboardViewer,
  TrainLeaderboardResponse,
} from '@/types/train';

function rowWithRank(rank: number | null): LeaderboardRow {
  return {
    rank,
    name: 'someone',
    value: 50,
    puzzles: 5,
    tentative: rank === null,
    is_viewer: false,
    visibility: 'public',
    gap_before: false,
    gap_after: false,
    medals: { gold: 0, silver: 0, bronze: 0 },
  };
}

describe('firstUnrankedRowIndex', () => {
  it('returns the index of the first row with a null rank', () => {
    expect(firstUnrankedRowIndex([rowWithRank(1), rowWithRank(2), rowWithRank(null), rowWithRank(null)])).toBe(2);
  });

  it('returns -1 when every row is ranked', () => {
    expect(firstUnrankedRowIndex([rowWithRank(1), rowWithRank(2)])).toBe(-1);
  });

  it('returns 0 when every row is unranked', () => {
    expect(firstUnrankedRowIndex([rowWithRank(null), rowWithRank(null)])).toBe(0);
  });
});

describe('boardValueLabel', () => {
  it('suffixes points with pts', () => {
    expect(boardValueLabel('points', 12)).toBe('12 pts');
    expect(boardValueLabel('points', 0)).toBe('0 pts');
  });

  it('suffixes accuracy with a percent sign', () => {
    expect(boardValueLabel('accuracy', 89)).toBe('89%');
    expect(boardValueLabel('accuracy', 100)).toBe('100%');
  });
});

describe('puzzleCountLabel', () => {
  it('is singular for exactly one puzzle', () => {
    expect(puzzleCountLabel(1)).toBe('1 puzzle');
  });

  it('is plural otherwise', () => {
    expect(puzzleCountLabel(23)).toBe('23 puzzles');
    expect(puzzleCountLabel(0)).toBe('0 puzzles');
  });
});

describe('parseLeaderboardTab', () => {
  it.each(['points', 'accuracy'] as const)('passes %s through', (tab) => {
    expect(parseLeaderboardTab(tab)).toBe(tab);
  });

  it.each([null, '', 'Accuracy', 'bogus', ' points', 'POINTS'])('falls back to points for %j', (value) => {
    expect(parseLeaderboardTab(value)).toBe('points');
    expect(DEFAULT_LEADERBOARD_TAB).toBe('points');
  });
});

describe('readLeaderboardTab / writeLeaderboardTab', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('returns points when nothing is stored', () => {
    expect(readLeaderboardTab()).toBe('points');
  });

  it('round-trips the stored tab under the documented key', () => {
    writeLeaderboardTab('accuracy');
    expect(localStorage.getItem(LEADERBOARD_TAB_STORAGE_KEY)).toBe('accuracy');
    expect(LEADERBOARD_TAB_STORAGE_KEY).toBe('flawchess_train_leaderboard_tab');
    expect(readLeaderboardTab()).toBe('accuracy');
  });

  it('returns points for an unknown stored value', () => {
    localStorage.setItem(LEADERBOARD_TAB_STORAGE_KEY, 'skill');
    expect(readLeaderboardTab()).toBe('points');
  });

  it('returns points when getItem throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied');
    });
    expect(readLeaderboardTab()).toBe('points');
  });

  it('swallows a throwing setItem', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota');
    });
    expect(() => writeLeaderboardTab('accuracy')).not.toThrow();
  });
});

describe('qualifier copy', () => {
  it('the divider states the Accuracy threshold', () => {
    expect(NOT_YET_QUALIFIED_DIVIDER_COPY).toBe('Not yet qualified (20+ puzzles)');
  });
});

const VIEWER: LeaderboardViewer = {
  rank: 7,
  rank_without_session: null,
  tentative: false,
  puzzles_to_qualify: 0,
  visibility: 'public',
};
const EMPTY_BOARD: LeaderboardBoard = { rows: [], viewer: null, last_week: null };

function response(points: Partial<LeaderboardBoard>, accuracy: Partial<LeaderboardBoard>): TrainLeaderboardResponse {
  return {
    week_start: '2032-01-05',
    week_end: '2032-01-12',
    seconds_remaining: 1000,
    points: { ...EMPTY_BOARD, ...points },
    accuracy: { ...EMPTY_BOARD, ...accuracy },
    blunder_check_points: EMPTY_BOARD,
    blunder_check_score: EMPTY_BOARD,
  };
}

describe('viewerHint', () => {
  it('points: enter-hint when the viewer has no points entry', () => {
    const hint = viewerHint('points', response({}, {}));
    expect(hint?.id).toBe('enter-hint');
  });

  it('points: no hint for a viewer already on the board', () => {
    expect(viewerHint('points', response({ viewer: VIEWER }, {}))).toBeNull();
  });

  it('accuracy: no hint for a tentative viewer (the divider states the threshold)', () => {
    const tentative = { ...VIEWER, tentative: true, puzzles_to_qualify: 18 };
    const data = response({ viewer: VIEWER }, { viewer: tentative });
    expect(viewerHint('accuracy', data)).toBeNull();
  });

  it('accuracy: a specific not-on-this-board line when only the points viewer exists', () => {
    const hint = viewerHint('accuracy', response({ viewer: VIEWER }, {}));
    expect(hint?.id).toBe('accuracy-not-entered');
    expect(hint?.text).toContain("similarly rated players' blunders don't count");
    expect(hint?.text).not.toMatch(/\d/);
  });

  it('accuracy: enter-hint when neither board has the viewer', () => {
    expect(viewerHint('accuracy', response({}, {}))?.id).toBe('enter-hint');
  });

  it('accuracy: no hint for a qualified viewer', () => {
    expect(viewerHint('accuracy', response({ viewer: VIEWER }, { viewer: VIEWER }))).toBeNull();
  });
});

describe('copy never frames the board as ability', () => {
  it('lib source and helper copy contain no "skill"', () => {
    const copy = Object.values(leaderboardLib).filter((v): v is string => typeof v === 'string');
    for (const text of copy) expect(text.toLowerCase()).not.toContain('skill');
  });
});

describe('remainingSeconds (server remainder minus time since fetch)', () => {
  it('subtracts the whole seconds elapsed since the fetch', () => {
    expect(remainingSeconds(388800, 1_000_000, 1_000_000 + 60_000)).toBe(388740);
  });

  it('drops a partial second of elapsed time', () => {
    expect(remainingSeconds(100, 1_000_000, 1_000_000 + 1_999)).toBe(99);
  });

  it('never returns below zero', () => {
    expect(remainingSeconds(30, 1_000_000, 1_000_000 + 10 * 60_000)).toBe(0);
    expect(remainingSeconds(0, 1_000_000, 1_000_000)).toBe(0);
  });

  it('treats a clock reading before the fetch as no elapsed time', () => {
    expect(remainingSeconds(500, 1_000_000, 990_000)).toBe(500);
  });
});

describe('formatCountdown', () => {
  it.each([
    [388800, 'ends in 4d 12h'],
    [100800, 'ends in 1d 4h'],
    [15120, 'ends in 4h 12m'],
    [720, 'ends in 12m'],
    [30, 'ends in 1m'],
    [0, 'ending now'],
    [-5, 'ending now'],
  ])('formats %i seconds as %s', (seconds, expected) => {
    expect(formatCountdown(seconds)).toBe(expected);
  });
});

describe('private row labels', () => {
  it('uses the hidden-row and guest-row wording', () => {
    expect(leaderboardLib.HIDDEN_FROM_OTHERS_LABEL).toBe('Hidden from others');
    expect(leaderboardLib.GUEST_ROW_LABEL).toBe('You (guest)');
  });
});

describe('rankLineCopy, public viewers', () => {
  it('first entry of the week reads "#N this week"', () => {
    expect(rankLineCopy('points', { ...VIEWER, rank: 12, rank_without_session: null })).toBe(
      'Points board: #12 this week',
    );
    expect(rankLineCopy('accuracy', { ...VIEWER, rank: 3, rank_without_session: null })).toBe(
      'Accuracy: #3 this week',
    );
  });

  it('an improvement reads "#N (up M)"', () => {
    expect(rankLineCopy('points', { ...VIEWER, rank: 4, rank_without_session: 7 })).toBe(
      'Points board: #4 (up 3)',
    );
  });

  it('an unchanged rank is the plain rank with no delta', () => {
    expect(rankLineCopy('points', { ...VIEWER, rank: 4, rank_without_session: 4 })).toBe(
      'Points board: #4',
    );
  });
});

describe('scoreRankLines (public viewers)', () => {
  it('returns a points and an accuracy line from the viewers', () => {
    const data = response(
      { viewer: { ...VIEWER, rank: 4, rank_without_session: 7 } },
      { viewer: { ...VIEWER, rank: 2, rank_without_session: 2 } },
    );
    expect(scoreRankLines(data)).toEqual([
      { id: 'points', text: 'Points board: #4 (up 3)' },
      { id: 'accuracy', text: 'Accuracy: #2' },
    ]);
  });
});

describe('rankLineCopy, guest, tentative and worse-rank variants', () => {
  it('a guest gets the hypothetical line with no delta', () => {
    const guest = { ...VIEWER, rank: 7, rank_without_session: 9, visibility: 'guest' as const };
    expect(rankLineCopy('points', guest)).toBe("Points board: You'd be #7");
  });

  it.each(['public', 'hidden', 'guest'] as const)(
    'an unranked tentative Accuracy viewer (%s) reads "N more to qualify"',
    (visibility) => {
      const viewer = {
        ...VIEWER,
        rank: null,
        rank_without_session: 3,
        tentative: true,
        puzzles_to_qualify: 8,
        visibility,
      };
      expect(rankLineCopy('accuracy', viewer)).toBe('Accuracy: 8 more to qualify');
    },
  );

  it('a qualified Accuracy improvement reads "(up N)" and a first entry reads "this week"', () => {
    expect(rankLineCopy('accuracy', { ...VIEWER, rank: 4, rank_without_session: 6 })).toBe('Accuracy: #4 (up 2)');
    // Also what a session that just crossed the 20-puzzle cutoff reads.
    expect(rankLineCopy('accuracy', { ...VIEWER, rank: 3, rank_without_session: null })).toBe(
      'Accuracy: #3 this week',
    );
  });

  it('a worse Accuracy rank after the session shows the plain rank and never "down"', () => {
    const viewer = { ...VIEWER, rank: 5, rank_without_session: 3 };
    const text = rankLineCopy('accuracy', viewer);
    expect(text).toBe('Accuracy: #5');
    expect(text.toLowerCase()).not.toContain('down');
  });

  it('no rank line ever contains the word tentative', () => {
    expect(rankLineCopy('accuracy', { ...VIEWER, rank: 4, rank_without_session: 4 })).not.toContain('tentative');
    expect(
      rankLineCopy('accuracy', { ...VIEWER, rank: null, tentative: true, puzzles_to_qualify: 8 }),
    ).not.toContain('tentative');
    // Points rows are never tentative on the wire, but even a stray flag must not leak.
    expect(rankLineCopy('points', { ...VIEWER, rank: 4, rank_without_session: 4, tentative: true })).not.toContain(
      'tentative',
    );
  });
});

describe('scoreRankLines, not-entered and hidden rules', () => {
  it('a Points viewer with no Accuracy viewer gets the not-entered line', () => {
    const lines = scoreRankLines(response({ viewer: VIEWER }, {}));
    expect(lines).toEqual([
      { id: 'points', text: 'Points board: #7 this week' },
      {
        id: 'accuracy',
        text: 'Accuracy: not ranked',
        info: "You're not on this board yet: similarly rated players' blunders don't count here.",
      },
    ]);
    expect(ACCURACY_NOT_ENTERED_LINE).toBe('Accuracy: not ranked');
  });

  it('both viewers null gives no lines', () => {
    expect(scoreRankLines(response({}, {}))).toEqual([]);
  });

  it('a hidden Points viewer adds a final "Hidden from others" line', () => {
    const lines = scoreRankLines(response({ viewer: { ...VIEWER, visibility: 'hidden' } }, {}));
    expect(lines[lines.length - 1]).toEqual({ id: 'hidden', text: 'Hidden from others' });
  });

  it('a public viewer gets no hidden line', () => {
    expect(scoreRankLines(response({ viewer: VIEWER }, {})).some((l) => l.id === 'hidden')).toBe(false);
  });
});

describe('Blunder check board helpers (Phase 251)', () => {
  it('boardValueLabel: points boards read pts, percent boards read %', () => {
    expect(boardValueLabel('blunder_check_points', 96)).toBe('96 pts');
    expect(boardValueLabel('blunder_check_score', 91)).toBe('91%');
  });

  it('count labels name puzzles on puzzle boards and sequences on Blunder check boards', () => {
    expect(sequenceCountLabel(1)).toBe('1 sequence');
    expect(sequenceCountLabel(23)).toBe('23 sequences');
    expect(boardCountLabel('points', 2)).toBe('2 puzzles');
    expect(boardCountLabel('accuracy', 1)).toBe('1 puzzle');
    expect(boardCountLabel('blunder_check_points', 2)).toBe('2 sequences');
    expect(boardCountLabel('blunder_check_score', 1)).toBe('1 sequence');
  });

  it('boardKindFor maps (mode, slot) to the board', () => {
    expect(boardKindFor('puzzles', 'points')).toBe('points');
    expect(boardKindFor('puzzles', 'accuracy')).toBe('accuracy');
    expect(boardKindFor('blunder_check', 'points')).toBe('blunder_check_points');
    expect(boardKindFor('blunder_check', 'accuracy')).toBe('blunder_check_score');
  });

  it('mirrors the backend 18-window Score % threshold (BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS)', () => {
    // Parity with app/services/train_leaderboard.py, pinned there by
    // test_bc_board_qualify_constant_is_eighteen_windows: change both or neither.
    expect(BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS).toBe(18);
    expect(BLUNDER_CHECK_NOT_YET_QUALIFIED_DIVIDER_COPY).toBe('Not yet qualified (18+ sequences)');
  });

  it('qualifyDividerCopy: puzzles say puzzles, Score % says sequences', () => {
    expect(qualifyDividerCopy('accuracy')).toBe(NOT_YET_QUALIFIED_DIVIDER_COPY);
    expect(qualifyDividerCopy('blunder_check_score')).toBe(BLUNDER_CHECK_NOT_YET_QUALIFIED_DIVIDER_COPY);
  });

  it('viewerHint: Blunder check boards get their own invitation, and none once the viewer is on the board', () => {
    const empty = response({}, {});
    expect(viewerHint('blunder_check_points', empty)?.text).toContain('Blunder check');
    expect(viewerHint('blunder_check_score', empty)?.id).toBe('enter-hint');
    const onBoard = { ...empty, blunder_check_points: { ...EMPTY_BOARD, viewer: VIEWER } };
    expect(viewerHint('blunder_check_points', onBoard)).toBeNull();
    // A puzzle-board viewer never changes the Blunder check hint.
    const puzzleOnly = response({ viewer: VIEWER }, { viewer: VIEWER });
    expect(viewerHint('blunder_check_score', puzzleOnly)?.id).toBe('enter-hint');
  });
});

describe('parseLeaderboardMode / readLeaderboardMode / writeLeaderboardMode', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it.each(['puzzles', 'blunder_check'] as const)('passes %s through', (mode) => {
    expect(parseLeaderboardMode(mode)).toBe(mode);
  });

  it.each([null, '', 'Puzzles', 'blunder-check', 'points', ' puzzles'])('falls back to puzzles for %j', (value) => {
    expect(parseLeaderboardMode(value)).toBe('puzzles');
    expect(DEFAULT_LEADERBOARD_MODE).toBe('puzzles');
  });

  it('round-trips under the documented key, separate from the tab key', () => {
    expect(readLeaderboardMode()).toBe('puzzles');
    writeLeaderboardMode('blunder_check');
    expect(LEADERBOARD_MODE_STORAGE_KEY).toBe('flawchess_train_leaderboard_mode');
    expect(localStorage.getItem(LEADERBOARD_MODE_STORAGE_KEY)).toBe('blunder_check');
    expect(localStorage.getItem(LEADERBOARD_TAB_STORAGE_KEY)).toBeNull();
    expect(readLeaderboardMode()).toBe('blunder_check');
  });

  it('returns puzzles for an unknown stored value and when getItem throws', () => {
    localStorage.setItem(LEADERBOARD_MODE_STORAGE_KEY, 'chess960');
    expect(readLeaderboardMode()).toBe('puzzles');
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied');
    });
    expect(readLeaderboardMode()).toBe('puzzles');
  });

  it('swallows a throwing setItem', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota');
    });
    expect(() => writeLeaderboardMode('blunder_check')).not.toThrow();
  });
});
