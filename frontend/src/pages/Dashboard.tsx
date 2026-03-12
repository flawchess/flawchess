import { useState, useCallback } from 'react';
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
import type { FilterState } from '@/components/filters/FilterPanel';
import type { AnalysisResponse } from '@/types/api';

const PAGE_SIZE = 50;

export function DashboardPage() {
  const { logout } = useAuth();

  // Board state
  const chess = useChessGame();

  // Filter state
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  // Analysis state
  const analysis = useAnalysis();
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [analysisOffset, setAnalysisOffset] = useState(0);

  // Import state
  const [importOpen, setImportOpen] = useState(false);
  const [activeJobIds, setActiveJobIds] = useState<string[]>([]);

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

  const handleJobDone = useCallback((jobId: string) => {
    setActiveJobIds((ids) => ids.filter((id) => id !== jobId));
  }, []);

  // ── Derived ────────────────────────────────────────────────────────────────

  const noGamesYet =
    analysisResult !== null &&
    analysisResult.stats.total === 0 &&
    analysisResult.matched_count === 0;

  // ── Render ─────────────────────────────────────────────────────────────────

  const leftColumn = (
    <div className="flex flex-col gap-3">
      <ChessBoard position={chess.position} onPieceDrop={chess.makeMove} />
      <MoveList
        moveHistory={chess.moveHistory}
        currentPly={chess.currentPly}
        onMoveClick={chess.goToMove}
      />
      <BoardControls
        onBack={chess.goBack}
        onForward={chess.goForward}
        onReset={chess.reset}
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
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center text-muted-foreground">
          <p className="text-base">Play moves on the board and click Analyze to see your stats</p>
        </div>
      ) : noGamesYet ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-4 text-muted-foreground">
            Import your games to start analyzing
          </p>
          <Button onClick={() => setImportOpen(true)}>Import Games</Button>
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
