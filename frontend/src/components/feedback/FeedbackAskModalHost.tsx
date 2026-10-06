/**
 * FeedbackAskModalHost: Phase 234 (SEED-191 #5). The feedback modal that
 * "Sure!" opens, mounted once at app level (ProtectedLayout) instead of inside
 * FeedbackAskBubble. The bubble's done response (and the 3s profile poll on
 * Import, and window-focus refetches) patch the cached profile and unmount the
 * bubble; a modal owned by the bubble would vanish with it, mid-draft
 * (RESEARCH Pitfall 1). The host is always mounted and renders nothing visible
 * while closed.
 *
 * No Umami event here: the submission is a database row carrying its source
 * ('milestone_ask'), which the browser need not duplicate.
 */

import type { ReactElement } from 'react';
import { FeedbackModal } from '@/components/feedback/FeedbackModal';
import {
  FEEDBACK_ASK_PLACEHOLDER,
  closeFeedbackAskModal,
  useFeedbackAskModalOpen,
} from '@/lib/feedbackAsk';

export function FeedbackAskModalHost(): ReactElement {
  const open = useFeedbackAskModalOpen();
  return (
    <FeedbackModal
      open={open}
      onOpenChange={(next) => {
        if (!next) closeFeedbackAskModal();
      }}
      source="milestone_ask"
      placeholder={FEEDBACK_ASK_PLACEHOLDER}
    />
  );
}
