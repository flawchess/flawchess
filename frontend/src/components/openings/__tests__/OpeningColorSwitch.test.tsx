// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { OpeningColorSwitch } from '../stats/OpeningColorSwitch';

const trackFeature = vi.hoisted(() => vi.fn());
vi.mock('@/lib/analytics', () => ({ trackFeature }));

beforeEach(() => {
  trackFeature.mockClear();
});

afterEach(() => {
  cleanup();
});

describe('OpeningColorSwitch', () => {
  it('fires nothing on render', () => {
    render(<OpeningColorSwitch idPrefix="t" selected="white" onSelect={vi.fn()} />);
    expect(trackFeature).not.toHaveBeenCalled();
  });

  it('selects the other colour and tracks exactly once', () => {
    const onSelect = vi.fn();
    render(<OpeningColorSwitch idPrefix="t" selected="white" onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId('opening-color-switch-t-black'));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith('black');
    expect(trackFeature).toHaveBeenCalledTimes(1);
    expect(trackFeature).toHaveBeenCalledWith('option-change', {
      target: 'opening-stats-color',
      value: 'black',
    });
  });

  it('ignores a click on the already selected colour', () => {
    const onSelect = vi.fn();
    render(<OpeningColorSwitch idPrefix="t" selected="white" onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId('opening-color-switch-t-white'));
    expect(onSelect).not.toHaveBeenCalled();
    expect(trackFeature).not.toHaveBeenCalled();
  });

  it('reflects the selection in aria-pressed', () => {
    render(<OpeningColorSwitch idPrefix="t" selected="black" onSelect={vi.fn()} />);
    expect(screen.getByTestId('opening-color-switch-t-white').getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByTestId('opening-color-switch-t-black').getAttribute('aria-pressed')).toBe('true');
  });
});
