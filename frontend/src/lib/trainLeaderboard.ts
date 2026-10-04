/**
 * trainLeaderboard — pure helpers and copy for the weekly Train leaderboard
 * card (Phase 230). No React import, so the rules are testable without a DOM.
 *
 * Copy rule (D-10): the boards measure effort and consistency, never ability.
 * Nothing in this file frames a rank as a measure of how good someone is.
 */
import type {
  LeaderboardBoardKind,
  LeaderboardPassTarget,
  LeaderboardViewer,
  TrainLeaderboardResponse,
} from '@/types/train';

/** localStorage key for the remembered tab (D-09). */
export const LEADERBOARD_TAB_STORAGE_KEY = 'flawchess_train_leaderboard_tab';

/** The tab shown on a first visit, and the fallback for any storage trouble. */
export const DEFAULT_LEADERBOARD_TAB: LeaderboardBoardKind = 'points';

/** Accuracy tab helper under the toggle (D-10 wording plus the D-19 caveat). */
export const ACCURACY_HELPER_COPY =
  "Average session score. Tactics puzzles don't count; 20+ puzzles to qualify.";
/** Viewer has Points entries but no Accuracy entry (D-19): never a misleading count. */
export const ACCURACY_NOT_ENTERED_COPY =
  "You're not on this board yet: tactics puzzles don't count here.";
export const ACCURACY_EMPTY_COPY = 'No accuracy entries yet this week.';
export const EMPTY_WEEK_COPY = 'No one has trained yet this week. Be the first.';
export const ENTER_BOARD_HINT_COPY = "Solve a puzzle to enter this week's board.";

/** Shown under the board for guests, above the shared sign-up action pair (D-14). */
export const GUEST_CLAIM_SPOT_COPY = 'Sign up to claim your spot';

/** '12 pts' on the Points board, '89%' on the Accuracy board. */
export function boardValueLabel(kind: LeaderboardBoardKind, value: number): string {
  return kind === 'points' ? `${value} pts` : `${value}%`;
}

/** '1 puzzle' / '23 puzzles'. */
export function puzzleCountLabel(puzzles: number): string {
  return `${puzzles} ${puzzles === 1 ? 'puzzle' : 'puzzles'}`;
}

/**
 * Validates a stored tab value (T-230-10: the value is user-editable). Only
 * the two literals pass; anything else, including null, is the default tab.
 */
export function parseLeaderboardTab(value: string | null): LeaderboardBoardKind {
  return value === 'points' || value === 'accuracy' ? value : DEFAULT_LEADERBOARD_TAB;
}

/** Reads the remembered tab. SSR or a throwing localStorage degrade to Points (D-09). */
export function readLeaderboardTab(): LeaderboardBoardKind {
  if (typeof localStorage === 'undefined') return DEFAULT_LEADERBOARD_TAB;
  try {
    return parseLeaderboardTab(localStorage.getItem(LEADERBOARD_TAB_STORAGE_KEY));
  } catch {
    return DEFAULT_LEADERBOARD_TAB;
  }
}

/** Persists the tab. Silently no-ops on SSR or a storage throw (quota, Safari private mode). */
export function writeLeaderboardTab(tab: LeaderboardBoardKind): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(LEADERBOARD_TAB_STORAGE_KEY, tab);
  } catch {
    // Degrade to "not remembered"; never crash the card.
  }
}

/** '1 more puzzle to qualify' / 'N more puzzles to qualify'. Never implies all solves count (D-19). */
export function puzzlesToQualifyCopy(n: number): string {
  return `${n} more ${n === 1 ? 'puzzle' : 'puzzles'} to qualify`;
}

/** '1 point to pass X' / 'N points to pass X'. */
export function passTargetCopy(target: LeaderboardPassTarget): string {
  const unit = target.points_needed === 1 ? 'point' : 'points';
  return `${target.points_needed} ${unit} to pass ${target.name}`;
}

export type ViewerHintId = 'pass-target' | 'qualify' | 'accuracy-not-entered' | 'enter-hint';

/**
 * The one hint line under the active board, or null. Every number comes from
 * the server (`puzzles_to_qualify`, `points_needed`); the client never counts
 * the viewer's solves itself (D-19).
 */
export function viewerHint(
  kind: LeaderboardBoardKind,
  data: TrainLeaderboardResponse,
): { id: ViewerHintId; text: string } | null {
  if (kind === 'points') return pointsHint(data);
  return accuracyHint(data);
}

