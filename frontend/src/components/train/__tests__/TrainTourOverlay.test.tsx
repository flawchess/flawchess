// @vitest-environment jsdom
/**
 * Hilda's tour panel on the board: the compact layout (avatar floated inside the panel, the
 * step counter in the top-right corner), the pointer-events-none contract, and the hidden
 * corner badge.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { TrainTourOverlay } from '@/components/train/TrainTourOverlay';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';

afterEach(() => {
  cleanup();
});

const PERSONA = PERSONA_REGISTRY['wall-1800'];

function renderOverlay(overrides: { stepCount?: number; hidden?: boolean; onReopen?: () => void } = {}) {
  return render(
    <TrainTourOverlay
      persona={PERSONA}
      copy="Your result is in the highlighted box."
      step={0}
      stepCount={overrides.stepCount ?? 2}
      hidden={overrides.hidden ?? false}
      onReopen={overrides.onReopen ?? vi.fn()}
    />,
  );
}

describe('TrainTourOverlay', () => {
  it('shows the panel as a persona-named group with the floated avatar and the step counter', () => {
    renderOverlay({ stepCount: 2 });

    const panel = screen.getByTestId('train-tour-overlay');
    expect(panel.getAttribute('role')).toBe('group');
    expect(panel.getAttribute('aria-label')).toBe(PERSONA.name);
    expect(panel.className).toContain('pointer-events-none');
    const avatar = screen.getByTestId('train-bot-avatar');
    expect(panel.contains(avatar)).toBe(true);
    expect(avatar.className).toContain('float-left');
    expect(screen.getByTestId('train-tour-step-count').textContent).toBe('1 / 2');
    expect(screen.getByTestId('train-bot-walkthrough').textContent).toBe(
      'Your result is in the highlighted box.',
    );
  });

  it('shows no step counter for a one-step part', () => {
    renderOverlay({ stepCount: 1 });

    expect(screen.queryByTestId('train-tour-step-count')).toBeNull();
  });

  it('hidden: only the corner badge renders, and a click reopens the tip', () => {
    const onReopen = vi.fn();
    renderOverlay({ hidden: true, onReopen });

    expect(screen.queryByTestId('train-tour-overlay')).toBeNull();
    fireEvent.click(screen.getByTestId('btn-train-tour-reopen'));
    expect(onReopen).toHaveBeenCalledTimes(1);
  });
});
