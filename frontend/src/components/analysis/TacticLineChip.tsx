/**
 * TacticLineChip — the missed/allowed tactic pill that opens (or collapses) a
 * tactic line from the /analysis move list ("fork 1"; orientation shown by color).
 *
 * Loading: spinner on the chip while its line is pending. Error: an inline note
 * next to the chip.
 *
 * Hover affordance mirrors the Games-card TacticMotifChip: pointer cursor, lift,
 * and a brightened background.
 */

import { useState } from 'react';
import type { ReactNode } from 'react';
import { Loader2 } from 'lucide-react';
import { tacticMotifLabel, tacticDepthBadge } from '@/lib/tacticComparisonMeta';
import { cn } from '@/lib/utils';
import {
  TAC_MISSED,
  TAC_MISSED_BG,
  TAC_MISSED_BORDER,
  TAC_ALLOWED,
  TAC_ALLOWED_BG,
  TAC_ALLOWED_BORDER,
  ACTIVE_FILTER_RING_CLASS,
} from '@/lib/theme';

// Same highlight-bg helper as TacticMotifChip/TagChip: bump the translucent alpha
// from 0.15 to 0.3 on hover so the chip clearly reads as highlighted.
const HIGHLIGHT_BG = (bg: string): string => bg.replace('/ 0.15)', '/ 0.3)');

type TacticOrientation = 'missed' | 'allowed';

export type TacticLineChipClick = (flaw: { ply: number; orientation: TacticOrientation }) => void;

interface TacticLineChipProps {
  motif: string;
  orientation: TacticOrientation;
  ply: number;
  depth: number | null;
  /** Set of `${ply}:${orientation}` keys for every currently open tactic chip. */
  activePvKeys: Set<string> | undefined;
  pvFetchPending: boolean | undefined;
  pvFetchError: boolean | undefined;
  onClick: TacticLineChipClick | undefined;
  testId: string;
  className?: string;
}

function chipText(motif: string, orientation: TacticOrientation, depth: number | null): string {
  // Mate-family motifs collapse to "checkmate". anchored=false: this is a navigable
  // surface, so the allowed +1 decision-anchor offset is dropped (allowed reads like missed).
  const motifLabel = tacticMotifLabel(motif);
  const depthLabel = tacticDepthBadge(motif, depth, orientation, false);
  return depthLabel != null ? `${motifLabel} ${depthLabel}` : motifLabel;
}

export function TacticLineChip({
  motif,
  orientation,
  ply,
  depth,
  activePvKeys,
  pvFetchPending,
  pvFetchError,
  onClick,
  testId,
  className,
}: TacticLineChipProps): ReactNode {
  // Active via key membership in the open-lines set, not a node/orientation match.
  const isActive = activePvKeys?.has(`${ply}:${orientation}`) ?? false;
  const isMissed = orientation === 'missed';
  const color = isMissed ? TAC_MISSED : TAC_ALLOWED;
  const bg = isMissed ? TAC_MISSED_BG : TAC_ALLOWED_BG;
  const border = isMissed ? TAC_MISSED_BORDER : TAC_ALLOWED_BORDER;
  const text = chipText(motif, orientation, depth);
  const ariaCollapse = `${text} tactic. Click to collapse tactic line.`;
  const ariaExpand = `${text} tactic. Click to expand tactic line.`;
  const showErrorNote = isActive && pvFetchError;

  // Brighten the chip while hovered/focused (tap-focus on mobile), like the Games card.
  const [highlighted, setHighlighted] = useState(false);

  const chipLabel =
    isActive && pvFetchPending ? (
      <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
    ) : (
      <span className="text-sm font-medium whitespace-nowrap">{text}</span>
    );

  return (
    <span className="inline-flex items-center gap-1">
      <button
        type="button"
        data-testid={testId}
        aria-label={isActive ? ariaCollapse : ariaExpand}
        className={cn(
          'inline-flex items-center h-5 px-1.5 rounded-full border',
          'cursor-pointer transition-all hover:-translate-y-px',
          isActive && ACTIVE_FILTER_RING_CLASS,
          isActive && pvFetchError && 'opacity-60',
          className,
        )}
        style={{
          color,
          backgroundColor: highlighted ? HIGHLIGHT_BG(bg) : bg,
          borderColor: border,
          filter: highlighted ? 'brightness(1.2)' : undefined,
        }}
        onMouseEnter={() => setHighlighted(true)}
        onMouseLeave={() => setHighlighted(false)}
        onFocus={() => setHighlighted(true)}
        onBlur={() => setHighlighted(false)}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.({ ply, orientation });
        }}
      >
        {chipLabel}
      </button>
      {showErrorNote && (
        <span className="text-sm text-muted-foreground ml-1" role="alert">
          Tactic line not available for this flaw.
        </span>
      )}
    </span>
  );
}
