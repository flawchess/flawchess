/**
 * The Facepalm chip on the Flaws card: "<palm> Facepalm 94%", a pill of its own
 * next to the Blunder badge (UAT 253: split out of the badge). It is the Facepalm
 * popover trigger. Colored and sized like the context TagChip (text-xs, the same requested
 * deviation from the text-sm floor), so it reads as a tag, not a second severity badge.
 * 257 D-08 / D-09: tinted by the facepalm type (teal missed win, crimson allowed loss); every
 * scored blunder has a type, so there is no neutral variant. The popover names the type (D-10).
 */

import { TreePalm } from 'lucide-react';
import { FACEPALM_TYPE_STYLE, toFacepalmPct } from '@/lib/facepalm';
import type { FacepalmType } from '@/types/library';
import { FacepalmBadgePopover } from './FacepalmBadgePopover';

interface FacepalmChipProps {
  /** Raw 0..1 facepalm score. */
  score: number;
  /** Facepalm type of the blunder; picks the tint. */
  type: FacepalmType;
  gameId: number;
  /** Flaw ply; with gameId it builds the numeric-only popover testid. */
  ply: number;
}

export function FacepalmChip({ score, type, gameId, ply }: FacepalmChipProps) {
  const style = FACEPALM_TYPE_STYLE[type];
  return (
    <FacepalmBadgePopover testId={`facepalm-badge-${gameId}-${ply}`} score={score} type={type}>
      <span
        className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-bold whitespace-nowrap transition-all hover:-translate-y-px hover:brightness-125"
        style={{ color: style.color, backgroundColor: style.bg, borderColor: style.border }}
      >
        <TreePalm className="h-3 w-3" aria-hidden="true" />
        <span>Facepalm</span>
        <span className="tabular-nums">{toFacepalmPct(score)}%</span>
      </span>
    </FacepalmBadgePopover>
  );
}
