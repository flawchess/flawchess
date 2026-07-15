import { Cpu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTier1Enqueue } from '@/hooks/useEnqueueGame';
import { AnalysisPendingPill } from '@/components/library/AnalysisPendingPill';

interface NoAnalysisStateProps {
  gameId: number;
  /** Whether this game already has engine analysis (analyzed via lichess or FlawChess). */
  isAnalyzed: boolean;
  /** Whether analysis of THIS game is currently in-flight (tier-1 just clicked). */
  isInFlight?: boolean;
  /**
   * Callback to set the local in-flight state in the parent card.
   * Called with true optimistically on click (before server confirm), enabling the
   * pulsing pill on THIS card only (D-118-11 — localized, not a global spinner).
   * Called with false on enqueue error to roll back the optimistic state.
   */
  onInFlightChange?: (inFlight: boolean) => void;
  /**
   * Active eval-job status from the library-games payload (260615-q1x).
   * 'pending'  → queued but not yet leased by a worker.
   * 'leased'   → actively being evaluated by a worker.
   * null       → no active job (unqueued or already analyzed).
   *
   * The pill shows "Analyzing…" when leased, "Pending…" otherwise
   * (optimistic in-flight OR pending). This rides the existing library-games
   * poll so no new endpoint is needed.
   */
  activeEvalStatus?: 'pending' | 'leased' | null;
}

/**
 * Per-game "No Analysis" affordance rendered when a game has no engine analysis.
 *
 * Branches (D-118-07/11/13):
 * - isAnalyzed: returns null (no affordance needed — caller only renders for unanalyzed games).
 * - !isAnalyzed && (isInFlight || activeEvalStatus): pulsing pill ("Pending…" or "Analyzing…").
 * - !isAnalyzed && !isInFlight && !activeEvalStatus: "Analyze" button (tier-1 enqueue).
 *
 * Guests see the same "Analyze" button as authenticated users (QUEUE-08 guest gate
 * opened for tier-1). The coverage badge CTA promotes signup for automatic all-games
 * analysis as a separate, higher-level prompt.
 *
 * The in-flight state is localized — only the specific card the user clicked shows
 * the pulsing state, never a global spinner across the archive.
 *
 * Pill label (260615-q1x):
 * - "Analyzing…" when activeEvalStatus === 'leased' (worker actively running).
 * - "Pending…"   when isInFlight (optimistic) or activeEvalStatus === 'pending'.
 */
export function NoAnalysisState({
  gameId,
  isAnalyzed,
  isInFlight = false,
  onInFlightChange,
  activeEvalStatus,
}: NoAnalysisStateProps) {
  const tier1Mutation = useTier1Enqueue(gameId);

  // Belt-and-suspenders: caller only renders this for no_engine_analysis games,
  // but return null when already analyzed (e.g. lichess-eval games, D-118-07).
  if (isAnalyzed) return null;

  // Show the pulsing pill when: optimistic click is in-flight OR the server-side
  // job is already active (pending or leased from the library-games payload).
  const showPill = isInFlight || activeEvalStatus === 'pending' || activeEvalStatus === 'leased';

  if (showPill) {
    // "Analyzing…" once a worker has leased the job; "Pending…" while queued/optimistic.
    return <AnalysisPendingPill gameId={gameId} leased={activeEvalStatus === 'leased'} />;
  }

  return (
    <Button
      variant="brand-outline"
      size="sm"
      data-testid={`btn-analyze-game-${gameId}`}
      aria-label="Analyze this game with Stockfish"
      onClick={() => {
        // Optimistic: show the Pending… pill immediately (before server confirm).
        // onError rolls it back to the Analyze button if the enqueue fails.
        onInFlightChange?.(true);
        tier1Mutation.mutate(undefined, {
          onError: () => onInFlightChange?.(false),
        });
      }}
      disabled={tier1Mutation.isPending}
    >
      <Cpu className="h-4 w-4 shrink-0 mr-1.5" aria-hidden="true" />
      Analyze
    </Button>
  );
}
