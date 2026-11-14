// @vitest-environment jsdom
/**
 * FacepalmBadgePopover vitest suite (D-16): hover, tap and keyboard opening of the
 * Facepalm chip popover, touch safety, close paths and Umami tracking.
 *
 * jsdom only simulates pointer types through event init, so the real-phone tap is a
 * HUMAN-UAT item; these tests pin the handler logic.
 */

import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FacepalmBadgePopover } from '../FacepalmBadgePopover';

const TEST_ID = 'facepalm-badge-7-24';
const POPOVER_ID = `${TEST_ID}-popover`;
const OPEN_DELAY_MS = 100;
const CLOSE_GRACE_MS = 80;

class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal('ResizeObserver', MockResizeObserver);

beforeEach(() => {
  vi.useFakeTimers();
  render(
    <>
      <FacepalmBadgePopover testId={TEST_ID} score={0.946}>
        <span>Blunder</span>
      </FacepalmBadgePopover>
      <button type="button" data-testid="other-button">
        other
      </button>
    </>,
  );
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

function trigger(): HTMLElement {
  return screen.getByTestId(TEST_ID);
}

function other(): HTMLElement {
  return screen.getByTestId('other-button');
}

function isOpen(): boolean {
  return screen.queryByTestId(POPOVER_ID) !== null;
}

function advance(ms: number): void {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

function focusEl(el: HTMLElement): void {
  act(() => {
    el.focus();
  });
}

describe('FacepalmBadgePopover content and name', () => {
  it('names the trigger with Facepalm and the percent', () => {
    expect(trigger().getAttribute('aria-label')).toBe('Facepalm 94%');
  });

  it('is closed on render', () => {
    expect(isOpen()).toBe(false);
  });
});

describe('mouse hover', () => {
  it('opens after the hover delay and not before', () => {
    fireEvent.pointerEnter(trigger(), { pointerType: 'mouse' });
    advance(OPEN_DELAY_MS - 1);
    expect(isOpen()).toBe(false);
    advance(1);
    expect(isOpen()).toBe(true);
  });

  it('closes after the grace period on pointer leave', () => {
    fireEvent.pointerEnter(trigger(), { pointerType: 'mouse' });
    advance(OPEN_DELAY_MS);
    fireEvent.pointerLeave(trigger(), { pointerType: 'mouse' });
    advance(CLOSE_GRACE_MS - 1);
    expect(isOpen()).toBe(true);
    advance(1);
    expect(isOpen()).toBe(false);
  });

  it('stays open when the pointer reaches the content within the grace period', () => {
    fireEvent.pointerEnter(trigger(), { pointerType: 'mouse' });
    advance(OPEN_DELAY_MS);
    fireEvent.pointerLeave(trigger(), { pointerType: 'mouse' });
    advance(CLOSE_GRACE_MS - 1);
    fireEvent.pointerEnter(screen.getByTestId(POPOVER_ID), { pointerType: 'mouse' });
    advance(CLOSE_GRACE_MS * 2);
    expect(isOpen()).toBe(true);
  });

  it('does not open when the pointer leaves before the delay', () => {
    fireEvent.pointerEnter(trigger(), { pointerType: 'mouse' });
    advance(OPEN_DELAY_MS - 20);
    fireEvent.pointerLeave(trigger(), { pointerType: 'mouse' });
    advance(OPEN_DELAY_MS * 2);
    expect(isOpen()).toBe(false);
  });
});

describe('touch', () => {
  it('neither opens nor closes on touch pointer enter and leave', () => {
    fireEvent.pointerEnter(trigger(), { pointerType: 'touch' });
    advance(OPEN_DELAY_MS * 5);
    expect(isOpen()).toBe(false);
  });

  it('a tap (pointerdown, focus, click) leaves it open through the trailing pointerleave', () => {
    fireEvent.pointerDown(trigger(), { pointerType: 'touch' });
    focusEl(trigger());
    fireEvent.click(trigger());
    expect(isOpen()).toBe(true);
    fireEvent.pointerLeave(trigger(), { pointerType: 'touch' });
    advance(CLOSE_GRACE_MS * 5);
    expect(isOpen()).toBe(true);
  });
});

describe('mouse click', () => {
  it('opens on a click and a second click keeps it open', () => {
    fireEvent.pointerDown(trigger(), { pointerType: 'mouse' });
    focusEl(trigger());
    fireEvent.click(trigger());
    expect(isOpen()).toBe(true);
    fireEvent.pointerDown(trigger(), { pointerType: 'mouse' });
    fireEvent.click(trigger());
    expect(isOpen()).toBe(true);
  });
});

describe('keyboard', () => {
  it('opens at once on a focus not preceded by a pointer press', () => {
    focusEl(trigger());
    expect(isOpen()).toBe(true);
  });

  it('closes on Escape', () => {
    focusEl(trigger());
    fireEvent.keyDown(trigger(), { key: 'Escape' });
    expect(isOpen()).toBe(false);
  });

  it('closes when focus moves to a button outside', () => {
    focusEl(trigger());
    focusEl(other());
    expect(isOpen()).toBe(false);
  });

  it('closes on a press outside', () => {
    focusEl(trigger());
    // Radix arms its outside-press listener on a 0 ms timer after mount.
    advance(1);
    // Radix defers the outside-press dismissal to the click that follows the press.
    fireEvent.pointerDown(document.body, { pointerType: 'mouse', button: 0 });
    fireEvent.click(document.body);
    expect(isOpen()).toBe(false);
  });
});

describe('keyboard after earlier pointer use', () => {
  it('opens on a keyboard focus after a click on the focused trigger, Escape and a blur', () => {
    focusEl(trigger());
    fireEvent.pointerDown(trigger(), { pointerType: 'mouse' });
    fireEvent.click(trigger());
    fireEvent.keyDown(trigger(), { key: 'Escape' });
    expect(isOpen()).toBe(false);
    focusEl(other());
    focusEl(trigger());
    expect(isOpen()).toBe(true);
  });

  it('opens on a keyboard focus after a press that never clicked (drag-off) and a blur', () => {
    focusEl(trigger());
    fireEvent.keyDown(trigger(), { key: 'Escape' });
    fireEvent.pointerDown(trigger(), { pointerType: 'mouse' });
    focusEl(other());
    expect(isOpen()).toBe(false);
    focusEl(trigger());
    expect(isOpen()).toBe(true);
  });

  it('opens on a keyboard focus after a mouse drag-off that never focused the trigger (Safari)', () => {
    fireEvent.pointerDown(trigger(), { pointerType: 'mouse' });
    fireEvent.pointerLeave(trigger(), { pointerType: 'mouse' });
    focusEl(trigger());
    expect(isOpen()).toBe(true);
  });

  it('opens on a keyboard focus after a touch press cancelled by a scroll', () => {
    fireEvent.pointerDown(trigger(), { pointerType: 'touch' });
    fireEvent.pointerCancel(trigger(), { pointerType: 'touch' });
    focusEl(trigger());
    expect(isOpen()).toBe(true);
  });

  it('opens on a keyboard focus after a click that never focused the trigger (Safari)', () => {
    fireEvent.pointerDown(trigger(), { pointerType: 'mouse' });
    fireEvent.click(trigger());
    fireEvent.keyDown(trigger(), { key: 'Escape' });
    expect(isOpen()).toBe(false);
    focusEl(trigger());
    expect(isOpen()).toBe(true);
  });
});

describe('popover-open tracking', () => {
  let track: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    track = vi.fn();
    window.umami = { track, identify: vi.fn() };
    window.history.pushState({}, '', '/library');
  });

  afterEach(() => {
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  it('sends nothing on render, one id-free popover-open on first open, nothing on reopen', () => {
    expect(track).not.toHaveBeenCalled();
    focusEl(trigger());
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('popover-open', { page: 'library', target: 'facepalm-badge' });
    fireEvent.keyDown(trigger(), { key: 'Escape' });
    focusEl(other());
    focusEl(trigger());
    expect(isOpen()).toBe(true);
    expect(track).toHaveBeenCalledTimes(1);
  });
});
