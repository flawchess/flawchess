// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach, beforeAll, beforeEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { FlawFilterControl } from '../FlawFilterControl';
import type { FlawTag } from '@/types/library';
import type { TacticFamily } from '@/lib/tacticComparisonMeta';

// Tactic tagging is beta-gated (Quick 260623). Mock useUserProfile with a mutable flag:
// beta=true keeps the tactic sections + collapsible Context for the existing suite;
// flip to false in the gating block to assert the non-beta layout.
let mockBetaEnabled = true;
vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => ({ data: { is_guest: false, beta_enabled: mockBetaEnabled }, isLoading: false }),
}));

// Stub ResizeObserver — required by Radix UI ToggleGroup (added Phase 129 TACUI-06).
// [Rule 1 - Bug] The ToggleGroup uses @radix-ui/react-use-size which calls ResizeObserver;
// jsdom doesn't provide it, so tests with showTacticFilter=true crash without this stub.
beforeAll(() => {
  if (typeof window.ResizeObserver === 'undefined') {
    window.ResizeObserver = class ResizeObserver {
      observe = vi.fn();
      unobserve = vi.fn();
      disconnect = vi.fn();
    };
  }
});

const defaultProps = {
  severity: ['blunder', 'mistake'] as ('blunder' | 'mistake')[],
  tags: [] as FlawTag[],
  onSeverityChange: vi.fn(),
  onTagChange: vi.fn(),
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  mockBetaEnabled = true;
});

/**
 * Render FlawFilterControl and expand the Context section so family/tag testids are
 * accessible. Use this helper in any test that needs Context tags or family groups.
 */
function renderExpanded(props: typeof defaultProps & Record<string, unknown> = defaultProps) {
  render(<FlawFilterControl {...props} />);
  fireEvent.click(screen.getByTestId('filter-flaw-context-toggle'));
}