function pointsHint(data: TrainLeaderboardResponse): { id: ViewerHintId; text: string } | null {
  if (data.points.viewer === null) return { id: 'enter-hint', text: ENTER_BOARD_HINT_COPY };
  if (data.points.pass_target !== null) {
    return { id: 'pass-target', text: passTargetCopy(data.points.pass_target) };
  }
  return null;
}

function accuracyHint(data: TrainLeaderboardResponse): { id: ViewerHintId; text: string } | null {
  const viewer = data.accuracy.viewer;
  if (viewer === null) {
    // On the Points board but not here: only tactics puzzles so far (D-19).
    return data.points.viewer !== null
      ? { id: 'accuracy-not-entered', text: ACCURACY_NOT_ENTERED_COPY }
      : { id: 'enter-hint', text: ENTER_BOARD_HINT_COPY };
  }
  if (viewer.tentative) {
    return { id: 'qualify', text: puzzlesToQualifyCopy(viewer.puzzles_to_qualify) };
  }
  return null;
}

/** Label on the viewer's own private row when they opted out (D-13). */
export const HIDDEN_FROM_OTHERS_LABEL = 'Hidden from others';
/** Replaces the server name on a guest's ghost row (D-14). */
export const GUEST_ROW_LABEL = 'You (guest)';

export const MS_PER_SECOND = 1000;
export const SECONDS_PER_MINUTE = 60;
export const SECONDS_PER_HOUR = 3600;
export const SECONDS_PER_DAY = 86400;
/** The countdown shows minutes at best, so a one-minute tick is precise enough. */
export const COUNTDOWN_TICK_MS = 60_000;
/**
 * WR-03 (phase 230 review): when the deadline refetch still returns the old
 * week (it landed a moment before the server's Monday reset), retry after this
 * delay, at most ROLLOVER_MAX_RETRIES times per week_end.
 */
export const ROLLOVER_RETRY_MS = 2_000;
export const ROLLOVER_MAX_RETRIES = 3;

/**
 * Seconds left to the deadline, derived from the SERVER's remainder minus the
 * time since that response was fetched (D-02). The client never does its own
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
};

/** Viewer has Points entries but no Accuracy entry (D-19): never a count. */
export const ACCURACY_NOT_ENTERED_LINE =
  "Accuracy: not on this board yet (tactics puzzles don't count)";

/** Only a tentative Accuracy ranking carries the suffix (D-11). */
function rankLineSuffix(kind: LeaderboardBoardKind, viewer: LeaderboardViewer): string {
  return kind === 'accuracy' && viewer.tentative ? ' (tentative)' : '';
}

/**
 * One score-screen rank line for a board (D-11, D-12, D-17, D-18).
 *
 * - guest: the hypothetical rank wording, no delta (D-17).
 * - first entry of the week: "#N this week".
 * - improvement: "#N (up M)".
 * - everything else, unchanged or worse: the plain "#N". D-18 (owner call):
 *   Accuracy can get worse after a session because the average moved, and the
 *   screen never shows a downward delta; there is deliberately no "down" path.
 */
export function rankLineCopy(kind: LeaderboardBoardKind, viewer: LeaderboardViewer): string {
  const label = RANK_LINE_LABEL[kind];
  const suffix = rankLineSuffix(kind, viewer);
  const before = viewer.rank_without_session;
  if (viewer.visibility === 'guest') return `${label}: You'd be #${viewer.rank}${suffix}`;
  if (before === null) return `${label}: #${viewer.rank} this week${suffix}`;
  if (before > viewer.rank) return `${label}: #${viewer.rank} (up ${before - viewer.rank})${suffix}`;
  return `${label}: #${viewer.rank}${suffix}`;
}

export interface ScoreRankLine {
  id: 'points' | 'accuracy' | 'hidden';
  text: string;
}

/**
 * The score screen's rank lines: one per board the viewer is on, the specific
 * not-entered line when only tactics puzzles kept them off Accuracy (D-19),
 * and a closing "Hidden from others" for an opted-out viewer (D-13).
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
    lines.push({ id: 'accuracy', text: ACCURACY_NOT_ENTERED_LINE });
  }
  if (points?.visibility === 'hidden') lines.push({ id: 'hidden', text: HIDDEN_FROM_OTHERS_LABEL });
  return lines;
}
