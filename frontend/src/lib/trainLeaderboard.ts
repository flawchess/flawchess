/**
 * trainLeaderboard — pure helpers and copy for the weekly Train leaderboard
 * card. No React import, so the rules are testable without a DOM.
 *
 * Copy rule: the boards measure effort and consistency, never ability.
 * Nothing in this file frames a rank as a measure of how good someone is.
 */
import type {
  LeaderboardBoardKind,
  LeaderboardRow,
  LeaderboardViewer,
  TrainLeaderboardResponse,
} from '@/types/train';

/** localStorage key for the remembered board tab (first or second board of the mode). */
export const LEADERBOARD_TAB_STORAGE_KEY = 'flawchess_train_leaderboard_tab';
/** localStorage key for the remembered mode (browser only, D-24). */
export const LEADERBOARD_MODE_STORAGE_KEY = 'flawchess_train_leaderboard_mode';

/** Which game mode the card shows: the puzzle boards or the Blunder check boards. */
export type LeaderboardMode = 'puzzles' | 'blunder_check';

/**
 * The board slot inside a mode: 'points' is the first board, 'accuracy' the
 * second (Accuracy for puzzles, Score % for Blunder check). One stored value
 * serves both modes, so the name stays 'accuracy' for the second slot.
 */
export type LeaderboardTab = 'points' | 'accuracy';

/** The tab shown on a first visit, and the fallback for any storage trouble. */
export const DEFAULT_LEADERBOARD_TAB: LeaderboardTab = 'points';
/** The mode shown on a first visit, and the fallback for any storage trouble. */
export const DEFAULT_LEADERBOARD_MODE: LeaderboardMode = 'puzzles';

/** (mode, slot) to the board it shows. */
const BOARD_KIND_BY_MODE: Record<LeaderboardMode, Record<LeaderboardTab, LeaderboardBoardKind>> = {
  puzzles: { points: 'points', accuracy: 'accuracy' },
  blunder_check: { points: 'blunder_check_points', accuracy: 'blunder_check_score' },
};

/** The board kind shown for a mode and slot. */
export function boardKindFor(mode: LeaderboardMode, tab: LeaderboardTab): LeaderboardBoardKind {
  return BOARD_KIND_BY_MODE[mode][tab];
}

/**
 * Accuracy board entry threshold. Mirrors ACCURACY_QUALIFY_MIN_PUZZLES in
 * app/services/train_leaderboard.py, pinned by a parity test in
 * tests/services/test_train_leaderboard.py.
 */
export const ACCURACY_QUALIFY_MIN_PUZZLES = 20;

/**
 * Blunder check Score % entry threshold, counted in ended sequences (windows).
 * Mirrors BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS in app/services/train_leaderboard.py,
 * pinned there by test_bc_board_qualify_constant_is_eighteen_windows and here by
 * trainLeaderboard.test.ts.
 */
export const BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS = 18;

/** Header info popover: what each board rewards (wording: effort and care, never ability). */
export const LEADERBOARD_INFO_POINTS_COPY = 'Points mainly rewards how many puzzles you solve.';
export const LEADERBOARD_INFO_ACCURACY_COPY =
  'Accuracy is your score across all puzzles this week: it rewards how carefully you solve. At equal accuracy, more puzzles ranks higher.';
export const LEADERBOARD_INFO_BLUNDER_CHECK_POINTS_COPY =
  'Points rewards how many Blunder check sequences you play.';
export const LEADERBOARD_INFO_BLUNDER_CHECK_SCORE_COPY =
  'Score % is your share of the points on offer this week. At equal Score %, more sequences ranks higher.';
export const LEADERBOARD_INFO_MEDALS_COPY =
  "The top 3 on each board win a medal every week. The icons next to a name show that player's medals on this board.";
/** Viewer has Points entries but no Accuracy entry: never a misleading count. */
export const ACCURACY_NOT_ENTERED_COPY =
  "You're not on this board yet: tactics puzzles don't count here.";
export const ACCURACY_EMPTY_COPY = 'No accuracy entries yet this week.';
export const EMPTY_WEEK_COPY = 'No one has trained yet this week. Be the first.';
export const ENTER_BOARD_HINT_COPY = "Solve a puzzle to enter this week's board.";
export const BLUNDER_CHECK_EMPTY_WEEK_COPY = 'No one has played Blunder check yet this week. Be the first.';
export const BLUNDER_CHECK_SCORE_EMPTY_COPY = 'No Score % entries yet this week.';
export const BLUNDER_CHECK_ENTER_BOARD_HINT_COPY = "Play a Blunder check sequence to enter this week's board.";

