// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { FlawFilterControl } from '../FlawFilterControl';
import type { FlawTag } from '@/types/library';

const defaultProps = {
  severity: ['blunder', 'mistake'] as ('blunder' | 'mistake')[],
  tags: [] as FlawTag[],
  onSeverityChange: vi.fn(),
  onTagChange: vi.fn(),
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('FlawFilterControl', () => {
  describe('severity buttons', () => {
    it('renders both severity buttons', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.getByTestId('filter-flaw-severity-blunder')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-severity-mistake')).toBeTruthy();
    });

    it('severity buttons reflect active state via aria-pressed', () => {
      render(
        <FlawFilterControl
          {...defaultProps}
          severity={['blunder']}
        />,
      );
      const blunderBtn = screen.getByTestId('filter-flaw-severity-blunder');
      const mistakeBtn = screen.getByTestId('filter-flaw-severity-mistake');
      expect(blunderBtn.getAttribute('aria-pressed')).toBe('true');
      expect(mistakeBtn.getAttribute('aria-pressed')).toBe('false');
    });

    it('clicking an inactive severity button calls onSeverityChange', () => {
      const onSeverityChange = vi.fn();
      render(
        <FlawFilterControl
          {...defaultProps}
          severity={['blunder']}
          onSeverityChange={onSeverityChange}
        />,
      );
      fireEvent.click(screen.getByTestId('filter-flaw-severity-mistake'));
      expect(onSeverityChange).toHaveBeenCalledWith(['blunder', 'mistake']);
    });

    it('at-least-one-severity guard: deselecting last active severity is a no-op', () => {
      const onSeverityChange = vi.fn();
      render(
        <FlawFilterControl
          {...defaultProps}
          severity={['blunder']}
          onSeverityChange={onSeverityChange}
        />,
      );
      // Clicking the only active severity should NOT call onSeverityChange
      fireEvent.click(screen.getByTestId('filter-flaw-severity-blunder'));
      expect(onSeverityChange).not.toHaveBeenCalled();
    });
  });

  describe('tag family groups', () => {
    it('renders all 3 family groups', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.getByTestId('filter-flaw-family-tempo')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-family-opportunity')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-family-impact')).toBeTruthy();
    });

    it('renders all 7 non-phase tag buttons', () => {
      render(<FlawFilterControl {...defaultProps} />);
      const tagButtons = [
        'filter-flaw-tag-low-clock',
        'filter-flaw-tag-hasty',
        'filter-flaw-tag-unrushed',
        'filter-flaw-tag-miss',
        'filter-flaw-tag-lucky',
        'filter-flaw-tag-reversed',
        'filter-flaw-tag-squandered',
      ];
      for (const testid of tagButtons) {
        expect(screen.getByTestId(testid)).toBeTruthy();
      }
    });

    it('phase tags are absent', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.queryByTestId('filter-flaw-tag-opening')).toBeNull();
      expect(screen.queryByTestId('filter-flaw-tag-middlegame')).toBeNull();
      expect(screen.queryByTestId('filter-flaw-tag-endgame')).toBeNull();
    });

    it('toggling an unselected tag calls onTagChange with the tag added', () => {
      const onTagChange = vi.fn();
      render(<FlawFilterControl {...defaultProps} onTagChange={onTagChange} />);
      fireEvent.click(screen.getByTestId('filter-flaw-tag-miss'));
      expect(onTagChange).toHaveBeenCalledWith(['miss']);
    });

    it('toggling a selected tag calls onTagChange with the tag removed', () => {
      const onTagChange = vi.fn();
      render(
        <FlawFilterControl
          {...defaultProps}
          tags={['miss', 'reversed'] as FlawTag[]}
          onTagChange={onTagChange}
        />,
      );
      fireEvent.click(screen.getByTestId('filter-flaw-tag-miss'));
      expect(onTagChange).toHaveBeenCalledWith(['reversed']);
    });

    it('tag buttons have aria-pressed reflecting selection', () => {
      render(
        <FlawFilterControl
          {...defaultProps}
          tags={['reversed'] as FlawTag[]}
        />,
      );
      expect(screen.getByTestId('filter-flaw-tag-reversed').getAttribute('aria-pressed')).toBe('true');
      expect(screen.getByTestId('filter-flaw-tag-miss').getAttribute('aria-pressed')).toBe('false');
    });
  });

  describe('canonical tag names', () => {
    it('renders the raw lowercase-with-dash tag name, not a title-cased label', () => {
      render(<FlawFilterControl {...defaultProps} />);
      const lucky = screen.getByTestId('filter-flaw-tag-lucky');
      const lowClock = screen.getByTestId('filter-flaw-tag-low-clock');
      expect(lucky.textContent).toContain('lucky');
      expect(lowClock.textContent).toContain('low-clock');
      // The old title-cased TAG_LABELS values must be gone.
      expect(lucky.textContent).not.toContain('Lucky');
      expect(lowClock.textContent).not.toContain('Low clock');
    });

    it('every non-phase tag button shows its canonical lowercase-with-dash name', () => {
      render(<FlawFilterControl {...defaultProps} />);
      const canonical: FlawTag[] = [
        'low-clock', 'hasty', 'unrushed', 'miss', 'lucky', 'reversed', 'squandered',
      ];
      for (const tag of canonical) {
        expect(screen.getByTestId(`filter-flaw-tag-${tag}`).textContent).toContain(tag);
      }
    });

  });

  describe('clear affordance', () => {
    it('no "Clear flaw filter" button rendered (reset is now in parent FilterActions footer)', () => {
      // The clear affordance was removed — Reset is handled by FilterActions in the parent panel.
      render(
        <FlawFilterControl
          {...defaultProps}
          severity={['blunder', 'mistake']}
          tags={[]}
        />,
      );
      expect(screen.queryByTestId('btn-clear-flaw-filter')).toBeNull();
    });

    it('no "Clear flaw filter" button even when tags are selected', () => {
      render(
        <FlawFilterControl
          {...defaultProps}
          tags={['miss'] as FlawTag[]}
        />,
      );
      expect(screen.queryByTestId('btn-clear-flaw-filter')).toBeNull();
    });
  });

  describe('accessibility', () => {
    it('family groups have correct role and aria-label', () => {
      render(<FlawFilterControl {...defaultProps} />);
      const tempoGroup = screen.getByTestId('filter-flaw-family-tempo');
      expect(tempoGroup.getAttribute('role')).toBe('group');
      expect(tempoGroup.getAttribute('aria-label')).toBe('Timing tag filters');

      const oppGroup = screen.getByTestId('filter-flaw-family-opportunity');
      expect(oppGroup.getAttribute('aria-label')).toBe('Opportunity tag filters');

      const impGroup = screen.getByTestId('filter-flaw-family-impact');
      expect(impGroup.getAttribute('aria-label')).toBe('Impact tag filters');
    });

    it('tag buttons have aria-label', () => {
      render(<FlawFilterControl {...defaultProps} />);
      const btn = screen.getByTestId('filter-flaw-tag-miss');
      expect(btn.getAttribute('aria-label')).toBe('Filter flaws by tag: miss');
    });

  });
});
