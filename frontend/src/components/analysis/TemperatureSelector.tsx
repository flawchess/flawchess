/**
 * TemperatureSelector — interactive control for Phase 159 Thread A's
 * policy-temperature knob (D-08/D-09, SEED-085): the underlying domain is
 * continuous and log-symmetric (0.5-2.0). The Radix <Slider> stays LINEAR over
 * [-1, 1] (Pitfall 7 — exact center); this component converts to/from the
 * temperature at its own boundary via sliderPositionToTemperature /
 * temperatureToSliderPosition (matching bases: `2 ** x` and `Math.log2`, so
 * position 0 <-> temperature 1 exactly, which is what lets
 * `useFlawChessEngine`'s `temperature === DEFAULT_POLICY_TEMPERATURE` no-op
 * short-circuit fire for every user who never touches the slider).
 *
 * Polarity: the slider's LEFT end is "Human" (LOW/sharp temperature) and the
 * RIGHT end is "Stockfish" (HIGH/flat temperature). This looks backwards until
 * you remember Maia's distribution models *human* choice — its peak is the
 * most human-likely move, not the objectively best one. Sharpening (Human end)
 * concentrates mass on that peak, so findability pushes rare-but-strong moves
 * down and the engine settles on the natural move; flattening (Stockfish end)
 * spreads mass onto the rarer moves, so a strong move you'd seldom find clears
 * the findability bar and surfaces. Endpoints are labelled with the
 * Maia-violet Human and Stockfish-blue Stockfish captions above the track; no
 * numeric value is shown.
 */

import { User, Cpu } from 'lucide-react';

import { Slider } from '@/components/ui/slider';
import { DEFAULT_POLICY_TEMPERATURE } from '@/lib/engine/policyTemperature';
import { MAIA_ACCENT, STOCKFISH_ACCENT } from '@/lib/theme';

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
 * temperature 1 EXACTLY (2 ** 0 === 1 in IEEE 754 — Pitfall 7). The LEFT end
 * (position -1) is "Human" (temperature 0.5, sharp) and the RIGHT end
 * (position +1) is "Stockfish" (temperature 2.0, flat) — moving the thumb
 * toward Stockfish RAISES the temperature (see the Polarity note above for why
 * a flatter Maia distribution is the more engine-optimal end).
 */
export function sliderPositionToTemperature(position: number): number {
  return 2 ** position;
}

/**
 * Inverse of sliderPositionToTemperature — `log2(t)` (not `-log2(1 / t)`) so
 * the center is exactly +0 (not -0) and the round trip is exact at the
 * endpoints (Pitfall 7).
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
      className="flex items-center gap-2 border-t border-border pt-2 text-sm font-medium"
    >
      <span
        className="inline-flex shrink-0 items-center gap-1"
        style={{ color: MAIA_ACCENT }}
      >
        <User aria-hidden="true" className="h-4 w-4" />
        Human
      </span>
      <Slider
        min={SLIDER_POSITION_MIN}
        max={SLIDER_POSITION_MAX}
        step={SLIDER_STEP}
        value={[temperatureToSliderPosition(value)]}
        onValueChange={handleValueChange}
        thumbLabels={['Play style']}
        className="min-w-16 flex-1"
      />
      <span
        className="inline-flex shrink-0 items-center gap-1"
        style={{ color: STOCKFISH_ACCENT }}
      >
        <Cpu aria-hidden="true" className="h-4 w-4" />
        Stockfish
      </span>
    </div>
  );
}
