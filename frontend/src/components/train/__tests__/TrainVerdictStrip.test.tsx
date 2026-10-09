// @vitest-environment jsdom
/**
 * TrainVerdictStrip.test.tsx — Phase 237 plan 08 (D-07/D-08/D-14).
 *
 * The strip is collapsed on mount, expands on a tap, and fires the Umami
 * `panel-open` / `train-verdict-strip` event exactly once per OPEN (from the click
 * handler: never on mount, never on collapse). The expansion carries the shared
 * verdict body, which holds no Analyze button.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { TrainVerdictDetails } from '@/components/train/TrainVerdictDetails';
import { TrainVerdictStrip } from '@/components/train/TrainVerdictStrip';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import { verdictCopy, verdictStripLine } from '@/lib/trainBotCopy';
import { scorePuzzle } from '@/lib/trainScore';
import type { SolveResponse } from '@/types/train';

const PERSONA = PERSONA_REGISTRY['wall-1800'];
const VERDICT: SolveResponse = {
  correct_guess: true,
  correct_move: true,
  move_quality: 'good',
  puzzle_type: 'sharp',
  item_status: 'active',
  streak: 1,
  due_date: '2026-07-28',
  session_complete: false,
  source: 'sr_item',
};

const track = vi.fn();

beforeEach(() => {
  track.mockClear();
  window.umami = { track, identify: vi.fn() };
  window.history.pushState({}, '', '/train');
});

afterEach(() => {
  cleanup();
  delete window.umami;
  window.history.pushState({}, '', '/');
});

function renderStrip(onExpand?: () => void): void {
  render(
    <TrainVerdictStrip
      persona={PERSONA}
      points={scorePuzzle(VERDICT.correct_guess, VERDICT.move_quality)}
      line={verdictStripLine(VERDICT.correct_guess, VERDICT.move_quality, true)}
      onExpand={onExpand}
    >
      <TrainVerdictDetails
        verdict={VERDICT}
        opening={verdictCopy(3, true, 'good', true, () => 0)}
        isBest
        sessionDate="2026-07-27"
        expiresOn={undefined}
        isWarmup={false}
        audience={{ hasGames: true, isGuest: false }}
        guess="critical"
        guessProse="You spotted the only move."
        motif={null}
        alsoFineSanList=""
      />
    </TrainVerdictStrip>,
  );
}

describe('TrainVerdictStrip', () => {
  it('starts collapsed with the avatar, the total and the one-line clause, and sends nothing on mount', () => {
    renderStrip();
    const strip = screen.getByTestId('train-verdict-strip');
    expect(strip.getAttribute('aria-expanded')).toBe('false');
    expect(screen.getByTestId('train-verdict-strip-line').textContent).toBe('Right call, best move');
    expect(screen.getByTestId('train-verdict-strip-points').textContent).toBe('+3');
    const avatar = screen.getByTestId('train-verdict-strip-avatar');
    expect(avatar.getAttribute('data-persona-id')).toBe(PERSONA.id);
    expect(avatar.getAttribute('data-persona-name')).toBe(PERSONA.name);
    expect(screen.queryByTestId('train-verdict-strip-details')).toBeNull();
    expect(track).not.toHaveBeenCalled();
  });

  it('a click opens it, calls onExpand once and sends exactly one panel-open event', () => {
    const onExpand = vi.fn();
    renderStrip(onExpand);
    fireEvent.click(screen.getByTestId('train-verdict-strip'));
    expect(screen.getByTestId('train-verdict-strip').getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByTestId('train-verdict-strip-details')).not.toBeNull();
    expect(onExpand).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('panel-open', { page: 'train', target: 'train-verdict-strip' });
  });

  it('a second click closes it and sends nothing more', () => {
    const onExpand = vi.fn();
    renderStrip(onExpand);
    fireEvent.click(screen.getByTestId('train-verdict-strip'));
    track.mockClear();
    fireEvent.click(screen.getByTestId('train-verdict-strip'));
    expect(screen.getByTestId('train-verdict-strip').getAttribute('aria-expanded')).toBe('false');
    expect(screen.queryByTestId('train-verdict-strip-details')).toBeNull();
    expect(track).not.toHaveBeenCalled();
    expect(onExpand).toHaveBeenCalledTimes(1);
  });

  it('re-opening fires once more (once per open), and the details carry the full feedback with no Analyze button', () => {
    renderStrip();
    fireEvent.click(screen.getByTestId('train-verdict-strip'));
    fireEvent.click(screen.getByTestId('train-verdict-strip'));
    fireEvent.click(screen.getByTestId('train-verdict-strip'));
    expect(track).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId('train-bot-verdict-line').textContent).toContain('Right call');
    expect(screen.getByTestId('train-bot-pill-guess').textContent).toBe('+1');
    expect(screen.getByTestId('train-verdict-guess-prose').textContent).toBe('You spotted the only move.');
    expect(screen.queryByTestId('btn-train-analyze')).toBeNull();
  });
});
