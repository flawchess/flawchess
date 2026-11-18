/**
 * TrainModeSettings: one collapsed settings row per Train mode (Personalized Puzzles and
 * Blunder Check), under the Today card (sketch 014 variant B, D-08).
 *
 * Each row is a Card whose trigger shows the mode name and a one-line summary; opening it
 * reveals the session-size slider. Every edit goes through the ONE shared settings draft
 * (`useTrainSettingsDraft`, owned by `TrainStartScreen`) so a size change made in the same
 * burst as a days edit rides one `PUT /train/settings` (T-251-26).
 *
 * The sliders track on commit through `useDebouncedTrackFeature` (one `option-change` per
 * adjustment burst, final value), never on every change.
 */
import { useState } from 'react';
import type { ReactElement } from 'react';
import { ChevronDown } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { useDebouncedTrackFeature } from '@/hooks/useDebouncedTrackFeature';
import type { EditableTrainSettings, TrainSettingsDraftApi } from '@/hooks/useTrainSettingsDraft';
import {
  enumeratedValue,
  TRAIN_BLUNDER_CHECK_PER_SESSION_VALUES,
  TRAIN_PUZZLES_PER_SESSION_VALUES,
} from '@/lib/analytics';
import { cn } from '@/lib/utils';

/** Puzzles per session: a slider in steps of 3. The default 6 and the older 3/6/9/12/15
 * presets all sit on this grid, so no stored value needs remapping. The backend's
 * `puzzles_per_session` CHECK stays at 0-50 on purpose: raising the max later is this
 * constant only. */
export const PUZZLES_PER_SESSION_MIN = 3;
export const PUZZLES_PER_SESSION_MAX = 30;
export const PUZZLES_PER_SESSION_STEP = 3;
/** Blunder-check sequences per session: 3-18 in steps of 3. */
export const BLUNDER_CHECK_PER_SESSION_MIN = 3;
export const BLUNDER_CHECK_PER_SESSION_MAX = 18;
export const BLUNDER_CHECK_PER_SESSION_STEP = 3;

type ModeSlug = 'puzzles' | 'blunder-check';

interface ModeConfig {
  slug: ModeSlug;
  title: string;
  sizeKey: 'puzzlesPerSession' | 'blunderCheckPerSession';
  sliderTestId: string;
  valueTestId: string;
  thumbLabel: string;
  min: number;
  max: number;
  step: number;
}

const PUZZLES_CONFIG: ModeConfig = {
  slug: 'puzzles',
  title: 'Personalized Puzzles',
  sizeKey: 'puzzlesPerSession',
  sliderTestId: 'filter-puzzles-per-session',
  valueTestId: 'train-puzzles-per-session-value',
  thumbLabel: 'Puzzles per session',
  min: PUZZLES_PER_SESSION_MIN,
  max: PUZZLES_PER_SESSION_MAX,
  step: PUZZLES_PER_SESSION_STEP,
};

const BLUNDER_CHECK_CONFIG: ModeConfig = {
  slug: 'blunder-check',
  title: 'Blunder Check',
  sizeKey: 'blunderCheckPerSession',
  sliderTestId: 'filter-blunder-check-per-session',
  valueTestId: 'train-blunder-check-per-session-value',
  thumbLabel: 'Blunder check sequences per session',
  min: BLUNDER_CHECK_PER_SESSION_MIN,
  max: BLUNDER_CHECK_PER_SESSION_MAX,
  step: BLUNDER_CHECK_PER_SESSION_STEP,
};

interface ModeRowProps {
  config: ModeConfig;
  draft: EditableTrainSettings | null;
  disabled: boolean;
  onSizeChange: (size: number) => void;
}

/** Tracks a committed slider value; the two modes use different registered value lists. */
function useTrackSizeCommit(slug: ModeSlug): (committed: number) => void {
  const track = useDebouncedTrackFeature('option-change');
  return (committed: number): void => {
    if (slug === 'puzzles') {
      const value = enumeratedValue(TRAIN_PUZZLES_PER_SESSION_VALUES, committed);
      if (value !== null) track({ target: 'train-puzzles-per-session', value });
      return;
    }
    const value = enumeratedValue(TRAIN_BLUNDER_CHECK_PER_SESSION_VALUES, committed);
    if (value !== null) track({ target: 'train-blunder-check-per-session', value });
  };
}

function SizeSlider({ config, draft, disabled, onSizeChange }: ModeRowProps): ReactElement {
  const trackCommit = useTrackSizeCommit(config.slug);
  const size = draft?.[config.sizeKey] ?? null;

  return (
    <div className="w-full">
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <p>Per session</p>
        {size !== null && (
          <span className="font-medium tabular-nums text-foreground" data-testid={config.valueTestId}>
            {size}
          </span>
        )}
      </div>
      <Slider
        min={config.min}
        max={config.max}
        step={config.step}
        value={[size ?? config.min]}
        onValueChange={(values: number[]) => {
          const next = values[0];
          if (next !== undefined) onSizeChange(next);
        }}
        onValueCommit={(values: number[]) => {
          const committed = values[0];
          if (committed !== undefined) trackCommit(committed);
        }}
        disabled={disabled}
        thumbLabels={[config.thumbLabel]}
        data-testid={config.sliderTestId}
      />
    </div>
  );
}

function ModeRow(props: ModeRowProps): ReactElement {
  const { config, draft } = props;
  const [open, setOpen] = useState(false);
  const size = draft?.[config.sizeKey] ?? null;
  return (
    <Card as="section" className="w-full" data-testid={`train-mode-settings-${config.slug}`}>
      <button
        type="button"
        className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm"
        aria-expanded={open}
        data-testid={`btn-train-mode-settings-${config.slug}`}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="flex-1 font-semibold">{config.title}</span>
        {size !== null && <span className="text-muted-foreground">{`${size} per session`}</span>}
        <ChevronDown
          className={cn('size-4 shrink-0 text-muted-foreground transition-transform', open && 'rotate-180')}
          aria-hidden="true"
        />
      </button>
      {open && (
        <div className="flex w-full flex-col gap-4 px-4 pb-4">
          <SizeSlider {...props} />
        </div>
      )}
    </Card>
  );
}

export interface TrainModeSettingsProps {
  /** The one shared settings draft (`useTrainSettingsDraft`, owned by `TrainStartScreen`). */
  settingsDraft: TrainSettingsDraftApi;
}

export function TrainModeSettings({ settingsDraft }: TrainModeSettingsProps): ReactElement {
  const { draft, update, isPending } = settingsDraft;
  const disabled = isPending || draft === null;
  return (
    <div className="flex w-full flex-col gap-4" data-testid="train-mode-settings">
      <ModeRow
        config={PUZZLES_CONFIG}
        draft={draft}
        disabled={disabled}
        onSizeChange={(size) => update({ puzzlesPerSession: size })}
      />
      <ModeRow
        config={BLUNDER_CHECK_CONFIG}
        draft={draft}
        disabled={disabled}
        onSizeChange={(size) => update({ blunderCheckPerSession: size })}
      />
    </div>
  );
}
