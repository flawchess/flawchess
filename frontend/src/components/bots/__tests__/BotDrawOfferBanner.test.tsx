// @vitest-environment jsdom
/**
 * BotDrawOfferBanner.test.tsx (Phase 183 Plan 05, D-07) — a non-blocking
 * inline banner for the bot's outgoing draw offer: persona-named prompt,
 * working Accept/Decline, and nothing rendered while no offer is live.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { BotDrawOfferBanner } from '../BotDrawOfferBanner';

afterEach(() => {
  cleanup();
});

describe('BotDrawOfferBanner', () => {
  it('renders nothing when no offer is live', () => {
    render(
      <BotDrawOfferBanner
        offerLive={false}
        personaName="Ziggy the Wasp"
        onAccept={vi.fn()}
        onDecline={vi.fn()}
      />,
    );

    expect(screen.queryByTestId('bot-draw-offer-banner')).toBeNull();
  });

  it('renders the persona-named draw-offer prompt with Accept and Decline', () => {
    render(
      <BotDrawOfferBanner
        offerLive={true}
        personaName="Ziggy the Wasp"
        onAccept={vi.fn()}
        onDecline={vi.fn()}
      />,
    );

    const banner = screen.getByTestId('bot-draw-offer-banner');
    expect(banner.textContent).toContain('Ziggy the Wasp offers a draw');
    expect(screen.getByTestId('btn-accept-bot-draw')).toBeTruthy();
    expect(screen.getByTestId('btn-decline-bot-draw')).toBeTruthy();
  });

  it('falls back to the generic "The bot offers a draw" copy when personaName is null (Custom game)', () => {
    render(
      <BotDrawOfferBanner offerLive={true} personaName={null} onAccept={vi.fn()} onDecline={vi.fn()} />,
    );

    expect(screen.getByTestId('bot-draw-offer-banner').textContent).toContain(
      'The bot offers a draw',
    );
  });

  it('Accept calls onAccept', () => {
    const onAccept = vi.fn();
    render(
      <BotDrawOfferBanner
        offerLive={true}
        personaName="Ziggy the Wasp"
        onAccept={onAccept}
        onDecline={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByTestId('btn-accept-bot-draw'));
    expect(onAccept).toHaveBeenCalledTimes(1);
  });

  it('Decline calls onDecline', () => {
    const onDecline = vi.fn();
    render(
      <BotDrawOfferBanner
        offerLive={true}
        personaName="Ziggy the Wasp"
        onAccept={vi.fn()}
        onDecline={onDecline}
      />,
    );

    fireEvent.click(screen.getByTestId('btn-decline-bot-draw'));
    expect(onDecline).toHaveBeenCalledTimes(1);
  });

  it('never uses sub-text-sm font-size utilities', () => {
    render(
      <BotDrawOfferBanner
        offerLive={true}
        personaName="Ziggy the Wasp"
        onAccept={vi.fn()}
        onDecline={vi.fn()}
      />,
    );

    expect(screen.getByTestId('bot-draw-offer-banner').innerHTML).not.toContain('text-xs');
  });
});