describe('FlawFilterControl', () => {
  describe('tactic motif family (Phase 126)', () => {
    it('hides the tactic section by default (showTacticFilter unset)', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.queryByTestId('filter-flaw-tactic-group-piece_attacks')).toBeNull();
    });

    it('renders the two always-on mechanism groups and their 9 family buttons when showTacticFilter is set', () => {
      render(<FlawFilterControl {...defaultProps} showTacticFilter />);
      for (const key of ['piece_attacks', 'discoveries']) {
        expect(screen.getByTestId(`filter-flaw-tactic-group-${key}`)).toBeTruthy();
      }
      // x_ray + the 5 tier-3 families live in the collapsed Advanced group, not here.
      for (const fam of [
        'fork', 'skewer', 'pin', 'double_check', 'discovered_check',
        'discovered_attack', 'trapped_piece', 'hanging', 'mate',
      ]) {
        expect(screen.getByTestId(`filter-flaw-tactic-${fam}`)).toBeTruthy();
      }
      // Chips read kebab-case; mate chip relabeled "checkmate" (Quick 260620-onv).
      expect(screen.getByTestId('filter-flaw-tactic-hanging').textContent).toBe('hanging-piece');
      expect(screen.getByTestId('filter-flaw-tactic-mate').textContent).toBe('checkmate');
    });

    // Advanced tier-3 group (Quick 260623-6pd) — collapsed by default.
    const ADVANCED_FAMILIES = [
      'x_ray', 'deflection', 'intermezzo', 'interference', 'clearance', 'capturing_defender',
      'en_passant', 'under_promotion',
    ];

    it('Advanced families are hidden until the Advanced toggle is expanded', () => {
      render(<FlawFilterControl {...defaultProps} showTacticFilter />);
      const toggle = screen.getByTestId('filter-flaw-advanced-toggle');
      expect(toggle.getAttribute('aria-expanded')).toBe('false');
      for (const fam of ADVANCED_FAMILIES) {
        expect(screen.queryByTestId(`filter-flaw-tactic-${fam}`)).toBeNull();
      }
    });

    it('clicking the Advanced toggle reveals x-ray + the 5 tier-3 family buttons', () => {
      render(<FlawFilterControl {...defaultProps} showTacticFilter />);
      fireEvent.click(screen.getByTestId('filter-flaw-advanced-toggle'));
      for (const fam of ADVANCED_FAMILIES) {
        expect(screen.getByTestId(`filter-flaw-tactic-${fam}`)).toBeTruthy();
      }
      // Chips read kebab-case (capturing_defender family → "capturing-defender" chip).
      expect(screen.getByTestId('filter-flaw-tactic-capturing_defender').textContent)
        .toBe('capturing-defender');
    });

    it('the Advanced toggle is absent on the Games tab (showTacticFilter unset)', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.queryByTestId('filter-flaw-advanced-toggle')).toBeNull();
    });

    it('Advanced toggle shows a "· N" badge counting selected tier-3 families', () => {
      render(
        <FlawFilterControl
          {...defaultProps}
          showTacticFilter
          tacticFamilies={['deflection', 'clearance'] as TacticFamily[]}
        />,
      );
      expect(screen.getByTestId('filter-flaw-advanced-toggle').textContent).toContain('Advanced · 2');
    });

    it('clicking a revealed Advanced family toggles it via onTacticFamiliesChange', () => {
      const onTacticFamiliesChange = vi.fn();
      render(
        <FlawFilterControl
          {...defaultProps}
          showTacticFilter
          tacticFamilies={[]}
          onTacticFamiliesChange={onTacticFamiliesChange}
        />,
      );
      fireEvent.click(screen.getByTestId('filter-flaw-advanced-toggle'));
      fireEvent.click(screen.getByTestId('filter-flaw-tactic-deflection'));
      expect(onTacticFamiliesChange).toHaveBeenCalledWith(['deflection']);
    });

    it('all families are off (aria-pressed=false) by default', () => {
      render(<FlawFilterControl {...defaultProps} showTacticFilter tacticFamilies={[]} />);
      expect(screen.getByTestId('filter-flaw-tactic-fork').getAttribute('aria-pressed')).toBe('false');
    });

    it('clicking an inactive family adds it via onTacticFamiliesChange', () => {
      const onTacticFamiliesChange = vi.fn();
      render(
        <FlawFilterControl
          {...defaultProps}
          showTacticFilter
          tacticFamilies={[]}
          onTacticFamiliesChange={onTacticFamiliesChange}
        />,
      );
      fireEvent.click(screen.getByTestId('filter-flaw-tactic-fork'));
      expect(onTacticFamiliesChange).toHaveBeenCalledWith(['fork']);
    });

    it('clicking an active family removes it', () => {
      const onTacticFamiliesChange = vi.fn();
      render(
        <FlawFilterControl
          {...defaultProps}
          showTacticFilter
          tacticFamilies={['fork', 'mate']}
          onTacticFamiliesChange={onTacticFamiliesChange}
        />,
      );
      fireEvent.click(screen.getByTestId('filter-flaw-tactic-fork'));
      expect(onTacticFamiliesChange).toHaveBeenCalledWith(['mate']);
    });
  });

  // Severity moved inside the collapsed Context section (Quick 260620-mjh follow-up):
  // it now lives on top of the tag families and is hidden until Context is expanded.
  describe('severity buttons', () => {
    it('hides severity buttons until Context is expanded', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.queryByTestId('filter-flaw-severity-blunder')).toBeNull();
    });

    it('renders both severity buttons after expanding Context', () => {
      renderExpanded();
      expect(screen.getByTestId('filter-flaw-severity-blunder')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-severity-mistake')).toBeTruthy();
    });

    it('severity buttons reflect active state via aria-pressed', () => {
      renderExpanded({ ...defaultProps, severity: ['blunder'] });
      const blunderBtn = screen.getByTestId('filter-flaw-severity-blunder');
      const mistakeBtn = screen.getByTestId('filter-flaw-severity-mistake');
      expect(blunderBtn.getAttribute('aria-pressed')).toBe('true');
      expect(mistakeBtn.getAttribute('aria-pressed')).toBe('false');
    });

    it('clicking an inactive severity button calls onSeverityChange', () => {
      const onSeverityChange = vi.fn();
      renderExpanded({ ...defaultProps, severity: ['blunder'], onSeverityChange });
      fireEvent.click(screen.getByTestId('filter-flaw-severity-mistake'));
      expect(onSeverityChange).toHaveBeenCalledWith(['blunder', 'mistake']);
    });

    it('deselecting the last active severity yields [] (both shown — no guard)', () => {
      const onSeverityChange = vi.fn();
      renderExpanded({ ...defaultProps, severity: ['blunder'], onSeverityChange });
      // Clicking the only active severity clears it — empty severity = both shown.
      fireEvent.click(screen.getByTestId('filter-flaw-severity-blunder'));
      expect(onSeverityChange).toHaveBeenCalledWith([]);
    });

    it('defaults render both severity buttons inactive (empty severity = both shown)', () => {
      renderExpanded({ ...defaultProps, severity: [] });
      expect(
        screen.getByTestId('filter-flaw-severity-blunder').getAttribute('aria-pressed'),
      ).toBe('false');
      expect(
        screen.getByTestId('filter-flaw-severity-mistake').getAttribute('aria-pressed'),
      ).toBe('false');
    });
  });

  describe('tag family groups', () => {
    it('renders all 4 family groups (incl. Game Phase) after expanding Context', () => {
      renderExpanded();
      expect(screen.getByTestId('filter-flaw-family-tempo')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-family-opportunity')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-family-impact')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-family-phase')).toBeTruthy();
    });

    it('renders all 7 non-phase tag buttons after expanding Context', () => {
      renderExpanded();
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

    it('renders the 3 phase tag buttons after expanding Context', () => {
      renderExpanded();
      expect(screen.getByTestId('filter-flaw-tag-opening')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-tag-middlegame')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-tag-endgame')).toBeTruthy();
    });

    it('toggling a phase tag calls onTagChange with the tag added', () => {
      const onTagChange = vi.fn();
      renderExpanded({ ...defaultProps, onTagChange });
      fireEvent.click(screen.getByTestId('filter-flaw-tag-middlegame'));
      expect(onTagChange).toHaveBeenCalledWith(['middlegame']);
    });

    it('toggling an unselected tag calls onTagChange with the tag added', () => {
      const onTagChange = vi.fn();
      renderExpanded({ ...defaultProps, onTagChange });
      fireEvent.click(screen.getByTestId('filter-flaw-tag-miss'));
      expect(onTagChange).toHaveBeenCalledWith(['miss']);
    });

    it('toggling a selected tag calls onTagChange with the tag removed', () => {
      const onTagChange = vi.fn();
      renderExpanded({
        ...defaultProps,
        tags: ['miss', 'reversed'] as FlawTag[],
        onTagChange,
      });
      fireEvent.click(screen.getByTestId('filter-flaw-tag-miss'));
      expect(onTagChange).toHaveBeenCalledWith(['reversed']);
    });

    it('tag buttons have aria-pressed reflecting selection', () => {
      renderExpanded({
        ...defaultProps,
        tags: ['reversed'] as FlawTag[],
      });
      expect(screen.getByTestId('filter-flaw-tag-reversed').getAttribute('aria-pressed')).toBe('true');
      expect(screen.getByTestId('filter-flaw-tag-miss').getAttribute('aria-pressed')).toBe('false');
    });
  });

  describe('canonical tag names', () => {
    it('renders the raw lowercase-with-dash tag name, not a title-cased label', () => {
      renderExpanded();
      const lucky = screen.getByTestId('filter-flaw-tag-lucky');
      const lowClock = screen.getByTestId('filter-flaw-tag-low-clock');
      expect(lucky.textContent).toContain('lucky');
      expect(lowClock.textContent).toContain('low-clock');
      // The old title-cased TAG_LABELS values must be gone.
      expect(lucky.textContent).not.toContain('Lucky');
      expect(lowClock.textContent).not.toContain('Low clock');
    });

    it('every non-phase tag button shows its canonical lowercase-with-dash name', () => {
      renderExpanded();
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
      renderExpanded();
      const tempoGroup = screen.getByTestId('filter-flaw-family-tempo');
      expect(tempoGroup.getAttribute('role')).toBe('group');
      expect(tempoGroup.getAttribute('aria-label')).toBe('Timing tag filters');

      const oppGroup = screen.getByTestId('filter-flaw-family-opportunity');
      expect(oppGroup.getAttribute('aria-label')).toBe('Opportunity tag filters');

      const impGroup = screen.getByTestId('filter-flaw-family-impact');
      expect(impGroup.getAttribute('aria-label')).toBe('Impact tag filters');
    });

    it('tag buttons have aria-label', () => {
      renderExpanded();
      const btn = screen.getByTestId('filter-flaw-tag-miss');
      expect(btn.getAttribute('aria-label')).toBe('Filter flaws by tag: miss');
    });

  });

  describe('context collapse (Quick 260620-mjh)', () => {
    it('Context family groups are hidden by default', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.queryByTestId('filter-flaw-family-tempo')).toBeNull();
    });

    it('the toggle exists with aria-expanded="false" by default', () => {
      render(<FlawFilterControl {...defaultProps} />);
      const toggle = screen.getByTestId('filter-flaw-context-toggle');
      expect(toggle.getAttribute('aria-expanded')).toBe('false');
    });

    it('aria-expanded becomes "true" after clicking the toggle', () => {
      render(<FlawFilterControl {...defaultProps} />);
      const toggle = screen.getByTestId('filter-flaw-context-toggle');
      fireEvent.click(toggle);
      expect(toggle.getAttribute('aria-expanded')).toBe('true');
    });

    it('clicking the toggle reveals Context family groups', () => {
      render(<FlawFilterControl {...defaultProps} />);
      fireEvent.click(screen.getByTestId('filter-flaw-context-toggle'));
      expect(screen.getByTestId('filter-flaw-family-tempo')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-tag-miss')).toBeTruthy();
    });

    it('clicking the toggle twice hides family groups again', () => {
      render(<FlawFilterControl {...defaultProps} />);
      const toggle = screen.getByTestId('filter-flaw-context-toggle');
      fireEvent.click(toggle);
      fireEvent.click(toggle);
      expect(screen.queryByTestId('filter-flaw-family-tempo')).toBeNull();
    });

    it('count badge shows "Context · 2" when 2 Context tags are selected', () => {
      render(
        <FlawFilterControl
          {...defaultProps}
          tags={['miss', 'opening'] as FlawTag[]}
        />,
      );
      const toggle = screen.getByTestId('filter-flaw-context-toggle');
      expect(toggle.textContent).toContain('Context · 2');
    });

    it('no count badge when no Context tags are selected', () => {
      render(<FlawFilterControl {...defaultProps} tags={[] as FlawTag[]} />);
      const toggle = screen.getByTestId('filter-flaw-context-toggle');
      expect(toggle.textContent).toContain('Context');
      expect(toggle.textContent).not.toContain('·');
    });

    it('Context toggle is present even when showTacticFilter is false (Games tab)', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.getByTestId('filter-flaw-context-toggle')).toBeTruthy();
    });
  });

  // Tactic tagging is hidden for non-beta users (Quick 260623): no tactic sections,
  // and the Context section renders inline (no collapsible toggle).
  describe('beta gating (Quick 260623)', () => {
    beforeEach(() => {
      mockBetaEnabled = false;
    });

    it('hides all tactic sections even when showTacticFilter is set', () => {
      render(<FlawFilterControl {...defaultProps} showTacticFilter />);
      expect(screen.queryByTestId('filter-flaw-tactic-group-piece_attacks')).toBeNull();
      expect(screen.queryByTestId('filter-flaw-advanced-toggle')).toBeNull();
      expect(screen.queryByTestId('filter-tactic-orientation')).toBeNull();
    });

    it('renders the Context section inline with no collapsible toggle', () => {
      render(<FlawFilterControl {...defaultProps} showTacticFilter />);
      expect(screen.queryByTestId('filter-flaw-context-toggle')).toBeNull();
      // Family groups + severity are visible without expanding anything.
      expect(screen.getByTestId('filter-flaw-family-tempo')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-severity-blunder')).toBeTruthy();
    });
  });
});
