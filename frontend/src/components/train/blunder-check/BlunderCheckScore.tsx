/**
 * BlunderCheckScore: the pot badge and the banked total of the drill's progress row
 * (Phase 249 UAT).
 *
 * The rule the row has to teach: points for "Good" calls pile up in the open window's pot
 * and are lost when the blunder is missed (or a move times out); they are only safe once
 * the window is over. So the row shows two numbers. The pot is a green "+N" badge, the
 * same badge that pops up over the board: every gain flies from the board into it
 * (BlunderCheckPointsFlash) and is added up as it lands, with a coin sound. A lost pot
 * turns red and shakes. The badge stays up on the solution (a red "+0" for a lost pot), so
 * the user sees what the window was worth, and slides into the total on Next. The total
 * next to it counts only banked points, so a lost pot never lowers it.
 *
 * Every number is the server's: the pot is the window's points, the total is the session's
 * points without the pot (see `drillProgress`). The other sounds play where their events
 * happen (BlunderCheckDrill), not here: this row remounts between the drill's screens.
 *
 * No Umami event is added for blunder check (D-19).
 */

import { useEffect, useState } from 'react';
import type { CSSProperties, ReactElement } from 'react';
import { POT_BADGE_TEST_ID } from '@/components/train/blunder-check/BlunderCheckPointsFlash';
import { POINTS_FLIGHT_LAND_MS } from '@/lib/blunderCheckDrill';
import type { DrillProgress, PotEvent } from '@/lib/blunderCheckDrill';
import { prefersReducedMotion } from '@/lib/confetti';
import { playSound } from '@/lib/sounds';
import { TRAIN_POINTS_FG_ON_DARK, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';

/**
 * The banked total starts counting once the pot badge has slid most of the way over, and
 * the whole count-up takes about BANK_COUNT_TOTAL_MS, however large the pot. Together they
 * stay under BANK_HOLD_MS, the time Next gives the handover.
 */
const BANK_COUNT_DELAY_MS = 250;
const BANK_COUNT_TOTAL_MS = 350;
const BANK_COUNT_MIN_STEP_MS = 40;

type PotLook = 'open' | 'empty' | 'bust' | 'lost' | 'bank';

const POT_ANIMATIONS: Partial<Record<PotLook, string>> = {
  bust: 'animate-blunder-check-pot-bust',
  bank: 'animate-blunder-check-pot-bank',
};

const POT_BADGE_CLASS =
  '-my-0.5 shrink-0 rounded-full border px-2.5 py-0.5 text-sm font-bold tabular-nums';

function potLook(
  pot: number | null,
  potEvent: PotEvent | null,
  windowOver: boolean,
): PotLook | null {
  if (pot === null) return potEvent?.kind === 'bank' ? 'bank' : null;
  if (potEvent?.kind === 'bust') return 'bust';
  if (pot > 0) return 'open';
  // Nothing in the pot: not yet while the window runs, lost once it is over.
  return windowOver ? 'lost' : 'empty';
}

/** The board badge's colours: green while there are points, red once they are lost. */
function potStyle(look: PotLook): CSSProperties | undefined {
  if (look === 'empty') return undefined;
  const background = look === 'bust' || look === 'lost' ? ZONE_DANGER : ZONE_SUCCESS;
  return { backgroundColor: background, borderColor: background, color: TRAIN_POINTS_FG_ON_DARK };
}

/**
 * The pot's points on screen. A gain is still in the air when the server's number arrives
 * (the board badge flies over, BlunderCheckPointsFlash), so the pot shows the old sum until
 * the badge lands, then adds it up and plays the coin. `landed` tells the first render
 * after a landing, for the pop.
 */
function useLandedPot(
  pot: number | null,
  potEvent: PotEvent | null,
  animated: boolean,
): { shown: number | null; landed: boolean } {
  const gain = pot !== null && potEvent?.kind === 'gain' ? potEvent.amount : null;
  // The pot size whose gain has landed; a new gain always changes the pot, so it is a new key.
  const [landedPot, setLandedPot] = useState<number | null>(null);
  useEffect(() => {
    if (gain === null || pot === null) {
      setLandedPot(null);
      return;
    }
    // Without motion nothing flies: the points count at once.
    const timer = setTimeout(
      () => {
        setLandedPot(pot);
        playSound('pot-gain');
      },
      animated ? POINTS_FLIGHT_LAND_MS : 0,
    );
    return () => clearTimeout(timer);
  }, [gain, pot, animated]);
  if (pot === null || gain === null) return { shown: pot, landed: false };
  const landed = landedPot === pot;
  return { shown: landed ? pot : pot - gain, landed };
}

/**
 * The pot badge. It keeps its place (invisible) while no window is open, so the progress bar
 * beside it does not change length between the drill's screens.
 */
function PotBadge({
  pot,
  potEvent,
  windowOver,
  animated,
}: {
  pot: number | null;
  potEvent: PotEvent | null;
  windowOver: boolean;
  animated: boolean;
}): ReactElement {
  const { shown, landed } = useLandedPot(pot, potEvent, animated);
  const look = potLook(shown, potEvent, windowOver);
  if (look === null) {
    return (
      <span aria-hidden="true" className={`invisible ${POT_BADGE_CLASS}`}>
        +0
      </span>
    );
  }
  // A banked or lost pot shows what was banked or lost, an open one what is in it.
  const settled = look === 'bank' || look === 'bust';
  const amount = settled ? (potEvent?.amount ?? 0) : (shown ?? 0);
  const animation = animated ? (POT_ANIMATIONS[look] ?? '') : '';
  return (
    <span
      className={`${POT_BADGE_CLASS} ${look === 'empty' ? 'border-border text-muted-foreground' : ''} ${animation}`}
      style={potStyle(look)}
      aria-label={look === 'bust' ? `${amount} points lost` : `${amount} points in this sequence`}
      data-testid={POT_BADGE_TEST_ID}
      data-pot-state={look}
    >
      {/* Re-keyed on the amount, so every landing replays the pop. */}
      <span
        key={amount}
        className={animated && landed ? 'animate-blunder-check-pot-gain' : undefined}
        data-testid="blunder-check-pot-amount"
      >
        {look === 'bust' ? '-' : '+'}
        {amount}
      </span>
    </span>
  );
}

/**
 * The banked total on screen. When the score mounts with a pot being banked (the progress
 * row re-keys it as Next starts the handover), the total starts without it and counts up to
 * the server's number as the badge slides over.
 */
function useBankedCount(banked: number, bankAmount: number): number {
  // Read once: the count-up belongs to the mount that shows the pot being banked.
  const [initial] = useState(bankAmount);
  const [pending, setPending] = useState(bankAmount);
  useEffect(() => {
    if (pending <= 0) return;
    const stepMs = Math.max(BANK_COUNT_MIN_STEP_MS, BANK_COUNT_TOTAL_MS / initial);
    const delay = pending === initial ? BANK_COUNT_DELAY_MS : stepMs;
    const timer = setTimeout(() => setPending((left) => left - 1), delay);
    return () => clearTimeout(timer);
  }, [pending, initial]);
  return banked - pending;
}

/** The pot badge and the banked total, the right end of the drill's progress row. */
export function BlunderCheckScore({
  progress,
}: {
  progress: Pick<DrillProgress, 'banked' | 'pot' | 'potEvent' | 'windowOver'>;
}): ReactElement {
  const { banked, pot, potEvent, windowOver } = progress;
  // Read once per mount, so the badge's animation and the count-up agree.
  const [animated] = useState(() => !prefersReducedMotion());
  const banking = potEvent?.kind === 'bank';
  const shown = useBankedCount(banked, animated && banking ? potEvent.amount : 0);
  return (
    <>
      <PotBadge pot={pot} potEvent={potEvent} windowOver={windowOver} animated={animated} />
      <p
        className={`shrink-0 text-sm font-semibold tabular-nums ${animated && banking ? 'animate-blunder-check-total-bank' : ''}`}
        data-testid="blunder-check-points"
      >
        {shown} pts
      </p>
    </>
  );
}
