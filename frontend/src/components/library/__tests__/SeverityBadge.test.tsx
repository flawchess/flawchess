// @vitest-environment jsdom
/**
 * SeverityBadge vitest suite — covers:
 *
 * 1. "Inacc." abbreviated label
 * 2. Active-filter ring when the severity filter is narrowed to exactly this severity
 * 3. No ring under the default both-M+B filter, and never for inaccuracy
 * 4. onHover fires true/false on pointer enter/leave
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { SeverityBadge } from '../SeverityBadge';
import { ACTIVE_FILTER_RING_CLASS } from '@/lib/theme';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

let mockFlawFilterState: FlawFilterState = { severity: ['blunder', 'mistake'], tags: [] };

vi.mock('@/hooks/useFlawFilterStore', () => ({
  useFlawFilterStore: () => [mockFlawFilterState, vi.fn()] as const,
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  mockFlawFilterState = { severity: ['blunder', 'mistake'], tags: [] };
});

const ringClasses = ACTIVE_FILTER_RING_CLASS.split(' ');

describe('SeverityBadge', () => {
  describe('labels', () => {
    it('renders the abbreviated "Inacc." label', () => {
      render(<SeverityBadge severity="inaccuracy" count={4} gameId={1} />);
      const badge = screen.getByTestId('severity-inaccuracy-1');
      expect(badge.textContent).toContain('Inacc.');
    });
  });

  describe('active-filter ring', () => {
    it('rings when the severity filter is narrowed to exactly this severity', () => {
      mockFlawFilterState = { severity: ['blunder'], tags: [] };
      render(<SeverityBadge severity="blunder" count={2} gameId={2} />);
      const badge = screen.getByTestId('severity-blunder-2');
      for (const cls of ringClasses) expect(badge.className).toContain(cls);
    });

    it('does NOT ring under the default both-M+B filter', () => {
      render(<SeverityBadge severity="blunder" count={2} gameId={3} />);
      const badge = screen.getByTestId('severity-blunder-3');
      for (const cls of ringClasses) expect(badge.className).not.toContain(cls);
    });

    it('does NOT ring a non-selected severity when narrowed to the other', () => {
      mockFlawFilterState = { severity: ['blunder'], tags: [] };
      render(<SeverityBadge severity="mistake" count={1} gameId={4} />);
      const badge = screen.getByTestId('severity-mistake-4');
      for (const cls of ringClasses) expect(badge.className).not.toContain(cls);
    });

    it('never rings the inaccuracy badge', () => {
      mockFlawFilterState = { severity: ['blunder'], tags: [] };
      render(<SeverityBadge severity="inaccuracy" count={5} gameId={5} />);
      const badge = screen.getByTestId('severity-inaccuracy-5');
      for (const cls of ringClasses) expect(badge.className).not.toContain(cls);
    });
  });

  describe('onHover callback', () => {
    it('fires true on mouseenter and false on mouseleave', () => {
      const onHover = vi.fn();
      render(<SeverityBadge severity="blunder" count={1} gameId={6} onHover={onHover} />);
      const badge = screen.getByTestId('severity-blunder-6');
      fireEvent.mouseEnter(badge);
      expect(onHover).toHaveBeenCalledWith(true);
      fireEvent.mouseLeave(badge);
      expect(onHover).toHaveBeenCalledWith(false);
    });

    it('applies the hover-lift class when interactive', () => {
      render(<SeverityBadge severity="blunder" count={1} gameId={7} onHover={() => {}} />);
      const badge = screen.getByTestId('severity-blunder-7');
      expect(badge.className).toContain('hover:-translate-y-px');
    });
  });

  describe('decorative default (Flaws card — no callbacks)', () => {
    it('has no hover-lift class when no callbacks are passed', () => {
      render(<SeverityBadge severity="blunder" count={1} gameId={8} showCount={false} />);
      const badge = screen.getByTestId('severity-blunder-8');
      expect(badge.className).not.toContain('hover:-translate-y-px');
    });
  });
  describe('move-quality icon (Flaws card)', () => {
    it.each([
      ['blunder', '??'],
      ['mistake', '?'],
    ] as const)('a %s badge with showIcon leads with the %s glyph', (severity, glyph) => {
      render(<SeverityBadge severity={severity} count={1} gameId={9} showCount={false} showIcon />);
      const badge = screen.getByTestId(`severity-${severity}-9`);
      expect(badge.firstElementChild?.tagName.toLowerCase()).toBe('svg');
      expect(badge.querySelector('svg text')?.textContent).toBe(glyph);
    });

    it('renders no icon by default and a count badge (Games card) is unchanged', () => {
      render(<SeverityBadge severity="blunder" count={3} gameId={11} />);
      const badge = screen.getByTestId('severity-blunder-11');
      expect(badge.querySelector('svg')).toBeNull();
      expect(badge.textContent).toBe('3Blunders');
      expect(badge.className).not.toContain('hover:-translate-y-px');
    });

    it('never carries the facepalm score: no button, no percent', () => {
      const { container } = render(
        <SeverityBadge severity="blunder" count={1} gameId={12} showCount={false} showIcon />,
      );
      expect(container.querySelector('button')).toBeNull();
      expect(screen.getByTestId('severity-blunder-12').textContent).toBe('??Blunder');
    });
  });
});
