// @vitest-environment jsdom
/**
 * SeverityBadge vitest suite — covers:
 *
 * 1. "Inacc." abbreviated label
 * 2. Active-filter ring when the badge's own tag is part of a narrowing selection (D-27):
 *    a "???" badge answers to Facepalm, a "??" badge to Blunder, a mistake badge to Mistake
 * 3. No ring with nothing or all three tags selected, and never for inaccuracy
 * 4. onHover fires true/false on pointer enter/leave
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { SeverityBadge } from '../SeverityBadge';
import {
  ACTIVE_FILTER_RING_CLASS,
  SEV_FACEPALM,
  SEV_FACEPALM_ON,
  SEV_BLUNDER,
  SEV_BLUNDER_BG,
  SEV_BLUNDER_BORDER,
} from '@/lib/theme';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

let mockFlawFilterState: FlawFilterState = { severity: [], tags: [] };

vi.mock('@/hooks/useFlawFilterStore', () => ({
  useFlawFilterStore: () => [mockFlawFilterState, vi.fn()] as const,
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  mockFlawFilterState = { severity: [], tags: [] };
});

/** jsdom normalizes colour strings (oklch(0.50 ..) -> oklch(0.5 ..)); compare normalized forms. */
function normalizedColor(prop: 'color' | 'backgroundColor' | 'borderColor', value: string): string {
  const probe = document.createElement('div');
  probe.style[prop] = value;
  return probe.style[prop];
}

const ringClasses = ACTIVE_FILTER_RING_CLASS.split(' ');

