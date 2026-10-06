// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  DEFAULT_LEADERBOARD_TAB,
  LEADERBOARD_TAB_STORAGE_KEY,
  ACCURACY_NOT_ENTERED_LINE,
  boardValueLabel,
  firstUnrankedRowIndex,
  parseLeaderboardTab,
  passTargetCopy,
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
    medals: { gold: 0, silver: 0, bronze: 0 },
  };
}

describe('firstUnrankedRowIndex (quick 261004-8rt)', () => {
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

describe('parseLeaderboardTab (D-09, T-230-10)', () => {
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

describe('qualifier and pass-target copy', () => {
  it('the divider states the Accuracy threshold', () => {
    expect(NOT_YET_QUALIFIED_DIVIDER_COPY).toBe('Not yet qualified (20+ puzzles)');
  });

  it('passTargetCopy is singular for 1 point', () => {
    expect(passTargetCopy({ name: 'magnus', points_needed: 1 })).toBe('1 point to pass magnus');
    expect(passTargetCopy({ name: 'magnus', points_needed: 5 })).toBe('5 points to pass magnus');
  });
});

const VIEWER: LeaderboardViewer = {
  rank: 7,
  rank_without_session: null,
  tentative: false,
  puzzles_to_qualify: 0,
  visibility: 'public',
};
const EMPTY_BOARD: LeaderboardBoard = { rows: [], viewer: null, pass_target: null, last_week: null };

function response(points: Partial<LeaderboardBoard>, accuracy: Partial<LeaderboardBoard>): TrainLeaderboardResponse {
  return {
    week_start: '2032-01-05',
    week_end: '2032-01-12',
    seconds_remaining: 1000,
    points: { ...EMPTY_BOARD, ...points },
    accuracy: { ...EMPTY_BOARD, ...accuracy },
  };
}

describe('viewerHint', () => {
  it('points: pass-target when the viewer has a pass target', () => {
    const data = response({ viewer: VIEWER, pass_target: { name: 'magnus', points_needed: 3 } }, {});
    expect(viewerHint('points', data)).toEqual({ id: 'pass-target', text: '3 points to pass magnus' });
  });

  it('points: enter-hint when the viewer has no points entry', () => {
    const hint = viewerHint('points', response({}, {}));
    expect(hint?.id).toBe('enter-hint');
  });

  it('points: no hint for a viewer already on top (no pass target)', () => {
    expect(viewerHint('points', response({ viewer: VIEWER }, {}))).toBeNull();
  });

  it('accuracy: no hint for a tentative viewer (the divider states the threshold)', () => {
    const tentative = { ...VIEWER, tentative: true, puzzles_to_qualify: 18 };
    const data = response({ viewer: VIEWER }, { viewer: tentative });
    expect(viewerHint('accuracy', data)).toBeNull();
  });

  it('accuracy: a specific not-on-this-board line when only the points viewer exists (D-19)', () => {
    const hint = viewerHint('accuracy', response({ viewer: VIEWER }, {}));
    expect(hint?.id).toBe('accuracy-not-entered');
    expect(hint?.text).toContain("tactics puzzles don't count");
    expect(hint?.text).not.toMatch(/\d/);
  });

  it('accuracy: enter-hint when neither board has the viewer', () => {
    expect(viewerHint('accuracy', response({}, {}))?.id).toBe('enter-hint');
  });

  it('accuracy: no hint for a qualified viewer', () => {
    expect(viewerHint('accuracy', response({ viewer: VIEWER }, { viewer: VIEWER }))).toBeNull();
  });
});

describe('copy never frames the board as ability (D-10)', () => {
  it('lib source and helper copy contain no "skill"', () => {
    const copy = Object.values(leaderboardLib).filter((v): v is string => typeof v === 'string');
    for (const text of copy) expect(text.toLowerCase()).not.toContain('skill');
  });
});

describe('remainingSeconds (D-02: server remainder minus time since fetch)', () => {
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
  it('uses the D-13 and D-14 wording', () => {
    expect(leaderboardLib.HIDDEN_FROM_OTHERS_LABEL).toBe('Hidden from others');
    expect(leaderboardLib.GUEST_ROW_LABEL).toBe('You (guest)');
  });
});

describe('rankLineCopy, public viewers (D-11, D-12)', () => {
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

describe('rankLineCopy, guest, tentative and worse-rank variants (D-11, D-17, D-18)', () => {
  it('a guest gets the hypothetical line with no delta (D-17)', () => {
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

  it('a worse Accuracy rank after the session shows the plain rank and never "down" (D-18)', () => {
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

describe('scoreRankLines, not-entered and hidden rules (D-13, D-19)', () => {
  it('a Points viewer with no Accuracy viewer gets the not-entered line (D-19)', () => {
    const lines = scoreRankLines(response({ viewer: VIEWER }, {}));
    expect(lines).toEqual([
      { id: 'points', text: 'Points board: #7 this week' },
      { id: 'accuracy', text: "Accuracy: not on this board yet (tactics puzzles don't count)" },
    ]);
    expect(ACCURACY_NOT_ENTERED_LINE).toBe("Accuracy: not on this board yet (tactics puzzles don't count)");
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
