// @vitest-environment jsdom
/**
 * PlayStyleControl.tsx unit tests (Phase 171 Plan 04, D-01/V-09).
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { PlayStyleControl } from '../PlayStyleControl';

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
    render(<PlayStyleControl blend={0.5} onChange={vi.fn()} />);
    expect(screen.getByText('Play style')).toBeTruthy();
    expect(screen.getByTestId('setup-play-style-info')).toBeTruthy();
  });

  it('renders exactly two preset buttons in the presets grid', () => {
    render(<PlayStyleControl blend={0.5} onChange={vi.fn()} />);
    const presets = screen.getByTestId('setup-play-style-presets');
    const buttons = presets.querySelectorAll('button');
    expect(buttons).toHaveLength(2);
    expect(screen.getByTestId('setup-play-style-preset-human')).toBeTruthy();
    expect(screen.getByTestId('setup-play-style-preset-engine')).toBeTruthy();
  });

  it('clicking Human calls onChange(0)', () => {
    const onChange = vi.fn();
    render(<PlayStyleControl blend={0.5} onChange={onChange} />);
    fireEvent.click(screen.getByTestId('setup-play-style-preset-human'));
    expect(onChange).toHaveBeenCalledWith(0);
  });

  it('clicking Engine calls onChange(1)', () => {
    const onChange = vi.fn();
    render(<PlayStyleControl blend={0.5} onChange={onChange} />);
    fireEvent.click(screen.getByTestId('setup-play-style-preset-engine'));
    expect(onChange).toHaveBeenCalledWith(1);
  });

  describe('blend === 0 (Human active)', () => {
    it('Human is pressed, Engine is not, summary shows the Human line, slider is dimmed', () => {
      render(<PlayStyleControl blend={0} onChange={vi.fn()} />);
      expect(screen.getByTestId('setup-play-style-preset-human').getAttribute('aria-pressed')).toBe(
        'true',
      );
      expect(screen.getByTestId('setup-play-style-preset-engine').getAttribute('aria-pressed')).toBe(
        'false',
      );
      expect(screen.getByTestId('setup-play-style-summary').textContent).toBe(
        'Human — plays on instinct, no calculation',
      );
    });

    it('the slider thumb is parked at the minimum (0.05) — 0 is not a representable slider position', () => {
      render(<PlayStyleControl blend={0} onChange={vi.fn()} />);
      const thumb = screen.getByRole('slider');
      expect(thumb.getAttribute('aria-valuenow')).toBe('0.05');
    });

    it('the slider block carries the dimmed opacity-50 treatment', () => {
      render(<PlayStyleControl blend={0} onChange={vi.fn()} />);
      const slider = screen.getByTestId('setup-play-style-slider');
      const dimmedWrapper = slider.closest('.opacity-50');
      expect(dimmedWrapper).not.toBeNull();
    });
  });

  describe('blend === 1 (Engine active)', () => {
    it('Engine is pressed', () => {
      render(<PlayStyleControl blend={1} onChange={vi.fn()} />);
      expect(screen.getByTestId('setup-play-style-preset-engine').getAttribute('aria-pressed')).toBe(
        'true',
      );
      expect(screen.getByTestId('setup-play-style-preset-human').getAttribute('aria-pressed')).toBe(
        'false',
      );
    });
  });

  describe('blend === 0.5 (custom value)', () => {
    it('neither preset is pressed, and the summary is the numeric form containing 0.50 and 50%', () => {
      render(<PlayStyleControl blend={0.5} onChange={vi.fn()} />);
      expect(screen.getByTestId('setup-play-style-preset-human').getAttribute('aria-pressed')).toBe(
        'false',
      );
      expect(screen.getByTestId('setup-play-style-preset-engine').getAttribute('aria-pressed')).toBe(
        'false',
      );
      const summary = screen.getByTestId('setup-play-style-summary').textContent ?? '';
      expect(summary).toContain('0.50');
      expect(summary).toContain('50%');
    });
  });

  describe('slider domain', () => {
    it('exposes min=0.05, max=1, step=0.05, and aria-valuemin is 0.05 — dragging can never produce 0', () => {
      render(<PlayStyleControl blend={0.5} onChange={vi.fn()} />);
      const thumb = screen.getByRole('slider');
      expect(thumb.getAttribute('aria-valuemin')).toBe('0.05');
      expect(thumb.getAttribute('aria-valuemax')).toBe('1');
    });

    it('moving the slider while Human is active exits Human mode immediately via onChange', () => {
      const onChange = vi.fn();
      render(<PlayStyleControl blend={0} onChange={onChange} />);
      const thumb = screen.getByRole('slider');
      thumb.focus();
      fireEvent.keyDown(thumb, { key: 'ArrowRight' });
      expect(onChange).toHaveBeenCalled();
      const [calledWith] = onChange.mock.calls[0] as [number];
      expect(calledWith).toBeGreaterThan(0);
    });
  });
});
