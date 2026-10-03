// @vitest-environment jsdom
/**
 * Phase 229 D-02/D-12/Pitfall 2 — analysis-board tracking: tab switches, PGN/FEN
 * paste open, the Maia ELO slider (commit-only + reset) and the play-style
 * temperature slider (3-value bucket, commit-only).
 *
 * Sliders are driven through the real Radix primitive via keyboard (Radix fires
 * onValueChange AND onValueCommit for one arrow press) and, to prove the
 * commit-only contract, via pointer events where onValueChange fires on
 * pointer-down and onValueCommit only on pointer-up.
 */

import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useState } from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { AnalysisTabs, MoveListHeaderContent } from '../AnalysisTabs';
import { EloSelector } from '../EloSelector';
import { TemperatureSelector, TEMPERATURE_DEFAULT, sliderPositionToTemperature } from '../TemperatureSelector';
import { MAIA_ELO_LADDER } from '@/lib/maiaEncoding';

const SLIDER_WIDTH_PX = 1000;

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
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver = ResizeObserverStub;
  // Radix Slider pointer drag needs pointer capture and a measurable track.
  Element.prototype.setPointerCapture = vi.fn();
  Element.prototype.releasePointerCapture = vi.fn();
  Element.prototype.hasPointerCapture = vi.fn(() => true);
});

let track: ReturnType<typeof vi.fn>;

beforeEach(() => {
  track = vi.fn();
  window.umami = { track, identify: vi.fn() };
  window.history.pushState({}, '', '/analysis');
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  delete window.umami;
  window.history.pushState({}, '', '/');
});

/** Drag the slider root from pointer-down to pointer-up at a horizontal position. */
function dragSliderTo(root: HTMLElement, fraction: number): { change: () => void; commit: () => void } {
  root.getBoundingClientRect = () =>
    ({ left: 0, right: SLIDER_WIDTH_PX, width: SLIDER_WIDTH_PX, top: 0, bottom: 10, height: 10, x: 0, y: 0 }) as DOMRect;
  const clientX = fraction * SLIDER_WIDTH_PX;
  return {
    change: () => {
      fireEvent.pointerDown(root, { clientX, button: 0, pointerId: 1 });
    },
    commit: () => {
      fireEvent.pointerUp(root, { clientX, button: 0, pointerId: 1 });
    },
  };
}

// Radix only fires onValueCommit when the value actually changed since the drag
// started, so drag tests need a stateful parent (a fixed `value` never moves).
function StatefulElo({ onChange }: { onChange: (elo: number) => void }) {
  const [elo, setElo] = useState(1500);
  return (
    <EloSelector
      value={elo}
      onChange={(next) => {
        setElo(next);
        onChange(next);
      }}
    />
  );
}

function StatefulTemperature() {
  const [temperature, setTemperature] = useState(TEMPERATURE_DEFAULT);
  return <TemperatureSelector value={temperature} onChange={setTemperature} />;
}

function renderTabs() {
  return render(
    <AnalysisTabs
      evalChartReady={false}
      evalPending={false}
      movesTab={<div data-testid="moves-content" />}
      evalTab={<div data-testid="eval-content" />}
      humanTab={<div data-testid="human-content" />}
      flawChessTab={<div data-testid="flawchess-content" />}
      statsTab={null}
    />,
  );
}

describe('AnalysisTabs tab-switch tracking (D-02)', () => {
  it('sends nothing on render', () => {
    renderTabs();
    expect(track).not.toHaveBeenCalled();
  });

  it.each(['eval', 'human', 'flawchess'] as const)('sends one tab-switch for the %s tab', (tab) => {
    renderTabs();
    fireEvent.mouseDown(screen.getByTestId(`analysis-tab-${tab}`), { button: 0, ctrlKey: false });
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('tab-switch', { page: 'analysis', target: tab });
  });
});

describe('MoveListHeaderContent paste-open tracking', () => {
  it('opens the paste modal and sends one board-tool paste-open', () => {
    const onOpenPasteModal = vi.fn();
    render(<MoveListHeaderContent onOpenPasteModal={onOpenPasteModal} />);
    expect(track).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('analysis-btn-paste'));
    expect(onOpenPasteModal).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('board-tool', { page: 'analysis', target: 'paste-open' });
  });
});

