import { Cpu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useTier1Enqueue } from '@/hooks/useEnqueueGame';

interface NoAnalysisStateProps {
  gameId: number;
  /** Whether the current user is a guest — show sign-up CTA instead of analyze button. */
  isGuest: boolean;
  /** Whether this game already has engine analysis (analyzed via lichess or FlawChess). */
  isAnalyzed: boolean;
  /** Whether analysis of THIS game is currently in-flight (tier-1 just clicked). */
  isInFlight?: boolean;
  /**
   * Callback to set the local in-flight state in the parent card.
   * Called with true when tier-1 enqueue is submitted, enabling the "Analyzing…" pulse
   * on THIS card only (D-118-11 — localized, not driven by aggregate inFlightCount).
   */
  onInFlightChange?: (inFlight: boolean) => void;
}

/**
 * Per-game "No Analysis" affordance rendered when a game has no engine analysis.
 *
 * Branches (D-118-07/11/13):
 * - isGuest: "Sign up to unlock analysis" link to /login?tab=register.
 * - isAnalyzed: returns null (no affordance needed — caller only renders for unanalyzed games).
 * - !isAnalyzed && isInFlight: pulsing "Analyzing…" text (localized to this game).
 * - !isAnalyzed && !isInFlight: "Analyze" button (tier-1 enqueue).
 *
 * The in-flight state is localized — only the specific card the user clicked shows
 * the "Analyzing…" state, never a global spinner across the archive.
 */
export function NoAnalysisState({
  gameId,
  isGuest,
  isAnalyzed,
  isInFlight = false,
  onInFlightChange,
}: NoAnalysisStateProps) {
  const navigate = useNavigate();
  const tier1Mutation = useTier1Enqueue(gameId);

  // Belt-and-suspenders: caller only renders this for no_engine_analysis games,
  // but return null when already analyzed (e.g. lichess-eval games, D-118-07).
  if (isAnalyzed) return null;

  if (isGuest) {
    return (
      <Button
        variant="brand-outline"
        size="sm"
        data-testid="btn-signup-for-analysis"
        aria-label="Sign up to unlock game analysis"
        onClick={() => navigate('/login?tab=register')}
      >
        <Cpu className="h-4 w-4 shrink-0 mr-1.5" aria-hidden="true" />
        Sign up to unlock analysis
      </Button>
    );
  }

  if (isInFlight) {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-sm font-bold text-muted-foreground animate-pulse"
        style={{ background: 'oklch(1 0 0 / 4%)' }}
        data-testid={`analyzing-${gameId}`}
        aria-label="Analysis in progress for this game"
      >
        <Cpu className="h-4 w-4 shrink-0" aria-hidden="true" />
        Analyzing…
      </span>
    );
  }

  return (
    <Button
      variant="brand-outline"
      size="sm"
      data-testid={`btn-analyze-game-${gameId}`}
      aria-label="Analyze this game with Stockfish"
      onClick={() => {
        tier1Mutation.mutate(undefined, {
          onSuccess: () => {
            onInFlightChange?.(true);
          },
        });
      }}
      disabled={tier1Mutation.isPending}
    >
      <Cpu className="h-4 w-4 shrink-0 mr-1.5" aria-hidden="true" />
      Analyze
    </Button>
  );
}
