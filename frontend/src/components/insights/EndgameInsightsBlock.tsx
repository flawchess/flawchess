import type { UseMutationResult } from '@tanstack/react-query';
import { BarChart3, BookOpen, Lightbulb, ListChecks, Loader2, Sparkles, Target, UserCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import type { FilterState } from '@/components/filters/FilterPanel';
import { useActiveJobs } from '@/hooks/useImport';
import type {
  EndgameInsightsResponse,
  InsightsAxiosError,
} from '@/types/insights';
import {
  EndgameInsightsBubble,
  type InsightsBubbleStatus,
} from '@/components/insights/EndgameInsightsBubble';
import {
  BLOCKED_REASON_TOOLTIP,
  type BlockedReason,
} from '@/components/insights/endgameInsightsCopy';

// Curated endgame study resource (GM Noël Studer), shown as a static link in the
// Recommendations card. Kept out of the LLM payload so the URL is always correct
// and clickable rather than emitted as dead plain text by the model.
const ENDGAME_STUDY_URL = 'https://lichess.org/study/mtiahamI';

// Lichess endgame puzzle trainer, shown alongside the study link for hands-on
// practice. Kept out of the LLM payload for the same reason as the study URL.
const ENDGAME_PUZZLES_URL = 'https://lichess.org/training/endgame';

/**
 * Top-of-tab Insights block.
 *
 * Parent owns the mutation + rendered state and only passes `rendered` when
 * the cached report matches current filters, so this component never has to
 * reason about "outdated" reports. When filters drift away from what the
 * report was generated against, the parent clears it and we fall back to
 * Shelly's bubble.
 *
 * Quick 260927-b05: every no-report state (idle, pending, error, blocked) is
 * Shelly the Turtle in a bot bubble (`EndgameInsightsBubble`); the report
 * card only renders once a report exists. Error still outranks a rendered
 * report, so a failed regenerate falls back to the bubble.
 *
 * Button gating: Generate / Try again are disabled only while an import is
 * running. Non-default filters don't block; onGenerate resets them first.
 */
export interface EndgameInsightsBlockProps {
  rendered: EndgameInsightsResponse | null;
  mutation: UseMutationResult<EndgameInsightsResponse, InsightsAxiosError, FilterState>;
  onGenerate: () => void;
}

/**
 * Returns the reason that prevents generating an insights report, or null
 * when the button should be enabled. Filters never block: the parent's
 * onGenerate resets them to the insights-compatible state (toInsightsFilters).
 */
function getBlockedReason(hasActiveImport: boolean): BlockedReason | null {
  return hasActiveImport ? 'import-running' : null;
}

function bubbleStatus(isError: boolean, isPending: boolean): InsightsBubbleStatus {
  if (isError) return 'error';
  return isPending ? 'pending' : 'idle';
}

export function EndgameInsightsBlock({
  rendered,
  mutation,
  onGenerate,
}: EndgameInsightsBlockProps) {
  const { data: activeJobs } = useActiveJobs(true);

  const isPending = mutation.isPending;
  const isError = mutation.isError;
  const hasRendered = rendered !== null;

  const hasActiveImport = (activeJobs?.length ?? 0) > 0;
  const blockedReason = getBlockedReason(hasActiveImport);

  if (isError || !hasRendered) {
    return (
      <EndgameInsightsBubble
        status={bubbleStatus(isError, isPending)}
        blockedReason={blockedReason}
        onGenerate={onGenerate}
      />
    );
  }

  return (
    <Accordion type="single" collapsible defaultValue="insights">
      <AccordionItem
        value="insights"
        data-testid="insights-block"
        className="charcoal-texture rounded-md overflow-hidden"
      >
        <AccordionTrigger
          data-testid="insights-block-trigger"
          band
        >
          <span className="flex items-center gap-2 flex-1">
            <span className="insight-lightbulb" aria-hidden="true">
              <Lightbulb className="size-5" />
            </span>
            <h2 className="text-base font-semibold text-foreground">Insights</h2>
          </span>
        </AccordionTrigger>
        <AccordionContent className="p-4">
          <RenderedState
            response={rendered}
            isPending={isPending}
            blockedReason={blockedReason}
            onRegenerate={onGenerate}
          />
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

// ─── State components ──────────────────────────────────────────────────

/** Wrap a disabled button in a Tooltip that explains the blocking reason. */
function MaybeBlockedTooltip({
  reason,
  children,
}: {
  reason: BlockedReason | null;
  children: React.ReactNode;
}) {
  if (reason === null) return <>{children}</>;
  return (
    <Tooltip content={BLOCKED_REASON_TOOLTIP[reason]} delayDuration={0}>
      <span className="inline-block">{children}</span>
    </Tooltip>
  );
}

function RenderedState({
  response,
  isPending,
  blockedReason,
  onRegenerate,
}: {
  response: EndgameInsightsResponse;
  isPending: boolean;
  blockedReason: BlockedReason | null;
  onRegenerate: () => void;
}) {
  const { player_profile: playerProfile, overview, recommendations } = response.report;
  const showOverview = overview !== '';
  const showPlayerProfile = playerProfile !== '';
  const showRecommendations = recommendations.length > 0;

  const disabled = isPending || blockedReason !== null;

  return (
    <>
      <div className="space-y-5 mb-3">
        {showPlayerProfile && (
          <InsightsSection
            testId="insights-player-profile"
            title="Player Profile"
            icon={UserCircle2}
          >
            <div className="text-sm text-muted-foreground leading-relaxed space-y-3">
              {playerProfile.split(/\n\n+/).map((paragraph, idx) => (
                <p key={idx}>{paragraph}</p>
              ))}
            </div>
          </InsightsSection>
        )}
        {showOverview && (
          <InsightsSection
            testId="insights-overview"
            title="Data Analysis"
            icon={BarChart3}
          >
            <div className="text-sm text-muted-foreground leading-relaxed space-y-3">
              {overview.split(/\n\n+/).map((paragraph, idx) => (
                <p key={idx}>{paragraph}</p>
              ))}
            </div>
          </InsightsSection>
        )}
        {showRecommendations && (
          <InsightsSection
            testId="insights-recommendations"
            title="Recommendations"
            icon={ListChecks}
          >
            <ul className="text-sm text-muted-foreground leading-relaxed list-disc pl-5 space-y-1">
              {recommendations.map((rec, idx) => (
                <li key={idx}>{rec}</li>
              ))}
            </ul>
            <div className="mt-3 space-y-2 border-t border-border/60 pt-3 text-sm text-muted-foreground">
              <div className="flex items-start gap-2">
                <BookOpen className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <span>
                  Study endgame technique by level (Basic to Advanced):{' '}
                  <a
                    href={ENDGAME_STUDY_URL}
                    data-umami-event="outbound-endgame-study"
                    className="text-primary underline-offset-4 hover:underline"
                    target="_blank"
                    rel="noopener noreferrer"
                    data-testid="insights-rec-endgame-study-link"
                  >
                    GM Noël Studer's endgame study
                  </a>
                </span>
              </div>
              <div className="flex items-start gap-2">
                <Target className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <span>
                  Practice endgame puzzles:{' '}
                  <a
                    href={ENDGAME_PUZZLES_URL}
                    data-umami-event="outbound-endgame-puzzles"
                    className="text-primary underline-offset-4 hover:underline"
                    target="_blank"
                    rel="noopener noreferrer"
                    data-testid="insights-rec-endgame-puzzles-link"
                  >
                    Lichess endgame puzzles
                  </a>
                </span>
              </div>
            </div>
          </InsightsSection>
        )}
      </div>
      <div className="flex items-center gap-2">
        <MaybeBlockedTooltip reason={blockedReason}>
          <Button
            variant="brand-outline"
            onClick={onRegenerate}
            disabled={disabled}
            aria-busy={isPending}
            data-testid="btn-generate-insights"
          >
            <Sparkles className="h-4 w-4" />
            Generate Insights
          </Button>
        </MaybeBlockedTooltip>
        {isPending && (
          <div
            className="flex items-center gap-2 text-sm text-muted-foreground"
            role="status"
            aria-live="polite"
          >
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            <span>Generating insights may take around 30 seconds...</span>
          </div>
        )}
      </div>
    </>
  );
}

function InsightsSection({
  testId,
  title,
  icon: Icon,
  children,
}: {
  testId: string;
  title: string;
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean }>;
  children: React.ReactNode;
}) {
  return (
    <div data-testid={testId}>
      <h3 className="flex items-center gap-2 text-base font-semibold text-foreground mb-2">
        <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        {title}
      </h3>
      {children}
    </div>
  );
}
