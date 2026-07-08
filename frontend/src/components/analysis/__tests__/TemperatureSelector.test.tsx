// @vitest-environment jsdom
/**
 * Phase 159 Plan 04 — TemperatureSelector tests (D-08/D-09, Pitfall 7).
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import {
  TemperatureSelector,
  TEMPERATURE_MIN,
  TEMPERATURE_MAX,
  TEMPERATURE_DEFAULT,
  sliderPositionToTemperature,
  temperatureToSliderPosition,
} from '../TemperatureSelector';
import { DEFAULT_POLICY_TEMPERATURE } from '@/lib/engine/policyTemperature';

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

describe('TemperatureSelector mapping helpers', () => {
  it('sliderPositionToTemperature(0) === 1 (strict — Pitfall 7 center exactness)', () => {
    expect(sliderPositionToTemperature(0)).toBe(1);
  });

  it('sliderPositionToTemperature(1) === 0.5 (right end = Stockfish/sharp)', () => {
    expect(sliderPositionToTemperature(1)).toBe(0.5);
  });

  it('sliderPositionToTemperature(-1) === 2 (left end = Human)', () => {
    expect(sliderPositionToTemperature(-1)).toBe(2);
  });

  it('temperatureToSliderPosition(1) === 0 (strict — Pitfall 7 center exactness)', () => {
    expect(temperatureToSliderPosition(1)).toBe(0);
  });

  it('temperatureToSliderPosition(2) === -1 (Human sits at the left end)', () => {
    expect(temperatureToSliderPosition(2)).toBe(-1);
  });

  it('temperatureToSliderPosition(0.5) === 1 (Stockfish sits at the right end)', () => {
    expect(temperatureToSliderPosition(0.5)).toBe(1);
  });

  it('round-trips exactly at min/center/max', () => {
    for (const t of [TEMPERATURE_MIN, TEMPERATURE_DEFAULT, TEMPERATURE_MAX]) {
      expect(sliderPositionToTemperature(temperatureToSliderPosition(t))).toBe(t);
    }
  });

  it('TEMPERATURE_MIN === 0.5, TEMPERATURE_MAX === 2.0, TEMPERATURE_DEFAULT === 1.0', () => {
    expect(TEMPERATURE_MIN).toBe(0.5);
    expect(TEMPERATURE_MAX).toBe(2.0);
    expect(TEMPERATURE_DEFAULT).toBe(1.0);
  });

  it('TEMPERATURE_DEFAULT === DEFAULT_POLICY_TEMPERATURE (search no-op value, T-159-08)', () => {
    expect(TEMPERATURE_DEFAULT).toBe(DEFAULT_POLICY_TEMPERATURE);
  });
});

describe('TemperatureSelector component', () => {
  it('does not render a numeric temperature value', () => {
    render(<TemperatureSelector value={1.4} onChange={vi.fn()} />);
    expect(screen.queryByTestId('analysis-temperature-selector-value')).toBeNull();
  });

  it('has data-testid="analysis-temperature-selector" and a plain-language aria-label', () => {
    render(<TemperatureSelector value={1.0} onChange={vi.fn()} />);
    const el = screen.getByTestId('analysis-temperature-selector');
    expect(el.getAttribute('aria-label')).toBe('Play style');
  });

  it('shows Human/Stockfish endpoint labels, never "Temperature"/"T=" jargon', () => {
    render(<TemperatureSelector value={1.0} onChange={vi.fn()} />);
    const el = screen.getByTestId('analysis-temperature-selector');
    expect(el.textContent).toMatch(/Human/);
    expect(el.textContent).toMatch(/Stockfish/);
    expect(el.textContent).not.toMatch(/Temperature/i);
    expect(el.textContent).not.toMatch(/T=/);
  });

  it('renders the slider thumb at the exact center position for the default temperature', () => {
    render(<TemperatureSelector value={TEMPERATURE_DEFAULT} onChange={vi.fn()} />);
    const thumb = screen.getByRole('slider');
    expect(thumb.getAttribute('aria-valuenow')).toBe('0');
  });
});
