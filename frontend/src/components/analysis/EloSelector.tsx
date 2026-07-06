/**
 * EloSelector — interactive control driving the "you are here" ELO used by the
 * FlawChess and Maia engines (Phase 151 Plan 05, D-06; moved below the Maia card
 * in 155 UAT since it drives both). A single-thumb Slider snapped to the
 * Maia ELO ladder (MAIA_ELO_LADDER, 600-2600 step 100 per UAT quick 260705-bm3) —
 * bounds and step derive from the ladder, never hard-coded, so a future contract
 * revision (a wider/narrower ladder) doesn't require touching this component.
 */

import { Slider } from '@/components/ui/slider';
import { MAIA_ELO_LADDER } from '@/lib/maiaEncoding';

export interface EloSelectorProps {
  /** Current selected ELO — must be a value present in `ladder`. */
  value: number;
  /** Called with the new ladder ELO when the user moves the slider. */
  onChange: (elo: number) => void;
  /** Ladder rungs the slider snaps to. Defaults to MAIA_ELO_LADDER. */
  ladder?: readonly number[];
}

/** Fallback step (ELO) used only if `ladder` somehow has a single rung. */
const SINGLE_RUNG_STEP_FALLBACK = 100;

export function EloSelector({
  value,
  onChange,
  ladder = MAIA_ELO_LADDER,
}: EloSelectorProps): React.ReactElement {
  const min = ladder[0] ?? value;
  const max = ladder[ladder.length - 1] ?? value;
  const first = ladder[0];
  const second = ladder[1];
  const step = first !== undefined && second !== undefined ? second - first : SINGLE_RUNG_STEP_FALLBACK;

  const handleValueChange = (values: number[]): void => {
    const next = values[0];
    if (next === undefined) return;
    onChange(next);
  };

  return (
    <div
      data-testid="analysis-elo-selector"
      role="group"
      aria-label="Engine strength (ELO)"
      className="flex items-center gap-3"
    >
      <span className="text-sm text-muted-foreground">ELO</span>
      <Slider
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={handleValueChange}
        thumbLabels={['Engine strength (ELO)']}
        className="min-w-24"
      />
      <span
        className="text-sm font-medium tabular-nums w-12 text-right"
        data-testid="analysis-elo-selector-value"
      >
        {value}
      </span>
    </div>
  );
}
