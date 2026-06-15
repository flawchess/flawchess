import { useState } from 'react';
import { MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useScrollDirection } from '@/hooks/useScrollDirection';
import { useOverlayOpen } from '@/hooks/useOverlayOpen';
import { FeedbackModal } from './FeedbackModal';

/**
 * Global floating feedback trigger button.
 *
 * Positioning / z-index per UI-SPEC ladder:
 * - z-20: below MobileBottomBar (z-40), install banner (z-30), overlays (z-50)
 * - bottom-[4.5rem] on mobile (<sm) to clear the 4rem MobileBottomBar
 * - bottom-4 on sm and up
 * - Safe-area inset via tailwindcss-safe-area pb-safe so it clears the iOS home indicator
 *
 * Visibility: hidden (opacity-0, pointer-events-none) when:
 * 1. Scrolling down (useScrollDirection returns 'down')
 * 2. Any overlay (dialog/drawer/sheet) is open (useOverlayOpen returns true)
 *
 * Transition: 150ms opacity + translate so hide/show feels intentional.
 */
export function FeedbackButton() {
  const [open, setOpen] = useState(false);
  const direction = useScrollDirection();
  const overlayOpen = useOverlayOpen();

  const visible = direction === 'up' && !overlayOpen;

  return (
    <>
      <div
        className={[
          // Position: fixed bottom-right; clears MobileBottomBar on mobile
          'fixed right-4 z-20',
          // Mobile: bottom-[4.5rem] to clear the 4rem MobileBottomBar; sm and up: bottom-4
          'bottom-[4.5rem] sm:bottom-4',
          // Safe-area: compose with bottom offset for iOS home indicator in PWA mode
          'pb-safe',
          // Visibility transition (≤200ms)
          'transition-all duration-150',
          visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2 pointer-events-none',
        ].join(' ')}
      >
        <Button
          // Brand-brown primary so the floating trigger reads as the high-emphasis CTA
          variant="default"
          // Override stock size="icon" (size-8/32px) to meet 44px touch target (D-02)
          className="h-11 w-11"
          aria-label="Send feedback"
          data-testid="btn-feedback-open"
          onClick={() => setOpen(true)}
        >
          <MessageSquare className="size-4" aria-hidden="true" />
        </Button>
      </div>

      <FeedbackModal open={open} onOpenChange={setOpen} />
    </>
  );
}
