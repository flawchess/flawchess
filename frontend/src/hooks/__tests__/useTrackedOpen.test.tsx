// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { useTrackedOpen } from '@/hooks/useTrackedOpen';
import { InfoPopover } from '@/components/ui/info-popover';

describe('useTrackedOpen', () => {
  it('does not call onOpen on mount', () => {
    const onOpen = vi.fn();
    renderHook(() => useTrackedOpen(onOpen));
    expect(onOpen).not.toHaveBeenCalled();
  });

  it('calls onOpen once per false-to-true transition', () => {
    const onOpen = vi.fn();
    const { result } = renderHook(() => useTrackedOpen(onOpen));
    act(() => result.current[1](true));
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(result.current[0]).toBe(true);
    act(() => result.current[1](true));
    expect(onOpen).toHaveBeenCalledTimes(1);
    act(() => result.current[1](false));
    act(() => result.current[1](true));
    expect(onOpen).toHaveBeenCalledTimes(2);
  });

  it('with once, stays at one call for the mounted instance', () => {
    const onOpen = vi.fn();
    const { result } = renderHook(() => useTrackedOpen(onOpen, { once: true }));
    act(() => result.current[1](true));
    act(() => result.current[1](false));
    act(() => result.current[1](true));
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it('returns a setter that is stable across renders', () => {
    const { result, rerender } = renderHook(() => useTrackedOpen(vi.fn()));
    const first = result.current[1];
    rerender();
    expect(result.current[1]).toBe(first);
  });
});

describe('InfoPopover popover-open tracking', () => {
  let track: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    track = vi.fn();
    window.umami = { track, identify: vi.fn() };
  });

  afterEach(() => {
    cleanup();
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  function renderPopover(testId: string): void {
    render(
      <InfoPopover ariaLabel="Info" testId={testId}>
        body
      </InfoPopover>,
    );
  }

  it('sends nothing on render and one id-free event on open, none on reopen', () => {
    window.history.pushState({}, '', '/library/stats');
    renderPopover('tag-legend-48213');
    expect(track).not.toHaveBeenCalled();

    const trigger = screen.getByTestId('tag-legend-48213');
    fireEvent.click(trigger);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('popover-open', { page: 'library', target: 'tag-legend' });

    fireEvent.click(trigger);
    fireEvent.click(trigger);
    expect(track).toHaveBeenCalledTimes(1);
  });

  it('sends nothing on an excluded route', () => {
    window.history.pushState({}, '', '/admin');
    renderPopover('some-info');
    fireEvent.click(screen.getByTestId('some-info'));
    expect(track).not.toHaveBeenCalled();
  });
});
