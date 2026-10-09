/**
 * TrainLineChips — the reveal's chips row (Phase 237, D-01/D-02).
 *
 * One semantic button per chip, keyed on the PRIMARY role (`train-chip-your` /
 * `-best` / `-game`), never on SAN, so no move text leaks into automation hooks.
 * Roles whose first move coincides arrive already merged from `buildChipGroups`
 * ("Move = Best"). Tapping a chip calls `onSelect(chip.key)`; the active chip
 * carries `aria-pressed="true"`, the brand ring and a brand fill, and each chip
 * shows a small arrow in its board arrow's color (Phase 237 UAT: the row reads
 * as a selector tied to the board's arrows).
 */

import type { ReactElement } from 'react';
import { ArrowUpRight, Loader2 } from 'lucide-react';

import { formatScore } from '@/components/analysis/EngineLines';
import { MoveQualityIcon } from '@/components/icons/MoveQualityIcon';
import { BEST_MOVE_ARROW } from '@/lib/theme';
import { chipArrowColor } from '@/lib/trainArrows';
import { cn } from '@/lib/utils';
import type { ChipGroup, RoleKey } from '@/lib/trainRevealLines';

interface TrainLineChipsProps {
  chips: readonly ChipGroup[];
  activeChip: RoleKey | null;
  onSelect: (key: RoleKey) => void;
  /** SAN of a game move with no searchable line: a non-interactive chip. */
  sanOnlyGameMove: string | null;
}

/** The chip's eval slot: a spinner while its line loads, nothing once it failed
 * (Phase 236 D-14/D-15), else the engine eval pill. */
function ChipEval({ chip, testid }: { chip: ChipGroup; testid: string }): ReactElement | null {
  if (chip.pending === 'loading') {
    return (
      <Loader2
        className="size-4 animate-spin text-muted-foreground"
        aria-label="Loading line"
        role="img"
        data-testid={`${testid}-loading`}
      />
    );
  }
  if (chip.pending === 'failed' || chip.line === null) return null;
  // WR-01: a restored Analyze stand-in grade carries an eval-less empty line;
  // formatScore(null, null) would render a permanent "…" pill, so hide it.
  if (chip.line.evalCp === null && chip.line.evalMate === null) return null;
  return (
    <span
      className="rounded px-1.5 py-0.5 text-sm font-semibold text-white"
      style={{ backgroundColor: BEST_MOVE_ARROW }}
      data-testid={`${testid}-eval`}
    >
      {formatScore(chip.line.evalCp, chip.line.evalMate)}
    </span>
  );
}

function LineChip({
  chip,
  active,
  onSelect,
}: {
  chip: ChipGroup;
  active: boolean;
  onSelect: (key: RoleKey) => void;
}): ReactElement {
  const testid = `train-chip-${chip.key}`;
  return (
    <button
      type="button"
      data-testid={testid}
      data-active={active ? 'true' : 'false'}
      data-roles={chip.roles.join(' ')}
      data-line-status={chip.pending ?? undefined}
      aria-pressed={active}
      onClick={() => onSelect(chip.key)}
      // Phase 237 UAT: the chips did not read as tappable. Same hover cue as the
      // move list's FlawChip (pointer, lift, brightened background), and the
      // active chip is filled, not just ringed, so it reads as the selection.
      className={cn(
        'flex min-w-0 cursor-pointer flex-col items-start gap-0.5 rounded-md border px-2 py-1.5 text-left text-sm',
        'transition-all hover:-translate-y-px',
        active
          ? 'border-brand-brown bg-brand-brown/25 ring-2 ring-brand-brown hover:bg-brand-brown/30'
          : 'border-border bg-card hover:bg-accent',
      )}
    >
      <span className="flex w-full items-center gap-1">
        {chip.quality !== null && (
          <span data-testid={`${testid}-quality`} data-quality={chip.quality}>
            <MoveQualityIcon quality={chip.quality} className="h-4 w-4" />
          </span>
        )}
        <span className="font-semibold" data-testid={`${testid}-label`}>
          {chip.label}
        </span>
        <ArrowUpRight
          aria-hidden
          className="ml-auto size-4 shrink-0"
          style={{ color: chipArrowColor(chip.roles, chip.quality) }}
          data-testid={`${testid}-arrow`}
        />
      </span>
      {/* Phase 237 UAT: eval before the move, like the Stockfish lines. */}
      <span className="flex min-w-0 items-center gap-1.5">
        <ChipEval chip={chip} testid={testid} />
        <span className="font-mono" data-testid={`${testid}-san`}>
          {chip.san}
        </span>
      </span>
    </button>
  );
}

export function TrainLineChips({
  chips,
  activeChip,
  onSelect,
  sanOnlyGameMove,
}: TrainLineChipsProps): ReactElement {
  return (
    <div
      role="group"
      aria-label="Lines"
      data-testid="train-line-chips"
      // Phase 237 UAT: no row ring for the tour; the active chip's own ring
      // already marks the row, and a second border around it read as clutter.
      className="grid grid-flow-col auto-cols-fr gap-2"
    >
      {chips.map((chip) => (
        <LineChip key={chip.key} chip={chip} active={chip.key === activeChip} onSelect={onSelect} />
      ))}
      {sanOnlyGameMove !== null && (
        <div
          data-testid="train-chip-game"
          data-interactive="false"
          className="flex min-w-0 flex-col items-start gap-0.5 rounded-md border border-border bg-card px-2 py-1.5 text-sm"
        >
          <span className="font-semibold">Game</span>
          <span className="font-mono">{sanOnlyGameMove}</span>
        </div>
      )}
    </div>
  );
}
