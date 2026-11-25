/**
 * Popover around the severity chip of a scored blunder on the Flaws card (D-16, D-18, 260-G2).
 * The trigger wraps the chip (the "Facepalm" or "Blunder" severity badge); the body explains the
 * facepalm score. Opening behavior and tracking live in ChipPopover.
 */

import type { ReactNode } from 'react';
import { ChipPopover } from '@/components/library/ChipPopover';
import { facepalmScoreLabel } from '@/lib/facepalm';
import type { FacepalmType } from '@/types/library';
import { FacepalmExplanation } from './FacepalmExplanation';

interface FacepalmBadgePopoverProps {
  /** Trigger testid; the content gets `${testId}-popover`. Numeric segments only after the prefix. */
  testId: string;
  /** Raw 0..1 facepalm score. */
  score: number;
  /** Facepalm type; named in the aria-label and the popover body (257 D-10). */
  type: FacepalmType;
  /** The severity chip. */
  children: ReactNode;
}

export function FacepalmBadgePopover({ testId, score, type, children }: FacepalmBadgePopoverProps) {
  return (
    <ChipPopover
      testId={testId}
      ariaLabel={facepalmScoreLabel(score, type)}
      content={<FacepalmExplanation score={score} type={type} />}
    >
      {children}
    </ChipPopover>
  );
}
