/**
 * ProseSpan — content-agnostic hover-intent + click-to-play interactive move
 * span shell (Phase 157, extracted from `MaiaMoveQualityBar`'s private
 * `ProseMoveSpan`, quick 260705-m3z/260705-mth). The button/Popover/ref wiring
 * is identical to the original — only the popover body is now parameterized
 * via `children` so a second consumer (`FlawChessAgreementVerdict.tsx`, Phase
 * 157-02) can supply its own D-10 two-line popover content without
 * duplicating the hover-intent/click-to-play mechanics.
 *
 * Interaction contract (unchanged from the original `ProseMoveSpan`):
 * - Hover opens the popover after a short intent delay (`onOpenDelayed`);
 *   focus/tap opens it immediately (`onOpenNow`).
 * - A content-bridge (`onMouseEnter`/`onMouseLeave` on the popover body too)
 *   keeps it open while the pointer moves onto the popover.
 * - Clicking/tapping PLAYS the move via `onPlay` when the popover was ALREADY
 *   open at press time (captured synchronously in a ref at `onPointerDown`,
 *   not React state, so a focus-driven re-render mid-tap can't race it); the
 *   first press (popover closed) only reveals it (`onOpenNow`).
 * - The popover is fully parent-controlled (`isOpen`); Radix's
 *   `onOpenChange` only ever carries an outside-click/Escape CLOSE — it never
 *   opens.
 */

import { useRef } from 'react';
import { Popover, PopoverAnchor, PopoverContent } from '@/components/ui/popover';

export interface ProseSpanProps {
  /** The SAN (or other short label) rendered as the clickable span text. */
  label: string;
  textColor: string;
  ariaLabel: string;
  testId: string;
  tooltipTestId: string;
  isOpen: boolean;
  onOpenDelayed: () => void;
  onOpenNow: () => void;
  onClose: () => void;
  onPlay?: () => void;
  /** Popover body — content-agnostic so each consumer supplies its own copy. */
  children: React.ReactNode;
}

export function ProseSpan({
  label,
  textColor,
  ariaLabel,
  testId,
  tooltipTestId,
  isOpen,
  onOpenDelayed,
  onOpenNow,
  onClose,
  onPlay,
  children,
}: ProseSpanProps): React.ReactElement {
  // Whether the popover was already open when this press began — decides
  // reveal-vs-play. A ref (not state) so it's synchronous and immune to the
  // focus-driven re-render that opens the popover mid-tap.
  const wasOpenAtPress = useRef(false);

  return (
    <Popover open={isOpen} onOpenChange={(next) => (next ? undefined : onClose())}>
      <PopoverAnchor asChild>
        <button
          type="button"
          className="font-semibold underline decoration-dotted underline-offset-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          style={{ color: textColor }}
          aria-label={ariaLabel}
          data-testid={testId}
          onMouseEnter={onOpenDelayed}
          onMouseLeave={onClose}
          onFocus={onOpenNow}
          onBlur={onClose}
          onPointerDown={() => {
            wasOpenAtPress.current = isOpen;
          }}
          onClick={() => {
            if (wasOpenAtPress.current) {
              if (onPlay) onPlay();
              else onClose();
            } else {
              onOpenNow();
            }
          }}
        >
          {label}
        </button>
      </PopoverAnchor>
      {/* Content-bridge: keep it open while the pointer is on the popover. */}
      <PopoverContent
        side="top"
        onMouseEnter={onOpenNow}
        onMouseLeave={onClose}
        className="w-auto max-w-xs rounded-lg border border-border/50 bg-background px-3 py-2 text-xs text-foreground shadow-xl"
        data-testid={tooltipTestId}
      >
        {children}
      </PopoverContent>
    </Popover>
  );
}
