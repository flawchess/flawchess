import { useCallback } from 'react';
import { useNavigate } from 'react-router';
import { pgnToSanArray } from '@/lib/pgn';
import { useReorderPositionBookmarks } from '@/hooks/usePositionBookmarks';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { MatchSide } from '@/types/api';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';
import type { OpeningInsightFinding } from '@/types/insights';
import type { OpeningsTab } from '@/types/openingsTab';
import type { HighlightedMove } from './useDeepLinkHighlight';

type ChessLike = {
  loadMoves: (sans: string[]) => void;
};

type SetFilters = (next: FilterState | ((prev: FilterState) => FilterState)) => void;

type UseOpeningsHandlersParams = {
  chess: ChessLike;
  navigate: ReturnType<typeof useNavigate>;
  activeTab: OpeningsTab;
  setBoardFlipped: (flipped: boolean) => void;
  setFilters: SetFilters;
  setHighlightedMove: (m: HighlightedMove | null) => void;
};

type OpeningsNavHandlers = {
  handleOpenChartBookmarkGames: (bookmark: PositionBookmarkResponse) => void;
  handleOpenGames: (pgn: string, color: 'white' | 'black') => void;
  handleOpenMoves: (pgn: string, color: 'white' | 'black') => void;
  handleOpenFinding: (finding: OpeningInsightFinding) => void;
  handleOpenFindingGames: (finding: OpeningInsightFinding) => void;
  handleLoadBookmark: (bkm: PositionBookmarkResponse) => void;
  handleReorder: (orderedIds: number[]) => void;
};

/**
 * Bundles the deep-link / open-from-{X} navigation callbacks used by
 * StatsTab (including its finding cards) and the bookmark sidebars. All handlers preserve the
 * original OpeningsPage behavior exactly:
 *  - mutate the chess board (loadMoves), update boardFlipped + filters, then
 *    navigate to the appropriate subtab and scroll to top.
 *  - handleOpenFinding additionally sets the deep-link highlight BEFORE
 *    navigation so MoveExplorer paints with the highlight on first render.
 */
export function useOpeningsHandlers(params: UseOpeningsHandlersParams): OpeningsNavHandlers {
  const {
    chess,
    navigate,
    activeTab,
    setBoardFlipped,
    setFilters,
    setHighlightedMove,
  } = params;
  const reorder = useReorderPositionBookmarks();

  const handleOpenChartBookmarkGames = useCallback((bookmark: PositionBookmarkResponse) => {
    // Chart entries are always real bookmarks (useOpeningsChartData filters the
    // bookmark list), so load unconditionally like handleLoadBookmark: an empty
    // moves list is a start-position bookmark, not a missing one.
    chess.loadMoves(bookmark.moves);
    const color = bookmark.color ?? 'white';
    setBoardFlipped(color === 'black');
    setFilters(prev => ({ ...prev, color, matchSide: bookmark.match_side }));
    navigate('/openings/games');
    window.scrollTo({ top: 0 });
  }, [chess, navigate, setFilters, setBoardFlipped]);

  const handleOpenGames = useCallback((pgn: string, color: 'white' | 'black') => {
    chess.loadMoves(pgnToSanArray(pgn));
    setBoardFlipped(color === 'black');
    setFilters(prev => ({ ...prev, color, matchSide: 'both' as MatchSide }));
    navigate('/openings/games');
    window.scrollTo({ top: 0 });
  }, [chess, navigate, setFilters, setBoardFlipped]);

  const handleOpenMoves = useCallback((pgn: string, color: 'white' | 'black') => {
    chess.loadMoves(pgnToSanArray(pgn));
    setBoardFlipped(color === 'black');
    setFilters(prev => ({ ...prev, color, matchSide: 'both' as MatchSide }));
    navigate('/openings/explorer');
    window.scrollTo({ top: 0 });
  }, [chess, navigate, setFilters, setBoardFlipped]);

  const handleOpenFinding = useCallback(
    (finding: OpeningInsightFinding) => {
      chess.loadMoves(finding.entry_san_sequence);
      // Set the deep-link highlight BEFORE navigation so MoveExplorer renders
      // with the highlight on its first paint after the route change.
      setHighlightedMove({ san: finding.candidate_move_san });
      setBoardFlipped(finding.color === 'black');
      setFilters((prev) => ({
        ...prev,
        color: finding.color,
        matchSide: 'both' as MatchSide,
      }));
      navigate('/openings/explorer');
      window.scrollTo({ top: 0 });
    },
    [chess, navigate, setFilters, setHighlightedMove, setBoardFlipped],
  );

  const handleOpenFindingGames = useCallback(
    (finding: OpeningInsightFinding) => {
      chess.loadMoves([...finding.entry_san_sequence, finding.candidate_move_san]);
      setBoardFlipped(finding.color === 'black');
      setFilters((prev) => ({
        ...prev,
        color: finding.color,
        matchSide: 'both' as MatchSide,
      }));
      navigate('/openings/games');
      window.scrollTo({ top: 0 });
    },
    [chess, navigate, setFilters, setBoardFlipped],
  );

  const handleLoadBookmark = useCallback((bkm: PositionBookmarkResponse) => {
    chess.loadMoves(bkm.moves);
    setBoardFlipped(bkm.is_flipped ?? false);
    setFilters(prev => ({ ...prev, color: bkm.color ?? 'white', matchSide: bkm.match_side }));
    if (activeTab !== 'explorer' && activeTab !== 'games') navigate('/openings/explorer');
    window.scrollTo({ top: 0 });
  }, [chess, setFilters, activeTab, navigate, setBoardFlipped]);

  const handleReorder = useCallback((orderedIds: number[]) => {
    reorder.mutate(orderedIds);
  }, [reorder]);

  return {
    handleOpenChartBookmarkGames,
    handleOpenGames,
    handleOpenMoves,
    handleOpenFinding,
    handleOpenFindingGames,
    handleLoadBookmark,
    handleReorder,
  };
}
