/**
 * TrainModeSettings: one card per Train mode (Personalized Puzzles and Blunder Check) on the
 * Train landing, the left column on desktop (D-08, merged with the launcher rows after Phase 251).
 *
 * Each card stacks the mode's launcher row (`TrainModeLauncherRow`: name, the red count badge, the
 * status line and Start / Resume / Turn on), the one-sentence pitch (always visible), and a
 * collapsed "Settings" footer with the summary ("N per session" or "Off"). Opening it reveals the
 * session-size slider, for Blunder Check the level picker, then the rationale and the rules under
 * one "Why and how it works" heading (Phase 251 UAT: the rules are no longer a collapsible). The
 * Blunder Check launch notice (`BlunderCheckNotice`) sits above the cards. Until the progress has
 * loaded a card shows the mode name in place of the launcher row.
 *
 * - D-04: each slider runs from 0 (shown as Off) in steps of 3.
 * - D-05: the slider of the last active mode stops at 3 and shows a hint to untick days for a
 *   break; the shared draft also refuses a patch that would set both sizes to 0.
 * - D-17: the level picker shows only to users without rated games; the stored level is
 *   preselected (Intermediate while none is stored).
 *
 * Every edit goes through the ONE shared settings draft (`useTrainSettingsDraft`, owned by
 * `TrainStartScreen`) so a size change made in the same burst as a days edit rides one
 * `PUT /train/settings` (T-251-26). The sliders write the draft and track on commit only
 * (WR-03: saves on release, so a drag position in transit never reaches the draft or the PUT);
 * the tracking goes through `useDebouncedTrackFeature` (one `option-change` per adjustment
 * burst, final value).
 */
import { useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { BlunderCheckNotice } from '@/components/train/BlunderCheckNotice';
import { TRAIN_LANDING_CARD_MIN_H_CLASS } from '@/components/train/landingStyles';
import { TrainModeLauncherRow } from '@/components/train/TrainModeLauncherRow';
import type { TrainLauncherMode } from '@/components/train/TrainModeLauncherRow';
import { puzzlesRowProgress } from '@/components/train/puzzlesLanding';
import type { PuzzlesLanding } from '@/components/train/puzzlesLanding';
import { Card } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { ToggleChipButton } from '@/components/ui/toggle-chip-button';
import { useDebouncedTrackFeature } from '@/hooks/useDebouncedTrackFeature';
import { useTrainProgress } from '@/hooks/useTrainProgress';
import { BLUNDER_CHECK_RULES } from '@/lib/trainBotCopy';
import type { EditableTrainSettings, TrainSettingsDraftApi } from '@/hooks/useTrainSettingsDraft';
import {
  enumeratedValue,
  trackFeature,
  TRAIN_BLUNDER_CHECK_PER_SESSION_VALUES,
  TRAIN_PUZZLES_PER_SESSION_VALUES,
} from '@/lib/analytics';
import { cn } from '@/lib/utils';
import type { BlunderCheckLevel } from '@/types/train';

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

/** GM Noël Studer, "How to avoid blunders consistently", linked from the Blunder Check card. */
const BLUNDER_CHECK_VIDEO_URL = 'https://www.youtube.com/watch?v=K9vKzNJAp3U&t=1s';
/** One heading over a mode's rationale paragraph and its rules. */
const RATIONALE_TITLE = 'Why and how it works';
const SETTINGS_TOGGLE_LABEL = 'Settings';
const LEVEL_LABEL = 'Your level (sets how hard the blunders are)';

type ModeSlug = 'puzzles' | 'blunder-check';

interface ModeConfig {
  slug: ModeSlug;
  title: string;
  pitch: string;
  /** Why the training helps, shown under the slider, above the rules (Phase 251 UAT). */
  motivation: ReactNode;
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
  motivation:
    'These puzzles target your personal blind spots, because they come from your own blunders. They are also closer to real games than regular puzzles, because you first have to spot whether there is a tactic at all.',
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
  motivation: (
    <>
      Many games are decided by a blunder, and checking every move before you play it is how
      strong players avoid them (watch GM Noël Studer's{' '}
      <a
        href={BLUNDER_CHECK_VIDEO_URL}
        data-umami-event="outbound-blunder-check-video"
        className="text-primary underline-offset-4 hover:underline"
        target="_blank"
        rel="noopener noreferrer"
        data-testid="train-mode-blunder-check-video-link"
      >
        How to avoid blunders consistently
      </a>
      ).
    </>
  ),
  howItWorks: BLUNDER_CHECK_RULES,
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
  // WR-03: the drag position lives here and only reaches the shared draft on commit (pointer
  // release or a keyboard step). Writing every onValueChange position into the draft let the
  // 600 ms debounced save persist an intermediate size, and a resize to <= ended windows
  // completes an open blunder-check session irreversibly (D-06). Null while not dragging.
  const [dragValue, setDragValue] = useState<number | null>(null);
  // On a keyboard step Radix fires onValueCommit BEFORE onValueChange, so the commit's reset
  // was overwritten and dragValue stuck at the committed value: the slider then ignored every
  // later outside change of `size` (Turn on left it showing Off). Drop the local position
  // whenever the saved size changes (adjust-state-on-prop-change, no effect needed).
  const [prevSize, setPrevSize] = useState(size);
  if (size !== prevSize) {
    setPrevSize(size);
    setDragValue(null);
  }
  const shownSize = dragValue ?? size;

  return (
    <div className="w-full">
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <p>Per session</p>
        {shownSize !== null && (
          <span className="font-medium tabular-nums text-foreground" data-testid={config.valueTestId}>
            {shownSize === 0 ? 'Off' : shownSize}
          </span>
        )}
      </div>
      <Slider
        min={min}
        max={config.max}
        step={config.step}
        value={[shownSize ?? min]}
        onValueChange={(values: number[]) => {
          const next = values[0];
          if (next !== undefined) setDragValue(next);
        }}
        onValueCommit={(values: number[]) => {
          const committed = values[0];
          setDragValue(null);
          if (committed === undefined) return;
          onSizeChange(committed);
          trackCommit(committed);
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

/** Why the mode helps and its rules, always shown under the slider (the pitch sits above it). */
function HowItWorks({ config }: { config: ModeConfig }): ReactElement {
  return (
    <div className="flex w-full flex-col gap-2" data-testid={`train-mode-how-${config.slug}`}>
      <h3 className="text-sm font-semibold">{RATIONALE_TITLE}</h3>
      <p className="text-sm text-muted-foreground" data-testid={`train-mode-motivation-${config.slug}`}>
        {config.motivation}
      </p>
      <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
        {config.howItWorks.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
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
  onSizeChange: (size: number) => void;
  /** Extra controls between the slider and the rationale (the level picker). */
  extra?: ReactNode;
  /** The mode's launcher row, or null while the progress has not loaded (the name shows instead). */
  launcher: ReactNode;
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
  onSizeChange,
  extra,
  launcher,
}: ModeRowProps): ReactElement {
  const [open, setOpen] = useState(false);
  const summary = summaryText(size);
  return (
    // Same desktop minimum as the streak card; the spare height goes above the settings footer.
    <Card
      as="section"
      className={cn('flex w-full flex-col', TRAIN_LANDING_CARD_MIN_H_CLASS)}
      data-testid={`train-mode-settings-${config.slug}`}
    >
      <div className="flex w-full flex-col gap-2 px-4 pt-4">
        {launcher ?? <span className="text-sm font-semibold">{config.title}</span>}
        <p className="text-sm text-muted-foreground" data-testid={`train-mode-pitch-${config.slug}`}>
          {config.pitch}
        </p>
      </div>
      <button
        type="button"
        className="mt-auto flex w-full items-center gap-2 px-4 py-3 text-left text-sm text-muted-foreground transition-colors hover:text-foreground"
        aria-expanded={open}
        data-testid={`btn-train-mode-settings-${config.slug}`}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="flex-1">{summary}</span>
        {SETTINGS_TOGGLE_LABEL}
        <ChevronDown
          className={cn('size-4 shrink-0 transition-transform', open && 'rotate-180')}
          aria-hidden="true"
        />
      </button>
      {open && (
        <div className="flex w-full flex-col gap-4 px-4 pb-4">
          <SizeSlider
            config={config}
            size={size}
            isLastActive={isLastActive}
            disabled={disabled}
            onSizeChange={onSizeChange}
          />
          {extra}
          <HowItWorks config={config} />
        </div>
      )}
    </Card>
  );
}

export interface TrainModeSettingsProps {
  /** The one shared settings draft (`useTrainSettingsDraft`, owned by `TrainStartScreen`). */
  settingsDraft: TrainSettingsDraftApi;
  /** Today's puzzle session as the landing knows it; overrides the server's puzzles estimate. */
  puzzlesLanding?: PuzzlesLanding;
  /** Disables the puzzles Start / Resume (the session is loading or has no puzzles). */
  puzzlesStartDisabled?: boolean;
  /** Puts the feature-route dot on the puzzles Start / Resume button. */
  showRouteDot?: boolean;
  /** Called by an off mode's Turn on button; no button renders without it. */
  onTurnOn?: (mode: TrainLauncherMode) => void;
}

/** True when `size` is a real 0 (the mode is off); null while settings load. */
function isOff(size: number | null): boolean {
  return size === 0;
}

function sizeOf(draft: EditableTrainSettings | null, config: ModeConfig): number | null {
  return draft === null ? null : draft[config.sizeKey];
}

export function TrainModeSettings({
  settingsDraft,
  puzzlesLanding,
  puzzlesStartDisabled = false,
  showRouteDot = false,
  onTurnOn,
}: TrainModeSettingsProps): ReactElement {
  const { draft, update, isPending } = settingsDraft;
  const progress = useTrainProgress();
  const modes = progress.data?.modes;
  const disabled = isPending || draft === null;
  const puzzlesSize = sizeOf(draft, PUZZLES_CONFIG);
  const blunderCheckSize = sizeOf(draft, BLUNDER_CHECK_CONFIG);
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

  const puzzlesLauncher = modes && (
    <TrainModeLauncherRow
      mode="puzzles"
      progress={puzzlesRowProgress(modes.puzzles, puzzlesLanding)}
      pointsToday={puzzlesLanding?.pointsToday ?? 0}
      disabled={puzzlesStartDisabled}
      showRouteDot={showRouteDot}
      onTurnOn={onTurnOn}
    />
  );
  const blunderCheckLauncher = modes && (
    <TrainModeLauncherRow
      mode="blunder_check"
      progress={modes.blunder_check}
      pointsToday={modes.blunder_check.points_today}
      onTurnOn={onTurnOn}
    />
  );

  return (
    <div className="flex w-full flex-col gap-4" data-testid="train-mode-settings">
      <BlunderCheckNotice />
      <ModeRow
        config={PUZZLES_CONFIG}
        launcher={puzzlesLauncher}
        size={puzzlesSize}
        isLastActive={isOff(blunderCheckSize)}
        disabled={disabled}
        onSizeChange={(size) => update({ puzzlesPerSession: size })}
      />
      <ModeRow
        config={BLUNDER_CHECK_CONFIG}
        size={blunderCheckSize}
        isLastActive={isOff(puzzlesSize)}
        disabled={disabled}
        onSizeChange={(size) => update({ blunderCheckPerSession: size })}
        extra={levelPicker}
        launcher={blunderCheckLauncher}
      />
    </div>
  );
}
