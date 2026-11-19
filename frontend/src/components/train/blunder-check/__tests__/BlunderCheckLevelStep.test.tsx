// @vitest-environment jsdom
/**
 * BlunderCheckLevelStep: the one-time level screen (D-17, D-20): three labelled options with
 * Intermediate preselected, no Elo numbers, Start confirms the picked level, Back leaves.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { BlunderCheckLevelStep } from '@/components/train/blunder-check/BlunderCheckLevelStep';
import type { BlunderCheckLevel } from '@/types/train';

afterEach(cleanup);

function renderStep(
  overrides: Partial<{
    initialLevel: BlunderCheckLevel;
    saving: boolean;
    error: boolean;
    onConfirm: (level: BlunderCheckLevel) => void;
    onBack: () => void;
  }> = {},
) {
  const props = {
    initialLevel: 'intermediate' as BlunderCheckLevel,
    saving: false,
    error: false,
    onConfirm: vi.fn(),
    onBack: vi.fn(),
    ...overrides,
  };
  render(<BlunderCheckLevelStep {...props} />);
  return props;
}

function pressed(testId: string): string | null {
  return screen.getByTestId(testId).getAttribute('aria-pressed');
}

describe('BlunderCheckLevelStep', () => {
  it('shows the three level labels and no Elo numbers (D-17)', () => {
    renderStep();

    expect(screen.getByTestId('btn-blunder-check-level-beginner').textContent).toBe('Beginner');
    expect(screen.getByTestId('btn-blunder-check-level-intermediate').textContent).toBe(
      'Intermediate',
    );
    expect(screen.getByTestId('btn-blunder-check-level-advanced').textContent).toBe('Advanced');
    expect(screen.getByTestId('blunder-check-level-step').textContent).not.toMatch(/\d/);
  });

  it('preselects the initial level and moves the selection on a tap', () => {
    renderStep();

    expect(pressed('btn-blunder-check-level-intermediate')).toBe('true');
    expect(pressed('btn-blunder-check-level-advanced')).toBe('false');
    fireEvent.click(screen.getByTestId('btn-blunder-check-level-advanced'));
    expect(pressed('btn-blunder-check-level-advanced')).toBe('true');
    expect(pressed('btn-blunder-check-level-intermediate')).toBe('false');
  });

  it('Start confirms the picked level', () => {
    const { onConfirm } = renderStep();

    fireEvent.click(screen.getByTestId('btn-blunder-check-level-advanced'));
    fireEvent.click(screen.getByTestId('btn-blunder-check-level-start'));

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith('advanced');
  });

  it('Back calls onBack', () => {
    const { onBack } = renderStep();

    fireEvent.click(screen.getByTestId('btn-blunder-check-level-back'));

    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it('disables Start while saving and shows the inline error with Start as the retry', () => {
    renderStep({ saving: true });
    expect(
      (screen.getByTestId('btn-blunder-check-level-start') as HTMLButtonElement).disabled,
    ).toBe(true);
    cleanup();

    const { onConfirm } = renderStep({ error: true });
    expect(screen.getByTestId('blunder-check-level-error').textContent).toContain(
      'Failed to save your level',
    );
    fireEvent.click(screen.getByTestId('btn-blunder-check-level-start'));
    expect(onConfirm).toHaveBeenCalledWith('intermediate');
  });
});
