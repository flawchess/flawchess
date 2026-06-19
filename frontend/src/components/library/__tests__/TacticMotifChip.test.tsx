// @vitest-environment jsdom
/**
 * TacticMotifChip vitest suite — Phase 126 TACUI-01 + Phase 126 UAT:
 *
 * 1. Renders the motif text and family-colored style
 * 2. Has the chip data-testid "chip-tactic-{motif}-{flawId}"
 * 3. aria-label references the motif and its definition
 * 4. UAT: the per-chip definition popover was removed; definitions live in the
 *    shared <TagLegend>. The chip is a highlight/cycle control on the Games card
 *    (onHover/onActivate) and a plain decorative span on FlawCard (no callbacks).
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { TacticMotifChip } from '../TacticMotifChip';

afterEach(() => {
  cleanup();
});

// ── Render helper ─────────────────────────────────────────────────────────────

function renderChip(motif = 'fork', flawId = 42) {
  return render(<TacticMotifChip motif={motif} flawId={flawId} />);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TacticMotifChip', () => {
  describe('chip rendering', () => {
    it('renders the motif text in the chip body', () => {
      renderChip('fork', 1);
      const chip = screen.getByTestId('chip-tactic-fork-1');
      expect(chip.textContent).toContain('fork');
    });

    it('renders pin motif text', () => {
      renderChip('pin', 10);
      const chip = screen.getByTestId('chip-tactic-pin-10');
      expect(chip.textContent).toContain('pin');
    });

    it('renders a motif with a dash in its name', () => {
      renderChip('back-rank-mate', 5);
      const chip = screen.getByTestId('chip-tactic-back-rank-mate-5');
      expect(chip.textContent).toContain('back-rank-mate');
    });

    it('applies family color via the style prop', () => {
      renderChip('fork', 1);
      const chip = screen.getByTestId('chip-tactic-fork-1');
      const style = chip.getAttribute('style') ?? '';
      expect(style).toContain('color');
      expect(style).toContain('background-color');
    });

    it('applies text-xs class (chip exception)', () => {
      renderChip('fork', 1);
      const chip = screen.getByTestId('chip-tactic-fork-1');
      expect(chip.className).toContain('text-xs');
    });
  });

  describe('data-testid stability', () => {
    it('has data-testid="chip-tactic-{motif}-{flawId}"', () => {
      renderChip('sacrifice', 99);
      expect(screen.getByTestId('chip-tactic-sacrifice-99')).toBeTruthy();
    });

    it('data-testid includes flawId for uniqueness', () => {
      renderChip('fork', 123);
      expect(screen.getByTestId('chip-tactic-fork-123')).toBeTruthy();
    });
  });

  describe('aria-label', () => {
    it('chip carries aria-label starting with "Tactic: {motif} — "', () => {
      renderChip('fork', 2);
      const chip = screen.getByTestId('chip-tactic-fork-2');
      const label = chip.getAttribute('aria-label') ?? '';
      expect(label).toMatch(/^Tactic: fork — /);
    });

    it('aria-label includes the definition text', () => {
      renderChip('pin', 3);
      const chip = screen.getByTestId('chip-tactic-pin-3');
      const label = chip.getAttribute('aria-label') ?? '';
      // The definition for 'pin' describes immobilization
      expect(label).toContain('piece');
    });
  });

  describe('decorative default (FlawCard — no callbacks)', () => {
    it('is not a button when no callbacks are passed', () => {
      renderChip('fork', 4);
      const chip = screen.getByTestId('chip-tactic-fork-4');
      expect(chip.getAttribute('role')).toBeNull();
    });

    it('is not focusable when no callbacks are passed', () => {
      renderChip('fork', 5);
      const chip = screen.getByTestId('chip-tactic-fork-5');
      expect(chip.getAttribute('tabindex')).toBeNull();
    });

    it('has no cursor-pointer class when no callbacks are passed', () => {
      renderChip('fork', 6);
      const chip = screen.getByTestId('chip-tactic-fork-6');
      expect(chip.className).not.toContain('cursor-pointer');
    });
  });

  describe('interactive (Games card — highlight/cycle)', () => {
    it('has role="button" when interactive', () => {
      render(<TacticMotifChip motif="fork" flawId={4} onActivate={() => {}} />);
      const chip = screen.getByTestId('chip-tactic-fork-4');
      expect(chip.getAttribute('role')).toBe('button');
    });

    it('has tabIndex=0 when interactive', () => {
      render(<TacticMotifChip motif="fork" flawId={5} onHover={() => {}} />);
      const chip = screen.getByTestId('chip-tactic-fork-5');
      expect(chip.getAttribute('tabindex')).toBe('0');
    });

    it('has cursor-pointer class when interactive', () => {
      render(<TacticMotifChip motif="fork" flawId={6} onActivate={() => {}} />);
      const chip = screen.getByTestId('chip-tactic-fork-6');
      expect(chip.className).toContain('cursor-pointer');
    });

    it('fires onHover(true) on mouseenter and onHover(false) on mouseleave', () => {
      const onHover = vi.fn();
      render(<TacticMotifChip motif="fork" flawId={7} onHover={onHover} />);
      const chip = screen.getByTestId('chip-tactic-fork-7');
      fireEvent.mouseEnter(chip);
      expect(onHover).toHaveBeenLastCalledWith(true);
      fireEvent.mouseLeave(chip);
      expect(onHover).toHaveBeenLastCalledWith(false);
    });

    it('fires onActivate on click', () => {
      const onActivate = vi.fn();
      render(<TacticMotifChip motif="fork" flawId={8} onActivate={onActivate} />);
      const chip = screen.getByTestId('chip-tactic-fork-8');
      fireEvent.click(chip);
      expect(onActivate).toHaveBeenCalledTimes(1);
    });

    it('fires onActivate on Enter and Space', () => {
      const onActivate = vi.fn();
      render(<TacticMotifChip motif="fork" flawId={9} onActivate={onActivate} />);
      const chip = screen.getByTestId('chip-tactic-fork-9');
      fireEvent.keyDown(chip, { key: 'Enter' });
      fireEvent.keyDown(chip, { key: ' ' });
      expect(onActivate).toHaveBeenCalledTimes(2);
    });
  });

  describe('unknown motif handling', () => {
    it('renders null for a completely unknown motif string', () => {
      const { container } = render(<TacticMotifChip motif="not-a-real-motif" flawId={1} />);
      // Unknown motif has no family mapping — renders nothing
      expect(container.firstChild).toBeNull();
    });
  });
});