/** Divider label before the first unranked (tentative) Accuracy row. */
export const NOT_YET_QUALIFIED_DIVIDER_COPY = `Not yet qualified (${ACCURACY_QUALIFY_MIN_PUZZLES}+ puzzles)`;
/** Divider label before the first unranked (tentative) Score % row. */
export const BLUNDER_CHECK_NOT_YET_QUALIFIED_DIVIDER_COPY = `Not yet qualified (${BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS}+ sequences)`;

/** Shown under the board for guests, above the shared sign-up action pair. */
export const GUEST_CLAIM_SPOT_COPY = 'Sign up to claim your spot';

/** Label of each mode on the switch. */
export const MODE_LABEL: Record<LeaderboardMode, string> = {
  puzzles: 'Puzzles',
  blunder_check: 'Blunder check',
};

/** Label of each board tab, per board kind. */
export const BOARD_TAB_LABEL: Record<LeaderboardBoardKind, string> = {
  points: 'Points',
  accuracy: 'Accuracy',
  blunder_check_points: 'Points',
  blunder_check_score: 'Score %',
};

/** Empty-board copy per board kind. */
export const EMPTY_BOARD_COPY: Record<LeaderboardBoardKind, string> = {
  points: EMPTY_WEEK_COPY,
  accuracy: ACCURACY_EMPTY_COPY,
  blunder_check_points: BLUNDER_CHECK_EMPTY_WEEK_COPY,
  blunder_check_score: BLUNDER_CHECK_SCORE_EMPTY_COPY,
};

/** Divider copy per board kind (only the qualifying boards ever show it). */
const QUALIFY_DIVIDER_COPY: Record<LeaderboardBoardKind, string> = {
  points: NOT_YET_QUALIFIED_DIVIDER_COPY,
  accuracy: NOT_YET_QUALIFIED_DIVIDER_COPY,
  blunder_check_points: BLUNDER_CHECK_NOT_YET_QUALIFIED_DIVIDER_COPY,
  blunder_check_score: BLUNDER_CHECK_NOT_YET_QUALIFIED_DIVIDER_COPY,
};

/** The "Not yet qualified (N+ units)" divider label of a board. */
export function qualifyDividerCopy(kind: LeaderboardBoardKind): string {
  return QUALIFY_DIVIDER_COPY[kind];
}

/** Value suffix per board: points boards read '12 pts', percent boards '89%'. */
const VALUE_SUFFIX: Record<LeaderboardBoardKind, string> = {
  points: ' pts',
  accuracy: '%',
  blunder_check_points: ' pts',
  blunder_check_score: '%',
};

/** '12 pts' on the Points boards, '89%' on Accuracy and Score %. */
export function boardValueLabel(kind: LeaderboardBoardKind, value: number): string {
  return `${value}${VALUE_SUFFIX[kind]}`;
}

/** '1 puzzle' / '23 puzzles'. */
export function puzzleCountLabel(puzzles: number): string {
  return `${puzzles} ${puzzles === 1 ? 'puzzle' : 'puzzles'}`;
}

/** '1 sequence' / '23 sequences'. */
export function sequenceCountLabel(sequences: number): string {
  return `${sequences} ${sequences === 1 ? 'sequence' : 'sequences'}`;
}

/** Row count label per board: puzzles on the puzzle boards, sequences on Blunder check. */
const COUNT_LABEL: Record<LeaderboardBoardKind, (count: number) => string> = {
  points: puzzleCountLabel,
  accuracy: puzzleCountLabel,
  blunder_check_points: sequenceCountLabel,
  blunder_check_score: sequenceCountLabel,
};

/** The accessible count label of one row. */
export function boardCountLabel(kind: LeaderboardBoardKind, count: number): string {
  return COUNT_LABEL[kind](count);
}

/**
 * Validates a stored tab value (the value is user-editable). Only
 * the two literals pass; anything else, including null, is the default tab.
 */
export function parseLeaderboardTab(value: string | null): LeaderboardTab {
  return value === 'points' || value === 'accuracy' ? value : DEFAULT_LEADERBOARD_TAB;
}

