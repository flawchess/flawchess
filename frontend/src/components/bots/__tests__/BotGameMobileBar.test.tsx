// @vitest-environment jsdom
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

vi.mock('@/components/settings/SettingsSheetButton', () => ({
  SettingsSheet: ({ open }: { open: boolean }) => (open ? <div data-testid="settings-sheet" /> : null),
}));

import { BotGameMobileBar } from '@/components/bots/BotGameMobileBar';

beforeAll(() => {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver = ResizeObserverStub;
});

afterEach(() => {
  cleanup();
});

/** Radix DropdownMenu opens on pointerdown or Enter, never on a bare click. */
function openMenu(): void {
  fireEvent.keyDown(screen.getByTestId('bot-game-btn-more'), { key: 'Enter' });
}

function renderBar(overrides?: Partial<Parameters<typeof BotGameMobileBar>[0]>) {
  const onResign = vi.fn();
  const onBack = vi.fn();
  const onForward = vi.fn();
  const onFlip = vi.fn();
  const onLeave = vi.fn();
  render(
    <BotGameMobileBar
      onResign={onResign}
      onBack={onBack}
      onForward={onForward}
      onFlip={onFlip}
      onLeave={onLeave}
      canGoBack={true}
      canGoForward={true}
      {...overrides}
    />,
  );
  return { onResign, onBack, onForward, onFlip, onLeave };
}

describe('BotGameMobileBar', () => {
  it('renders exactly four actions: Resign, Back, Forward, More', () => {
    renderBar();
    expect(screen.getByTestId('bot-game-mobile-bar')).toBeTruthy();
    expect(screen.getByTestId('board-btn-resign')).toBeTruthy();
    expect(screen.getByTestId('board-btn-back')).toBeTruthy();
    expect(screen.getByTestId('board-btn-forward')).toBeTruthy();
    expect(screen.getByTestId('bot-game-btn-more')).toBeTruthy();
    // Closed menu and dialog content is not mounted, so exactly 4 buttons exist.
    expect(screen.getAllByRole('button')).toHaveLength(4);
  });

  it('Back and Forward fire their callbacks exactly once each', () => {
    const { onBack, onForward } = renderBar();
    fireEvent.click(screen.getByTestId('board-btn-back'));
    fireEvent.click(screen.getByTestId('board-btn-forward'));
    expect(onBack).toHaveBeenCalledTimes(1);
    expect(onForward).toHaveBeenCalledTimes(1);
  });

  it('disables Back when canGoBack is false and Forward when canGoForward is false', () => {
    renderBar({ canGoBack: false, canGoForward: false });
    expect(screen.getByTestId('board-btn-back')).toHaveProperty('disabled', true);
    expect(screen.getByTestId('board-btn-forward')).toHaveProperty('disabled', true);
    expect(screen.getByTestId('bot-game-btn-more')).toHaveProperty('disabled', false);
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

  // Every action carries a visible label under its icon, the
  // same shape as the main nav bar this one replaces.
  it('labels all four actions Resign / Back / Next / More', () => {
    renderBar();
    expect(screen.getByTestId('board-btn-resign').textContent).toContain('Resign');
    expect(screen.getByTestId('board-btn-back').textContent).toContain('Back');
    expect(screen.getByTestId('board-btn-forward').textContent).toContain('Next');
    expect(screen.getByTestId('bot-game-btn-more').textContent).toContain('More');
  });

  it('the More menu flips the board', () => {
    const { onFlip, onLeave } = renderBar();
    openMenu();
    fireEvent.click(screen.getByTestId('board-btn-flip'));
    expect(onFlip).toHaveBeenCalledTimes(1);
    expect(onLeave).not.toHaveBeenCalled();
  });

  it('the More menu leads back to the bot list', () => {
    const { onLeave } = renderBar();
    openMenu();
    fireEvent.click(screen.getByTestId('bots-back'));
    expect(onLeave).toHaveBeenCalledTimes(1);
  });

  it('the settings sheet stays open while the game goes on (the bar re-renders with a new ply)', () => {
    const props = {
      onResign: vi.fn(), onBack: vi.fn(), onForward: vi.fn(), onFlip: vi.fn(), onLeave: vi.fn(),
      canGoForward: false,
    };
    const { rerender } = render(<BotGameMobileBar {...props} canGoBack={false} />);
    openMenu();
    fireEvent.click(screen.getByTestId('bot-game-menu-settings'));
    expect(screen.getByTestId('settings-sheet')).toBeTruthy();
    rerender(<BotGameMobileBar {...props} canGoBack />);
    expect(screen.getByTestId('settings-sheet')).toBeTruthy();
  });

  it('never uses a sub-text-sm font-size utility anywhere in the bar', () => {
    renderBar();
    expect(screen.getByTestId('bot-game-mobile-bar').innerHTML).not.toContain('text-xs');
  });
});
