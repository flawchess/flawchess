// @vitest-environment jsdom
/**
 * FacepalmChip: the library chip, tinted and named by its facepalm type.
 */

import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { FacepalmChip } from '../FacepalmChip';

class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal('ResizeObserver', MockResizeObserver);

afterEach(cleanup);

function open(el: HTMLElement): void {
  act(() => {
    el.focus();
  });
}

describe('FacepalmChip', () => {
  it('keeps the library testid, type aria-label and type line', () => {
    render(<FacepalmChip score={0.8} type="allowed_loss" gameId={12} ply={34} />);
    const trigger = screen.getByTestId('facepalm-badge-12-34');
    expect(trigger.getAttribute('aria-label')).toMatch(/, allowed loss$/);
    open(trigger);
    expect(screen.getByTestId('facepalm-explanation-type').textContent).toContain('Allowed loss:');
    expect(screen.getByTestId('facepalm-badge-12-34-popover').textContent).toContain('a player at your level');
  });
});