describe('SeverityBadge', () => {
  describe('labels', () => {
    it('a facepalm blunder badge without a count reads "Facepalm" (aria-label too), testid stays blunder', () => {
      render(<SeverityBadge severity="blunder" count={1} gameId={21} showCount={false} showIcon facepalm />);
      const badge = screen.getByTestId('severity-blunder-21');
      expect(badge.textContent).toBe('???Facepalm');
      expect(badge.getAttribute('aria-label')).toBe('Facepalm');
    });

    it('a plain blunder badge reads "Blunder" and a facepalm flag on a mistake is ignored', () => {
      render(<SeverityBadge severity="blunder" count={1} gameId={22} showCount={false} showIcon />);
      const blunder = screen.getByTestId('severity-blunder-22');
      expect(blunder.textContent).toBe('??Blunder');
      expect(blunder.getAttribute('aria-label')).toBe('Blunder');
      render(<SeverityBadge severity="mistake" count={1} gameId={23} showCount={false} showIcon facepalm />);
      expect(screen.getByTestId('severity-mistake-23').textContent).toBe('?Mistake');
    });

    it('renders the abbreviated "Inacc." label', () => {
      render(<SeverityBadge severity="inaccuracy" count={4} gameId={1} />);
      const badge = screen.getByTestId('severity-inaccuracy-1');
      expect(badge.textContent).toContain('Inacc.');
    });
  });

  describe('palette (260-G1)', () => {
    it('a facepalm blunder badge is a solid SEV_FACEPALM fill with a light label', () => {
      render(<SeverityBadge severity="blunder" count={1} gameId={31} showCount={false} showIcon facepalm />);
      const badge = screen.getByTestId('severity-blunder-31');
      expect(badge.style.backgroundColor).toBe(normalizedColor('backgroundColor', SEV_FACEPALM));
      expect(badge.style.borderColor).toBe(normalizedColor('borderColor', SEV_FACEPALM));
      expect(badge.style.color).toBe(normalizedColor('color', SEV_FACEPALM_ON));
    });

    it('a plain blunder badge keeps the tinted pill', () => {
      render(<SeverityBadge severity="blunder" count={1} gameId={32} showCount={false} showIcon />);
      const badge = screen.getByTestId('severity-blunder-32');
      expect(badge.style.color).toBe(normalizedColor('color', SEV_BLUNDER));
      expect(badge.style.backgroundColor).toBe(normalizedColor('backgroundColor', SEV_BLUNDER_BG));
      expect(badge.style.borderColor).toBe(normalizedColor('borderColor', SEV_BLUNDER_BORDER));
    });

    it('a ringed Facepalm badge rings in SEV_FACEPALM (D-27)', () => {
      mockFlawFilterState = { severity: ['facepalm'], tags: [] };
      render(<SeverityBadge severity="blunder" count={1} gameId={33} showCount={false} showIcon facepalm />);
      const badge = screen.getByTestId('severity-blunder-33');
      for (const cls of ringClasses) expect(badge.className).toContain(cls);
      expect(badge.style.getPropertyValue('--tw-ring-color')).toBe(SEV_FACEPALM);
    });
  });

  describe('active-filter ring', () => {
    it('rings when the severity filter is narrowed to this severity', () => {
      mockFlawFilterState = { severity: ['blunder'], tags: [] };
      render(<SeverityBadge severity="blunder" count={2} gameId={2} />);
      const badge = screen.getByTestId('severity-blunder-2');
      for (const cls of ringClasses) expect(badge.className).toContain(cls);
    });

    it('does NOT ring when no tag is selected (the default filter)', () => {
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

    it('does NOT ring any badge when all three tags are selected', () => {
      mockFlawFilterState = { severity: ['facepalm', 'blunder', 'mistake'], tags: [] };
      render(<SeverityBadge severity="blunder" count={2} gameId={6} />);
      render(<SeverityBadge severity="blunder" count={2} gameId={7} facepalm />);
      render(<SeverityBadge severity="mistake" count={2} gameId={8} />);
      for (const id of ['severity-blunder-6', 'severity-blunder-7', 'severity-mistake-8']) {
        for (const cls of ringClasses) expect(screen.getByTestId(id).className).not.toContain(cls);
      }
    });

    it('rings a "???" badge under facepalm and facepalm+mistake, not under blunder', () => {
      mockFlawFilterState = { severity: ['facepalm'], tags: [] };
      render(<SeverityBadge severity="blunder" count={1} gameId={9} showIcon facepalm />);
      for (const cls of ringClasses) {
        expect(screen.getByTestId('severity-blunder-9').className).toContain(cls);
      }
      cleanup();
      mockFlawFilterState = { severity: ['facepalm', 'mistake'], tags: [] };
      render(<SeverityBadge severity="blunder" count={1} gameId={10} showIcon facepalm />);
      for (const cls of ringClasses) {
        expect(screen.getByTestId('severity-blunder-10').className).toContain(cls);
      }
      cleanup();
      mockFlawFilterState = { severity: ['blunder'], tags: [] };
      render(<SeverityBadge severity="blunder" count={1} gameId={11} showIcon facepalm />);
      for (const cls of ringClasses) {
        expect(screen.getByTestId('severity-blunder-11').className).not.toContain(cls);
      }
    });

    it('rings a "??" badge under blunder, not under facepalm', () => {
      mockFlawFilterState = { severity: ['blunder', 'facepalm'], tags: [] };
      render(<SeverityBadge severity="blunder" count={1} gameId={12} showIcon />);
      for (const cls of ringClasses) {
        expect(screen.getByTestId('severity-blunder-12').className).toContain(cls);
      }
      cleanup();
      mockFlawFilterState = { severity: ['facepalm'], tags: [] };
      render(<SeverityBadge severity="blunder" count={1} gameId={13} showIcon />);
      for (const cls of ringClasses) {
        expect(screen.getByTestId('severity-blunder-13').className).not.toContain(cls);
      }
    });

    it('rings a mistake badge under mistake', () => {
      mockFlawFilterState = { severity: ['mistake'], tags: [] };
      render(<SeverityBadge severity="mistake" count={1} gameId={14} />);
      for (const cls of ringClasses) {
        expect(screen.getByTestId('severity-mistake-14').className).toContain(cls);
      }
    });

    it('never rings when showActiveFilterRing is false (Train card)', () => {
      mockFlawFilterState = { severity: ['blunder'], tags: [] };
      render(<SeverityBadge severity="blunder" count={1} gameId={15} showActiveFilterRing={false} />);
      for (const cls of ringClasses) {
        expect(screen.getByTestId('severity-blunder-15').className).not.toContain(cls);
      }
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
