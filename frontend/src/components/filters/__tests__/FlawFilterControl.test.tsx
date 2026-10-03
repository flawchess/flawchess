// @vitest-environment jsdom
import { useState } from 'react';
import { describe, it, expect, vi, afterEach, beforeAll, beforeEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { FlawFilterControl } from '../FlawFilterControl';
import { OpponentStrengthFilter } from '../OpponentStrengthFilter';
import { TacticDepthFilter } from '../TacticDepthFilter';
import { ANY_RANGE } from '@/lib/opponentStrength';
import type { OpponentStrengthRange } from '@/types/api';
import { DEFAULT_TACTIC_DEPTH_VALUE, type TacticDepthValue } from '@/lib/tacticDepth';
import type { FlawTag } from '@/types/library';

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
});

/**
 * Render FlawFilterControl. The Context tag families now render as a normal (always
 * visible) titled section, so no expansion step is needed — this is a thin alias for
 * render() kept so existing tests read clearly.
 */
function renderExpanded(props: typeof defaultProps & Record<string, unknown> = defaultProps) {
  render(<FlawFilterControl {...props} />);
}

describe('FlawFilterControl', () => {
  describe('tactic motif family (Phase 126)', () => {
    it('hides the tactic section by default (showTacticFilter unset)', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.queryByTestId('filter-flaw-tactic-group-piece_attacks')).toBeNull();
    });

    it('renders the two always-on mechanism groups and their 8 family buttons when showTacticFilter is set', () => {
      render(<FlawFilterControl {...defaultProps} showTacticFilter />);
      for (const key of ['piece_attacks', 'discoveries']) {
        expect(screen.getByTestId(`filter-flaw-tactic-group-${key}`)).toBeTruthy();
      }
      // trapped_piece + x_ray + the tier-3 families live in the collapsed Advanced group, not here.
      for (const fam of [
        'fork', 'skewer', 'pin', 'double_check', 'discovered_check',
        'discovered_attack', 'hanging', 'mate',
      ]) {
        expect(screen.getByTestId(`filter-flaw-tactic-${fam}`)).toBeTruthy();
      }
      // Chips read kebab-case; mate chip relabeled "checkmate" (Quick 260620-onv).
      expect(screen.getByTestId('filter-flaw-tactic-hanging').textContent).toBe('hanging-piece');
      expect(screen.getByTestId('filter-flaw-tactic-mate').textContent).toBe('checkmate');
    });

    // Advanced tier-3 group (Quick 260623-6pd) — now a normal always-visible section.
    // "clearance" REMOVED (Phase 221 plan 06, D-07 suppression).
    const ADVANCED_FAMILIES = [
      'trapped_piece', 'x_ray', 'deflection', 'intermezzo', 'interference',
      'capturing_defender', 'en_passant', 'under_promotion',
    ];

    it('Advanced families render as a normal titled section (no toggle)', () => {
      render(<FlawFilterControl {...defaultProps} showTacticFilter />);
      // The old collapse toggle is gone; the group is rendered directly.
      expect(screen.queryByTestId('filter-flaw-advanced-toggle')).toBeNull();
      expect(screen.getByTestId('filter-flaw-tactic-group-advanced')).toBeTruthy();
      for (const fam of ADVANCED_FAMILIES) {
        expect(screen.getByTestId(`filter-flaw-tactic-${fam}`)).toBeTruthy();
      }
      // Chips read kebab-case (capturing_defender family → "capturing-defender" chip).
      expect(screen.getByTestId('filter-flaw-tactic-capturing_defender').textContent)
        .toBe('capturing-defender');
    });

    it('the Advanced section is absent on the Games tab (showTacticFilter unset)', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.queryByTestId('filter-flaw-tactic-group-advanced')).toBeNull();
    });

    it('clicking an Advanced family toggles it via onTacticFamiliesChange', () => {
      const onTacticFamiliesChange = vi.fn();
      render(
        <FlawFilterControl
          {...defaultProps}
          showTacticFilter
          tacticFamilies={[]}
          onTacticFamiliesChange={onTacticFamiliesChange}
        />,
      );
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

  // Severity is pinned to the top of the panel, above Tactic Depth (Quick 260624):
  // it is always visible, no longer inside the collapsed Context section.
  describe('severity buttons', () => {
    it('renders both severity buttons without expanding Context', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.getByTestId('filter-flaw-severity-blunder')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-severity-mistake')).toBeTruthy();
    });

    it('severity buttons reflect active state via aria-pressed', () => {
      render(<FlawFilterControl {...defaultProps} severity={['blunder']} />);
      const blunderBtn = screen.getByTestId('filter-flaw-severity-blunder');
      const mistakeBtn = screen.getByTestId('filter-flaw-severity-mistake');
      expect(blunderBtn.getAttribute('aria-pressed')).toBe('true');
      expect(mistakeBtn.getAttribute('aria-pressed')).toBe('false');
    });

    it('clicking an inactive severity button calls onSeverityChange', () => {
      const onSeverityChange = vi.fn();
      render(
        <FlawFilterControl {...defaultProps} severity={['blunder']} onSeverityChange={onSeverityChange} />,
      );
      fireEvent.click(screen.getByTestId('filter-flaw-severity-mistake'));
      expect(onSeverityChange).toHaveBeenCalledWith(['blunder', 'mistake']);
    });

    it('deselecting the last active severity yields [] (both shown — no guard)', () => {
      const onSeverityChange = vi.fn();
      render(
        <FlawFilterControl {...defaultProps} severity={['blunder']} onSeverityChange={onSeverityChange} />,
      );
      // Clicking the only active severity clears it — empty severity = both shown.
      fireEvent.click(screen.getByTestId('filter-flaw-severity-blunder'));
      expect(onSeverityChange).toHaveBeenCalledWith([]);
    });

    it('defaults render both severity buttons inactive (empty severity = both shown)', () => {
      render(<FlawFilterControl {...defaultProps} severity={[]} />);
      expect(
        screen.getByTestId('filter-flaw-severity-blunder').getAttribute('aria-pressed'),
      ).toBe('false');
      expect(
        screen.getByTestId('filter-flaw-severity-mistake').getAttribute('aria-pressed'),
      ).toBe('false');
    });
  });

  describe('Best Moves (gem / great toggles, FILT-01 Phase 175)', () => {
    // Real usage: BOTH library tabs pass showTacticFilter=true. The Games tab is
    // distinguished ONLY by passing the gem/great toggle handlers (GamesTab), while
    // the Flaws tab passes none (FlawsTab). The render gate keys on the handlers'
    // presence, NOT showTacticFilter — the post-verify bug fix. These props mirror
    // GamesTab's two render sites exactly.
    const gamesTabProps = {
      ...defaultProps,
      showTacticFilter: true,
      onHasGemToggle: vi.fn(),
      onHasGreatToggle: vi.fn(),
    };

    it('renders both toggles on the Games tab (showTacticFilter=true + gem/great handlers)', () => {
      render(<FlawFilterControl {...gamesTabProps} />);
      expect(screen.getByTestId('filter-has-gem')).toBeTruthy();
      expect(screen.getByTestId('filter-has-great')).toBeTruthy();
    });

    it('hides both toggles on the Flaws tab (showTacticFilter=true, NO gem/great handlers)', () => {
      // Mirrors FlawsTab: showTacticFilter=true but no onHasGem/GreatToggle props.
      // Regression guard: the old `!showTactics` gate would WRONGLY hide the section
      // on the Games tab and (coincidentally) also here — this test only passes with
      // the handler-presence gate because the Games-tab test above uses the same
      // showTacticFilter=true, so the two cases now differ ONLY by the handlers.
      render(<FlawFilterControl {...defaultProps} showTacticFilter />);
      expect(screen.queryByTestId('filter-has-gem')).toBeNull();
      expect(screen.queryByTestId('filter-has-great')).toBeNull();
    });

    it('both toggles default to aria-pressed=false', () => {
      render(<FlawFilterControl {...gamesTabProps} />);
      expect(screen.getByTestId('filter-has-gem').getAttribute('aria-pressed')).toBe('false');
      expect(screen.getByTestId('filter-has-great').getAttribute('aria-pressed')).toBe('false');
    });

    it('reflects hasGem/hasGreat props via aria-pressed', () => {
      render(<FlawFilterControl {...gamesTabProps} hasGem hasGreat />);
      expect(screen.getByTestId('filter-has-gem').getAttribute('aria-pressed')).toBe('true');
      expect(screen.getByTestId('filter-has-great').getAttribute('aria-pressed')).toBe('true');
    });

    it('clicking the has-gem toggle fires onHasGemToggle', () => {
      const onHasGemToggle = vi.fn();
      render(<FlawFilterControl {...gamesTabProps} onHasGemToggle={onHasGemToggle} />);
      fireEvent.click(screen.getByTestId('filter-has-gem'));
      expect(onHasGemToggle).toHaveBeenCalledTimes(1);
    });

    it('clicking the has-great toggle fires onHasGreatToggle', () => {
      const onHasGreatToggle = vi.fn();
      render(<FlawFilterControl {...gamesTabProps} onHasGreatToggle={onHasGreatToggle} />);
      fireEvent.click(screen.getByTestId('filter-has-great'));
      expect(onHasGreatToggle).toHaveBeenCalledTimes(1);
    });

    it('has-gem and has-great are independent — clicking one does not fire the other', () => {
      const onHasGemToggle = vi.fn();
      const onHasGreatToggle = vi.fn();
      render(
        <FlawFilterControl
          {...gamesTabProps}
          onHasGemToggle={onHasGemToggle}
          onHasGreatToggle={onHasGreatToggle}
        />,
      );
      fireEvent.click(screen.getByTestId('filter-has-gem'));
      expect(onHasGemToggle).toHaveBeenCalledTimes(1);
      expect(onHasGreatToggle).not.toHaveBeenCalled();

      fireEvent.click(screen.getByTestId('filter-has-great'));
      expect(onHasGreatToggle).toHaveBeenCalledTimes(1);
      expect(onHasGemToggle).toHaveBeenCalledTimes(1);
    });

    it('toggle buttons have aria-label', () => {
      render(<FlawFilterControl {...gamesTabProps} />);
      expect(screen.getByTestId('filter-has-gem').getAttribute('aria-label')).toBe(
        'Filter by gem moves',
      );
      expect(screen.getByTestId('filter-has-great').getAttribute('aria-label')).toBe(
        'Filter by great moves',
      );
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

  describe('context section', () => {
    it('Context family groups render by default (no collapse)', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.getByTestId('filter-flaw-family-tempo')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-tag-miss')).toBeTruthy();
    });

    it('renders a static "Context" heading, not a toggle', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.queryByTestId('filter-flaw-context-toggle')).toBeNull();
      const heading = screen.getByTestId('filter-flaw-context-heading');
      expect(heading.textContent).toBe('Context');
    });

    it('Context section renders even when showTacticFilter is false (Games tab)', () => {
      render(<FlawFilterControl {...defaultProps} />);
      expect(screen.getByTestId('filter-flaw-context-heading')).toBeTruthy();
      expect(screen.getByTestId('filter-flaw-family-tempo')).toBeTruthy();
    });
  });
});

