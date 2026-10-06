/**
 * leaderboardMedalsDemoData — client-side fixtures for the admin "Leaderboard
 * medals demo" (Phase 231). Typed as the real wire types so tsc catches drift
 * from the backend schema. No API call, no query hook: the demo renders the
 * production TrainLeaderboardCardView and MedalClaimDialog from these objects.
 */
import type {
  LeaderboardBoard,
  LeaderboardBoardKind,
  LeaderboardLastWeek,
  LeaderboardMedals,
  LeaderboardRow,
  TrainLeaderboardResponse,
  UnclaimedMedal,
} from '@/types/train';

export type BoardScenarioId =
  | 'tallies-none'
  | 'tallies-one-type'
  | 'tallies-all-three'
  | 'long-names'
  | 'tentative-tally'
  | 'anonymous-tally'
  | 'podium-tie'
  | 'podium-deleted-user'
  | 'podium-viewer'
  | 'finished-12';
export type CelebrateScenarioId =
  | 'gold-points'
  | 'silver-points'
  | 'bronze-points'
  | 'gold-accuracy'
  | 'gold-points-bronze-accuracy'
  | 'three-weeks'
  | 'shared-gold';

/** Fixed countdown shown in the demo card header (2 days, 3 hours). */
export const DEMO_REMAINING_SECONDS = 2 * 86400 + 3 * 3600;

const DEMO_WEEK_START = '2026-10-05';
const DEMO_WEEK_END = '2026-10-12';
const DEMO_LAST_WEEK_START = '2026-09-28';
const DEMO_WEEK_BEFORE_LAST_START = '2026-09-21';
const DEMO_THIRD_WEEK_START = '2026-09-14';

/** Viewer's finishing rank in the 'finished-12' scenario (outside the podium). */
const DEMO_FINISHED_RANK = 12;
/** A 30+ character name, to check truncation and wrapping at 375 px. */
const LONG_NAME_A = 'GrandmasterOfTheLongUsernameAlpha';
const LONG_NAME_B = 'AnotherExtremelyLongPlayerNameBravo';
const LONG_NAME_C = 'YetAnotherVeryLongHandleCharlie01';

const NO_MEDALS: LeaderboardMedals = { gold: 0, silver: 0, bronze: 0 };

function row(rank: number | null, name: string, value: number, puzzles: number, medals: Partial<LeaderboardMedals> = {}): LeaderboardRow {
  return {
    rank,
    name,
    value,
    puzzles,
    tentative: false,
    is_viewer: false,
    visibility: 'public',
    gap_before: false,
    gap_after: false,
    medals: { ...NO_MEDALS, ...medals },
  };
}

function viewerRow(rank: number | null, name: string, value: number, puzzles: number, medals: Partial<LeaderboardMedals> = {}): LeaderboardRow {
  return { ...row(rank, name, value, puzzles, medals), is_viewer: true };
}

function emptyBoard(): LeaderboardBoard {
  return { rows: [], viewer: null, pass_target: null, last_week: null };
}

function lastWeek(podium: LeaderboardLastWeek['podium'], viewerFinalRank: number | null = null): LeaderboardLastWeek {
  return { week_start: DEMO_LAST_WEEK_START, podium, viewer_final_rank: viewerFinalRank };
}

function response(points: LeaderboardBoard, accuracy: LeaderboardBoard = emptyBoard()): TrainLeaderboardResponse {
  return {
    week_start: DEMO_WEEK_START,
    week_end: DEMO_WEEK_END,
    seconds_remaining: DEMO_REMAINING_SECONDS,
    points,
    accuracy,
  };
}

export const DEMO_BOARD_SCENARIOS: Record<
  BoardScenarioId,
  { label: string; tab: LeaderboardBoardKind; data: TrainLeaderboardResponse }
