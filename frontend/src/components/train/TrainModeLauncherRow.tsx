/**
 * TrainModeLauncherRow: one mode's row on the Today card (sketch 014 variant B, D-08 / D-09).
 *
 * The rows are the streak checklist: name, a red badge with the count left, a second status
 * line and the action. Four states:
 *  - pending: badge with the count (hidden at 0), "N left", Start
 *  - in progress: badge with the remaining count, "N left", Resume
 *  - done: a checkmark and "Done today, N points", no badge and no button
 *  - off: muted, "Off", and a Turn on button only when the card passes `onTurnOn`
 *
 * Start / Resume call the page's actions (`useTrainTodayActions`), so audio unlocks inside the
 * tap and the card never receives the session loop through a prop chain. The puzzles Start
 * keeps `btn-train-start` / `btn-train-resume` and the feature-route dot; the Blunder Check
 * Start keeps `btn-train-blunder-check-start`.
 */
import type { ReactElement } from 'react';
import { Check } from 'lucide-react';
import { RouteDot } from '@/components/feature-route/RouteDot';
import { Button } from '@/components/ui/button';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { useTrainTodayActions } from '@/components/train/trainTodayActions';
import { ROUTE_DOT_COLOR_CLASS } from '@/lib/theme';
import { cn } from '@/lib/utils';
import type { TrainModeProgress } from '@/types/train';

export type TrainLauncherMode = 'puzzles' | 'blunder_check';

interface ModeCopy {
  /** testid segment (kebab-case). */
  slug: 'puzzles' | 'blunder-check';
  name: string;
  unitOne: string;
  unitMany: string;
}

const MODE_COPY: Record<TrainLauncherMode, ModeCopy> = {
  puzzles: { slug: 'puzzles', name: 'Personalized Puzzles', unitOne: 'puzzle', unitMany: 'puzzles' },
  blunder_check: {
    slug: 'blunder-check',
    name: 'Blunder Check',
    unitOne: 'sequence',
    unitMany: 'sequences',
  },
};

export interface TrainModeLauncherRowProps {
  mode: TrainLauncherMode;
  progress: TrainModeProgress;
  /** Points earned today, shown in the done state. */
  pointsToday: number;
  /** Disables Start / Resume (the puzzles session is still loading). */
  disabled?: boolean;
  /** Puts the feature-route dot on the puzzles Start / Resume button. */
  showRouteDot?: boolean;
  /** Renders a Turn on button in the off state when passed. */
  onTurnOn?: (mode: TrainLauncherMode) => void;
}

function statusLine(copy: ModeCopy, progress: TrainModeProgress): string {
  if (progress.state === 'off') return 'Off';
  if (progress.remaining <= 0) return 'Nothing waiting';
  const unit = progress.remaining === 1 ? copy.unitOne : copy.unitMany;
  return `${progress.remaining} ${unit} left`;
}

/** The badge shows the count left while in progress, and while pending only when the server
 * counts it toward the nav badge (`pending` is 0 off a scheduled day). */
function showsBadge(progress: TrainModeProgress): boolean {
  if (progress.remaining <= 0) return false;
  if (progress.state === 'in_progress') return true;
  return progress.state === 'pending' && progress.pending > 0;
}

function startTestId(mode: TrainLauncherMode, progress: TrainModeProgress): string {
  if (mode === 'blunder_check') return 'btn-train-blunder-check-start';
  return progress.state === 'in_progress' ? 'btn-train-resume' : 'btn-train-start';
}

export function TrainModeLauncherRow({
  mode,
  progress,
  pointsToday,
  disabled = false,
  showRouteDot = false,
  onTurnOn,
}: TrainModeLauncherRowProps): ReactElement {
  const { startPuzzles, startBlunderCheck } = useTrainTodayActions();
  const copy = MODE_COPY[mode];
  const { state } = progress;
  const isOff = state === 'off';

  let action: ReactElement | null = null;
  if (state === 'done') {
    action = (
      <Check
        className="h-5 w-5 shrink-0 text-green-500"
        aria-hidden="true"
        data-testid={`train-launcher-check-${copy.slug}`}
      />
    );
  } else if (isOff) {
    if (onTurnOn !== undefined) {
      action = (
        <Button
          variant="brand-outline"
          className={cn(TRAIN_BUTTON_CLASS, 'min-w-24')}
          onClick={() => onTurnOn(mode)}
          data-testid={`btn-train-launcher-turn-on-${copy.slug}`}
        >
          Turn on
        </Button>
      );
    }
  } else {
    action = (
      <Button
        variant="default"
        className={cn(TRAIN_BUTTON_CLASS, 'relative min-w-24')}
        disabled={disabled}
        onClick={mode === 'puzzles' ? startPuzzles : startBlunderCheck}
        data-testid={startTestId(mode, progress)}
      >
        {state === 'in_progress' ? 'Resume' : 'Start'}
        {mode === 'puzzles' && showRouteDot && (
          <RouteDot testid="train-start-notification-dot" variant="corner" />
        )}
      </Button>
    );
  }

  return (
    <div
      className={cn('flex items-center justify-between gap-3', isOff && 'opacity-60')}
      data-testid={`train-launcher-row-${copy.slug}`}
      data-state={state}
    >
      <div className="flex min-w-0 flex-col">
        <span className="flex items-center gap-2 text-sm font-semibold">
          {copy.name}
          {showsBadge(progress) && (
            <span
              className={cn(
                'flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-sm leading-none font-semibold text-white',
                ROUTE_DOT_COLOR_CLASS,
              )}
              data-testid={`train-launcher-badge-${copy.slug}`}
            >
              {progress.remaining}
            </span>
          )}
        </span>
        {state === 'done' ? (
          <span className="text-sm text-muted-foreground" data-testid={`train-launcher-done-${copy.slug}`}>
            {`Done today, ${pointsToday} ${pointsToday === 1 ? 'point' : 'points'}`}
          </span>
        ) : (
          <span className="text-sm text-muted-foreground" data-testid={`train-launcher-status-${copy.slug}`}>
            {statusLine(copy, progress)}
          </span>
        )}
      </div>
      {action}
    </div>
  );
}
