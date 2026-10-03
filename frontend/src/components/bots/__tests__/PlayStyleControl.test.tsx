// @vitest-environment jsdom
/**
 * PlayStyleControl.tsx unit tests (Phase 171 Plan 04, D-01/V-09;
 * reworked to preset-only, quick 260717-lr9).
 */

import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { PlayStyleControl } from '../PlayStyleControl';
import { DEEP_BLEND, LIGHT_BLEND } from '@/lib/playStyle';

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('PlayStyleControl', () => {
  it('renders the "Play style" label with its info popover', () => {
    render(<PlayStyleControl blend={0.05} onChange={vi.fn()} />);
    expect(screen.getByText('Play style')).toBeTruthy();
    expect(screen.getByTestId('setup-play-style-info')).toBeTruthy();
  });

  it('renders exactly three preset buttons in the presets grid and no slider', () => {
    render(<PlayStyleControl blend={0.05} onChange={vi.fn()} />);
    const presets = screen.getByTestId('setup-play-style-presets');
    const buttons = presets.querySelectorAll('button');
    expect(buttons.length).toBe(3);
    expect(screen.getByTestId('setup-play-style-preset-human')).toBeTruthy();
    expect(screen.getByTestId('setup-play-style-preset-light')).toBeTruthy();
    expect(screen.getByTestId('setup-play-style-preset-deep')).toBeTruthy();
    expect(screen.queryByRole('slider')).toBeNull();
  });

  it('clicking Human calls onChange(0)', () => {
    const onChange = vi.fn();
    render(<PlayStyleControl blend={0.05} onChange={onChange} />);
    fireEvent.click(screen.getByTestId('setup-play-style-preset-human'));
    expect(onChange).toHaveBeenCalledWith(0);
  });

  it('clicking Light calls onChange(0.05)', () => {
    const onChange = vi.fn();
    render(<PlayStyleControl blend={0.5} onChange={onChange} />);
    fireEvent.click(screen.getByTestId('setup-play-style-preset-light'));
    expect(onChange).toHaveBeenCalledWith(0.05);
  });

  it('clicking Deep calls onChange(0.5)', () => {
    const onChange = vi.fn();
    render(<PlayStyleControl blend={0.05} onChange={onChange} />);
    fireEvent.click(screen.getByTestId('setup-play-style-preset-deep'));
    expect(onChange).toHaveBeenCalledWith(0.5);
  });

  const pressedMap = (): Record<string, string | null> => ({
    human: screen.getByTestId('setup-play-style-preset-human').getAttribute('aria-pressed'),
    light: screen.getByTestId('setup-play-style-preset-light').getAttribute('aria-pressed'),
    deep: screen.getByTestId('setup-play-style-preset-deep').getAttribute('aria-pressed'),
  });

  describe('active preset reflects the blend', () => {
    it('blend 0 → Human pressed, summary is the Human line', () => {
      render(<PlayStyleControl blend={0} onChange={vi.fn()} />);
      expect(pressedMap()).toEqual({ human: 'true', light: 'false', deep: 'false' });
      expect(screen.getByTestId('setup-play-style-summary').textContent).toBe(
        'Human — instinct, no calculation',
      );
    });

    it('blend 0.05 → Light pressed (the default)', () => {
      render(<PlayStyleControl blend={0.05} onChange={vi.fn()} />);
      expect(pressedMap()).toEqual({ human: 'false', light: 'true', deep: 'false' });
      expect(screen.getByTestId('setup-play-style-summary').textContent).toBe(
        'Light — calculates a little',
      );
    });

    it('blend 0.5 → Deep pressed', () => {
      render(<PlayStyleControl blend={0.5} onChange={vi.fn()} />);
      expect(pressedMap()).toEqual({ human: 'false', light: 'false', deep: 'true' });
      expect(screen.getByTestId('setup-play-style-summary').textContent).toBe(
        'Deep — calculates hard',
      );
    });

    it('a non-preset legacy blend (1) → no preset pressed, neutral summary', () => {
      render(<PlayStyleControl blend={1} onChange={vi.fn()} />);
      expect(pressedMap()).toEqual({ human: 'false', light: 'false', deep: 'false' });
      expect(screen.getByTestId('setup-play-style-summary').textContent).toBe(
        'Custom calculation depth',
      );
    });
  });

  it('the summary never leaks a blend number or ELO for the three presets', () => {
    for (const blend of [0, 0.05, 0.5]) {
      cleanup();
      render(<PlayStyleControl blend={blend} onChange={vi.fn()} />);
      expect(screen.getByTestId('setup-play-style-summary').textContent).not.toMatch(/\d/);
    }
  });
});

// Phase 229 (D-12): option-change reaches window.umami.track through the real analytics module.
describe('PlayStyleControl feature events (Phase 229)', () => {
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

  it('picking a different preset sends one play-style option-change and calls onChange', () => {
    const onChange = vi.fn();
    render(<PlayStyleControl blend={LIGHT_BLEND} onChange={onChange} />);
    expect(track).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('setup-play-style-preset-deep'));
    expect(onChange).toHaveBeenCalledWith(DEEP_BLEND);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('option-change', {
      page: 'bots',
      target: 'play-style',
      value: 'deep',
    });
  });

  it('re-picking the already-active preset sends nothing', () => {
    render(<PlayStyleControl blend={LIGHT_BLEND} onChange={vi.fn()} />);
    fireEvent.click(screen.getByTestId('setup-play-style-preset-light'));
    expect(track).not.toHaveBeenCalled();
  });
});
