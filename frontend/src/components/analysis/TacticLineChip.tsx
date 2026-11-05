/**
 * TacticLineChip — the missed/allowed tactic pill that opens (or collapses) a
 * tactic line on /analysis. Shared by the move list (short label "fork 1") and
 * the Explain bar (long label "missed fork in 1"), so both read and behave the same.
 *
 * Loading: spinner on the chip while its line is pending. Error: an inline note
 * next to the chip (move list only; the Explain bar row has no room for it).
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

/** short: "fork 1" (move list, orientation shown by color). long: "missed fork in 1" (Explain bar). */
export type TacticLineChipLabel = 'short' | 'long';

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
  label?: TacticLineChipLabel;
  testId: string;
  className?: string;
}

function chipText(motif: string, orientation: TacticOrientation, depth: number | null, label: TacticLineChipLabel): string {
  // Mate-family motifs collapse to "checkmate". anchored=false: this is a navigable
  // surface, so the allowed +1 decision-anchor offset is dropped (allowed reads like missed).
  const motifLabel = tacticMotifLabel(motif);
  const depthLabel = tacticDepthBadge(motif, depth, orientation, false);
  if (label === 'long') {
    return depthLabel != null ? `${orientation} ${motifLabel} in ${depthLabel}` : `${orientation} ${motifLabel}`;
  }
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
  label = 'short',
  testId,
  className,
}: TacticLineChipProps): ReactNode {
  // Multiple chips read active via key membership (flat siblings),
  // not a node/orientation singleton match.
  const isActive = activePvKeys?.has(`${ply}:${orientation}`) ?? false;
  const isMissed = orientation === 'missed';
  const color = isMissed ? TAC_MISSED : TAC_ALLOWED;
  const bg = isMissed ? TAC_MISSED_BG : TAC_ALLOWED_BG;
  const border = isMissed ? TAC_MISSED_BORDER : TAC_ALLOWED_BORDER;
  const text = chipText(motif, orientation, depth, label);
  const ariaCollapse = `${text} tactic. Click to collapse tactic line.`;
  const ariaExpand = `${text} tactic. Click to expand tactic line.`;
  const showErrorNote = label === 'short' && isActive && pvFetchError;

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
