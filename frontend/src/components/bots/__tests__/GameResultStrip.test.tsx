// @vitest-environment jsdom
/**
 * GameResultStrip.test.tsx (Phase 171 Plan 07, V-16/V-17; Quick 260714-rj5
 * retires V-17) — mirrors `GameResultDialog.test.tsx` case-for-case. The
 * strip IS the mobile/dismissed surface (CLAUDE.md: apply every change to
 * both) — a dialog-only test suite would let this surface silently regress.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import {
  GameResultStrip,
} from '../GameResultStrip';
import { BOT_GAME_SAVED_COPY, GUEST_NOT_AUTO_ANALYZED_COPY } from '../GameResultDialog';
import type { BotGameOutcome } from '@/lib/botGameEnd';

afterEach(() => {
  cleanup();
});

const OUTCOME: BotGameOutcome = { reason: 'resignation', winner: 'white' };

function renderStrip(overrides: Partial<Parameters<typeof GameResultStrip>[0]> = {}) {
  const onNewGame = vi.fn();
  const onAnalyze = vi.fn();
  const onRematch = vi.fn();
  render(
    <MemoryRouter>
      <GameResultStrip
        outcome={OUTCOME}
        userColor="white"
        onNewGame={onNewGame}
        onAnalyze={onAnalyze}
        storeSucceeded={false}
        isGuest={false}
        analyzeBusy={false}
        personaName={null}
        onRematch={onRematch}
        {...overrides}
      />
    </MemoryRouter>,
  );
  return { onNewGame, onAnalyze, onRematch };
}

describe('GameResultStrip — Saved to Library + guest caveat (V-16)', () => {
  it('renders neither the save link nor the guest caveat when storeSucceeded is false (idle/pending/error)', () => {
    renderStrip({ storeSucceeded: false, isGuest: false });

    expect(screen.queryByTestId('strip-saved-to-library')).toBeNull();
    expect(screen.queryByTestId('strip-guest-analysis-caveat')).toBeNull();
  });

  it('renders neither row even for a guest while storeSucceeded is false — no partial-store hedge copy', () => {
    renderStrip({ storeSucceeded: false, isGuest: true });

    expect(screen.queryByTestId('strip-saved-to-library')).toBeNull();
    expect(screen.queryByTestId('strip-guest-analysis-caveat')).toBeNull();
  });

  it('renders the save link (not the caveat) once storeSucceeded is true for a non-guest', () => {
    renderStrip({ storeSucceeded: true, isGuest: false });

    const link = screen.getByTestId('strip-saved-to-library');
    expect(link).toBeTruthy();
    expect(link.textContent).toBe(BOT_GAME_SAVED_COPY);
    expect(link.getAttribute('href')).toBe('/library/games');
    expect(screen.queryByTestId('strip-guest-analysis-caveat')).toBeNull();
  });

  it('renders BOTH the save link and the guest caveat once storeSucceeded is true for a guest', () => {
    renderStrip({ storeSucceeded: true, isGuest: true });

    expect(screen.getByTestId('strip-saved-to-library')).toBeTruthy();
    const caveat = screen.getByTestId('strip-guest-analysis-caveat');
    expect(caveat.textContent).toBe(GUEST_NOT_AUTO_ANALYZED_COPY);
  });
});

describe('GameResultStrip — Analyze is store-gated (Quick 260714-rj5, retires V-17)', () => {
  it('"Analyze this game" is disabled while analyzeBusy is true — click does not fire onAnalyze', () => {
    const { onAnalyze } = renderStrip({ analyzeBusy: true });

    const btn = screen.getByTestId('strip-btn-analyze-game') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    fireEvent.click(btn);
    expect(onAnalyze).not.toHaveBeenCalled();
  });

  it('"Analyze this game" is enabled and fires onAnalyze once analyzeBusy is false, regardless of storeSucceeded', () => {
    const { onAnalyze } = renderStrip({ analyzeBusy: false, storeSucceeded: false });

    const btn = screen.getByTestId('strip-btn-analyze-game') as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
    fireEvent.click(btn);
    expect(onAnalyze).toHaveBeenCalledTimes(1);
  });

  it('"Analyze this game" still fires onAnalyze when storeSucceeded is true and analyzeBusy is false', () => {
    const { onAnalyze } = renderStrip({ analyzeBusy: false, storeSucceeded: true });

    fireEvent.click(screen.getByTestId('strip-btn-analyze-game'));
    expect(onAnalyze).toHaveBeenCalledTimes(1);
  });

  it('"New game" still calls onNewGame regardless of storeSucceeded/analyzeBusy', () => {
    const { onNewGame } = renderStrip({ storeSucceeded: false, analyzeBusy: true });

    fireEvent.click(screen.getByTestId('strip-btn-new-game'));
    expect(onNewGame).toHaveBeenCalledTimes(1);
  });
});

describe('GameResultStrip — persona-named copy + Rematch/New opponent (Phase 183, D-06/D-08, mobile parity)', () => {
  const BOT_LOSS_OUTCOME: BotGameOutcome = { reason: 'checkmate', winner: 'black' };

  it('renders the generic title and NO Rematch button for a Custom game (personaName null)', () => {
    renderStrip({ personaName: null, outcome: BOT_LOSS_OUTCOME });

    expect(screen.getByText('You lost — checkmate')).toBeTruthy();
    expect(screen.queryByTestId('strip-btn-rematch')).toBeNull();
    expect(screen.getByTestId('strip-btn-new-game').textContent).toBe('New opponent');
  });

  it('renders the SAME persona-named title as GameResultDialog and a working "Rematch <Persona>" (mobile parity)', () => {
    const { onRematch } = renderStrip({
      personaName: 'Ziggy the Wasp',
      outcome: BOT_LOSS_OUTCOME,
    });

    expect(screen.getByText('Ziggy the Wasp wins — checkmate')).toBeTruthy();
    const rematchBtn = screen.getByTestId('strip-btn-rematch');
    expect(rematchBtn.textContent).toBe('Rematch Ziggy the Wasp');

    fireEvent.click(rematchBtn);
    expect(onRematch).toHaveBeenCalledTimes(1);
  });
});
