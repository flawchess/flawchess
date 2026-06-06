// @vitest-environment jsdom
/**
 * TagChip vitest suite — tests Plan 108-08 D-05 requirements:
 *
 * 1. Clicking a chip navigates to /library/flaws?tag={TAG} (no game_id)
 * 2. aria-label is "Filter flaws by tag: {tag}"
 * 3. data-testid="chip-{tag}-{gameId}" is unchanged
 * 4. The chip is a semantic <button> element
 * 5. Family colors are applied (via style prop)
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TagChip } from '../TagChip';

// ── Controlled useNavigate mock ───────────────────────────────────────────────

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// ── Render helper ─────────────────────────────────────────────────────────────

function renderTagChip(tag: Parameters<typeof TagChip>[0]['tag'], gameId = 42) {
  return render(
    <MemoryRouter>
      <TagChip tag={tag} gameId={gameId} />
    </MemoryRouter>,
  );
}

// ── Setup / teardown ──────────────────────────────────────────────────────────

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TagChip', () => {
  describe('D-05: navigation deep-link', () => {
    it('navigates to /library/flaws?tag={tag} on click (no game_id)', () => {
      renderTagChip('result-changing', 99);
      const chip = screen.getByTestId('chip-result-changing-99');
      fireEvent.click(chip);
      expect(mockNavigate).toHaveBeenCalledWith('/library/flaws?tag=result-changing');
      // Verify game_id is NOT in the navigation URL (D-05)
      const callArg = mockNavigate.mock.calls[0]?.[0] as string;
      expect(callArg).not.toContain('game_id');
      expect(callArg).not.toContain('99');
    });

    it('navigates to /library/flaws?tag=low-clock for tempo chip', () => {
      renderTagChip('low-clock', 7);
      const chip = screen.getByTestId('chip-low-clock-7');
      fireEvent.click(chip);
      expect(mockNavigate).toHaveBeenCalledWith('/library/flaws?tag=low-clock');
    });

    it('navigates to /library/flaws?tag=miss for opportunity chip', () => {
      renderTagChip('miss', 3);
      const chip = screen.getByTestId('chip-miss-3');
      fireEvent.click(chip);
      expect(mockNavigate).toHaveBeenCalledWith('/library/flaws?tag=miss');
    });

    it('navigates to /library/flaws?tag=while-ahead for impact chip', () => {
      renderTagChip('while-ahead', 12);
      const chip = screen.getByTestId('chip-while-ahead-12');
      fireEvent.click(chip);
      expect(mockNavigate).toHaveBeenCalledWith('/library/flaws?tag=while-ahead');
    });
  });

  describe('semantic HTML + ARIA', () => {
    it('renders as a <button> element (not <span>)', () => {
      renderTagChip('miss', 1);
      const chip = screen.getByTestId('chip-miss-1');
      expect(chip.tagName.toLowerCase()).toBe('button');
    });

    it('has type="button" to avoid accidental form submission', () => {
      renderTagChip('miss', 1);
      const chip = screen.getByTestId('chip-miss-1');
      expect(chip.getAttribute('type')).toBe('button');
    });

    it('aria-label is "Filter flaws by tag: {tag}" (D-05 chip contract)', () => {
      renderTagChip('result-changing', 5);
      const chip = screen.getByTestId('chip-result-changing-5');
      expect(chip.getAttribute('aria-label')).toBe('Filter flaws by tag: result-changing');
    });

    it('aria-label does NOT contain the popover-style "Tag: {tag} —" pattern', () => {
      renderTagChip('miss', 2);
      const chip = screen.getByTestId('chip-miss-2');
      const label = chip.getAttribute('aria-label') ?? '';
      expect(label).not.toContain('Tag: miss —');
    });
  });

  describe('data-testid stability', () => {
    it('data-testid is "chip-{tag}-{gameId}" (unchanged format)', () => {
      renderTagChip('low-clock', 42);
      // Should find by the exact data-testid format from Phase 107
      expect(screen.getByTestId('chip-low-clock-42')).toBeTruthy();
    });

    it('data-testid includes gameId for uniqueness within a game card', () => {
      renderTagChip('considered', 123);
      expect(screen.getByTestId('chip-considered-123')).toBeTruthy();
    });
  });

  describe('visual styling', () => {
    it('renders the tag label text', () => {
      renderTagChip('result-changing', 1);
      // The chip should display the tag name as text
      expect(screen.getByText('result-changing')).toBeTruthy();
    });

    it('has cursor-pointer class', () => {
      renderTagChip('miss', 1);
      const chip = screen.getByTestId('chip-miss-1');
      expect(chip.className).toContain('cursor-pointer');
    });

    it('applies family color styles via the style prop', () => {
      renderTagChip('low-clock', 1);
      const chip = screen.getByTestId('chip-low-clock-1');
      // Tempo family: FAM_TEMPO color is applied
      const style = chip.getAttribute('style') ?? '';
      // The style should contain color (FAM_TEMPO value)
      expect(style).toContain('color');
      expect(style).toContain('background-color');
    });
  });
});
