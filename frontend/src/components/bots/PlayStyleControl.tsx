/**
 * PlayStyleControl — preset-only play-style control for the Bots setup screen
 * (Phase 171 D-01, PLAY-02; reworked to three-button segmented control,
 * quick 260717-lr9).
 *
 * Three discrete presets, no slider: Human (blend 0) / Light (blend 0.05,
 * default) / Deep (blend 0.5). They are named by CALCULATION BEHAVIOR, not by
 * rating — the engine isn't ELO-calibrated yet, so the copy makes no strength
 * promise. See `lib/playStyle.ts`'s module header.
 */

import { InfoPopover } from '@/components/ui/info-popover';
import {
  CHIP_BASE_CLASS,
  CHIP_ACTIVE_CLASS,
  CHIP_INACTIVE_CLASS,
} from '@/components/bots/chipStyles';
import { cn } from '@/lib/utils';
import {
  HUMAN_BLEND,
  LIGHT_BLEND,
  DEEP_BLEND,
  deriveActivePlayStylePreset,
  formatPlayStyleSummary,
  type PlayStylePreset,
} from '@/lib/playStyle';

interface PlayStyleControlProps {
  blend: number;
  onChange: (blend: number) => void;
}

interface PresetDef {
  key: PlayStylePreset;
  label: string;
  blend: number;
  testId: string;
}

const PRESETS: readonly PresetDef[] = [
  { key: 'human', label: 'Human', blend: HUMAN_BLEND, testId: 'setup-play-style-preset-human' },
  { key: 'light', label: 'Light', blend: LIGHT_BLEND, testId: 'setup-play-style-preset-light' },
  { key: 'deep', label: 'Deep', blend: DEEP_BLEND, testId: 'setup-play-style-preset-deep' },
];

export function PlayStyleControl({ blend, onChange }: PlayStyleControlProps) {
  const activePreset = deriveActivePlayStylePreset(blend);
  const summary = formatPlayStyleSummary(blend);

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
                <strong>Human</strong> plays Maia moves, no calculation — its rated style,
                unfiltered. <strong>Light</strong> adds a little Stockfish calculation on top;{' '}
                <strong>Deep</strong> calculates hard. Strengths aren&apos;t ELO-calibrated yet, so
                treat these as three distinct opponents to experiment with.
              </p>
            </InfoPopover>
          </span>
        </p>
        <span
          className={cn(
            'text-sm',
            activePreset !== null ? 'font-medium text-toggle-active' : 'text-muted-foreground',
          )}
          data-testid="setup-play-style-summary"
        >
          {summary}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-1" data-testid="setup-play-style-presets">
        {PRESETS.map((preset) => (
          <button
            key={preset.key}
            type="button"
            onClick={() => onChange(preset.blend)}
            data-testid={preset.testId}
            aria-pressed={activePreset === preset.key}
            className={cn(
              CHIP_BASE_CLASS,
              activePreset === preset.key ? CHIP_ACTIVE_CLASS : CHIP_INACTIVE_CLASS,
            )}
          >
            {preset.label}
          </button>
        ))}
      </div>
    </div>
  );
}
