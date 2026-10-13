import type { ReactElement } from 'react';
import { TrainBotAvatar } from '@/components/train/TrainBotBubble';
import { INSIGHTS_HOST_ID } from '@/components/insights/endgameInsightsCopy';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import { cn } from '@/lib/utils';

const EXPAND_HINT = 'Click or tap for details';

/**
 * The expand hint of a collapsed accordion header band (238 UAT). It
 * hides via the trigger's aria-expanded group variant once the body is open, so it is only
 * meaningful inside an AccordionTrigger. The one place the string and its styling live.
 */
function ExpandHint(): ReactElement {
  return (
    <span className="text-xs font-normal text-muted-foreground group-aria-expanded/accordion-trigger:hidden">
      {EXPAND_HINT}
    </span>
  );
}

/**
 * Shelly's round avatar as the Insights marker: the report header and every
 * per-section insight. Replaced the gold lightbulb (238 UAT) so the narration
 * reads as Shelly's voice, matching her bubble above the report.
 */
function ShellyAvatar({ className }: { className: string }): ReactElement {
  return (
    <TrainBotAvatar persona={PERSONA_REGISTRY[INSIGHTS_HOST_ID]} className={cn('shrink-0', className)} />
  );
}

/**
 * Shelly's avatar followed by her words as an italic quote: the header of the
 * Insights block (report summary) and of every per-section insight. A speech
 * bubble reads badly inside a collapsible header band (238 UAT), so the quote
 * marks and italics carry the "Shelly is talking" cue instead.
 */
export function ShellyQuote({
  text,
  avatarClassName,
  className,
  expandHint = false,
}: {
  text: string;
  avatarClassName: string;
  className?: string;
  /**
   * Show the expand hint under the quote while its accordion is
   * collapsed (238 UAT). Only meaningful inside an AccordionTrigger: it hides via
   * the trigger's aria-expanded group variant once the body is open.
   */
  expandHint?: boolean;
}): ReactElement {
  return (
    <span className="flex flex-1 items-center gap-2">
      <ShellyAvatar className={avatarClassName} />
      <span className="flex flex-col gap-0.5">
        <q className={cn('italic text-foreground', className)}>{text}</q>
        {expandHint && <ExpandHint />}
      </span>
    </span>
  );
}
