// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { GameControls } from '@/components/bots/GameControls';
import { TooltipProvider } from '@/components/ui/tooltip';

afterEach(() => {
  cleanup();
});

function renderControls(overrides?: Partial<Parameters<typeof GameControls>[0]>) {
  const onOfferDrawConfirmed = vi.fn();
  const onResignConfirmed = vi.fn();
  // The app mounts one TooltipProvider at its root; the cooldown branch's
  // Tooltip needs it here too.
  render(
    <TooltipProvider>
      <GameControls
        offerDrawDisabled={false}
        drawCooldownActive={false}
        onOfferDrawConfirmed={onOfferDrawConfirmed}
        onResignConfirmed={onResignConfirmed}
        {...overrides}
      />
    </TooltipProvider>,
  );
  return { onOfferDrawConfirmed, onResignConfirmed };
}

describe('GameControls — user draw offer (quick 260916)', () => {
  it('Draw opens the confirm dialog; only the confirm button calls through, and it closes the dialog', () => {
    const { onOfferDrawConfirmed } = renderControls();
    expect(screen.queryByTestId('draw-offer-confirm-dialog')).toBeNull();

    fireEvent.click(screen.getByTestId('board-btn-offer-draw'));
    expect(screen.getByTestId('draw-offer-confirm-dialog')).toBeTruthy();
    expect(onOfferDrawConfirmed).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('board-btn-offer-draw-cancel'));
    expect(onOfferDrawConfirmed).not.toHaveBeenCalled();
    expect(screen.queryByTestId('draw-offer-confirm-dialog')).toBeNull();

    fireEvent.click(screen.getByTestId('board-btn-offer-draw'));
    fireEvent.click(screen.getByTestId('board-btn-offer-draw-confirm'));
    expect(onOfferDrawConfirmed).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId('draw-offer-confirm-dialog')).toBeNull();
  });

  it('a disabled Draw button never opens the dialog', () => {
    const { onOfferDrawConfirmed } = renderControls({ offerDrawDisabled: true });
    const button = screen.getByTestId('board-btn-offer-draw');
    expect(button).toHaveProperty('disabled', true);
    fireEvent.click(button);
    expect(screen.queryByTestId('draw-offer-confirm-dialog')).toBeNull();
    expect(onOfferDrawConfirmed).not.toHaveBeenCalled();
  });

  it('wraps the button in the cooldown tooltip host only while the cooldown is the reason', () => {
    renderControls({ offerDrawDisabled: true, drawCooldownActive: true });
    // The Tooltip's trigger `<span>` becomes the button's parent in the cooldown branch.
    expect(screen.getByTestId('board-btn-offer-draw').parentElement?.tagName).toBe('SPAN');

    cleanup();
    renderControls({ offerDrawDisabled: true, drawCooldownActive: false });
    expect(screen.getByTestId('board-btn-offer-draw').parentElement?.tagName).toBe('DIV');
  });

  it('Resign keeps its own two-step dialog, independent of the draw dialog', () => {
    const { onResignConfirmed, onOfferDrawConfirmed } = renderControls();
    fireEvent.click(screen.getByTestId('board-btn-resign'));
    expect(screen.getByTestId('resign-confirm-dialog')).toBeTruthy();
    expect(screen.queryByTestId('draw-offer-confirm-dialog')).toBeNull();
    fireEvent.click(screen.getByTestId('board-btn-resign-confirm'));
    expect(onResignConfirmed).toHaveBeenCalledTimes(1);
    expect(onOfferDrawConfirmed).not.toHaveBeenCalled();
  });
});
