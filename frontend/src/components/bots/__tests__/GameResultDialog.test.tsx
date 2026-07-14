// @vitest-environment jsdom
/**
 * GameResultDialog.test.tsx (Phase 171 Plan 07, V-16/V-17) — the D-20/D-21
 * "Saved to your Library" link + guest not-auto-analyzed caveat render
 * strictly gated on `storeSucceeded`/`isGuest`, and the "Analyze this game"
 * CTA is never gated on the store (V-17).
 *
 * Mirrors `GameResultStrip.test.tsx` case-for-case — the strip is the
 * mobile/dismissed surface (CLAUDE.md: apply every change to both).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import {
  GameResultDialog,
  BOT_GAME_SAVED_COPY,
  GUEST_NOT_AUTO_ANALYZED_COPY,
} from '../GameResultDialog';
import type { BotGameOutcome } from '@/lib/botGameEnd';

afterEach(() => {
  cleanup();
});

const OUTCOME: BotGameOutcome = { reason: 'resignation', winner: 'white' };

function renderDialog(overrides: Partial<Parameters<typeof GameResultDialog>[0]> = {}) {
  const onDismiss = vi.fn();
  const onNewGame = vi.fn();
  const onAnalyze = vi.fn();
  render(
    <MemoryRouter>
      <GameResultDialog
        outcome={OUTCOME}
        userColor="white"
        open={true}
        onDismiss={onDismiss}
        onNewGame={onNewGame}
        onAnalyze={onAnalyze}
        storeSucceeded={false}
        isGuest={false}
        {...overrides}
      />
    </MemoryRouter>,
  );
  return { onDismiss, onNewGame, onAnalyze };
}

describe('GameResultDialog — Saved to Library + guest caveat (V-16)', () => {
  it('renders neither the save link nor the guest caveat when storeSucceeded is false (idle/pending/error)', () => {
    renderDialog({ storeSucceeded: false, isGuest: false });

    expect(screen.queryByTestId('result-saved-to-library')).toBeNull();
    expect(screen.queryByTestId('result-guest-analysis-caveat')).toBeNull();
  });

  it('renders neither row even for a guest while storeSucceeded is false — no partial-store hedge copy', () => {
    renderDialog({ storeSucceeded: false, isGuest: true });

    expect(screen.queryByTestId('result-saved-to-library')).toBeNull();
    expect(screen.queryByTestId('result-guest-analysis-caveat')).toBeNull();
  });

  it('renders the save link (not the caveat) once storeSucceeded is true for a non-guest', () => {
    renderDialog({ storeSucceeded: true, isGuest: false });

    const link = screen.getByTestId('result-saved-to-library');
    expect(link).toBeTruthy();
    expect(link.textContent).toBe(BOT_GAME_SAVED_COPY);
    expect(link.getAttribute('href')).toBe('/library/games');
    expect(screen.queryByTestId('result-guest-analysis-caveat')).toBeNull();
  });

  it('renders BOTH the save link and the guest caveat once storeSucceeded is true for a guest', () => {
    renderDialog({ storeSucceeded: true, isGuest: true });

    expect(screen.getByTestId('result-saved-to-library')).toBeTruthy();
    const caveat = screen.getByTestId('result-guest-analysis-caveat');
    expect(caveat.textContent).toBe(GUEST_NOT_AUTO_ANALYZED_COPY);
  });
});

describe('GameResultDialog — Analyze/New-game unaffected by the store (V-17)', () => {
  it('"Analyze this game" renders, is enabled, and fires onAnalyze even when storeSucceeded is false', () => {
    const { onAnalyze } = renderDialog({ storeSucceeded: false });

    const btn = screen.getByTestId('btn-analyze-game');
    expect(btn).toBeTruthy();
    expect((btn as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(btn);
    expect(onAnalyze).toHaveBeenCalledTimes(1);
  });

  it('"Analyze this game" still fires onAnalyze when storeSucceeded is true — not re-pointed at the stored game', () => {
    const { onAnalyze } = renderDialog({ storeSucceeded: true });

    fireEvent.click(screen.getByTestId('btn-analyze-game'));
    expect(onAnalyze).toHaveBeenCalledTimes(1);
  });

  it('"New game" still calls onNewGame regardless of storeSucceeded', () => {
    const { onNewGame } = renderDialog({ storeSucceeded: false });

    fireEvent.click(screen.getByTestId('btn-new-game'));
    expect(onNewGame).toHaveBeenCalledTimes(1);
  });
});
