// @vitest-environment jsdom
/**
 * useBoardNavigationInput tests (Phase 237 Plan 02): the optional `goHome` binding
 * for the Home key. The ArrowLeft/ArrowRight/wheel behavior itself is covered
 * through useAnalysisBoard.test.ts; this file pins what the new option adds and
 * that omitting it leaves Home alone for Analysis and Openings.
 */
import { fireEvent, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useBoardNavigationInput } from '@/hooks/useBoardNavigationInput';
import type { BoardNavigationInputOptions } from '@/hooks/useBoardNavigationInput';

let board: HTMLDivElement;
// The hook registers window listeners, and this project's vitest setup has no
// auto-cleanup: unmount every instance explicitly or listeners leak across tests.
let unmounts: Array<() => void> = [];

beforeEach(() => {
  board = document.createElement('div');
  document.body.appendChild(board);
});

afterEach(() => {
  unmounts.forEach((unmount) => unmount());
  unmounts = [];
  board.remove();
});

function setup(overrides: Partial<BoardNavigationInputOptions> = {}) {
  const goBack = vi.fn();
  const goForward = vi.fn();
  const goHome = vi.fn();
  const containerRef = { current: board };
  const { unmount } = renderHook(() =>
    useBoardNavigationInput({
      containerRefs: [containerRef],
      goBack,
      goForward,
      goHome,
      ...overrides,
    }),
  );
  unmounts.push(unmount);
  return { goBack, goForward, goHome };
}

/** Dispatches a keydown on window and reports whether it was default-prevented. */
function pressKey(key: string, init: KeyboardEventInit = {}): boolean {
  const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init });
  window.dispatchEvent(event);
  return event.defaultPrevented;
}

describe('useBoardNavigationInput goHome', () => {
  it('Home calls goHome once and is default-prevented', () => {
    const { goHome, goBack, goForward } = setup();

    const prevented = pressKey('Home');

    expect(goHome).toHaveBeenCalledTimes(1);
    expect(prevented).toBe(true);
    expect(goBack).not.toHaveBeenCalled();
    expect(goForward).not.toHaveBeenCalled();
  });

  it('without goHome, Home is ignored and NOT default-prevented (the page still scrolls)', () => {
    const { goBack, goForward } = setup({ goHome: undefined });

    const prevented = pressKey('Home');

    expect(prevented).toBe(false);
    expect(goBack).not.toHaveBeenCalled();
    expect(goForward).not.toHaveBeenCalled();
  });

  it('ArrowLeft and ArrowRight still step', () => {
    const { goBack, goForward, goHome } = setup();

    pressKey('ArrowLeft');
    pressKey('ArrowRight');

    expect(goBack).toHaveBeenCalledTimes(1);
    expect(goForward).toHaveBeenCalledTimes(1);
    expect(goHome).not.toHaveBeenCalled();
  });

  it('Home is inert without a mounted container', () => {
    const { goHome } = setup({ containerRefs: [{ current: null }] });

    const prevented = pressKey('Home');

    expect(goHome).not.toHaveBeenCalled();
    expect(prevented).toBe(false);
  });

  it('Home keeps the shared guards: modifiers and typing targets', () => {
    const { goHome } = setup();
    const input = document.createElement('input');
    document.body.appendChild(input);

    pressKey('Home', { ctrlKey: true });
    fireEvent.keyDown(input, { key: 'Home' });
    input.remove();

    expect(goHome).not.toHaveBeenCalled();
  });

  it('picks up a replaced goHome without re-registering the listener', () => {
    const first = vi.fn();
    const second = vi.fn();
    const containerRef = { current: board };
    const { rerender, unmount } = renderHook(
      ({ home }: { home: () => void }) =>
        useBoardNavigationInput({
          containerRefs: [containerRef],
          goBack: vi.fn(),
          goForward: vi.fn(),
          goHome: home,
        }),
      { initialProps: { home: first } },
    );
    unmounts.push(unmount);

    rerender({ home: second });
    pressKey('Home');

    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
  });
});
