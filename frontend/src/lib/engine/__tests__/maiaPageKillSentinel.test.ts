// @vitest-environment jsdom
/**
 * maiaPageKillSentinel.ts unit tests (SEED-158, 2026-09-07): the record must
 * exist exactly while Maia is alive AND the page is in the foreground, must
 * vanish on every ordinary end of a page, and a leftover record on the next
 * load must become exactly one Sentry event carrying the previous session's
 * facts in context (never in the message).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as Sentry from '@sentry/react';
import {
  armMaiaPageKillSentinel,
  disarmMaiaPageKillSentinel,
  noteMaiaDispatch,
  previousMaiaPageKillSummary,
  reportMaiaPageKillFromPreviousSession,
  resetMaiaPageKillSentinelForTests,
} from '../maiaPageKillSentinel';

vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));

const KEY = 'flawchess:maia:page-session';
const FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';

function record(): Record<string, unknown> | null {
  const raw = localStorage.getItem(KEY);
  return raw === null ? null : (JSON.parse(raw) as Record<string, unknown>);
}

function setVisibility(state: 'visible' | 'hidden'): void {
  Object.defineProperty(document, 'visibilityState', { value: state, configurable: true });
  document.dispatchEvent(new Event('visibilitychange'));
}

describe('maiaPageKillSentinel', () => {
  beforeEach(() => {
    localStorage.clear();
    resetMaiaPageKillSentinelForTests();
    vi.mocked(Sentry.captureException).mockClear();
    setVisibility('visible');
  });

  afterEach(() => {
    resetMaiaPageKillSentinelForTests();
    localStorage.clear();
  });

  it('arm writes the record; dispatches update it; disarm removes it', () => {
    armMaiaPageKillSentinel({ backend: 'webgpu', numThreads: 1 });
    expect(record()).toMatchObject({ backend: 'webgpu', numThreads: 1, dispatches: 0, last: null, ios: false });

    noteMaiaDispatch(FEN, 11);
    noteMaiaDispatch(FEN, 10);
    expect(record()).toMatchObject({ dispatches: 2, last: { batch: 10, fen: FEN } });

    disarmMaiaPageKillSentinel();
    expect(record()).toBeNull();
    // A dispatch after disarm is ignored (no worker is running).
    noteMaiaDispatch(FEN, 1);
    expect(record()).toBeNull();
  });

  it('is removed on pagehide (an ordinary navigation / reload / close)', () => {
    armMaiaPageKillSentinel({ backend: 'wasm', numThreads: 2 });
    window.dispatchEvent(new Event('pagehide'));
    expect(record()).toBeNull();
  });

  it('is removed while the document is hidden and restored when it becomes visible again', () => {
    armMaiaPageKillSentinel({ backend: 'webgpu', numThreads: 1 });
    noteMaiaDispatch(FEN, 21);

    setVisibility('hidden');
    expect(record()).toBeNull();
    // A dispatch while hidden must not resurrect the record.
    noteMaiaDispatch(FEN, 1);
    expect(record()).toBeNull();

    setVisibility('visible');
    expect(record()).toMatchObject({ dispatches: 2 });
  });

  it('a leftover record on the next load is captured once, with fixed message, tags and context, then cleared', () => {
    const leftover = {
      armedAt: 1000,
      backend: 'webgpu',
      numThreads: 1,
      ios: true,
      pathname: '/analysis',
      dispatches: 7,
      last: { at: 5000, batch: 10, fen: FEN },
    };
    localStorage.setItem(KEY, JSON.stringify(leftover));

    const summary = reportMaiaPageKillFromPreviousSession();

    expect(summary).toContain('KILLED last session');
    expect(previousMaiaPageKillSummary()).toBe(summary);
    expect(record()).toBeNull();
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
    expect(Sentry.captureException).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Maia worker: page was killed while Maia was active' }),
      expect.objectContaining({
        tags: { source: 'maia-page-kill-sentinel', backend: 'webgpu', maia_failure: 'page-killed', ios: 'true' },
        contexts: expect.objectContaining({
          maia_page_kill: expect.objectContaining({
            pathname: '/analysis',
            dispatches: 7,
            last: leftover.last,
            sessionAgeMs: expect.any(Number),
            sinceLastDispatchMs: expect.any(Number),
          }),
          engine_device: expect.objectContaining({ numThreads: 1 }),
        }),
      }),
    );
  });

  it('reports nothing when there is no record, and never throws on a garbage record', () => {
    expect(reportMaiaPageKillFromPreviousSession()).toBeNull();
    expect(Sentry.captureException).not.toHaveBeenCalled();

    localStorage.setItem(KEY, '{not json');
    expect(reportMaiaPageKillFromPreviousSession()).toBeNull();
    expect(record()).toBeNull();
    expect(Sentry.captureException).not.toHaveBeenCalled();
  });
});
