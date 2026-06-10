interface NoAnalysisStateProps {
  gameId: number;
}

/**
 * Dashed pill rendered when a game has no engine analysis (chess.com games or
 * lichess games without computer analysis). Replaces the entire severity row +
 * chips section. Per UI-SPEC §'"No engine analysis" state': never shows count
 * text — the schema enforces severity_counts=null for these games.
 */
export function NoAnalysisState({ gameId }: NoAnalysisStateProps) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-dashed px-3 py-1 text-sm font-bold text-muted-foreground bg-white/5"
      aria-label="No engine analysis available for this game"
      data-testid={`no-analysis-${gameId}`}
    >
      <span className="h-2 w-2 rounded-full border border-muted-foreground" />
      No Analysis
    </span>
  );
}
