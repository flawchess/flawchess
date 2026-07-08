/**
 * TemperatureSelector — interactive control for Phase 159 Thread A's
 * policy-temperature knob (D-08/D-09, SEED-085): mirrors EloSelector.tsx's
 * structure, but the underlying domain is continuous and log-symmetric
 * (0.5-2.0) rather than a discrete ELO ladder. The Radix <Slider> stays
 * LINEAR over [-1, 1] (Pitfall 7 — exact center); this component converts
 * to/from the displayed temperature at its own boundary via
 * sliderPositionToTemperature / temperatureToSliderPosition (matching
 * bases: `2 ** x` and `Math.log2`, so position 0 <-> temperature 1 exactly,
 * which is what lets `useFlawChessEngine`'s `temperature === DEFAULT_POLICY_TEMPERATURE`
 * no-op short-circuit fire for every user who never touches the slider).
 *
 * Plain-language copy per D-09: no "Temperature"/"T=" jargon in the primary
 * label — a "Play style" group label with "Sharper" <-> "More human" endpoint
 * captions; the numeric T value is shown subtly (text-sm, one decimal).
 */

import { Slider } from '@/components/ui/slider';
import { DEFAULT_POLICY_TEMPERATURE } from '@/lib/engine/policyTemperature';

export interface TemperatureSelectorProps {
  /** Current policy temperature (TEMPERATURE_MIN-TEMPERATURE_MAX). */
  value: number;
  /** Called with the new temperature when the user moves the slider. */
  onChange: (temperature: number) => void;
}

/** D-08: log-symmetric range around the default — halving/doubling are equal visual steps. */
export const TEMPERATURE_MIN = 0.5;
export const TEMPERATURE_MAX = 2.0;

/**
 * Must equal the search core's no-op value (Pitfall 7 / T-159-08) — imported
 * directly rather than merely coincidentally set to the same literal, so the
 * slider's visual center and the search's short-circuit value can never
 * silently drift apart.
 */
export const TEMPERATURE_DEFAULT: number = DEFAULT_POLICY_TEMPERATURE;

const SLIDER_POSITION_MIN = Math.log2(TEMPERATURE_MIN); // -1
const SLIDER_POSITION_MAX = Math.log2(TEMPERATURE_MAX); // 1
const SLIDER_STEP = 0.01;

/**
 * Radix Slider stays linear internally over [-1, 1]; position 0 maps to
 * temperature 1 EXACTLY (2 ** 0 === 1 in IEEE 754 — Pitfall 7).
 */
export function sliderPositionToTemperature(position: number): number {
  return 2 ** position;
}

/**
 * Inverse of sliderPositionToTemperature — matching `Math.log2`/`2 **` bases
 * (Pitfall 7) so the round trip is exact at the endpoints and center.
 */
export function temperatureToSliderPosition(temperature: number): number {
  return Math.log2(temperature);
}

export function TemperatureSelector({
  value,
  onChange,
}: TemperatureSelectorProps): React.ReactElement {
  const handleValueChange = (values: number[]): void => {
    const next = values[0];
    if (next === undefined) return;
    onChange(sliderPositionToTemperature(next));
  };

  return (
    <div
      data-testid="analysis-temperature-selector"
      role="group"
      aria-label="Play style"
      className="flex flex-wrap items-center gap-3"
    >
      <span className="text-sm text-muted-foreground">Play style</span>
      <span className="text-sm text-muted-foreground">Sharper</span>
      <Slider
        min={SLIDER_POSITION_MIN}
        max={SLIDER_POSITION_MAX}
        step={SLIDER_STEP}
        value={[temperatureToSliderPosition(value)]}
        onValueChange={handleValueChange}
        thumbLabels={['Play style']}
        className="min-w-24"
      />
      <span className="text-sm text-muted-foreground">More human</span>
      <span
        className="text-sm font-medium tabular-nums w-10 text-right"
        data-testid="analysis-temperature-selector-value"
      >
        {value.toFixed(1)}
      </span>
    </div>
  );
}
