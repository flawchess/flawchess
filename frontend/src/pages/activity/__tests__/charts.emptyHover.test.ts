// @vitest-environment jsdom
/**
 * FLAWCHESS-BG regression: a bar chart rendered with zero labels (every row
 * filtered out of the day range) must not crash on pointermove. Before the
 * `hover()` guard, the nearest-index search returned 0 and `num(undefined)`
 * threw "Cannot read properties of undefined (reading 'toLocaleString')".
 */
import { describe, it, expect, beforeAll } from 'vitest';

interface ChartToolkit {
  barChart: (
    host: HTMLElement,
    opts: { labels: string[]; series: { name: string; values: number[]; color: string }[] },
  ) => void;
}

function mountHost(): HTMLElement {
  document.body.innerHTML = '<div id="tip"></div><div class="card"><h3>T</h3><div id="host"></div></div>';
  const host = document.getElementById('host') as HTMLElement;
  Object.defineProperty(host, 'clientWidth', { value: 600, configurable: true });
  return host;
}

/**
 * Dispatches pointermove on every rect in the chart (the hover overlay is the
 * last one when present). jsdom routes a listener exception to the window
 * `error` event instead of throwing from dispatchEvent, so the caller collects
 * those via `captureWindowErrors()` rather than `toThrow()`.
 */
function pointerMoveAllRects(host: HTMLElement, clientX: number): void {
  host.querySelectorAll('rect').forEach((rect) => {
    rect.dispatchEvent(new MouseEvent('pointermove', { bubbles: true, clientX, clientY: 50 }));
  });
}

function captureWindowErrors(): string[] {
  const errors: string[] = [];
  window.addEventListener('error', (ev) => {
    ev.preventDefault();
    errors.push(ev.message);
  });
  return errors;
}

describe('activity charts with empty labels (FLAWCHESS-BG)', () => {
  let fc: ChartToolkit;

  beforeAll(async () => {
    await import('../charts.js');
    fc = (window as unknown as { __fc: ChartToolkit }).__fc;
  });

  it('barChart with no labels survives pointermove', () => {
    const host = mountHost();
    const errors = captureWindowErrors();
    fc.barChart(host, { labels: [], series: [{ name: 'A', values: [], color: '#000' }] });
    pointerMoveAllRects(host, 300);
    expect(errors).toEqual([]);
  });

  it('barChart with data still renders a tooltip on pointermove', () => {
    const host = mountHost();
    fc.barChart(host, { labels: ['2026-09-01', '2026-09-02'], series: [{ name: 'A', values: [3, 1234], color: '#000' }] });
    pointerMoveAllRects(host, 500);
    expect(document.getElementById('tip')?.innerHTML).toContain('1,234');
  });
});
