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
  onClear: vi.fn(),
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
        'filter-flaw-tag-impatient',
        'filter-flaw-tag-considered',
        'filter-flaw-tag-miss',
        'filter-flaw-tag-lucky-escape',
        'filter-flaw-tag-result-changing',
        'filter-flaw-tag-while-ahead',
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
          tags={['miss', 'result-changing'] as FlawTag[]}
          onTagChange={onTagChange}
        />,
      );
      fireEvent.click(screen.getByTestId('filter-flaw-tag-miss'));
      expect(onTagChange).toHaveBeenCalledWith(['result-changing']);
    });

    it('tag buttons have aria-pressed reflecting selection', () => {
      render(
        <FlawFilterControl
          {...defaultProps}
          tags={['result-changing'] as FlawTag[]}
        />,
      );
      expect(screen.getByTestId('filter-flaw-tag-result-changing').getAttribute('aria-pressed')).toBe('true');
      expect(screen.getByTestId('filter-flaw-tag-miss').getAttribute('aria-pressed')).toBe('false');
    });
  });

  describe('clear affordance', () => {
    it('clear button is hidden when filter is at default (both severities, no tags)', () => {
      render(
        <FlawFilterControl
          {...defaultProps}
          severity={['blunder', 'mistake']}
          tags={[]}
        />,
      );
      expect(screen.queryByTestId('btn-clear-flaw-filter')).toBeNull();
    });

    it('clear button is shown when a tag is selected', () => {
      render(
        <FlawFilterControl
          {...defaultProps}
          tags={['miss'] as FlawTag[]}
        />,
      );
      expect(screen.getByTestId('btn-clear-flaw-filter')).toBeTruthy();
    });

    it('clear button is shown when severity is not both M+B', () => {
      render(
        <FlawFilterControl
          {...defaultProps}
          severity={['blunder']}
          tags={[]}
        />,
      );
      expect(screen.getByTestId('btn-clear-flaw-filter')).toBeTruthy();
    });

    it('clicking clear calls onClear', () => {
      const onClear = vi.fn();
      render(
        <FlawFilterControl
          {...defaultProps}
          tags={['miss'] as FlawTag[]}
          onClear={onClear}
        />,
      );
      fireEvent.click(screen.getByTestId('btn-clear-flaw-filter'));
      expect(onClear).toHaveBeenCalledOnce();
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

    it('clear button has correct aria-label', () => {
      render(
        <FlawFilterControl
          {...defaultProps}
          tags={['miss'] as FlawTag[]}
        />,
      );
      const clearBtn = screen.getByTestId('btn-clear-flaw-filter');
      expect(clearBtn.getAttribute('aria-label')).toBe('Clear all flaw filter selections');
    });
  });
});
