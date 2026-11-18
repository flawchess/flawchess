/**
 * trainMedals — pure copy and helpers for the weekly leaderboard medals
 * No React import, so the rules are testable without a DOM.
 *
 * Copy rule (same as trainLeaderboard.ts): medals record effort and
 * consistency in a week, never ability.
 */
import { format, parseISO } from 'date-fns';
import type {
  LeaderboardBoardKind,
  LeaderboardMedals,
  MedalKey,
  MedalKind,
  UnclaimedMedal,
} from '@/types/train';

/** Screen-reader label per medal type. */
export const MEDAL_LABEL: Record<MedalKind, string> = {
  gold: 'Gold',
  silver: 'Silver',
  bronze: 'Bronze',
};

/** Lead-in of the last-week line below each board. */
export const LAST_WEEK_PODIUM_LABEL = 'Last week:';

/** Display order of medal types in a tally: best first. */
export const MEDAL_KIND_ORDER: readonly MedalKind[] = ['gold', 'silver', 'bronze'];

/**
 * Board name with its mode, used in the tally's accessible label and the claim
 * dialog's entries (D-15: one dialog holds medals of both modes, so each entry
 * names its mode and board).
 */
export const BOARD_LABEL: Record<LeaderboardBoardKind, string> = {
  points: 'Puzzles Points',
  accuracy: 'Puzzles Accuracy',
  blunder_check_points: 'Blunder check Points',
  blunder_check_score: 'Blunder check Score %',
};

/** Non-zero medal counts in gold, silver, bronze order; empty when the user has no medals. */
export function tallyEntries(medals: LeaderboardMedals): { kind: MedalKind; count: number }[] {
  return MEDAL_KIND_ORDER.map((kind) => ({ kind, count: medals[kind] })).filter((entry) => entry.count > 0);
}

/** '3 gold, 1 silver Points medals' / '1 gold Accuracy medal'. */
export function tallyAriaLabel(medals: LeaderboardMedals, board: LeaderboardBoardKind): string {
  const entries = tallyEntries(medals);
  const total = entries.reduce((sum, entry) => sum + entry.count, 0);
  const counts = entries.map((entry) => `${entry.count} ${entry.kind}`).join(', ');
  return `${counts} ${BOARD_LABEL[board]} ${total === 1 ? 'medal' : 'medals'}`;
}

/** The viewer's own finish on the last-week line, for a non-medal row. */
export function lastWeekFinishCopy(rank: number): string {
  return `You: #${rank}`;
}

/** Label of the dialog's primary button; the tap is also the audio-unlock gesture. */
export const CLAIM_BUTTON_LABEL = 'Claim';

/** Delay between consecutive medals' pop-in animation in the claim dialog. */
export const MEDAL_POP_STAGGER_MS = 120;

/** 'You won a medal!' / 'You won 3 medals!'. */
export function medalDialogTitle(count: number): string {
  return count === 1 ? 'You won a medal!' : `You won ${count} medals!`;
}

/** 'Gold, Puzzles Points' / 'Gold, Blunder check Score % (shared)' when another user holds the same medal. */
export function medalEntryLabel(medal: MedalKind, board: LeaderboardBoardKind, shared: boolean): string {
  return `${MEDAL_LABEL[medal]}, ${BOARD_LABEL[board]}${shared ? ' (shared)' : ''}`;
}

/**
 * 'Week of Sep 28' from the week's Monday. parseISO reads a date-only string
 * as LOCAL midnight; the Date constructor would read it as UTC midnight and
 * show the Sunday in the Americas.
 */
export function weekOfLabel(weekStart: string): string {
  return `Week of ${format(parseISO(weekStart), 'MMM d')}`;
}

/** The (week_start, board) keys of the shown medals, in order: the claim POST body. */
export function medalKeys(medals: readonly UnclaimedMedal[]): MedalKey[] {
  return medals.map((entry) => ({ week_start: entry.week_start, board: entry.board }));
}

/** One week's unclaimed medals, in the order the API sent them. */
export interface MedalWeekGroup {
  /** ISO date of the week's Monday (UTC). */
  weekStart: string;
  medals: UnclaimedMedal[];
}

/**
 * Groups unclaimed medals by week for the single claim dialog (D-15): newest
 * week first, and inside a week the API's board order (points, accuracy,
 * blunder-check points, blunder-check score). ISO dates sort as strings, so no
 * date parsing is needed; the sort is stable, so equal weeks keep API order.
 */
export function groupMedalsByWeek(medals: readonly UnclaimedMedal[]): MedalWeekGroup[] {
  const byWeek = new Map<string, UnclaimedMedal[]>();
  for (const entry of medals) {
    const group = byWeek.get(entry.week_start);
    if (group === undefined) byWeek.set(entry.week_start, [entry]);
    else group.push(entry);
  }
  return [...byWeek.entries()]
    .sort(([a], [b]) => (a < b ? 1 : a > b ? -1 : 0))
    .map(([weekStart, weekMedals]) => ({ weekStart, medals: weekMedals }));
}
