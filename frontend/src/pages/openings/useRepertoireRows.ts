import { useMemo } from 'react';
import { sanArrayToPgn } from '@/lib/pgn';
import { stripEcoSuffix } from '@/lib/openingVerdict';
import type { ConfidenceLevel } from '@/lib/scoreConfidence';
import type { BookmarkPhaseEntryItem, MostPlayedOpeningsResponse, OpeningWDL } from '@/types/stats';
import type {
  BookmarkTimeSeries,
  PositionBookmarkResponse,
  TimeSeriesResponse,
} from '@/types/position_bookmarks';

const PERCENT_SCALE = 100;

export type RepertoireRowKind = 'bookmark' | 'current' | 'past';

/** One repertoire card, whether it comes from a bookmark or from the most-played list. */
export interface RepertoireRowModel {
  /** Stable React key and testid source; never the opening name (names repeat without ECO). */
  key: string;
  kind: RepertoireRowKind;
  color: 'white' | 'black';
  /** Display name without the ECO suffix. */
  name: string;
  moveLine: string;
  fen: string;
  fullHash: string;
  bookmark: PositionBookmarkResponse | null;
  games: number;
  wins: number;
  draws: number;
  losses: number;
  winPct: number;
  drawPct: number;
  lossPct: number;
  lastPlayedAt: string | null;
  isCurrent: boolean;
  score: number;
  scoreConfidence: ConfidenceLevel;
  scorePValue: number | null;
  scoreCi99Low: number | null;
  scoreCi99High: number | null;
  avgEvalPawns: number | null;
  evalN: number;
  evalConfidence: ConfidenceLevel;
  evalPValue: number | null;
  evalCi99Low: number | null;
  evalCi99High: number | null;
  /** The bookmark's score-over-time series; null for most-played rows. */
  series: BookmarkTimeSeries | null;
}

interface UseRepertoireRowsParams {
  color: 'white' | 'black';
  mostPlayedData: MostPlayedOpeningsResponse | undefined;
  bookmarks: PositionBookmarkResponse[];
  tsData: TimeSeriesResponse | undefined;
  bookmarkPhaseEntryByHash: Map<string, BookmarkPhaseEntryItem>;
}

interface UseRepertoireRowsResult {
  bookmarkRows: RepertoireRowModel[];
  currentRows: RepertoireRowModel[];
  pastRows: RepertoireRowModel[];
}

function pct(count: number, total: number): number {
  return total > 0 ? (count / total) * PERCENT_SCALE : 0;
}

function mostPlayedRow(
  opening: OpeningWDL,
  color: 'white' | 'black',
  kind: 'current' | 'past',
): RepertoireRowModel {
  return {
    key: `mpo-${opening.full_hash}`,
    kind,
    color,
    // display_name, never label: label carries the ECO code (no ECO in the table).
    name: stripEcoSuffix(opening.display_name),
    moveLine: opening.pgn,
    fen: opening.fen,
    fullHash: opening.full_hash,
    bookmark: null,
    games: opening.total,
    wins: opening.wins,
    draws: opening.draws,
    losses: opening.losses,
    winPct: opening.win_pct,
    drawPct: opening.draw_pct,
    lossPct: opening.loss_pct,
    lastPlayedAt: opening.last_played_at ?? null,
    isCurrent: opening.is_current,
    score: opening.score,
    scoreConfidence: opening.score_confidence,
    scorePValue: opening.score_p_value,
    scoreCi99Low: opening.score_ci99_low,
    scoreCi99High: opening.score_ci99_high,
    avgEvalPawns: opening.avg_eval_pawns ?? null,
    evalN: opening.eval_n,
    evalConfidence: opening.eval_confidence,
    evalPValue: opening.eval_p_value ?? null,
    evalCi99Low: opening.eval_ci99_low_pawns ?? null,
    evalCi99High: opening.eval_ci99_high_pawns ?? null,
    series: null,
  };
}

function bookmarkRow(
  bookmark: PositionBookmarkResponse,
  color: 'white' | 'black',
  series: BookmarkTimeSeries,
  phaseEntry: BookmarkPhaseEntryItem | undefined,
): RepertoireRowModel {
  return {
    key: `bookmark-${bookmark.id}`,
    kind: 'bookmark',
    color,
    name: stripEcoSuffix(bookmark.label),
    moveLine: sanArrayToPgn(bookmark.moves),
    fen: bookmark.fen,
    fullHash: bookmark.target_hash,
    bookmark,
    games: series.total_games,
    wins: series.total_wins,
    draws: series.total_draws,
    losses: series.total_losses,
    winPct: pct(series.total_wins, series.total_games),
    drawPct: pct(series.total_draws, series.total_games),
    lossPct: pct(series.total_losses, series.total_games),
    lastPlayedAt: series.last_played_at ?? null,
    isCurrent: series.is_current,
    // Score verdict inputs are server-side (D-18), identical to the most-played rows.
    score: series.score,
    scoreConfidence: series.score_confidence,
    scorePValue: series.score_p_value,
    scoreCi99Low: series.score_ci99_low,
    scoreCi99High: series.score_ci99_high,
    avgEvalPawns: phaseEntry?.avg_eval_pawns ?? null,
    evalN: phaseEntry?.eval_n ?? 0,
    evalConfidence: phaseEntry?.eval_confidence ?? 'low',
    evalPValue: phaseEntry?.eval_p_value ?? null,
    evalCi99Low: phaseEntry?.eval_ci99_low_pawns ?? null,
    evalCi99High: phaseEntry?.eval_ci99_high_pawns ?? null,
    series,
  };
}

/**
 * Bookmarks of the colour that have games under the active filters, biggest first. A bookmark
 * with no colour never reaches either table. Bookmarks are never capped or dropped (D-06).
 */
function buildBookmarkRows(
  color: 'white' | 'black',
  bookmarks: PositionBookmarkResponse[],
  tsData: TimeSeriesResponse | undefined,
  phaseEntryByHash: Map<string, BookmarkPhaseEntryItem>,
): RepertoireRowModel[] {
  const seriesById = new Map<number, BookmarkTimeSeries>(
    (tsData?.series ?? []).map((s) => [s.bookmark_id, s]),
  );
  return bookmarks
    .filter((b) => b.color === color)
    .flatMap((b) => {
      const series = seriesById.get(b.id);
      if (!series || series.total_games <= 0) return [];
      return [bookmarkRow(b, color, series, phaseEntryByHash.get(b.target_hash))];
    })
    .sort((a, b) => b.games - a.games);
}

/**
 * View-model for the repertoire cards of one colour: pinned bookmarks, the current most-played
 * rows and the "Played before" rows. The backend already deduped, ordered and capped the
 * most-played lists and flags each row `is_current`, so this only maps and splits.
 */
export function useRepertoireRows({
  color,
  mostPlayedData,
  bookmarks,
  tsData,
  bookmarkPhaseEntryByHash,
}: UseRepertoireRowsParams): UseRepertoireRowsResult {
  return useMemo(() => {
    const openings = mostPlayedData?.[color] ?? [];
    return {
      bookmarkRows: buildBookmarkRows(color, bookmarks, tsData, bookmarkPhaseEntryByHash),
      currentRows: openings.filter((o) => o.is_current).map((o) => mostPlayedRow(o, color, 'current')),
      pastRows: openings.filter((o) => !o.is_current).map((o) => mostPlayedRow(o, color, 'past')),
    };
  }, [color, mostPlayedData, bookmarks, tsData, bookmarkPhaseEntryByHash]);
}
