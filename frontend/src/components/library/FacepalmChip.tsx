/**
 * The Facepalm chip on the Flaws card: "<palm> Facepalm 94%", a pill of its own
 * next to the Blunder badge (UAT 253: split out of the badge). It is the Facepalm
 * popover trigger. Colored and sized like the context TagChip (text-xs, the same requested
 * deviation from the text-sm floor), so it reads as a tag, not a second severity badge.
 */

import { TreePalm } from 'lucide-react';
import { FACEPALM_CHIP, FACEPALM_CHIP_BG } from '@/lib/theme';
import { toFacepalmPct } from '@/lib/facepalm';
import { FacepalmBadgePopover } from './FacepalmBadgePopover';

interface FacepalmChipProps {
  /** Raw 0..1 facepalm score. */
  score: number;
  gameId: number;
  /** Flaw ply; with gameId it builds the numeric-only popover testid. */
  ply: number;
}

export function FacepalmChip({ score, gameId, ply }: FacepalmChipProps) {
  return (
    <FacepalmBadgePopover testId={`facepalm-badge-${gameId}-${ply}`} score={score}>
      <span
        className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-bold whitespace-nowrap transition-all hover:-translate-y-px hover:brightness-125"
        style={{ color: FACEPALM_CHIP, backgroundColor: FACEPALM_CHIP_BG, borderColor: FACEPALM_CHIP }}
      >
        <TreePalm className="h-3 w-3" aria-hidden="true" />
        <span>Facepalm</span>
        <span className="tabular-nums">{toFacepalmPct(score)}%</span>
      </span>
    </FacepalmBadgePopover>
  );
}
