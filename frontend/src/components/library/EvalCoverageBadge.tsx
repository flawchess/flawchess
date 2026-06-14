import { Cpu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { InfoPopover } from '@/components/ui/info-popover';
import { Button } from '@/components/ui/button';
import { LOW_COVERAGE_THRESHOLD, ANALYSIS_COVERAGE_INFO_COPY } from '@/components/library/analysisCoverageCopy';

interface EvalCoverageBadgeProps {
  /** Games with engine analysis (the "x" in "x of y"). */
  analyzedN: number;
  /** Total games in scope (the "y" in "x of y"). */
  totalN: number;
  /** Whether the current user is a guest — show sign-up instead of analyze CTA. */
  isGuest: boolean;
  /** Whether the eval-coverage query failed (T-118-13 isError requirement). */
  isCoverageError: boolean;
}

/**
 * Compact inline badge showing "N of M analyzed" with a pulsing CPU icon while
 * analysis is incomplete (analyzedN < totalN). The CPU icon is static at 100%.
 * Matches the sibling EvalCoverageHeader / EvalCpuPlaceholder pulse pattern.
 *
 * Rendered top-right of the match-count row on three surfaces:
 * - Stats tab (GlobalStats): prop values come from the flaw-stats probe.
 * - Games subtab (LibraryGameCardList): prop values from useEvalCoverage().
 * - Flaws subtab (FlawsTab): prop values from useEvalCoverage().
 *
 * All three place this inside a `flex items-center justify-between gap-3`
 * wrapper so the count stays left and the badge sits right.
 *
 * CTA logic:
 * - Guest, coverage < LOW_COVERAGE_THRESHOLD: "Sign up to analyze" link →
 *   /login?tab=register (guests are excluded from the background queue, so the
 *   sign-up prompt is their only path to analysis — D-118-13).
 * - Non-guest: no button. Recent games are analyzed automatically in the
 *   background (activity-based auto-enqueue); the badge plus its InfoPopover
 *   tell that story, and per-game analysis lives on each card's "Analyze" button.
 *
 * in_flight_count removed in Phase 119-03: tier-3 derived picks have no
 * eval_jobs rows, so aggregate in-flight was structurally blind to the dominant
 * backlog drain. The pulsing CPU icon gates on analyzedN < totalN instead.
 *
 * Polling is handled by the caller's useEvalCoverage() invocation.
 */
export function EvalCoverageBadge({
  analyzedN,
  totalN,
  isGuest,
  isCoverageError,
}: EvalCoverageBadgeProps) {
  const navigate = useNavigate();

  if (isCoverageError) {
    return (
      <p className="text-sm text-destructive" data-testid="eval-coverage-badge-error">
        Failed to load analysis status. Something went wrong. Please try again in a moment.
      </p>
    );
  }

  // Don't render while there's nothing to report (no games imported yet).
  if (totalN === 0) return null;

  const coverageRatio = totalN > 0 ? analyzedN / totalN : 1;
  const isBelowThreshold = coverageRatio < LOW_COVERAGE_THRESHOLD;
  const isIncomplete = analyzedN < totalN;

  const ariaLabel = `${analyzedN} of ${totalN} games analyzed`;

  return (
    <div className="flex items-center gap-2 flex-wrap justify-end">
      {/* Coverage pill */}
      <div
        className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-sm font-bold shrink-0"
        style={{ background: 'oklch(1 0 0 / 4%)' }}
        data-testid="eval-coverage-badge"
        aria-label={ariaLabel}
      >
        {/* Pulse while analysis is incomplete, static at 100% — matches
            EvalCoverageHeader / EvalCpuPlaceholder sibling pattern. */}
        <Cpu
          className={cn('h-4 w-4 shrink-0', isIncomplete && 'animate-pulse')}
          aria-hidden="true"
        />
        <span style={{ color: 'white', fontWeight: 700 }}>{analyzedN}</span>
        <span className="text-muted-foreground font-normal">of</span>
        <span style={{ color: 'white', fontWeight: 700 }}>{totalN}</span>
        <span className="text-muted-foreground font-normal">analyzed</span>
        <InfoPopover ariaLabel="About game analysis coverage" testId="eval-coverage-badge-info">
          <p>{ANALYSIS_COVERAGE_INFO_COPY}</p>
        </InfoPopover>
      </div>

      {/* Guest sign-up CTA — guests are excluded from the auto-enqueue queue, so
          the sign-up prompt is their only path to analysis. Non-guests get no
          button: recent games are analyzed automatically in the background. */}
      {isGuest && isBelowThreshold && (
        <Button
          variant="brand-outline"
          size="sm"
          data-testid="btn-coverage-signup"
          aria-label="Sign up to unlock full-game analysis"
          onClick={() => navigate('/login?tab=register')}
        >
          Sign up to analyze
        </Button>
      )}
    </div>
  );
}
