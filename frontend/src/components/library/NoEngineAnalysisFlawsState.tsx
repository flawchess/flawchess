import { Cpu } from 'lucide-react';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';

interface NoEngineAnalysisFlawsStateProps {
  /** Whether the current user is a guest (show sign-up CTA). */
  isGuest: boolean;
}

/**
 * Full-width message shown on the Flaws tab when the user has imported games
 * but none have analyzed flaws.
 *
 * Branches:
 * - Guest: sign-up CTA to /login?tab=register that keeps the guest data.
 * - Non-guest: passive explainer — analysis runs automatically in the
 *   background; points to the per-game "Analyze" button on the Games tab
 *   for immediate single-game analysis. No bulk button (auto-enqueue covers it).
 *   The EvalCoverageBadge CPU icon (pulsing while analyzedN < totalN) and the
 *   per-card NoAnalysisState button are the real-time progress signals; this
 *   state provides context for why the flaw list is empty.
 *
 * No in-flight branch here: an eval_jobs count misses tier-3 picks (they have no
 * eval_jobs rows). The pulsing EvalCoverageBadge carries the 'analysis is running'
 * signal for all tiers.
 */
export function NoEngineAnalysisFlawsState({ isGuest }: NoEngineAnalysisFlawsStateProps) {
  const { logoutForPromotion } = useAuth();

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
            data-umami-event="signup-cta"
            data-umami-event-source="flaws-no-analysis"
            aria-label="Sign up to unlock full-game analysis"
            // Bug fix: this used to navigate('/login?tab=register')
            // while the guest was still signed in, so AuthPage bounced them back to /
            // and the button did nothing. Drop the guest session first (guest_token is
            // kept for promotion) and hard-navigate, like EvalCoverageBadge.
            onClick={() => {
              logoutForPromotion();
              window.location.href = '/login?tab=register';
            }}
          >
            Sign up free
          </Button>
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
            the &ldquo;Analyze&rdquo; button.
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
