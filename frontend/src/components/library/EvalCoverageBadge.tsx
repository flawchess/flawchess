import { Cpu } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { InfoPopover } from '@/components/ui/info-popover';
import { Button } from '@/components/ui/button';
import { LOW_COVERAGE_THRESHOLD, ANALYSIS_COVERAGE_INFO_COPY } from '@/components/library/analysisCoverageCopy';

/**
 * Guest sign-up CTA — guests can analyze one game at a time via the card "Analyze"
 * button; signing up unlocks automatic ALL-games background analysis with no per-game
 * clicking. Non-guests get no button: recent games are analyzed automatically in the
 * background. Shared with the Library Stats coverage line.
 */
export function CoverageSignupButton() {
  const { logoutForPromotion } = useAuth();
  return (
    <Button
      variant="brand-outline"
      size="sm"
      data-testid="btn-coverage-signup"
      data-umami-event="signup-cta"
      data-umami-event-source="eval-coverage"
      aria-label="Sign up to unlock full-game analysis"
      // A guest holds a guest JWT, so AuthPage treats them as authenticated
      // and bounces them off /login. Drop the guest token first (keeping
      // guest_token for account promotion) and do a full-page nav, matching
      // the working Welcome.tsx / Import.tsx sign-up path.
      onClick={() => {
        logoutForPromotion();
        window.location.href = '/login?tab=register';
      }}
    >
      Sign up to analyze all games
    </Button>
  );
}

interface EvalCoverageBadgeProps {
  /** Games with engine analysis (the "x" in "x of y"). */
  analyzedN: number;
  /** Total games in scope (the "y" in "x of y"). */
  totalN: number;
  /** Whether the current user is a guest — show sign-up instead of analyze CTA. */
  isGuest: boolean;
  /** Whether the eval-coverage query failed (rendered as an error state, not as zero coverage). */
  isCoverageError: boolean;
}

/**
 * Compact inline badge showing "N of M analyzed" with a pulsing CPU icon while
 * analysis is incomplete (analyzedN < totalN). The CPU icon is static at 100%.
 * Matches the sibling EvalCoverageHeader / EvalCpuPlaceholder pulse pattern.
 *
 * Rendered top-right of the match-count row on two surfaces (the Stats tab shows
 * per-TC coverage in its Flaw Stats basis line instead):
 * - Games subtab (LibraryGameCardList): prop values from useEvalCoverage().
 * - Flaws subtab (FlawsTab): prop values from useEvalCoverage().
 *
 * Both place this inside a `flex items-center justify-between gap-3`
 * wrapper so the count stays left and the badge sits right.
 *
 * CTA logic:
 * - Guest, coverage < LOW_COVERAGE_THRESHOLD: "Sign up to analyze all games"
 *   link → /login?tab=register. Guests can analyze games one at a time on demand
 *   (each card's "Analyze" button, tier-1), but they
 *   stay excluded from the background queue, so signing up is the only way to get
 *   the whole library analyzed automatically — that is what this CTA sells.
 * - Non-guest: no button. Recent games are analyzed automatically in the
 *   background (activity-based auto-enqueue); the badge plus its InfoPopover
 *   tell that story, and per-game analysis lives on each card's "Analyze" button.
 *
 * The pulsing CPU icon gates on analyzedN < totalN. Don't use an eval_jobs
 * in-flight count, because tier-3 derived picks have no eval_jobs rows.
 *
 * Polling is handled by the caller's useEvalCoverage() invocation.
 */
export function EvalCoverageBadge({
  analyzedN,
  totalN,
  isGuest,
  isCoverageError,
}: EvalCoverageBadgeProps) {
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

      {isGuest && isBelowThreshold && <CoverageSignupButton />}
    </div>
  );
}
