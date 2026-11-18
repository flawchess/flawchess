/**
 * TrainModeSettings: one collapsed settings row per Train mode (Personalized Puzzles and
 * Blunder Check), under the Today card (sketch 014 variant B, D-08).
 *
 * Each row is a Card whose trigger shows the mode name and a one-line summary ("N per
 * session" or "Off"). Opening it reveals the pitch, a "How it works" collapsible, for Blunder
 * Check the level picker, and the session-size slider.
 *
 * - D-04: each slider runs from 0 (shown as Off) in steps of 3.
 * - D-05: the slider of the last active mode stops at 3 and shows a hint to untick days for a
 *   break; the shared draft also refuses a patch that would set both sizes to 0.
 * - D-10: How it works is open until the user's first completed session in that mode
 *   (`first_session_done`), collapsed afterwards; the user can toggle it either way.
 * - D-17: the level picker shows only to users without rated games; the stored level is
 *   preselected (Intermediate while none is stored).
 *
 * Every edit goes through the ONE shared settings draft (`useTrainSettingsDraft`, owned by
 * `TrainStartScreen`) so a size change made in the same burst as a days edit rides one
 * `PUT /train/settings` (T-251-26). The sliders track on commit through
 * `useDebouncedTrackFeature` (one `option-change` per adjustment burst, final value), never on
 * every change.
 */
import { useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { ToggleChipButton } from '@/components/ui/toggle-chip-button';
import { useDebouncedTrackFeature } from '@/hooks/useDebouncedTrackFeature';
import { useTrainProgress } from '@/hooks/useTrainProgress';
import type { EditableTrainSettings, TrainSettingsDraftApi } from '@/hooks/useTrainSettingsDraft';
import {
  enumeratedValue,
  trackFeature,
  TRAIN_BLUNDER_CHECK_PER_SESSION_VALUES,
  TRAIN_PUZZLES_PER_SESSION_VALUES,
} from '@/lib/analytics';
import { cn } from '@/lib/utils';
import type { BlunderCheckLevel, TrainModeProgress } from '@/types/train';

/** Puzzles per session: 0 (Off) to 30 in steps of 3. The default 6 and the older 3/6/9/12/15
 * presets all sit on this grid, so no stored value needs remapping. The backend's
 * `puzzles_per_session` CHECK stays at 0-50 on purpose: raising the max later is this
 * constant only. */
export const PUZZLES_PER_SESSION_MIN = 0;
export const PUZZLES_PER_SESSION_MAX = 30;
export const PUZZLES_PER_SESSION_STEP = 3;
/** Blunder-check sequences per session: 0 (Off) to 18 in steps of 3. */
export const BLUNDER_CHECK_PER_SESSION_MIN = 0;
export const BLUNDER_CHECK_PER_SESSION_MAX = 18;
export const BLUNDER_CHECK_PER_SESSION_STEP = 3;
/** The slider floor of the last active mode: at least one mode must stay on (D-05). */
export const MODE_SIZE_MIN_ACTIVE = 3;
/** The size a launcher row's "Turn on" sets (the product default, 6). */
export const DEFAULT_MODE_SIZE = 6;

/** Mirror `CORRECT_RETRY_DAYS` / `FAIL_RETRY_DAYS` in `app/services/train_scheduler.py`. */
const PUZZLE_CORRECT_RETRY_DAYS = 10;
const PUZZLE_FAIL_RETRY_DAYS = 4;

const BREAK_HINT = 'To take a break, untick days in the schedule.';
const LEVEL_LABEL = 'Your level (sets how hard the blunders are)';

type ModeSlug = 'puzzles' | 'blunder-check';

interface ModeConfig {
  slug: ModeSlug;
  title: string;
  pitch: string;
  howItWorks: readonly string[];
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
  pitch: 'Your own blunders as puzzles: find the move you missed in the game.',
  howItWorks: [
    'Puzzles come from mistakes and blunders in your imported games.',
    `Solve one correctly and it returns after ${PUZZLE_CORRECT_RETRY_DAYS} days, missed ones after ${PUZZLE_FAIL_RETRY_DAYS}.`,
    'Two correct solves in a row and the puzzle is mastered.',
  ],
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
  pitch: 'Replay a stretch of a real game and call each move before it is played: good or blunder?',
  howItWorks: [
    'Some sequences have no blunder at all, so you can never tell when one is coming.',
    "Every correct Good call adds a point to the sequence's pot.",
    'Catch the blunder for bonus points, then find a better move for more.',
    'Miss the blunder and the pot is lost. A false alarm ends the sequence, but you keep the pot.',
  ],
  sizeKey: 'blunderCheckPerSession',
  sliderTestId: 'filter-blunder-check-per-session',
  valueTestId: 'train-blunder-check-per-session-value',
  thumbLabel: 'Blunder check sequences per session',
  min: BLUNDER_CHECK_PER_SESSION_MIN,
  max: BLUNDER_CHECK_PER_SESSION_MAX,
  step: BLUNDER_CHECK_PER_SESSION_STEP,
};

interface LevelOption {
  level: BlunderCheckLevel;
  label: string;
}

const LEVEL_OPTIONS: readonly LevelOption[] = [
  { level: 'beginner', label: 'Beginner' },
  { level: 'intermediate', label: 'Intermediate' },
  { level: 'advanced', label: 'Advanced' },
];

/** The level shown selected while none is stored (matches the one-time level step's default). */
const DEFAULT_LEVEL: BlunderCheckLevel = 'intermediate';

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

interface SizeSliderProps {
  config: ModeConfig;
  /** The draft's value, or null while settings are still loading. */
  size: number | null;
  /** True when the other mode is off, so this is the last active mode (D-05). */
  isLastActive: boolean;
  disabled: boolean;
  onSizeChange: (size: number) => void;
}

function SizeSlider({ config, size, isLastActive, disabled, onSizeChange }: SizeSliderProps): ReactElement {
  const trackCommit = useTrackSizeCommit(config.slug);
  const min = isLastActive ? MODE_SIZE_MIN_ACTIVE : config.min;

  return (
    <div className="w-full">
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <p>Per session</p>
        {size !== null && (
          <span className="font-medium tabular-nums text-foreground" data-testid={config.valueTestId}>
            {size === 0 ? 'Off' : size}
          </span>
        )}
      </div>
      <Slider
        min={min}
        max={config.max}
        step={config.step}
        value={[size ?? min]}
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
      {isLastActive && (
        <p className="text-sm text-muted-foreground" data-testid={`train-mode-break-hint-${config.slug}`}>
          {BREAK_HINT}
        </p>
      )}
    </div>
  );
}

interface HowItWorksProps {
  config: ModeConfig;
  /** From the progress row; undefined while it loads (collapsed until known). */
  firstSessionDone: boolean | undefined;
}

/** Open until the first completed session in the mode (D-10); the user's own toggle wins. */
function HowItWorks({ config, firstSessionDone }: HowItWorksProps): ReactElement {
  const [userOpen, setUserOpen] = useState<boolean | null>(null);
  const open = userOpen ?? firstSessionDone === false;
  return (
    <div className="w-full" data-testid={`train-mode-how-${config.slug}`}>
      <button
        type="button"
        className="flex w-full items-center gap-1 text-left text-sm text-brand-brown-light transition-colors hover:text-brand-brown-highlight"
        aria-expanded={open}
        data-testid={`btn-train-mode-how-${config.slug}`}
        onClick={() => setUserOpen(!open)}
      >
        How it works
        <ChevronDown
          className={cn('size-4 shrink-0 transition-transform', open && 'rotate-180')}
          aria-hidden="true"
        />
      </button>
      {open && (
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {config.howItWorks.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface LevelPickerProps {
  /** The draft's stored level (null until chosen), or undefined while settings load. */
  level: BlunderCheckLevel | null | undefined;
  disabled: boolean;
  onLevelChange: (level: BlunderCheckLevel) => void;
}

/** The self-declared level for a user without rated games (D-17); labels only, never Elo. */
function LevelPicker({ level, disabled, onLevelChange }: LevelPickerProps): ReactElement {
  const selected = level ?? DEFAULT_LEVEL;
  return (
    <div className="w-full" data-testid="train-mode-level-picker">
      <p className="mb-1 text-sm text-muted-foreground">{LEVEL_LABEL}</p>
      <div className="grid grid-cols-3 gap-1">
        {LEVEL_OPTIONS.map((option) => (
          <ToggleChipButton
            key={option.level}
            active={selected === option.level}
            onClick={() => onLevelChange(option.level)}
            testId={`btn-train-level-${option.level}`}
            ariaLabel={option.label}
            disabled={disabled}
          >
            {option.label}
          </ToggleChipButton>
        ))}
      </div>
    </div>
  );
}

interface ModeRowProps {
  config: ModeConfig;
  size: number | null;
  isLastActive: boolean;
  disabled: boolean;
  firstSessionDone: boolean | undefined;
  onSizeChange: (size: number) => void;
  /** Extra controls between How it works and the slider (the level picker). */
  extra?: ReactNode;
}

function summaryText(size: number | null): string | null {
  if (size === null) return null;
  return size === 0 ? 'Off' : `${size} per session`;
}

function ModeRow({
  config,
  size,
  isLastActive,
  disabled,
  firstSessionDone,
  onSizeChange,
  extra,
}: ModeRowProps): ReactElement {
  const [open, setOpen] = useState(false);
  const summary = summaryText(size);
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
        {summary !== null && <span className="text-muted-foreground">{summary}</span>}
        <ChevronDown
          className={cn('size-4 shrink-0 text-muted-foreground transition-transform', open && 'rotate-180')}
          aria-hidden="true"
        />
      </button>
      {open && (
        <div className="flex w-full flex-col gap-4 px-4 pb-4">
          <p className="text-sm text-muted-foreground">{config.pitch}</p>
          <HowItWorks config={config} firstSessionDone={firstSessionDone} />
          {extra}
          <SizeSlider
            config={config}
            size={size}
            isLastActive={isLastActive}
            disabled={disabled}
            onSizeChange={onSizeChange}
          />
        </div>
      )}
    </Card>
  );
}

export interface TrainModeSettingsProps {
  /** The one shared settings draft (`useTrainSettingsDraft`, owned by `TrainStartScreen`). */
  settingsDraft: TrainSettingsDraftApi;
}

/** True when `size` is a real 0 (the mode is off); null while settings load. */
function isOff(size: number | null): boolean {
  return size === 0;
}

function sizeOf(draft: EditableTrainSettings | null, config: ModeConfig): number | null {
  return draft === null ? null : draft[config.sizeKey];
}

export function TrainModeSettings({ settingsDraft }: TrainModeSettingsProps): ReactElement {
  const { draft, update, isPending } = settingsDraft;
  const progress = useTrainProgress();
  const modes = progress.data?.modes;
  const disabled = isPending || draft === null;
  const puzzlesSize = sizeOf(draft, PUZZLES_CONFIG);
  const blunderCheckSize = sizeOf(draft, BLUNDER_CHECK_CONFIG);
  const puzzlesProgress: TrainModeProgress | undefined = modes?.puzzles;
  const blunderCheckProgress = modes?.blunder_check;

  const handleLevelChange = (level: BlunderCheckLevel): void => {
    // Compare with the STORED level, not the displayed one: while none is stored
    // Intermediate only looks selected, and tapping it is how the user confirms it.
    if (draft === null || level === draft.blunderCheckLevel) return;
    update({ blunderCheckLevel: level });
    trackFeature('option-change', { target: 'train-blunder-check-level', value: level });
  };

  const levelPicker =
    blunderCheckProgress?.has_rated_games === false ? (
      <LevelPicker level={draft?.blunderCheckLevel} disabled={disabled} onLevelChange={handleLevelChange} />
    ) : null;

  return (
    <div className="flex w-full flex-col gap-4" data-testid="train-mode-settings">
      <ModeRow
        config={PUZZLES_CONFIG}
        size={puzzlesSize}
        isLastActive={isOff(blunderCheckSize)}
        disabled={disabled}
        firstSessionDone={puzzlesProgress?.first_session_done}
        onSizeChange={(size) => update({ puzzlesPerSession: size })}
      />
      <ModeRow
        config={BLUNDER_CHECK_CONFIG}
        size={blunderCheckSize}
        isLastActive={isOff(puzzlesSize)}
        disabled={disabled}
        firstSessionDone={blunderCheckProgress?.first_session_done}
        onSizeChange={(size) => update({ blunderCheckPerSession: size })}
        extra={levelPicker}
      />
    </div>
  );
}
