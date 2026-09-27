import type { ReactElement } from 'react';
import { Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import {
  BLOCKED_REASON_BUBBLE_COPY,
  INSIGHTS_BUBBLE_COPY,
  INSIGHTS_HOST_ID,
  type BlockedReason,
} from '@/components/insights/endgameInsightsCopy';

export type InsightsBubbleStatus = 'idle' | 'pending' | 'error';

export interface EndgameInsightsBubbleProps {
  status: InsightsBubbleStatus;
  blockedReason: BlockedReason | null;
  onGenerate: () => void;
}

/**
 * Shelly the Turtle hosting every no-report state of the Endgames Insights
 * block (quick 260927-b05): idle pitch, pending, error and blocked. It
 * replaced the old hero card, skeleton card and error card, so the page no
 * longer jumps between three different cards before a report lands. Once a
 * report exists the parent hides this bubble and shows the report card.
 *
 * A blocked action stays visible but disabled, and Shelly SAYS why in a
 * second paragraph. This replaced a hover tooltip on the disabled button,
 * which phones never showed.
 */
export function EndgameInsightsBubble({
  status,
  blockedReason,
  onGenerate,
}: EndgameInsightsBubbleProps): ReactElement {
  const isPending = status === 'pending';
  const isError = status === 'error';
  // Pending is never "blocked": the button is already disabled, and a second
  // line would contradict the in-progress copy.
  const blockedLine =
    !isPending && blockedReason !== null ? BLOCKED_REASON_BUBBLE_COPY[blockedReason] : null;

  return (
    <div data-testid="insights-bubble" data-status={status}>
      <TrainBotBubble
        persona={PERSONA_REGISTRY[INSIGHTS_HOST_ID]}
        state="prompt"
        avatarSize="large"
        actions={
          isError ? (
            <RetryButton disabled={blockedReason !== null} onRetry={onGenerate} />
          ) : (
            <GenerateButton
              isPending={isPending}
              disabled={isPending || blockedReason !== null}
              onGenerate={onGenerate}
            />
          )
        }
      >
        <div className="space-y-2" {...bubbleRegionProps(status)}>
          <p data-testid="insights-bubble-copy">{INSIGHTS_BUBBLE_COPY[status]}</p>
          {blockedLine !== null && <p data-testid="insights-blocked-reason">{blockedLine}</p>}
        </div>
      </TrainBotBubble>
    </div>
  );
}

/** Live-region semantics per status: errors interrupt, progress is polite. */
function bubbleRegionProps(status: InsightsBubbleStatus): Record<string, string> {
  if (status === 'error') return { role: 'alert', 'data-testid': 'insights-error' };
  if (status === 'pending') return { role: 'status', 'aria-live': 'polite' };
  return {};
}

function GenerateButton({
  isPending,
  disabled,
  onGenerate,
}: {
  isPending: boolean;
  disabled: boolean;
  onGenerate: () => void;
}): ReactElement {
  return (
    <Button
      variant="default"
      onClick={onGenerate}
      disabled={disabled}
      aria-busy={isPending}
      data-testid="btn-generate-insights"
    >
      {isPending ? (
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      ) : (
        <Sparkles className="h-4 w-4" aria-hidden="true" />
      )}
      Generate Insights
    </Button>
  );
}

/**
 * Retry is gated on `blockedReason` exactly like Generate.
 *
 * WHY (FLAWCHESS-AG): this button used to be unconditionally enabled, so once
 * any failure put the block into the error state the user could apply a
 * blocking filter and keep firing requests the router rejects with 400
 * filters_not_supported — the one path around getBlockedReason.
 */
function RetryButton({
  disabled,
  onRetry,
}: {
  disabled: boolean;
  onRetry: () => void;
}): ReactElement {
  return (
    <Button
      variant="default"
      onClick={onRetry}
      disabled={disabled}
      data-testid="btn-insights-retry"
    >
      Try again
    </Button>
  );
}
