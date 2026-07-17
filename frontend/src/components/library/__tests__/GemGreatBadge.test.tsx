// @vitest-environment jsdom
/**
 * GemGreatBadge vitest suite (Phase 175 Plan 06) — mirrors SeverityBadge.test.tsx's
 * coverage shape: labels, hover callback, and the decorative (no-callback) default.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { GemGreatBadge } from '../GemGreatBadge';

afterEach(() => {
  cleanup();
});

describe('GemGreatBadge', () => {
  it('renders the gem badge with count + "Gem" label', () => {
    render(<GemGreatBadge tier="gem" count={2} gameId={1} />);
    const badge = screen.getByTestId('badge-gem-1');
    expect(badge.textContent).toContain('2');
    expect(badge.textContent).toContain('Gem');
  });

  it('renders the great badge with count + "Great" label', () => {
    render(<GemGreatBadge tier="great" count={3} gameId={1} />);
    const badge = screen.getByTestId('badge-great-1');
    expect(badge.textContent).toContain('3');
    expect(badge.textContent).toContain('Great');
  });

  it('fires onHover(true)/onHover(false) on mouseenter/mouseleave', () => {
    const onHover = vi.fn();
    render(<GemGreatBadge tier="gem" count={1} gameId={2} onHover={onHover} />);
    const badge = screen.getByTestId('badge-gem-2');
    fireEvent.mouseEnter(badge);
    expect(onHover).toHaveBeenCalledWith(true);
    fireEvent.mouseLeave(badge);
    expect(onHover).toHaveBeenCalledWith(false);
  });

  it('fires onActivate on click and is keyboard-activatable', () => {
    const onActivate = vi.fn();
    render(<GemGreatBadge tier="great" count={1} gameId={3} onActivate={onActivate} />);
    const badge = screen.getByTestId('badge-great-3');
    expect(badge.getAttribute('role')).toBe('button');
    fireEvent.click(badge);
    expect(onActivate).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(badge, { key: 'Enter' });
    expect(onActivate).toHaveBeenCalledTimes(2);
  });

  it('has no hover-lift class when no callbacks are passed (decorative default)', () => {
    render(<GemGreatBadge tier="gem" count={1} gameId={4} />);
    const badge = screen.getByTestId('badge-gem-4');
    expect(badge.className).not.toContain('hover:-translate-y-px');
    expect(badge.getAttribute('role')).toBeNull();
  });
});
