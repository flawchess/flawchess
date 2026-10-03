// @vitest-environment jsdom
/**
 * Tests for ResumeGate (Phase 170 Plan 05) — the "Resume game?" overlay on
 * `/bots`. Covers the D-04 identity line, the Resume/Discard actions, and
 * the D-05 discard-confirms-first flow. The cancel-does-not-discard case is
 * the load-bearing one: an accidental discard destroys an in-progress game
 * with no server-side trace (SC2).
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { ResumeGate } from '../ResumeGate';
import type { BotGameSnapshot } from '@/lib/botGameSnapshot';

afterEach(() => {
  cleanup();
});

function buildSnapshot(overrides: Partial<BotGameSnapshot> = {}): BotGameSnapshot {
  return {
    version: 1,
    gameUuid: 'test-uuid',
    settings: {
      botElo: 1500,
      blend: 0.5,
      baseSeconds: 300,
      incrementSeconds: 3,
      userColor: 'white',
    },
    pgn: '1. e4 e5',
    whiteClockMs: 250_000,
    blackClockMs: 260_000,
    movesSinceLastDecline: 5,
    hasLeftBook: false,
    hasFiredLowTime: false,
    savedAt: Date.now(),
    ...overrides,
  };
}

describe('ResumeGate', () => {
  it('renders the game identity line (TC label, bot ELO, move count, age)', () => {
    const snapshot = buildSnapshot({ savedAt: Date.now() - 1000 });
    render(
      <ResumeGate
        snapshot={snapshot}
        plyCount={14}
        onResume={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );
    const gate = screen.getByTestId('resume-gate');
    expect(gate.textContent).toContain('Blitz 5+3');
    expect(gate.textContent).toContain('1500');
    expect(gate.textContent).toContain('14 moves');
    expect(gate.textContent).toContain('just now');
  });

  it('clicking Resume calls onResume exactly once and opens no dialog', () => {
    const onResume = vi.fn();
    const onDiscard = vi.fn();
    render(
      <ResumeGate
        snapshot={buildSnapshot()}
        plyCount={14}
        onResume={onResume}
        onDiscard={onDiscard}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-resume'));
    expect(onResume).toHaveBeenCalledTimes(1);
    expect(onDiscard).not.toHaveBeenCalled();
    expect(screen.queryByTestId('discard-confirm-dialog')).toBeNull();
  });

  it('clicking Discard does NOT call onDiscard — it only opens the confirm dialog', () => {
    const onDiscard = vi.fn();
    render(
      <ResumeGate
        snapshot={buildSnapshot()}
        plyCount={14}
        onResume={vi.fn()}
        onDiscard={onDiscard}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-discard'));
    expect(onDiscard).toHaveBeenCalledTimes(0);
    expect(screen.getByTestId('discard-confirm-dialog')).not.toBeNull();
  });

  it('confirming in the discard dialog calls onDiscard exactly once and closes the dialog', () => {
    const onDiscard = vi.fn();
    render(
      <ResumeGate
        snapshot={buildSnapshot()}
        plyCount={14}
        onResume={vi.fn()}
        onDiscard={onDiscard}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-discard'));
    fireEvent.click(screen.getByTestId('btn-discard-confirm'));
    expect(onDiscard).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId('discard-confirm-dialog')).toBeNull();
  });

  it('cancelling in the discard dialog closes it and calls onDiscard ZERO times', () => {
    const onDiscard = vi.fn();
    render(
      <ResumeGate
        snapshot={buildSnapshot()}
        plyCount={14}
        onResume={vi.fn()}
        onDiscard={onDiscard}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-discard'));
    fireEvent.click(screen.getByTestId('btn-discard-cancel'));
    expect(onDiscard).toHaveBeenCalledTimes(0);
    expect(screen.queryByTestId('discard-confirm-dialog')).toBeNull();
  });

  describe('formatRelativeAge (via the rendered identity line)', () => {
    it('renders "just now" under a minute', () => {
      const snapshot = buildSnapshot({ savedAt: Date.now() - 10_000 });
      render(
        <ResumeGate snapshot={snapshot} plyCount={2} onResume={vi.fn()} onDiscard={vi.fn()} />,
      );
      expect(screen.getByTestId('resume-gate').textContent).toContain('just now');
    });

    it('renders singular "1 minute ago"', () => {
      const snapshot = buildSnapshot({ savedAt: Date.now() - 60_000 });
      render(
        <ResumeGate snapshot={snapshot} plyCount={2} onResume={vi.fn()} onDiscard={vi.fn()} />,
      );
      expect(screen.getByTestId('resume-gate').textContent).toContain('1 minute ago');
    });

    it('renders plural "N minutes ago"', () => {
      const snapshot = buildSnapshot({ savedAt: Date.now() - 5 * 60_000 });
      render(
        <ResumeGate snapshot={snapshot} plyCount={2} onResume={vi.fn()} onDiscard={vi.fn()} />,
      );
      expect(screen.getByTestId('resume-gate').textContent).toContain('5 minutes ago');
    });

    it('renders singular "1 hour ago"', () => {
      const snapshot = buildSnapshot({ savedAt: Date.now() - 60 * 60_000 });
      render(
        <ResumeGate snapshot={snapshot} plyCount={2} onResume={vi.fn()} onDiscard={vi.fn()} />,
      );
      expect(screen.getByTestId('resume-gate').textContent).toContain('1 hour ago');
    });

    it('renders plural "N hours ago"', () => {
      const snapshot = buildSnapshot({ savedAt: Date.now() - 3 * 60 * 60_000 });
      render(
        <ResumeGate snapshot={snapshot} plyCount={2} onResume={vi.fn()} onDiscard={vi.fn()} />,
      );
      expect(screen.getByTestId('resume-gate').textContent).toContain('3 hours ago');
    });

    it('renders singular "1 day ago"', () => {
      const snapshot = buildSnapshot({ savedAt: Date.now() - 24 * 60 * 60_000 });
      render(
        <ResumeGate snapshot={snapshot} plyCount={2} onResume={vi.fn()} onDiscard={vi.fn()} />,
      );
      expect(screen.getByTestId('resume-gate').textContent).toContain('1 day ago');
    });

    it('renders plural "N days ago"', () => {
      const snapshot = buildSnapshot({ savedAt: Date.now() - 2 * 24 * 60 * 60_000 });
      render(
        <ResumeGate snapshot={snapshot} plyCount={2} onResume={vi.fn()} onDiscard={vi.fn()} />,
      );
      expect(screen.getByTestId('resume-gate').textContent).toContain('2 days ago');
    });
  });

  describe('formatTcLabel (via the rendered identity line)', () => {
    it('formatTcLabel(300, 3) -> "Blitz 5+3"', () => {
      const snapshot = buildSnapshot({
        settings: {
          botElo: 1500,
          blend: 0.5,
          baseSeconds: 300,
          incrementSeconds: 3,
          userColor: 'white',
        },
      });
      render(
        <ResumeGate snapshot={snapshot} plyCount={2} onResume={vi.fn()} onDiscard={vi.fn()} />,
      );
      expect(screen.getByTestId('resume-gate').textContent).toContain('Blitz 5+3');
    });

    it('formatTcLabel(600, 0) -> "Rapid 10+0"', () => {
      const snapshot = buildSnapshot({
        settings: {
          botElo: 1500,
          blend: 0.5,
          baseSeconds: 600,
          incrementSeconds: 0,
          userColor: 'white',
        },
      });
      render(
        <ResumeGate snapshot={snapshot} plyCount={2} onResume={vi.fn()} onDiscard={vi.fn()} />,
      );
      expect(screen.getByTestId('resume-gate').textContent).toContain('Rapid 10+0');
    });

    it('formatTcLabel(1800, 20) -> "Classical 30+20"', () => {
      const snapshot = buildSnapshot({
        settings: {
          botElo: 1500,
          blend: 0.5,
          baseSeconds: 1800,
          incrementSeconds: 20,
          userColor: 'white',
        },
      });
      render(
        <ResumeGate snapshot={snapshot} plyCount={2} onResume={vi.fn()} onDiscard={vi.fn()} />,
      );
      expect(screen.getByTestId('resume-gate').textContent).toContain('Classical 30+20');
    });
  });
});

// Phase 229 (D-12 group 3): Resume and the CONFIRMED discard are tracked; the
// first Discard click only opens the confirm dialog and sends nothing.
describe('ResumeGate feature events (Phase 229)', () => {
  const track = vi.fn();

  beforeEach(() => {
    track.mockClear();
    window.umami = { track, identify: vi.fn() };
    window.history.pushState({}, '', '/bots');
  });

  afterEach(() => {
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  function renderGate(): { onResume: () => void; onDiscard: () => void } {
    const onResume = vi.fn();
    const onDiscard = vi.fn();
    render(
      <ResumeGate snapshot={buildSnapshot()} plyCount={14} onResume={onResume} onDiscard={onDiscard} />,
    );
    return { onResume, onDiscard };
  }

  it('Resume fires one bot-resume action', () => {
    const { onResume } = renderGate();
    expect(track).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('btn-resume'));
    expect(onResume).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('action', { page: 'bots', target: 'bot-resume' });
  });

  it('the first Discard click and Cancel send nothing; the confirmed discard fires bot-discard once', () => {
    renderGate();
    fireEvent.click(screen.getByTestId('btn-discard'));
    expect(track).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('btn-discard-cancel'));
    expect(track).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('btn-discard'));
    fireEvent.click(screen.getByTestId('btn-discard-confirm'));
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('action', { page: 'bots', target: 'bot-discard' });
  });
});
