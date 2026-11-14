/**
 * Popover around the Facepalm chip on the Flaws card (D-16, D-18).
 *
 * The trigger is a real <button> wrapping the chip span; the chip keeps its own
 * look (D-20), the button adds none. The body explains the Facepalm score.
 *
 * text-xs is allowed in the body: frontend/CLAUDE.md exempts short, transient,
 * opt-in info popover bodies from the text-sm floor.
 *
 * The `testId` becomes the Umami `popover-open` target via `popoverTargetFromTestId`,
 * so callers build it from numeric ids only (`facepalm-badge-{gameId}-{ply}`), which
 * normalizes to `facepalm-badge`.
 */

import * as React from 'react';
import type { ReactNode } from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { useTrackedPopoverOpen } from '@/hooks/useTrackedOpen';
import { toFacepalmPct } from '@/lib/facepalm';
import { cn } from '@/lib/utils';
import { FacepalmExplanation } from './FacepalmExplanation';

/** Hover-open delay, the TagChip value. */
const HOVER_OPEN_DELAY_MS = 100;
/** Grace period for the pointer to travel from the chip to the content, the TagChip value. */
const HOVER_CLOSE_GRACE_MS = 80;

interface FacepalmBadgePopoverProps {
  /** Trigger testid; the content gets `${testId}-popover`. Numeric segments only after the prefix. */
  testId: string;
  /** Raw 0..1 facepalm score. */
  score: number;
  /** The chip span. */
  children: ReactNode;
}

export function FacepalmBadgePopover({ testId, score, children }: FacepalmBadgePopoverProps) {
  const [open, setOpen] = useTrackedPopoverOpen(testId);
  const pct = toFacepalmPct(score);
  const openTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const closeTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  // True only while a pointer press is in progress on the trigger, so a focus caused
  // by that press is not mistaken for keyboard focus. Cleared on focus, click and blur:
  // a press on an already-focused trigger is cleared by its click, a drag-off with no
  // click by the blur that must precede any re-focus, and Safari (no focus on button
  // click) by the click.
  // Bug fix (253 review WR-01): Safari does not focus a button on press, so a mouse
  // drag-off or a touch that turned into a scroll fired no focus, click or blur and
  // left the flag set; the next keyboard focus then failed to open. A mouse
  // pointerleave and any pointercancel end the press too, so they clear it.
  const pointerDownRef = React.useRef(false);

  const clearTimers = (): void => {
    if (openTimer.current) clearTimeout(openTimer.current);
    if (closeTimer.current) clearTimeout(closeTimer.current);
    openTimer.current = null;
    closeTimer.current = null;
  };

  // Clear pending timers on unmount so they cannot fire setOpen late.
  React.useEffect(() => clearTimers, []);

  // Mouse only: touch fires pointerleave right after pointerup (it would close a
  // just-tapped popover) and compat mouse events would arm a second opener.
  const armOpen = (event: React.PointerEvent): void => {
    if (event.pointerType !== 'mouse') return;
    clearTimers();
    openTimer.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
  };

  const armClose = (event: React.PointerEvent): void => {
    if (event.pointerType !== 'mouse') return;
    clearTimers();
    closeTimer.current = setTimeout(() => setOpen(false), HOVER_CLOSE_GRACE_MS);
  };

  const keepOpen = (event: React.PointerEvent): void => {
    if (event.pointerType !== 'mouse') return;
    clearTimers();
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <button
          type="button"
          aria-label={`Facepalm ${pct}%`}
          data-testid={testId}
          className="inline-flex cursor-pointer rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onPointerEnter={armOpen}
          onPointerLeave={(event) => {
            if (event.pointerType === 'mouse') pointerDownRef.current = false;
            armClose(event);
          }}
          onPointerDown={() => {
            pointerDownRef.current = true;
          }}
          onPointerCancel={() => {
            pointerDownRef.current = false;
          }}
          onFocus={() => {
            const fromPointer = pointerDownRef.current;
            pointerDownRef.current = false;
            if (!fromPointer) setOpen(true);
          }}
          onBlur={() => {
            pointerDownRef.current = false;
          }}
          onClick={(event) => {
            // Skip the toggle Radix composes onto the trigger click: a click or tap
            // opens and never closes an open popover (touch would double toggle).
            event.preventDefault();
            pointerDownRef.current = false;
            setOpen(true);
          }}
        >
          {children}
        </button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="top"
          sideOffset={4}
          onPointerEnter={keepOpen}
          onPointerLeave={armClose}
          // Radix would move focus into the content and back to the trigger on close,
          // which re-fires focus-open and leaves a stray ring.
          onOpenAutoFocus={(event) => event.preventDefault()}
          onCloseAutoFocus={(event) => event.preventDefault()}
          data-testid={`${testId}-popover`}
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          <FacepalmExplanation score={score} />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
