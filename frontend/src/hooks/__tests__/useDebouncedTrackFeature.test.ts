// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { SLIDER_TRACK_DEBOUNCE_MS, useDebouncedTrackFeature } from '@/hooks/useDebouncedTrackFeature';

const BURST_STEP_MS = 100;

let track: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.useFakeTimers();
  track = vi.fn();
  window.umami = { track, identify: vi.fn() };
  window.history.pushState({}, '', '/analysis');
});

afterEach(() => {
  vi.useRealTimers();
  delete window.umami;
  window.history.pushState({}, '', '/');
});

describe('useDebouncedTrackFeature', () => {
  it('collapses a burst into one event with the last props, after the window', () => {
    const { result } = renderHook(() => useDebouncedTrackFeature('option-change'));
    act(() => result.current({ target: 'elo', value: '1600' }));
    act(() => vi.advanceTimersByTime(BURST_STEP_MS));
    act(() => result.current({ target: 'elo', value: '1700' }));
    act(() => vi.advanceTimersByTime(BURST_STEP_MS));
    act(() => result.current({ target: 'elo', value: '1800' }));
    expect(track).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(SLIDER_TRACK_DEBOUNCE_MS - 1));
    expect(track).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('option-change', { page: 'analysis', target: 'elo', value: '1800' });
  });

  it('sends one event per adjustment when they are separated by more than the window', () => {
    const { result } = renderHook(() => useDebouncedTrackFeature('option-change'));
    act(() => result.current({ target: 'elo', value: '1600' }));
    act(() => vi.advanceTimersByTime(SLIDER_TRACK_DEBOUNCE_MS));
    act(() => result.current({ target: 'elo', value: '1700' }));
    act(() => vi.advanceTimersByTime(SLIDER_TRACK_DEBOUNCE_MS));
    expect(track).toHaveBeenCalledTimes(2);
  });

  it('flushes a pending event on unmount and sends nothing afterwards', () => {
    const { result, unmount } = renderHook(() => useDebouncedTrackFeature('option-change'));
    act(() => result.current({ target: 'elo', value: '1600' }));
    unmount();
    expect(track).toHaveBeenCalledTimes(1);
    act(() => vi.advanceTimersByTime(SLIDER_TRACK_DEBOUNCE_MS * 2));
    expect(track).toHaveBeenCalledTimes(1);
  });

  it('attributes a flush after navigation to the page where the slider was moved', () => {
    const { result, unmount } = renderHook(() => useDebouncedTrackFeature('option-change'));
    act(() => result.current({ target: 'elo', value: '1600' }));
    window.history.pushState({}, '', '/library');
    unmount();
    expect(track).toHaveBeenCalledTimes(1);
    expect(track.mock.calls[0]?.[1]).toMatchObject({ page: 'analysis' });
  });

  it('never sends from an excluded route (D-14 at the captured path)', () => {
    window.history.pushState({}, '', '/admin');
    const { result, unmount } = renderHook(() => useDebouncedTrackFeature('option-change'));
    act(() => result.current({ target: 'elo', value: '1600' }));
    window.history.pushState({}, '', '/analysis');
    act(() => vi.advanceTimersByTime(SLIDER_TRACK_DEBOUNCE_MS));
    unmount();
    expect(track).not.toHaveBeenCalled();
  });

  it('sends nothing on unmount when nothing is pending', () => {
    const { unmount } = renderHook(() => useDebouncedTrackFeature('option-change'));
    unmount();
    expect(track).not.toHaveBeenCalled();
  });
});
