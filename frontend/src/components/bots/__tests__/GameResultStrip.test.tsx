// @vitest-environment jsdom
/**
 * GameResultStrip.test.tsx (Phase 171 Plan 07, V-16/V-17) — mirrors
 * `GameResultDialog.test.tsx` case-for-case. The strip IS the mobile/
 * dismissed surface (CLAUDE.md: apply every change to both) — a
 * dialog-only test suite would let this surface silently regress.
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
  render(
    <MemoryRouter>
      <GameResultStrip
        outcome={OUTCOME}
        userColor="white"
        onNewGame={onNewGame}
        onAnalyze={onAnalyze}
        storeSucceeded={false}
        isGuest={false}
        {...overrides}
      />
    </MemoryRouter>,
  );
  return { onNewGame, onAnalyze };
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

describe('GameResultStrip — Analyze/New-game unaffected by the store (V-17)', () => {
  it('"Analyze this game" renders, is enabled, and fires onAnalyze even when storeSucceeded is false', () => {
    const { onAnalyze } = renderStrip({ storeSucceeded: false });

    const btn = screen.getByTestId('strip-btn-analyze-game');
    expect(btn).toBeTruthy();
    expect((btn as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(btn);
    expect(onAnalyze).toHaveBeenCalledTimes(1);
  });

  it('"Analyze this game" still fires onAnalyze when storeSucceeded is true — not re-pointed at the stored game', () => {
    const { onAnalyze } = renderStrip({ storeSucceeded: true });

    fireEvent.click(screen.getByTestId('strip-btn-analyze-game'));
    expect(onAnalyze).toHaveBeenCalledTimes(1);
  });

  it('"New game" still calls onNewGame regardless of storeSucceeded', () => {
    const { onNewGame } = renderStrip({ storeSucceeded: false });

    fireEvent.click(screen.getByTestId('strip-btn-new-game'));
    expect(onNewGame).toHaveBeenCalledTimes(1);
  });
});
