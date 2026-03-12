import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { useChessGame } from '@/hooks/useChessGame';
import { useAnalysis } from '@/hooks/useAnalysis';
import { ChessBoard } from '@/components/board/ChessBoard';
import { MoveList } from '@/components/board/MoveList';
import { BoardControls } from '@/components/board/BoardControls';
import { FilterPanel, DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import { WDLBar } from '@/components/results/WDLBar';
import { GameTable } from '@/components/results/GameTable';
import { ImportModal } from '@/components/import/ImportModal';
import { ImportProgress } from '@/components/import/ImportProgress';
import { apiClient } from '@/api/client';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { AnalysisResponse } from '@/types/api';

const PAGE_SIZE = 50;

export function DashboardPage() {
  const { logout } = useAuth();

  // Board state
  const chess = useChessGame();
  const [boardFlipped, setBoardFlipped] = useState(false);

  // Filter state
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  // Analysis state
  const analysis = useAnalysis();
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [analysisOffset, setAnalysisOffset] = useState(0);

  // Import state
  const [importOpen, setImportOpen] = useState(false);
  const [activeJobIds, setActiveJobIds] = useState<string[]>([]);

  // Total game count — fetched on load to drive empty-state messaging
  const { data: gameCountData, refetch: refetchGameCount } = useQuery<{ count: number }>({
    queryKey: ['gameCount'],
    queryFn: async () => {
      const response = await apiClient.get<{ count: number }>('/games/count');
      return response.data;
    },
    staleTime: 30_000,
  });
  const totalGames = gameCountData?.count ?? null;

  // ── Analyze ────────────────────────────────────────────────────────────────

  const handleAnalyze = useCallback(async () => {
    const request = {
      target_hash: chess.getHashForAnalysis(filters.matchSide),
      match_side: filters.matchSide,
      time_control: filters.timeControls,
      rated: filters.rated,
      recency: filters.recency,
      color: filters.color,
      offset: analysisOffset,
      limit: PAGE_SIZE,
    };
    try {
      const result = await analysis.mutateAsync(request);
      setAnalysisResult(result);
    } catch {
      // Error displayed via toast via axios interceptor
    }
  }, [chess, filters, analysis, analysisOffset]);

  const handlePageChange = useCallback(
    async (newOffset: number) => {
      setAnalysisOffset(newOffset);
      const request = {
        target_hash: chess.getHashForAnalysis(filters.matchSide),
        match_side: filters.matchSide,
        time_control: filters.timeControls,
        rated: filters.rated,
        recency: filters.recency,
        color: filters.color,
        offset: newOffset,
        limit: PAGE_SIZE,
      };
      try {
        const result = await analysis.mutateAsync(request);
        setAnalysisResult(result);
      } catch {
        // Error handled by axios interceptor
      }
    },
    [chess, filters, analysis],
  );

  const handleFiltersChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    setAnalysisOffset(0);
    // Don't auto-run analysis — user must click Analyze
  }, []);

  // ── Import ─────────────────────────────────────────────────────────────────

  const handleImportStarted = useCallback((jobId: string) => {
    setActiveJobIds((ids) => [...ids, jobId]);
  }, []);

  const handleJobDone = useCallback(
    (jobId: string) => {
      setActiveJobIds((ids) => ids.filter((id) => id !== jobId));
      // Refresh game count after import completes
      refetchGameCount();
    },
    [refetchGameCount],
  );

  // ── Derived ────────────────────────────────────────────────────────────────

  // User has zero imported games (known)
  const hasNoGames = totalGames !== null && totalGames === 0;
  // Analysis returned no results
  const analysisReturnedEmpty = analysisResult !== null && analysisResult.matched_count === 0;
  // Analysis returned no results and user has no games at all
  const noGamesAtAll = analysisReturnedEmpty && (totalGames === 0 || totalGames === null);
  // Analysis returned no results but user has games (filters are too narrow)
  const filtersMatchNothing = analysisReturnedEmpty && totalGames !== null && totalGames > 0;

  // ── Render ─────────────────────────────────────────────────────────────────

  const importButton = (
    <Button variant="outline" size="sm" onClick={() => setImportOpen(true)}>
      Import Games
    </Button>
  );

  const leftColumn = (
    <div className="flex flex-col gap-3">
      <ChessBoard
        position={chess.position}
        onPieceDrop={chess.makeMove}
        flipped={boardFlipped}
        lastMove={chess.lastMove}
      />
      {chess.openingName ? (
        <div className="flex items-baseline gap-2 px-1 text-sm">
          <span className="font-mono text-xs text-muted-foreground">{chess.openingName.eco}</span>
          <span className="text-foreground">{chess.openingName.name}</span>
        </div>
      ) : (
        <div className="h-5" />
      )}
      <MoveList
        moveHistory={chess.moveHistory}
        currentPly={chess.currentPly}
        onMoveClick={chess.goToMove}
      />
      <BoardControls
        onBack={chess.goBack}
        onForward={chess.goForward}
        onReset={chess.reset}
        onFlip={() => setBoardFlipped((f) => !f)}
        canGoBack={chess.currentPly > 0}
        canGoForward={chess.currentPly < chess.moveHistory.length}
      />

      <div className="mt-1">
        <FilterPanel filters={filters} onChange={handleFiltersChange} />
      </div>

      <Button
        onClick={handleAnalyze}
        disabled={analysis.isPending}
        className="w-full"
        size="lg"
      >
        {analysis.isPending ? 'Analyzing...' : 'Analyze'}
      </Button>
    </div>
  );

  const rightColumn = (
    <div className="flex flex-col gap-4">
      {analysisResult === null ? (
        /* Initial state: no analysis run yet */
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          {hasNoGames ? (
            /* New user with no games */
            <>
              <p className="mb-2 text-base font-medium text-foreground">No games imported yet</p>
              <p className="mb-6 text-sm text-muted-foreground">
                Import your games from chess.com or lichess to start analyzing positions.
              </p>
              {importButton}
            </>
          ) : (
            /* Has games (or count unknown) — show normal prompt */
            <>
              <p className="text-base text-muted-foreground">
                Play moves on the board and click Analyze to see your stats
              </p>
              {totalGames !== null && totalGames > 0 && (
                <p className="mt-2 text-xs text-muted-foreground">
                  {totalGames.toLocaleString()} games imported
                </p>
              )}
            </>
          )}
        </div>
      ) : noGamesAtAll ? (
        /* Ran analysis, 0 results, 0 total games */
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">No games imported yet</p>
          <p className="mb-6 text-sm text-muted-foreground">
            Import your games from chess.com or lichess to start analyzing positions.
          </p>
          {importButton}
        </div>
      ) : filtersMatchNothing ? (
        /* Has games but current filters matched nothing */
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center text-muted-foreground">
          <p className="text-base">No games matched the current filter settings.</p>
          <p className="mt-1 text-sm">Try adjusting the time control, rated, or recency filters.</p>
        </div>
      ) : (
        <>
          <WDLBar stats={analysisResult.stats} />
          <GameTable
            games={analysisResult.games}
            matchedCount={analysisResult.matched_count}
            totalGames={analysisResult.stats.total}
            offset={analysisOffset}
            limit={PAGE_SIZE}
            onPageChange={handlePageChange}
          />
        </>
      )}
    </div>
  );

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight text-foreground">Chessalytics</h1>
          <div className="flex items-center gap-2">
            {totalGames !== null && (
              <span className="hidden text-xs text-muted-foreground sm:block">
                {totalGames.toLocaleString()} games
              </span>
            )}
            <Button variant="outline" size="sm" onClick={() => setImportOpen(true)}>
              Import Games
            </Button>
            <Button variant="ghost" size="sm" onClick={logout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Body */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 md:px-6">
        {/* Desktop: two-column layout */}
        <div className="hidden md:grid md:grid-cols-[auto_1fr] md:gap-8 xl:grid-cols-[400px_1fr]">
          <div className="min-w-0">{leftColumn}</div>
          <div className="min-w-0">{rightColumn}</div>
        </div>

        {/* Mobile: single column */}
        <div className="md:hidden">{leftColumn}</div>
        <div className="mt-6 md:hidden">{rightColumn}</div>
      </main>

      {/* Import modal */}
      <ImportModal
        open={importOpen}
        onOpenChange={setImportOpen}
        onImportStarted={handleImportStarted}
      />

      {/* Import progress toasts */}
      <ImportProgress jobIds={activeJobIds} onJobDone={handleJobDone} />
    </div>
  );
}
