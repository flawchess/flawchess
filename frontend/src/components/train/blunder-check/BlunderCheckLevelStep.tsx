/**
 * BlunderCheckLevelStep: the one-time level screen shown before a user's first blunder-check
 * drill when the server says a level is needed (no rated games and no stored level, guests
 * included; D-20). The facepalm score is computed at the mover's rating, so a guess far from the
 * truth would hand out invisible or trivial blunders.
 *
 * Labels only, never Elo numbers (D-17). The host saves the picked level and composes after the
 * save succeeded; this component only collects the choice. Tracks nothing itself (the host sends
 * the option-change event from its confirm handler).
 */

import { useState } from 'react';
import type { ReactElement } from 'react';
import { Button } from '@/components/ui/button';
import { ToggleChipButton } from '@/components/ui/toggle-chip-button';
import { TRAIN_CTA_BUTTON_CLASS } from '@/components/train/buttonStyles';
import type { BlunderCheckLevel } from '@/types/train';

interface LevelOption {
  level: BlunderCheckLevel;
  label: string;
}

const LEVEL_OPTIONS: readonly LevelOption[] = [
  { level: 'beginner', label: 'Beginner' },
  { level: 'intermediate', label: 'Intermediate' },
  { level: 'advanced', label: 'Advanced' },
];

export interface BlunderCheckLevelStepProps {
  /** The preselected level (Intermediate). */
  initialLevel: BlunderCheckLevel;
  /** The level save (or the settings fetch it needs) is in flight: Start is disabled. */
  saving: boolean;
  /** The last save failed: shows the inline error; Start is the retry. */
  error: boolean;
  onConfirm: (level: BlunderCheckLevel) => void;
  /** Leaves the host without saving (back to the Today card). */
  onBack: () => void;
}

export function BlunderCheckLevelStep({
  initialLevel,
  saving,
  error,
  onConfirm,
  onBack,
}: BlunderCheckLevelStepProps): ReactElement {
  const [level, setLevel] = useState<BlunderCheckLevel>(initialLevel);
  return (
    <div
      className="mx-auto flex w-full max-w-md flex-col gap-4"
      data-testid="blunder-check-level-step"
    >
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold" data-testid="blunder-check-level-heading">
          Pick your level
        </h2>
        <p className="text-sm text-muted-foreground">
          It sets how hard the blunders are. You can change it later in the Blunder Check settings.
        </p>
      </div>
      <div className="grid grid-cols-3 gap-2" role="group" aria-label="Level">
        {LEVEL_OPTIONS.map((option) => (
          <ToggleChipButton
            key={option.level}
            active={level === option.level}
            onClick={() => setLevel(option.level)}
            ariaLabel={option.label}
            testId={`btn-blunder-check-level-${option.level}`}
          >
            {option.label}
          </ToggleChipButton>
        ))}
      </div>
      <div className="flex flex-col gap-1 text-sm text-muted-foreground">
        <p>
          You replay short stretches of real games and call each move before it is played: good or
          blunder?
        </p>
        <p>Some sequences have no blunder at all.</p>
      </div>
      {error && (
        <p className="text-sm text-muted-foreground" data-testid="blunder-check-level-error">
          Failed to save your level. Something went wrong. Please try again in a moment.
        </p>
      )}
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button
          className={TRAIN_CTA_BUTTON_CLASS}
          disabled={saving}
          onClick={() => onConfirm(level)}
          data-testid="btn-blunder-check-level-start"
        >
          Start
        </Button>
        <Button
          variant="brand-outline"
          className={TRAIN_CTA_BUTTON_CLASS}
          onClick={onBack}
          data-testid="btn-blunder-check-level-back"
        >
          Back
        </Button>
      </div>
    </div>
  );
}
