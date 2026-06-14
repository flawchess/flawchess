import { Cpu } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';

interface NoEngineAnalysisFlawsStateProps {
  /** Whether the current user is a guest (show sign-up CTA). */
  isGuest: boolean;
  /** Count of eval jobs currently in-flight for this user. */
  inFlightCount: number;
  /** Number of games already analyzed (for progress display when in-flight). */
  analyzedCount: number;
  /** Total games imported (for progress display when in-flight). */
  totalCount: number;
}

/**
 * Full-width message shown on the Flaws tab when the user has imported games
 * but none have analyzed flaws.
 *
 * Branches:
 * - Guest: sign-up CTA linking to /login?tab=register (D-118-13).
 * - Non-guest, in-flight: "Analyzing your games…" + "N of M analyzed" progress text.
 * - Non-guest, idle: passive explainer — analysis runs automatically in the
 *   background; points to the per-game "Analyze" button on the Games tab
 *   for immediate single-game analysis. No bulk button (auto-enqueue covers it).
 */
export function NoEngineAnalysisFlawsState({
  isGuest,
  inFlightCount,
  analyzedCount,
  totalCount,
}: NoEngineAnalysisFlawsStateProps) {
  const navigate = useNavigate();

  return (
    <div
      data-testid="flaws-no-engine-analysis"
      className="flex min-h-[40vh] flex-col items-center justify-center gap-4 px-4 py-12 text-center"
    >
      <Cpu className="h-8 w-8 text-amber-600" aria-hidden="true" />

      {isGuest ? (
        <>
          <h2 className="text-xl font-semibold text-foreground">
            Sign up to unlock full-game analysis
          </h2>
          <p className="text-sm text-muted-foreground max-w-sm">
            Create a free account to queue Stockfish analysis of your games and see
            blunders, mistakes, and inaccuracies.
          </p>
          <Button
            variant="brand-outline"
            data-testid="btn-signup-for-analysis-flaws"
            aria-label="Sign up to unlock full-game analysis"
            onClick={() => navigate('/login?tab=register')}
          >
            Sign up free
          </Button>
        </>
      ) : inFlightCount > 0 ? (
        <>
          <h2 className="text-xl font-semibold text-foreground">Analyzing your games…</h2>
          <p className="text-sm text-muted-foreground max-w-sm">
            {analyzedCount} of {totalCount} analyzed
          </p>
        </>
      ) : (
        <>
          <h2 className="text-xl font-semibold text-foreground">
            Your games will be analyzed automatically
          </h2>
          <p className="text-sm text-muted-foreground max-w-sm">
            FlawChess runs Stockfish analysis on your most recent games in the background,
            and staying active keeps your games near the front of the queue. Check back
            shortly to see blunders, mistakes, and inaccuracies classified by phase and
            time pressure. To analyze one game right away, open it on the Games tab and use
            the "Analyze" button.
          </p>
          <Button
            variant="brand-outline"
            asChild
            data-testid="btn-go-to-games"
            aria-label="Go to the Games tab"
          >
            <Link to="/library/games">Go to Games</Link>
          </Button>
        </>
      )}
    </div>
  );
}