/** Reads the remembered tab. SSR or a throwing localStorage degrade to Points. */
export function readLeaderboardTab(): LeaderboardTab {
  if (typeof localStorage === 'undefined') return DEFAULT_LEADERBOARD_TAB;
  try {
    return parseLeaderboardTab(localStorage.getItem(LEADERBOARD_TAB_STORAGE_KEY));
  } catch {
    return DEFAULT_LEADERBOARD_TAB;
  }
}

/** Persists the tab. Silently no-ops on SSR or a storage throw (quota, Safari private mode). */
export function writeLeaderboardTab(tab: LeaderboardTab): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(LEADERBOARD_TAB_STORAGE_KEY, tab);
  } catch {
    // Degrade to "not remembered"; never crash the card.
  }
}

/**
 * Validates a stored mode (T-251-16: the value is user-editable). Only the two
 * literals pass; anything else, including null, is Puzzles.
 */
export function parseLeaderboardMode(value: string | null): LeaderboardMode {
  return value === 'puzzles' || value === 'blunder_check' ? value : DEFAULT_LEADERBOARD_MODE;
}

/** Reads the remembered mode. SSR or a throwing localStorage degrade to Puzzles. */
export function readLeaderboardMode(): LeaderboardMode {
  if (typeof localStorage === 'undefined') return DEFAULT_LEADERBOARD_MODE;
  try {
    return parseLeaderboardMode(localStorage.getItem(LEADERBOARD_MODE_STORAGE_KEY));
  } catch {
    return DEFAULT_LEADERBOARD_MODE;
  }
}

/** Persists the mode. Silently no-ops on SSR or a storage throw (quota, Safari private mode). */
export function writeLeaderboardMode(mode: LeaderboardMode): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(LEADERBOARD_MODE_STORAGE_KEY, mode);
  } catch {
    // Degrade to "not remembered"; never crash the card.
  }
}

/**
 * Index of the first unranked row (rank null), where the "Not yet qualified"
 * divider goes; -1 when every row is ranked.
 */
export function firstUnrankedRowIndex(rows: readonly LeaderboardRow[]): number {
  return rows.findIndex((row) => row.rank === null);
}

export type ViewerHintId = 'accuracy-not-entered' | 'enter-hint';

/** Hint line shown under a board for a viewer who is not on it yet. */
const ENTER_HINT_COPY: Record<LeaderboardBoardKind, string> = {
  points: ENTER_BOARD_HINT_COPY,
  accuracy: ENTER_BOARD_HINT_COPY,
  blunder_check_points: BLUNDER_CHECK_ENTER_BOARD_HINT_COPY,
  blunder_check_score: BLUNDER_CHECK_ENTER_BOARD_HINT_COPY,
};

/**
 * The one hint line under the active board, or null: only for a viewer who
 * is not on that board yet. A tentative Accuracy or Score % viewer gets no
 * hint: the "Not yet qualified" divider already states the threshold.
 */
export function viewerHint(
  kind: LeaderboardBoardKind,
  data: TrainLeaderboardResponse,
): { id: ViewerHintId; text: string } | null {
  // The response keys are the board kinds, so data[kind] is the active board.
  if (data[kind].viewer !== null) return null;
  // On the Points board but not on Accuracy: only tactics puzzles so far.
  if (kind === 'accuracy' && data.points.viewer !== null) {
    return { id: 'accuracy-not-entered', text: ACCURACY_NOT_ENTERED_COPY };
  }
  return { id: 'enter-hint', text: ENTER_HINT_COPY[kind] };
}

/** Label on the viewer's own private row when they opted out. */
export const HIDDEN_FROM_OTHERS_LABEL = 'Hidden from others';
/** Replaces the server name on a guest's ghost row. */
export const GUEST_ROW_LABEL = 'You (guest)';

export const MS_PER_SECOND = 1000;
export const SECONDS_PER_MINUTE = 60;
export const SECONDS_PER_HOUR = 3600;
export const SECONDS_PER_DAY = 86400;
/** The countdown shows minutes at best, so a one-minute tick is precise enough. */
export const COUNTDOWN_TICK_MS = 60_000;
/**
 * When the deadline refetch still returns the old week (it landed a moment
 * before the server's Monday reset), retry after this delay, at most
 * ROLLOVER_MAX_RETRIES times per week_end.
 */
export const ROLLOVER_RETRY_MS = 2_000;
export const ROLLOVER_MAX_RETRIES = 3;

/**
 * Seconds left to the deadline, derived from the SERVER's remainder minus the
 * time since that response was fetched. The client never does its own
 * week math: its clock and timezone are not the week's. Floored at 0, and a
 * clock reading before the fetch counts as no elapsed time.
 */
