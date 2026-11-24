// @vitest-environment jsdom
/**
 * On touch the chart tooltip must behave like Recharts: a tap pins it (lifting
 * the finger used to drop it at once), a horizontal drag scrubs, a vertical
 * swipe only scrolls, and a tap elsewhere dismisses it.
 */
import { beforeAll, beforeEach, describe, expect, it } from 'vitest';

interface ChartToolkit {
  lineChart: (
    host: HTMLElement,
    opts: { labels: string[]; series: { name: string; values: number[]; color: string }[] },
  ) => void;
}

const LABELS = ['2026-09-01', '2026-09-02'];
const LEFT_X = 60;
const RIGHT_X = 580;

let fc: ChartToolkit;

function fire(target: Element, type: string, clientX: number, clientY: number, pointerType = 'touch'): void {
  const ev = new MouseEvent(type, { bubbles: true, clientX, clientY });
  Object.defineProperties(ev, { pointerType: { value: pointerType }, isPrimary: { value: true } });
  target.dispatchEvent(ev);
}

/** A touch pointer is released with pointerup followed by pointerleave. */
function lift(target: Element, x: number, y: number): void {
  fire(target, 'pointerup', x, y);
  fire(target, 'pointerleave', x, y);
}

function tap(target: Element, x: number, y = 50): void {
  fire(target, 'pointerdown', x, y);
  lift(target, x, y);
}

function draw(id: string): Element {
  const host = document.getElementById(id) as HTMLElement;
  Object.defineProperty(host, 'clientWidth', { value: 600, configurable: true });
  fc.lineChart(host, { labels: LABELS, series: [{ name: id, values: [3, 7], color: '#000' }] });
  const rects = host.querySelectorAll('rect');
  return rects[rects.length - 1] as Element;
}

const tip = (): HTMLElement => document.getElementById('tip') as HTMLElement;
const visible = (): boolean => tip().style.opacity === '1';

describe('activity chart tooltips on touch', () => {
  beforeAll(async () => {
    await import('../charts.js');
    fc = (window as unknown as { __fc: ChartToolkit }).__fc;
  });

  let overlay: Element;
  beforeEach(() => {
    document.body.innerHTML =
      '<div id="tip"></div><p id="outside"></p>' +
      '<div class="card"><h3>A</h3><div id="a"></div></div><div class="card"><h3>B</h3><div id="b"></div></div>';
    overlay = draw('a');
  });

  it('stays open after a tap', () => {
    tap(overlay, RIGHT_X);
    expect(visible()).toBe(true);
    expect(tip().innerHTML).toContain('2 Sep 2026');
  });

  it('moves to another point on a second tap', () => {
    tap(overlay, RIGHT_X);
    tap(overlay, LEFT_X);
    expect(visible()).toBe(true);
    expect(tip().innerHTML).toContain('1 Sep 2026');
  });

  it('scrubs on a horizontal drag and stays open', () => {
    fire(overlay, 'pointerdown', LEFT_X, 50);
    fire(overlay, 'pointermove', RIGHT_X, 52);
    lift(overlay, RIGHT_X, 52);
    expect(visible()).toBe(true);
    expect(tip().innerHTML).toContain('2 Sep 2026');
  });

  it('does not open on a vertical swipe', () => {
    fire(overlay, 'pointerdown', LEFT_X, 50);
    fire(overlay, 'pointermove', LEFT_X + 2, 90);
    fire(overlay, 'pointercancel', LEFT_X + 2, 90);
    expect(visible()).toBe(false);
  });

  it('closes on a tap outside, but not on a swipe outside', () => {
    const outside = document.getElementById('outside') as HTMLElement;
    tap(overlay, RIGHT_X);
    fire(outside, 'pointerdown', 10, 200);
    fire(outside, 'pointercancel', 10, 150);
    expect(visible()).toBe(true);
    tap(outside, 10, 200);
    expect(visible()).toBe(false);
  });

  it('hands the tooltip over to another chart', () => {
    const other = draw('b');
    tap(overlay, RIGHT_X);
    tap(other, LEFT_X);
    expect(visible()).toBe(true);
    expect(tip().innerHTML).toContain('>b<');
    expect(document.querySelector('#a svg line[opacity=".45"]')).toBeNull();
  });

  it('closes when its chart is redrawn', () => {
    tap(overlay, RIGHT_X);
    draw('a');
    expect(visible()).toBe(false);
  });

  it('still closes on pointerleave with a mouse', () => {
    fire(overlay, 'pointermove', RIGHT_X, 50, 'mouse');
    expect(visible()).toBe(true);
    fire(overlay, 'pointerleave', RIGHT_X, 50, 'mouse');
    expect(visible()).toBe(false);
  });
});
