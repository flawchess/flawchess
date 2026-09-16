// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { BotGameMobileBar } from '@/components/bots/BotGameMobileBar';

afterEach(() => {
  cleanup();
});

function renderBar(overrides?: Partial<Parameters<typeof BotGameMobileBar>[0]>) {
  const onResign = vi.fn();
  const onBack = vi.fn();
  const onForward = vi.fn();
  const onFlip = vi.fn();
  render(
    <BotGameMobileBar
      onResign={onResign}
      onBack={onBack}
      onForward={onForward}
      onFlip={onFlip}
      canGoBack={true}
      canGoForward={true}
      {...overrides}
    />,
  );
  return { onResign, onBack, onForward, onFlip };
}

describe('BotGameMobileBar (Phase 223, BOTVOICE-05/D-10)', () => {
  it('renders exactly four actions: Resign, Back, Forward, Flip', () => {
    renderBar();
    expect(screen.getByTestId('bot-game-mobile-bar')).toBeTruthy();
    expect(screen.getByTestId('board-btn-resign')).toBeTruthy();
    expect(screen.getByTestId('board-btn-back')).toBeTruthy();
    expect(screen.getByTestId('board-btn-forward')).toBeTruthy();
    expect(screen.getByTestId('board-btn-flip')).toBeTruthy();
    // Closed dialog content is not mounted, so exactly 4 buttons exist.
    expect(screen.getAllByRole('button')).toHaveLength(4);
  });

  it('Back and Forward fire their callbacks exactly once each', () => {
    const { onBack, onForward, onFlip } = renderBar();
    fireEvent.click(screen.getByTestId('board-btn-back'));
    fireEvent.click(screen.getByTestId('board-btn-forward'));
    fireEvent.click(screen.getByTestId('board-btn-flip'));
    expect(onBack).toHaveBeenCalledTimes(1);
    expect(onForward).toHaveBeenCalledTimes(1);
    expect(onFlip).toHaveBeenCalledTimes(1);
  });

  it('disables Back when canGoBack is false and Forward when canGoForward is false', () => {
    renderBar({ canGoBack: false, canGoForward: false });
    expect(screen.getByTestId('board-btn-back')).toHaveProperty('disabled', true);
    expect(screen.getByTestId('board-btn-forward')).toHaveProperty('disabled', true);
    expect(screen.getByTestId('board-btn-flip')).toHaveProperty('disabled', false);
  });

  it('Resign opens the two-step confirm dialog; only the confirm button calls through', () => {
    const { onResign } = renderBar();
    expect(screen.queryByTestId('resign-confirm-dialog')).toBeNull();

    fireEvent.click(screen.getByTestId('board-btn-resign'));
    expect(screen.getByTestId('resign-confirm-dialog')).toBeTruthy();
    expect(onResign).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText('Cancel'));
    expect(onResign).not.toHaveBeenCalled();
    expect(screen.queryByTestId('resign-confirm-dialog')).toBeNull();

    fireEvent.click(screen.getByTestId('board-btn-resign'));
    fireEvent.click(screen.getByTestId('board-btn-resign-confirm'));
    expect(onResign).toHaveBeenCalledTimes(1);
  });

  // Phase 223 UAT: every action carries a visible label under its icon, the
  // same shape as the main nav bar this one replaces.
  it('labels all four actions Resign / Back / Next / Flip', () => {
    renderBar();
    expect(screen.getByTestId('board-btn-resign').textContent).toContain('Resign');
    expect(screen.getByTestId('board-btn-back').textContent).toContain('Back');
    expect(screen.getByTestId('board-btn-forward').textContent).toContain('Next');
    expect(screen.getByTestId('board-btn-flip').textContent).toContain('Flip');
  });

  it('never uses a sub-text-sm font-size utility anywhere in the bar', () => {
    renderBar();
    expect(screen.getByTestId('bot-game-mobile-bar').innerHTML).not.toContain('text-xs');
  });
});