export function remainingSeconds(
  serverSecondsRemaining: number,
  fetchedAtMs: number,
  nowMs: number,
): number {
  const elapsedSeconds = Math.max(0, Math.floor((nowMs - fetchedAtMs) / MS_PER_SECOND));
  return Math.max(0, serverSecondsRemaining - elapsedSeconds);
}

/** 'ends in 1d 4h' / 'ends in 4h 12m' / 'ends in 12m' / 'ending now'. */
export function formatCountdown(seconds: number): string {
  if (seconds <= 0) return 'ending now';
  if (seconds >= SECONDS_PER_DAY) {
    const days = Math.floor(seconds / SECONDS_PER_DAY);
    const hours = Math.floor((seconds % SECONDS_PER_DAY) / SECONDS_PER_HOUR);
    return `ends in ${days}d ${hours}h`;
  }
  if (seconds >= SECONDS_PER_HOUR) {
    const hours = Math.floor(seconds / SECONDS_PER_HOUR);
    const minutes = Math.floor((seconds % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE);
    return `ends in ${hours}h ${minutes}m`;
  }
  // Under an hour: never show "0m" while time remains.
  return `ends in ${Math.max(1, Math.floor(seconds / SECONDS_PER_MINUTE))}m`;
}

/** Board label at the start of a score-screen rank line. */
const RANK_LINE_LABEL: Record<LeaderboardBoardKind, string> = {
  points: 'Points board',
  accuracy: 'Accuracy',
  blunder_check_points: 'Blunder check points',
  blunder_check_score: 'Blunder check score',
};

/** Viewer has Points entries but no Accuracy entry: never a count. */
export const ACCURACY_NOT_ENTERED_LINE = 'Accuracy: not ranked';

/**
 * One score-screen rank line for a board.
 *
 * - unranked (rank null, a tentative Accuracy viewer): "Accuracy: N more to
 *   qualify" from the server's puzzles_to_qualify. A tentative viewer never
 *   gets a numbered rank line or a "(tentative)" suffix. The wording names no
 *   solve type.
 * - guest: the hypothetical rank wording, no delta.
 * - first entry of the week: "#N this week".
 * - improvement: "#N (up M)".
 * - everything else, unchanged or worse: the plain "#N". Accuracy can get
 *   worse after a session because the average moved, and the screen never
 *   shows a downward delta; there is deliberately no "down" path.
 *
 * "(up N)" is only computed when both ranks are numbers: the server nulls
 * rank_without_session whenever the viewer is tentative without the session,
 * so a delta never spans the qualification cutoff.
 */
export function rankLineCopy(kind: LeaderboardBoardKind, viewer: LeaderboardViewer): string {
  const label = RANK_LINE_LABEL[kind];
  if (viewer.rank === null) return `${label}: ${viewer.puzzles_to_qualify} more to qualify`;
  const before = viewer.rank_without_session;
  if (viewer.visibility === 'guest') return `${label}: You'd be #${viewer.rank}`;
  if (before === null) return `${label}: #${viewer.rank} this week`;
  if (before > viewer.rank) return `${label}: #${viewer.rank} (up ${before - viewer.rank})`;
  return `${label}: #${viewer.rank}`;
}

export interface ScoreRankLine {
  id: 'points' | 'accuracy' | 'hidden';
  text: string;
  /** Explanation for an info popover beside the line. */
  info?: string;
}

/**
 * The score screen's rank lines: one per board the viewer is on, the specific
 * not-entered line when only tactics puzzles kept them off Accuracy,
 * and a closing "Hidden from others" for an opted-out viewer.
 */
export function scoreRankLines(data: TrainLeaderboardResponse): ScoreRankLine[] {
  const points = data.points.viewer;
  if (points === null && data.accuracy.viewer === null) return [];
  const lines: ScoreRankLine[] = [];
  if (points !== null) lines.push({ id: 'points', text: rankLineCopy('points', points) });
  const accuracy = data.accuracy.viewer;
  if (accuracy !== null) {
    lines.push({ id: 'accuracy', text: rankLineCopy('accuracy', accuracy) });
  } else {
    lines.push({ id: 'accuracy', text: ACCURACY_NOT_ENTERED_LINE, info: ACCURACY_NOT_ENTERED_COPY });
  }
  if (points?.visibility === 'hidden') lines.push({ id: 'hidden', text: HIDDEN_FROM_OTHERS_LABEL });
  return lines;
}
