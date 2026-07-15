/**
 * PlayStyleControl — single-thumb play-style control for the Bots setup
 * screen (Phase 171 D-01, PLAY-02, V-09).
 *
 * A SIBLING of `PresetRangeFilter`, not a prop variant or a wrapper: that
 * component's `slider.value` is hard-typed `[number, number]` with a required
 * `minStepsBetweenThumbs` (a two-thumb-only contract with other consumers).
 * This component copies its visual shell (label + InfoPopover + summary row,
 * preset chip grid, Slider) but wires a single-thumb value instead.
 *
 * The slider floor is `PLAY_STYLE_MIN` (0.05), never `HUMAN_BLEND` (0) — see
 * `lib/playStyle.ts`'s module header for why 0 is a different regime, not a
 * reachable point on this continuum. Reaching blend 0 is only possible via
 * the Human preset button; dragging the slider can never produce it.
 */

import { Slider } from '@/components/ui/slider';
import { InfoPopover } from '@/components/ui/info-popover';
import {
  CHIP_BASE_CLASS,
  CHIP_ACTIVE_CLASS,
  CHIP_INACTIVE_CLASS,
} from '@/components/bots/chipStyles';
import { cn } from '@/lib/utils';
import {
  HUMAN_BLEND,
  ENGINE_BLEND,
  PLAY_STYLE_MIN,
  PLAY_STYLE_MAX,
  PLAY_STYLE_STEP,
  deriveActivePlayStylePreset,
  formatPlayStyleSummary,
} from '@/lib/playStyle';

interface PlayStyleControlProps {
  blend: number;
  onChange: (blend: number) => void;
}

export function PlayStyleControl({ blend, onChange }: PlayStyleControlProps) {
  const activePreset = deriveActivePlayStylePreset(blend);
  const summary = formatPlayStyleSummary(blend);
  const isHuman = blend === HUMAN_BLEND;

  const handleSliderChange = (values: number[]): void => {
    const next = values[0];
    if (next !== undefined) onChange(next);
  };

  return (
    <div data-testid="setup-play-style">
      <div className="mb-1 flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            Play style
            <InfoPopover
              ariaLabel="Play style info"
              testId="setup-play-style-info"
              side="bottom"
            >
              <p>
                <strong>Human</strong>: plays on instinct, no calculation — its rated style,
                unfiltered. <strong>Engine</strong>: calculates every move at full strength. The
                slider in between blends the two — style stays the same, calculation gets
                sharper as you move right.
              </p>
            </InfoPopover>
          </span>
        </p>
        <span
          className={cn(
            'text-sm tabular-nums',
            activePreset !== null ? 'font-medium text-toggle-active' : 'text-muted-foreground',
          )}
          data-testid="setup-play-style-summary"
        >
          {summary}
        </span>
      </div>

      <div className="mb-1 grid grid-cols-2 gap-1" data-testid="setup-play-style-presets">
        <button
          type="button"
          onClick={() => onChange(HUMAN_BLEND)}
          data-testid="setup-play-style-preset-human"
          aria-pressed={activePreset === 'human'}
          className={cn(
            CHIP_BASE_CLASS,
            activePreset === 'human' ? CHIP_ACTIVE_CLASS : CHIP_INACTIVE_CLASS,
          )}
        >
          Human
        </button>
        <button
          type="button"
          onClick={() => onChange(ENGINE_BLEND)}
          data-testid="setup-play-style-preset-engine"
          aria-pressed={activePreset === 'engine'}
          className={cn(
            CHIP_BASE_CLASS,
            activePreset === 'engine' ? CHIP_ACTIVE_CLASS : CHIP_INACTIVE_CLASS,
          )}
        >
          Engine
        </button>
      </div>

      <div className={cn('px-1.5', isHuman && 'opacity-50')}>
        <Slider
          min={PLAY_STYLE_MIN}
          max={PLAY_STYLE_MAX}
          step={PLAY_STYLE_STEP}
          value={[isHuman ? PLAY_STYLE_MIN : blend]}
          onValueChange={handleSliderChange}
          thumbLabels={['Play style']}
          data-testid="setup-play-style-slider"
        />
      </div>
    </div>
  );
}
