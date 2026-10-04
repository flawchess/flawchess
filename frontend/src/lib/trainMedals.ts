/**
 * trainMedals — pure copy and helpers for the weekly leaderboard medals
 * (Phase 231). No React import, so the rules are testable without a DOM.
 *
 * Copy rule (D-10 of Phase 230 carries over): medals record effort and
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

/** Lead-in of the podium line at the top of each tab (D-09). */
export const LAST_WEEK_PODIUM_LABEL = 'Last week:';

/** Display order of medal types in a tally: best first. */
export const MEDAL_KIND_ORDER: readonly MedalKind[] = ['gold', 'silver', 'bronze'];

/** Board name used in the tally's accessible label. */
export const BOARD_LABEL: Record<LeaderboardBoardKind, string> = {
  points: 'Points',
  accuracy: 'Accuracy',
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

/** The viewer's own finish last week, for a non-medal row (D-03). */
export function lastWeekFinishCopy(rank: number): string {
  return `You finished #${rank} last week`;
}

/** Label of the dialog's primary button; the tap is also the audio-unlock gesture (D-13). */
export const CLAIM_BUTTON_LABEL = 'Claim';

/** Delay between consecutive medals' pop-in animation in the claim dialog (D-11). */
export const MEDAL_POP_STAGGER_MS = 120;

/** 'You won a medal!' / 'You won 3 medals!' (D-11). */
export function medalDialogTitle(count: number): string {
  return count === 1 ? 'You won a medal!' : `You won ${count} medals!`;
}

/** 'Gold, Points' / 'Gold, Points (shared)' when another user holds the same medal. */
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
