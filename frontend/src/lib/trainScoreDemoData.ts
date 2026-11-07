/**
 * trainScoreDemoData — fixtures for the admin "Session feedback demo". Each
 * score scenario is one list of per-puzzle points, so the percentage and the
 * bubble's miss count derive from the same data and cannot disagree.
 */
import { aggregateSessionScore, type TrainMoveTier, type TrainSessionScore } from '@/lib/trainScore';
import type {
  LeaderboardBoard,
  LeaderboardViewer,
  LeaderboardVisibility,
  SolvedResult,
  TrainLeaderboardResponse,
} from '@/types/train';

/** The (guess, move) pair behind each per-puzzle score. */
const OUTCOME_BY_POINTS: Record<number, { correct_guess: boolean; move_quality: TrainMoveTier }> = {
  3: { correct_guess: true, move_quality: 'good' },
  2: { correct_guess: false, move_quality: 'good' },
  1: { correct_guess: false, move_quality: 'inaccuracy' },
  0: { correct_guess: false, move_quality: 'wrong' },
};
const FALLBACK_OUTCOME = { correct_guess: false, move_quality: 'wrong' } as const;

export const DEMO_SCORE_SCENARIO_IDS = ['perfect', 'strong', 'solid', 'tough'] as const;
export type ScoreScenarioId = (typeof DEMO_SCORE_SCENARIO_IDS)[number];

export interface ScoreScenario {
  label: string;
  score: TrainSessionScore;
  outcomes: SolvedResult[];
}

function scoreScenario(label: string, points: number[]): ScoreScenario {
  return {
    label,
    score: aggregateSessionScore(points),
    outcomes: points.map((value) => ({
      ...(OUTCOME_BY_POINTS[value] ?? FALLBACK_OUTCOME),
      source: 'sr_item',
      item_status: 'active',
      due_date: null,
    })),
  };
}

export const DEMO_SCORE_SCENARIOS: Record<ScoreScenarioId, ScoreScenario> = {
  perfect: scoreScenario('Perfect', [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]),
  strong: scoreScenario('Strong', [3, 3, 2, 3, 3, 1, 3, 3, 2, 3, 3, 1, 3, 2, 1]),
  solid: scoreScenario('Solid', [3, 2, 1, 3, 0, 2, 3, 1, 2, 3, 0, 2, 1, 3, 1]),
  tough: scoreScenario('Tough', [1, 0, 2, 0, 3, 1, 0, 0, 2, 1, 0, 3, 0, 1, 0]),
};

export const DEMO_NEXT_SESSION_SCENARIO_IDS = ['tomorrow', 'in-3-days', 'in-a-week'] as const;
export type NextSessionScenarioId = (typeof DEMO_NEXT_SESSION_SCENARIO_IDS)[number];

export const DEMO_NEXT_SESSION_SCENARIOS: Record<NextSessionScenarioId, { label: string; daysAhead: number }> = {
  tomorrow: { label: 'Next: tomorrow', daysAhead: 1 },
  'in-3-days': { label: 'Next: in 3 days', daysAhead: 3 },
  'in-a-week': { label: 'Next: in a week', daysAhead: 7 },
};

export const DEMO_RANK_SCENARIO_IDS = ['ranked', 'not-ranked', 'qualifying', 'hidden'] as const;
export type RankScenarioId = (typeof DEMO_RANK_SCENARIO_IDS)[number];

const DEMO_SECONDS_REMAINING = 200_000;

function viewer(
  rank: number | null,
  rankWithoutSession: number | null,
  overrides: { puzzlesToQualify?: number; visibility?: LeaderboardVisibility } = {},
): LeaderboardViewer {
  return {
    rank,
    rank_without_session: rankWithoutSession,
    tentative: rank === null,
    puzzles_to_qualify: overrides.puzzlesToQualify ?? 0,
    visibility: overrides.visibility ?? 'public',
  };
}

function board(boardViewer: LeaderboardViewer | null): LeaderboardBoard {
  return { rows: [], viewer: boardViewer, last_week: null };
}

function leaderboard(
  points: LeaderboardViewer | null,
  accuracy: LeaderboardViewer | null,
): TrainLeaderboardResponse {
  return {
    week_start: '2026-11-02',
    week_end: '2026-11-09',
    seconds_remaining: DEMO_SECONDS_REMAINING,
    points: board(points),
    accuracy: board(accuracy),
  };
}

export const DEMO_RANK_SCENARIOS: Record<RankScenarioId, { label: string; data: TrainLeaderboardResponse }> = {
  ranked: { label: 'Ranks: moved up', data: leaderboard(viewer(4, 7), viewer(15, 17)) },
  'not-ranked': { label: 'Ranks: accuracy not ranked', data: leaderboard(viewer(4, 7), null) },
  qualifying: {
    label: 'Ranks: accuracy qualifying',
    data: leaderboard(viewer(4, 7), viewer(null, null, { puzzlesToQualify: 5 })),
  },
  hidden: {
    label: 'Ranks: hidden',
    data: leaderboard(viewer(4, 7, { visibility: 'hidden' }), viewer(15, 17, { visibility: 'hidden' })),
  },
};
