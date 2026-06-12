/**
 * Shared "no engine analysis" copy, kept in a component-free module so it can be
 * imported by both the badge tooltips and the full-width empty state without
 * tripping react-refresh's only-export-components rule.
 *
 * Used verbatim across three surfaces:
 * - per-game NoAnalysisState pill tooltip,
 * - FlawDenominatorPill coverage-badge tooltip (FlawStatsPanel),
 * - full-width Flaws-tab empty state (NoEngineAnalysisFlawsState).
 */
export const ANALYSIS_COVERAGE_PARAGRAPHS: readonly string[] = [
  'Flaw analysis requires full Stockfish game analysis. Full Stockfish analysis is currently available only for games imported from Lichess that have been analyzed already.',
  'FlawChess currently performs only partial Stockfish analysis of game phase transitions. Full analysis of chess.com games on FlawChess is coming soon.',
];

/** The same copy as a popover body (two stacked paragraphs) for the badge tooltips. */
export const ANALYSIS_COVERAGE_COPY = (
  <div className="space-y-2">
    {ANALYSIS_COVERAGE_PARAGRAPHS.map((para) => (
      <p key={para}>{para}</p>
    ))}
  </div>
);