// ─── Phase 229 (D-03, D-12 group 2): filter-change tracking ────────────────────
// Real analytics module + window.umami stub, so the whole handler -> trackFeature
// -> window.umami.track path is exercised.

describe('filter-change tracking (Phase 229)', () => {
  const track = vi.fn();

  beforeEach(() => {
    track.mockClear();
    window.umami = { track, identify: vi.fn() };
    window.history.pushState({}, '', '/library');
  });

  afterEach(() => {
    delete window.umami;
  });

  function expectSingleEvent(args: Record<string, string>): void {
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('filter-change', { page: 'library', ...args });
  }

  it('fires nothing on render', () => {
    render(
      <FlawFilterControl {...defaultProps} showTacticFilter onHasGemToggle={vi.fn()} onHasGreatToggle={vi.fn()} />,
    );
    expect(track).not.toHaveBeenCalled();
  });

  it('reports the toggled severity, flaw tag and tactic family', () => {
    render(<FlawFilterControl {...defaultProps} showTacticFilter onTacticFamiliesChange={vi.fn()} />);
    fireEvent.click(screen.getByTestId('filter-flaw-severity-blunder'));
    expectSingleEvent({ target: 'severity', value: 'blunder' });
    track.mockClear();
    fireEvent.click(screen.getByTestId('filter-flaw-tag-miss'));
    expectSingleEvent({ target: 'flaw-tag', value: 'miss' });
    track.mockClear();
    fireEvent.click(screen.getByTestId('filter-flaw-tactic-fork'));
    expectSingleEvent({ target: 'tactic-family', value: 'fork' });
  });

  it('reports the NEW gem/great state (on when it was off, off when it was on)', () => {
    const { rerender } = render(
      <FlawFilterControl {...defaultProps} hasGem={false} hasGreat onHasGemToggle={vi.fn()} onHasGreatToggle={vi.fn()} />,
    );
    fireEvent.click(screen.getByTestId('filter-has-gem'));
    expectSingleEvent({ target: 'has-gem', value: 'on' });
    track.mockClear();
    fireEvent.click(screen.getByTestId('filter-has-great'));
    expectSingleEvent({ target: 'has-great', value: 'off' });
    track.mockClear();
    rerender(
      <FlawFilterControl {...defaultProps} hasGem hasGreat={false} onHasGemToggle={vi.fn()} onHasGreatToggle={vi.fn()} />,
    );
    fireEvent.click(screen.getByTestId('filter-has-gem'));
    expectSingleEvent({ target: 'has-gem', value: 'off' });
  });

  it('reports a tactic orientation change, and nothing when the active item is re-tapped', () => {
    render(<FlawFilterControl {...defaultProps} showTacticFilter orientation="either" onOrientationChange={vi.fn()} />);
    fireEvent.click(screen.getByTestId('filter-tactic-orientation-either'));
    expect(track).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('filter-tactic-orientation-missed'));
    expectSingleEvent({ target: 'tactic-orientation', value: 'missed' });
  });

  it('reports tactic-depth and opponent-strength presets', () => {
    render(
      <>
        <TacticDepthFilter value={DEFAULT_TACTIC_DEPTH_VALUE} onChange={vi.fn()} />
        <OpponentStrengthFilter value={ANY_RANGE} onChange={vi.fn()} />
      </>,
    );
    fireEvent.click(screen.getByTestId('filter-tactic-depth-preset-medium'));
    expectSingleEvent({ target: 'tactic-depth', value: 'medium' });
    track.mockClear();
    fireEvent.click(screen.getByTestId('filter-opponent-strength-preset-stronger'));
    expectSingleEvent({ target: 'opponent-strength', value: 'stronger' });
  });

  it('stays silent when the already-active preset is re-clicked', () => {
    render(
      <>
        <TacticDepthFilter value={DEFAULT_TACTIC_DEPTH_VALUE} onChange={vi.fn()} />
        <OpponentStrengthFilter value={ANY_RANGE} onChange={vi.fn()} />
      </>,
    );
    // DEFAULT_TACTIC_DEPTH_VALUE is the 'high' preset range.
    fireEvent.click(screen.getByTestId('filter-tactic-depth-preset-high'));
    fireEvent.click(screen.getByTestId('filter-opponent-strength-preset-any'));
    expect(track).not.toHaveBeenCalled();
  });

  describe('slider commit (Pitfall 2)', () => {
    const SLIDER_WIDTH_PX = 400;

    beforeAll(() => {
      // Radix Slider needs pointer capture and a measurable track in jsdom.
      Element.prototype.setPointerCapture = vi.fn();
      Element.prototype.releasePointerCapture = vi.fn();
      Element.prototype.hasPointerCapture = vi.fn(() => true);
    });

    function stubSliderRect(slider: HTMLElement): void {
      slider.getBoundingClientRect = () =>
        ({ left: 0, right: SLIDER_WIDTH_PX, width: SLIDER_WIDTH_PX, top: 0, bottom: 20, height: 20, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect;
    }

    // Radix only commits when the controlled value actually moved during the
    // drag, so the sliders need real state (a vi.fn() onChange never moves them).
    function StatefulStrength({ onChange }: { onChange: (v: OpponentStrengthRange) => void }) {
      const [value, setValue] = useState<OpponentStrengthRange>(ANY_RANGE);
      return (
        <OpponentStrengthFilter
          value={value}
          onChange={(next) => {
            setValue(next);
            onChange(next);
          }}
        />
      );
    }

    function StatefulDepth() {
      const [value, setValue] = useState<TacticDepthValue>(DEFAULT_TACTIC_DEPTH_VALUE);
      return <TacticDepthFilter value={value} onChange={setValue} />;
    }

    it('fires nothing per drag step and exactly one event on drag end', () => {
      const onChange = vi.fn();
      render(<StatefulStrength onChange={onChange} />);
      const slider = screen.getByTestId('filter-opponent-strength-slider');
      stubSliderRect(slider);

      fireEvent.pointerDown(slider, { clientX: 300, pointerId: 1, button: 0, buttons: 1 });
      fireEvent.pointerMove(slider, { clientX: 320, pointerId: 1, buttons: 1 });
      fireEvent.pointerMove(slider, { clientX: 340, pointerId: 1, buttons: 1 });
      // The drag moved the value (onValueChange ran) but nothing was tracked yet.
      expect(onChange).toHaveBeenCalled();
      expect(track).not.toHaveBeenCalled();

      fireEvent.pointerUp(slider, { clientX: 340, pointerId: 1 });
      expect(track).toHaveBeenCalledTimes(1);
      const [name, props] = track.mock.calls[0] as [string, Record<string, string>];
      expect(name).toBe('filter-change');
      expect(props.target).toBe('opponent-strength');
      // A bound drag never leaks the Elo gap: only a preset name or 'custom'.
      expect(['any', 'stronger', 'similar', 'weaker', 'custom']).toContain(props.value);
    });

    it('reports a tactic-depth slider commit as a preset or custom', () => {
      render(<StatefulDepth />);
      const slider = screen.getByTestId('filter-tactic-depth-slider');
      stubSliderRect(slider);
      fireEvent.pointerDown(slider, { clientX: 100, pointerId: 1, button: 0, buttons: 1 });
      expect(track).not.toHaveBeenCalled();
      fireEvent.pointerUp(slider, { clientX: 100, pointerId: 1 });
      expect(track).toHaveBeenCalledTimes(1);
      // Default is the full range (high); dragging the low thumb to ~3 matches no preset.
      expect(track.mock.calls[0]?.[1]).toMatchObject({ target: 'tactic-depth', value: 'custom' });
    });
  });
});