> = {
  'tallies-none': {
    label: 'Tallies: none',
    tab: 'points',
    data: response({
      rows: [row(1, 'alice', 320, 22), row(2, 'bob', 280, 19), row(3, 'carol', 240, 17)],
      viewer: null,
      pass_target: null,
      last_week: null,
    }),
  },
  'tallies-one-type': {
    label: 'Tallies: one type',
    tab: 'points',
    data: response({
      rows: [row(1, 'alice', 320, 22, { gold: 3 }), row(2, 'bob', 280, 19), row(3, 'carol', 240, 17)],
      viewer: null,
      pass_target: null,
      last_week: null,
    }),
  },
  'tallies-all-three': {
    label: 'Tallies: all three, two digits',
    tab: 'points',
    data: response({
      rows: [
        row(1, 'alice', 320, 22, { gold: 12, silver: 10, bronze: 11 }),
        row(2, 'bob', 280, 19, { gold: 1, silver: 2, bronze: 3 }),
        row(3, 'carol', 240, 17),
      ],
      viewer: null,
      pass_target: null,
      last_week: null,
    }),
  },
  'long-names': {
    label: 'Long names',
    tab: 'points',
    data: response({
      rows: [
        row(1, LONG_NAME_A, 620, 41, { gold: 4, silver: 2, bronze: 1 }),
        row(2, LONG_NAME_B, 480, 33, { silver: 3 }),
        row(3, LONG_NAME_C, 390, 28, { gold: 1, bronze: 5 }),
      ],
      viewer: null,
      pass_target: null,
      last_week: lastWeek([
        { medal: 'gold', name: LONG_NAME_A, is_viewer: false },
        { medal: 'silver', name: LONG_NAME_B, is_viewer: false },
        { medal: 'bronze', name: LONG_NAME_C, is_viewer: false },
      ]),
    }),
  },
  'tentative-tally': {
    label: 'Tentative row with a tally',
    tab: 'accuracy',
    data: response(emptyBoard(), {
      rows: [
        row(1, 'alice', 91, 44, { gold: 2 }),
        { ...row(null, 'bob', 96, 8, { silver: 1 }), tentative: true },
      ],
      viewer: null,
      pass_target: null,
      last_week: null,
    }),
  },
  'anonymous-tally': {
    label: 'Anonymous with a tally',
    tab: 'points',
    data: response({
      rows: [row(1, 'Anonymous', 410, 30, { gold: 2, bronze: 1 }), row(2, 'bob', 350, 26), row(3, 'carol', 300, 21)],
      viewer: null,
      pass_target: null,
      last_week: null,
    }),
  },
  'podium-tie': {
    label: 'Podium with a tie',
    tab: 'points',
    data: response({
      rows: [
        row(1, 'alice', 540, 38, { gold: 2, silver: 1 }),
        row(2, 'bob', 498, 31, { gold: 1 }),
        row(3, 'carol', 455, 29, { bronze: 2 }),
      ],
      viewer: null,
      pass_target: null,
      last_week: lastWeek([
        { medal: 'gold', name: 'alice', is_viewer: false },
        { medal: 'gold', name: 'bob', is_viewer: false },
        { medal: 'bronze', name: 'carol', is_viewer: false },
      ]),
    }),
  },
  'podium-deleted-user': {
    label: 'Podium with a deleted user',
    tab: 'points',
    data: response({
      rows: [row(1, 'bob', 498, 31, { gold: 1 }), row(2, 'carol', 455, 29), row(3, 'dave', 410, 25)],
      viewer: null,
      pass_target: null,
      last_week: lastWeek([
        { medal: 'gold', name: 'Deleted user', is_viewer: false },
        { medal: 'silver', name: 'bob', is_viewer: false },
        { medal: 'bronze', name: 'carol', is_viewer: false },
      ]),
    }),
  },
  'podium-viewer': {
    label: "Viewer on last week's podium",
    tab: 'points',
    data: response({
      rows: [
        viewerRow(1, 'You', 540, 38, { silver: 1 }),
        row(2, 'alice', 498, 31, { gold: 2 }),
        row(3, 'carol', 455, 29),
      ],
      viewer: { rank: 1, rank_without_session: null, tentative: false, puzzles_to_qualify: 0, visibility: 'public' },
      pass_target: null,
      last_week: lastWeek([
        { medal: 'gold', name: 'alice', is_viewer: false },
        { medal: 'silver', name: 'You', is_viewer: true },
        { medal: 'bronze', name: 'carol', is_viewer: false },
      ]),
    }),
  },
  'finished-12': {
    label: 'Viewer finished #12 last week',
    tab: 'points',
    data: response({
      rows: [
        row(1, 'alice', 540, 38, { gold: 2 }),
        row(2, 'bob', 498, 31),
        viewerRow(3, 'You', 455, 29),
      ],
      viewer: { rank: 3, rank_without_session: null, tentative: false, puzzles_to_qualify: 0, visibility: 'public' },
      pass_target: { name: 'bob', points_needed: 43 },
      last_week: lastWeek(
        [
          { medal: 'gold', name: 'alice', is_viewer: false },
          { medal: 'silver', name: 'bob', is_viewer: false },
          { medal: 'bronze', name: 'carol', is_viewer: false },
        ],
        DEMO_FINISHED_RANK,
      ),
    }),
  },
};

export const DEMO_CELEBRATE_SCENARIOS: Record<CelebrateScenarioId, { label: string; medals: UnclaimedMedal[] }> = {
  'gold-points': {
    label: 'Gold, Points',
    medals: [{ week_start: DEMO_LAST_WEEK_START, board: 'points', medal: 'gold', value: 412, shared: false }],
  },
  'silver-points': {
    label: 'Silver, Points',
    medals: [{ week_start: DEMO_LAST_WEEK_START, board: 'points', medal: 'silver', value: 388, shared: false }],
  },
  'bronze-points': {
    label: 'Bronze, Points',
    medals: [{ week_start: DEMO_LAST_WEEK_START, board: 'points', medal: 'bronze', value: 301, shared: false }],
  },
  'gold-accuracy': {
    label: 'Gold, Accuracy',
    medals: [{ week_start: DEMO_LAST_WEEK_START, board: 'accuracy', medal: 'gold', value: 94, shared: false }],
  },
  'gold-points-bronze-accuracy': {
    label: 'Gold Points + bronze Accuracy',
    medals: [
      { week_start: DEMO_LAST_WEEK_START, board: 'points', medal: 'gold', value: 412, shared: false },
      { week_start: DEMO_LAST_WEEK_START, board: 'accuracy', medal: 'bronze', value: 87, shared: false },
    ],
  },
  'three-weeks': {
    label: 'Three weeks',
    medals: [
      { week_start: DEMO_LAST_WEEK_START, board: 'points', medal: 'gold', value: 412, shared: false },
      { week_start: DEMO_WEEK_BEFORE_LAST_START, board: 'accuracy', medal: 'silver', value: 91, shared: false },
      { week_start: DEMO_THIRD_WEEK_START, board: 'points', medal: 'bronze', value: 301, shared: false },
    ],
  },
  'shared-gold': {
    label: 'Shared gold',
    medals: [{ week_start: DEMO_LAST_WEEK_START, board: 'points', medal: 'gold', value: 412, shared: true }],
  },
};
