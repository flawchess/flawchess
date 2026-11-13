/**
 * BlunderCheckPointsFlash: the "+N" gain and "-N" forfeit badge over the drill board
 * (Phase 249, D-12, D-13).
 *
 * A gain pops in over the board, then flies and shrinks into the pot badge of the progress
 * row, which adds it up as it lands (BlunderCheckScore). The flight's end point is measured
 * at mount, from this badge's own resting place to the pot badge. Without a pot badge to fly
 * to, or under prefers-reduced-motion, the gain falls back to Train's points pop in place.
 * A forfeit (points taken away by a timeout or a missed blunder) is a red badge that drops
 * and fades. All three end invisible, so no unmount timer is needed. The amount is always
 * the server's number.
 */

import { useLayoutEffect, useRef, useState } from 'react';
import type { CSSProperties, ReactElement } from 'react';
import { POINTS_FLIGHT_MS } from '@/lib/blunderCheckDrill';
import type { FeedbackFlash } from '@/lib/blunderCheckDrill';
import { prefersReducedMotion } from '@/lib/confetti';
import { TRAIN_POINTS_FG_ON_DARK, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';

/** The pot badge in the progress row, where a gain lands. */
export const POT_BADGE_TEST_ID = 'blunder-check-pot';

interface FlightOffset {
  x: number;
  y: number;
}

function centerOf(rect: DOMRect): FlightOffset {
  return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
}

/** From the badge's resting place (the centre of its positioned parent) to the pot badge. */
function measureFlight(badge: HTMLElement): FlightOffset | null {
  const origin = badge.offsetParent;
  const target = document.querySelector(`[data-testid="${POT_BADGE_TEST_ID}"]`);
  if (origin === null || target === null) return null;
  const from = centerOf(origin.getBoundingClientRect());
  const to = centerOf(target.getBoundingClientRect());
  return { x: to.x - from.x, y: to.y - from.y };
}

const BADGE_CLASS =
  'pointer-events-none absolute left-1/2 top-1/2 z-10 select-none whitespace-nowrap rounded-full px-6 py-1.5 text-2xl font-bold shadow-lg';

export function BlunderCheckPointsFlash({ amount, variant }: FeedbackFlash): ReactElement {
  const badgeRef = useRef<HTMLDivElement>(null);
  // null until measured: the badge stays hidden for that one frame, so it never pops in
  // place first and then restarts as a flight.
  const [flight, setFlight] = useState<FlightOffset | 'none' | null>(null);
  const flies = variant === 'gain';
  useLayoutEffect(() => {
    if (!flies) return;
    const badge = badgeRef.current;
    const offset = badge === null || prefersReducedMotion() ? null : measureFlight(badge);
    setFlight(offset ?? 'none');
  }, [flies]);

  if (!flies) {
    return (
      <div
        className={`animate-blunder-check-forfeit ${BADGE_CLASS}`}
        style={{ backgroundColor: ZONE_DANGER, color: TRAIN_POINTS_FG_ON_DARK }}
        data-testid="blunder-check-points-flash"
      >
        -{amount}
      </div>
    );
  }
  const flying = flight !== null && flight !== 'none';
  let animationClass = 'opacity-0';
  if (flying) animationClass = 'animate-blunder-check-points-fly';
  else if (flight === 'none') animationClass = 'animate-train-points-pop';
  const style: CSSProperties = { backgroundColor: ZONE_SUCCESS, color: TRAIN_POINTS_FG_ON_DARK };
  return (
    <div
      ref={badgeRef}
      className={`${animationClass} ${BADGE_CLASS}`}
      style={
        flying
          ? ({
              ...style,
              '--fly-x': `${flight.x}px`,
              '--fly-y': `${flight.y}px`,
              animationDuration: `${POINTS_FLIGHT_MS}ms`,
            } as CSSProperties)
          : style
      }
      data-testid="blunder-check-points-flash"
    >
      +{amount}
    </div>
  );
}
