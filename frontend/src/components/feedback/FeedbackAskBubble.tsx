/**
 * FeedbackAskBubble: Phase 234 (SEED-191 #2/#4/#5/#6/#7). Hilda asks an
 * engaged user for an idea, on every surface that hosts the milestone ask
 * (Import now; Train landing and Bots roster in plan 04). D-05: built only
 * from the existing `TrainBotBubble` and the `SignupAskActions` button shape,
 * no new visual component or style.
 *
 * The feedback modal is deliberately not owned here: it must outlive the
 * bubble (a done response hides the bubble while the modal is still open), so
 * FeedbackAskModalHost renders it at app level and "Sure!" opens it from there.
 */

import { useEffect } from 'react';
import type { ReactElement } from 'react';
import { Button } from '@/components/ui/button';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import type { TrainBotAvatarSize } from '@/components/train/TrainBotBubble';
import { useFeedbackAsk } from '@/hooks/useFeedbackAsk';
import { trackFeature } from '@/lib/analytics';
import { feedbackAskCopy, openFeedbackAskModal } from '@/lib/feedbackAsk';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import { HILDA_ID } from '@/lib/trainBotCopy';

type FeedbackAskSurface = 'import' | 'train-landing' | 'bots';

interface FeedbackAskActionsProps {
  surface: FeedbackAskSurface;
  onLater: () => void;
  onSure: () => void;
}

/** SignupAskActions shape: secondary ("Maybe later") first, primary ("Sure!") second. */
function FeedbackAskActions({ surface, onLater, onSure }: FeedbackAskActionsProps): ReactElement {
  return (
    <>
      <Button
        variant="brand-outline"
        className={TRAIN_BUTTON_CLASS}
        onClick={onLater}
        data-testid={`btn-feedback-ask-later-${surface}`}
      >
        Maybe later
      </Button>
      <Button
        variant="default"
        className={TRAIN_BUTTON_CLASS}
        onClick={onSure}
        data-testid={`btn-feedback-ask-sure-${surface}`}
      >
        Sure!
      </Button>
    </>
  );
}

interface FeedbackAskBubbleProps {
  surface: FeedbackAskSurface;
  activeDays: number;
  avatarSize?: TrainBotAvatarSize;
}

export function FeedbackAskBubble({
  surface,
  activeDays,
  avatarSize = 'default',
}: FeedbackAskBubbleProps): ReactElement {
  const { mutate } = useFeedbackAsk();

  // An API call, not an Umami event (frontend/CLAUDE.md forbids trackFeature on
  // mount). A view counts only when the bubble actually renders (SEED-191 #7),
  // never on profile fetch. StrictMode's double mount and remounts are
  // harmless: the server dedupes views per UTC day.
  useEffect(() => {
    mutate('view');
  }, [mutate]);

  // Why these two events exist although the ask state lives in the database
  // (FBASK-10, frontend/CLAUDE.md "track only what the browser knows"): the
  // event's page names the surface ('library' for /library/import, 'train',
  // 'bots'), which users.prompt_state never stores, and a round-2 view
  // overwrites round 1's snooze fields in place, so the round-1 click history
  // survives only in Umami. No day count, round or free value is sent (D-04).
  const handleLater = (): void => {
    trackFeature('action', { target: 'feedback-ask-later' });
    mutate('snooze');
  };

  // Open first, then record done: the dialog is up before the done response's
  // cache patch unmounts this bubble (the host lives at app level, so it stays).
  const handleSure = (): void => {
    trackFeature('action', { target: 'feedback-ask-sure' });
    openFeedbackAskModal();
    mutate('done');
  };

  return (
    <div data-testid={`feedback-ask-${surface}`}>
      <TrainBotBubble
        persona={PERSONA_REGISTRY[HILDA_ID]}
        state="prompt"
        avatarSize={avatarSize}
        actions={<FeedbackAskActions surface={surface} onLater={handleLater} onSure={handleSure} />}
      >
        <p data-testid="feedback-ask-copy">{feedbackAskCopy(activeDays)}</p>
      </TrainBotBubble>
    </div>
  );
}
