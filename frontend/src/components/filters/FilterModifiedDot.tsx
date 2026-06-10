import { useState, useRef, useEffect } from 'react';

// ─── Pulse-on-change hook ──────────────────────────────────────────────────────

/**
 * Returns true for ~1s after `value` changes (reference inequality). Drives the
 * brief ping animation on the filter "modified" dots when a filter is applied.
 */
export function usePulseOnChange(value: unknown): boolean {
  const [isPulsing, setIsPulsing] = useState(false);
  const prevRef = useRef(value);
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    if (prevRef.current !== value) {
      prevRef.current = value;
      setIsPulsing(true);
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = window.setTimeout(() => {
        setIsPulsing(false);
        timeoutRef.current = null;
      }, 1000);
    }
    return () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [value]);

  return isPulsing;
}

// ─── Modified dot ──────────────────────────────────────────────────────────────

/**
 * Small "modified" indicator dot shown on filter buttons/strip icons when a filter
 * differs from its default. Pulses briefly when the filter was just applied.
 */
export function ModifiedDot({
  active,
  pulsing,
  testId,
}: {
  active: boolean;
  pulsing: boolean;
  testId: string;
}): React.ReactNode {
  if (!active) return undefined;
  return (
    <span
      className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
      data-testid={testId}
      aria-hidden="true"
    >
      {pulsing && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-brown opacity-75" />
      )}
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
    </span>
  );
}
