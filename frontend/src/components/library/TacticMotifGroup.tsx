import * as React from 'react';
import { TacticMotifChip } from './TacticMotifChip';
import { ChipColumn } from './ChipColumn';

// Quick 260620-sep: how many tactic chips a single orientation group shows before
// collapsing the rest behind a "+N more" toggle. Beginner games can span many distinct
// motifs; capping keeps the Games-tab card height bounded. Each group now sits in its own
// ~1/3-width column, so a handful before collapsing is plenty.
const TACTIC_CHIP_CAP_PER_GROUP = 6;

interface TacticMotifGroupProps {
  /** Orientation this group represents — drives the chip ring/testid/highlight payload. */
  orientation: 'allowed' | 'missed';
  /** Muted leading label shown before the chips (e.g. "Allowed"). */
  label: string;
  /** Game id — keeps chip + control testids unique within a card. */
  gameId: number;
  /**
   * Distinct motifs for this orientation, with per-motif occurrence count. Quick
   * 260702-mnd (D-2): optional `filterRingActive` overrides the store-derived ring
   * with the caller's precise all-axes (family+orientation+depth) match — passed
   * through unconditionally so a `false` value (a chip that fails the depth filter)
   * suppresses the ring rather than falling back to the coarser store match.
   */
  motifs: { motif: string; count: number; filterRingActive?: boolean }[];
  /** Hover a chip → parent highlights this motif's eval-chart markers. */
  onChipHover: (motif: string, active: boolean) => void;
  /** Activate a chip → parent cycles the eval chart through this motif's plies. */
  onChipActivate: (motif: string) => void;
  /** Optional legend tooltip icon, pinned to the right of the group label so each
   *  orientation explains only its own motifs (Quick 260620: per-column legends). */
  legend?: React.ReactNode;
  /** Optional node rendered below the chips inside this column lane (Quick 260625: the
   *  desktop game-card Explore button is pinned under the Missed column). */
  footer?: React.ReactNode;
}

/**
 * Quick 260620-sep: one orientation group ("Allowed" / "Missed") of tactic motif chips
 * on the Library Games-tab card. Replaces the old flat, prefix-per-chip row — the group
 * label conveys orientation so chips render prefix-free (hidePrefix) with a count. Caps
 * the visible chips at TACTIC_CHIP_CAP_PER_GROUP with a "+N more" / "Show less" toggle so
 * busy beginner games don't grow the card unbounded.
 */
export function TacticMotifGroup({
  orientation,
  label,
  gameId,
  motifs,
  onChipHover,
  onChipActivate,
  legend,
  footer,
}: TacticMotifGroupProps) {
  const [expanded, setExpanded] = React.useState(false);

  const overCap = motifs.length > TACTIC_CHIP_CAP_PER_GROUP;
  const visible = expanded || !overCap ? motifs : motifs.slice(0, TACTIC_CHIP_CAP_PER_GROUP);
  const hiddenCount = motifs.length - TACTIC_CHIP_CAP_PER_GROUP;

  // Empty group still renders its (placeholder) column so the 3-column grid keeps stable
  // 1/3 lanes — e.g. a game with allowed tactics but no missed ones shows "Missed —".
  return (
    <ChipColumn
      label={label}
      testId={`tactic-group-${orientation}-${gameId}`}
      isEmpty={motifs.length === 0}
      labelTrailing={legend}
      footer={footer}
    >
      {visible.map(({ motif, count, filterRingActive }) => (
        <TacticMotifChip
          key={motif}
          motif={motif}
          orientation={orientation}
          hidePrefix
          count={count}
          flawId={gameId}
          filterRingActive={filterRingActive}
          onHover={(active) => onChipHover(motif, active)}
          onActivate={() => onChipActivate(motif)}
        />
      ))}
      {overCap && (
        <button
          type="button"
          className="text-sm font-medium text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
          onClick={() => setExpanded((v) => !v)}
          data-testid={`btn-tactic-more-${orientation}-${gameId}`}
        >
          {expanded ? 'Show less' : `+${hiddenCount} more`}
        </button>
      )}
    </ChipColumn>
  );
}