describe('EloSelector tracking (Pitfall 2)', () => {
  it('fires option-change elo once per drag, on commit, with the snapped ladder rung', () => {
    const onChange = vi.fn();
    render(<StatefulElo onChange={onChange} />);
    const drag = dragSliderTo(screen.getByRole('slider').closest('[data-slot="slider"]') as HTMLElement, 0.5);

    drag.change();
    // The slider moved (onChange fired) but the drag is not finished: nothing tracked.
    expect(onChange).toHaveBeenCalled();
    expect(track).not.toHaveBeenCalled();

    drag.commit();
    expect(track).toHaveBeenCalledTimes(1);
    const [name, props] = track.mock.calls[0] as [string, { page: string; target: string; value: string }];
    expect(name).toBe('option-change');
    expect(props.page).toBe('analysis');
    expect(props.target).toBe('elo');
    // Never a free number: the value is one of the Maia ladder rungs.
    expect(MAIA_ELO_LADDER.map(String)).toContain(props.value);
  });

  it('fires once for a keyboard step (one commit)', () => {
    render(<EloSelector value={1500} onChange={vi.fn()} />);
    const thumb = screen.getByRole('slider');
    thumb.focus();
    fireEvent.keyDown(thumb, { key: 'ArrowRight' });
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('option-change', { page: 'analysis', target: 'elo', value: '1600' });
  });

  it('reset button fires board-tool elo-reset and calls onReset', () => {
    const onReset = vi.fn();
    render(<EloSelector value={1700} onChange={vi.fn()} defaultElo={1500} onReset={onReset} />);
    fireEvent.click(screen.getByTestId('analysis-elo-selector-reset'));
    expect(onReset).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('board-tool', { page: 'analysis', target: 'elo-reset' });
  });

  it('is attributed to the bots page on the Bots setup screen route', () => {
    window.history.pushState({}, '', '/bots');
    render(<EloSelector value={1500} onChange={vi.fn()} />);
    const thumb = screen.getByRole('slider');
    thumb.focus();
    fireEvent.keyDown(thumb, { key: 'ArrowLeft' });
    expect(track).toHaveBeenCalledWith('option-change', { page: 'bots', target: 'elo', value: '1400' });
  });
});

describe('TemperatureSelector tracking', () => {
  it('fires once per drag on commit, never on change alone, with a bucket not a float', () => {
    render(<StatefulTemperature />);
    const drag = dragSliderTo(screen.getByRole('slider').closest('[data-slot="slider"]') as HTMLElement, 0.9);

    drag.change();
    expect(track).not.toHaveBeenCalled();

    drag.commit();
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('option-change', { page: 'analysis', target: 'temperature', value: 'higher' });
  });

  it('commits below the default as lower', () => {
    render(<TemperatureSelector value={TEMPERATURE_DEFAULT} onChange={vi.fn()} />);
    const thumb = screen.getByRole('slider');
    thumb.focus();
    fireEvent.keyDown(thumb, { key: 'ArrowLeft' });
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('option-change', { page: 'analysis', target: 'temperature', value: 'lower' });
  });

  it('commits exactly at the default as default', () => {
    // One step right of center, then one step left lands back on position 0.
    render(<TemperatureSelector value={sliderPositionToTemperature(0.01)} onChange={vi.fn()} />);
    const thumb = screen.getByRole('slider');
    thumb.focus();
    fireEvent.keyDown(thumb, { key: 'ArrowLeft' });
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('option-change', { page: 'analysis', target: 'temperature', value: 'default' });
  });

  it('never sends the raw temperature float', () => {
    render(<TemperatureSelector value={TEMPERATURE_DEFAULT} onChange={vi.fn()} />);
    const thumb = screen.getByRole('slider');
    thumb.focus();
    fireEvent.keyDown(thumb, { key: 'ArrowRight' });
    const [, props] = track.mock.calls[0] as [string, { value: string }];
    expect(['lower', 'default', 'higher']).toContain(props.value);
  });
});
