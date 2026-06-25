// @vitest-environment jsdom
/**
 * TacticLineExplorer vitest suite (Phase 135, Plan 03).
 *
 * Tests:
 * 1. Renders Dialog on desktop (matchMedia wide)
 * 2. Renders Drawer on mobile (matchMedia narrow)
 * 3. Toggle hidden when only one line (single-line flaw)
 * 4. Toggle visible when both lines present
 * 5. Clicking a tag switches orientation (active tag marked aria-pressed)
 * 6. Empty state copy when active line is null
 * 7. isError copy on query error
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';

// ── Mock useTacticLines ───────────────────────────────────────────────────────

vi.mock('@/hooks/useLibrary', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/useLibrary')>('@/hooks/useLibrary');
  return {
    ...actual,
    useTacticLines: vi.fn(),
  };
});

// ── Stub react-chessboard to avoid SVG rendering ─────────────────────────────

vi.mock('react-chessboard', () => ({
  Chessboard: vi.fn(() => null),
}));

// ── Stub Tooltip ──────────────────────────────────────────────────────────────

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => children,
  TooltipProvider: ({ children }: { children: ReactNode }) => children,
}));

// ── Stub useFlawFilterStore (TacticMotifChip + explorer filter gating use it) ─
// Mutable holder so individual tests can set the active filter; reset in afterEach.

const DEFAULT_TEST_FILTER = {
  severity: ['blunder', 'mistake'],
  tags: [],
  tacticFamilies: [],
  tacticOrientation: 'either',
  tacticDepthMin: 0,
  tacticDepthMax: 11,
};

const { mockFilter } = vi.hoisted(() => ({
  mockFilter: {
    value: {
      severity: ['blunder', 'mistake'],
      tags: [],
      tacticFamilies: [],
      tacticOrientation: 'either',
      tacticDepthMin: 0,
      tacticDepthMax: 11,
    } as Record<string, unknown>,
  },
}));

vi.mock('@/hooks/useFlawFilterStore', () => ({
  useFlawFilterStore: () => [mockFilter.value, vi.fn()] as const,
}));

// ── jsdom stubs ───────────────────────────────────────────────────────────────

// ResizeObserver is used by ChessBoard to track container width; jsdom doesn't have it.
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal('ResizeObserver', MockResizeObserver);

// jsdom does not implement Element.prototype.scrollIntoView; the move list's
// auto-scroll effect (HorizontalMoveList, now used on desktop too) calls it.
Element.prototype.scrollIntoView = vi.fn();

import { TacticLineExplorer } from '../TacticLineExplorer';
import { useTacticLines } from '@/hooks/useLibrary';
import type { TacticLinesResponse } from '@/types/library';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';

const BOTH_LINES_RESPONSE: TacticLinesResponse = {
  missed_moves: ['Nf6', 'Nc3', 'e5'],
  missed_depth: 1,
  missed_tactic_ply_index: 1,
  missed_motif: 'fork',
  missed_eval_cp: 150,
  missed_eval_mate: null,
  allowed_moves: ['e5', 'Qh5', 'd6'],
  allowed_depth: 0,
  // allowed_moves[0] is the prepended flaw move ('e5'); the refutation punchline
  // ('Qh5') is at index 1 → ply_index = allowed_depth + 1 (Phase 135 UAT).
  allowed_tactic_ply_index: 1,
  allowed_motif: 'fork',
  allowed_eval_cp: -80,
  allowed_eval_mate: null,
  position_fen: STARTING_FEN,
  flaw_move_san: 'e5',
  best_move_uci: 'g8f6',
  flaw_ply: 10,
  flaw_severity: 'blunder',
};

const MISSED_ONLY_RESPONSE: TacticLinesResponse = {
  missed_moves: ['Nf6', 'Nc3'],
  missed_depth: 0,
  missed_tactic_ply_index: 0,
  missed_motif: 'fork',
  missed_eval_cp: 220,
  missed_eval_mate: null,
  allowed_moves: null,
  allowed_depth: null,
  allowed_tactic_ply_index: null,
  allowed_motif: null,
  allowed_eval_cp: null,
  allowed_eval_mate: null,
  position_fen: STARTING_FEN,
  flaw_move_san: 'e5',
  best_move_uci: 'g8f6',
  flaw_ply: 10,
  flaw_severity: 'blunder',
};

// Allowed-only flaw. The backend ALWAYS returns missed_moves (the decision-position
// engine PV exists for every flaw), but with no tagged missed tactic missed_motif is
// null. The explorer must show the ALLOWED refutation line (flaw_ply+1), not the
// always-present missed PV (flaw_ply) (Phase 135 UAT).
const ALLOWED_ONLY_RESPONSE: TacticLinesResponse = {
  missed_moves: ['Nf6', 'Nc3'], // present (engine PV) but NOT a tagged missed tactic
  missed_depth: 0,
  missed_tactic_ply_index: 0,
  missed_motif: null,
  missed_eval_cp: 150,
  missed_eval_mate: null,
  allowed_moves: ['e5', 'Qh5', 'd6'],
  allowed_depth: 0,
  allowed_tactic_ply_index: 1,
  allowed_motif: 'fork',
  allowed_eval_cp: -80,
  allowed_eval_mate: null,
  position_fen: STARTING_FEN,
  flaw_move_san: 'e5',
  best_move_uci: 'g8f6',
  flaw_ply: 10,
  flaw_severity: 'blunder',
};

const NULL_LINE_RESPONSE: TacticLinesResponse = {
  missed_moves: null,
  missed_depth: null,
  missed_tactic_ply_index: null,
  missed_motif: null,
  missed_eval_cp: null,
  missed_eval_mate: null,
  allowed_moves: null,
  allowed_depth: null,
  allowed_tactic_ply_index: null,
  allowed_motif: null,
  allowed_eval_cp: null,
  allowed_eval_mate: null,
  position_fen: STARTING_FEN,
  flaw_move_san: null,
  best_move_uci: null,
  flaw_ply: 10,
  flaw_severity: 'blunder',
};

/** Helper to mock matchMedia for a given width. */
function mockMatchMedia(isMobile: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: isMobile, // (max-width: 767px)
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

// ─── Tests ────────────────────────────────────────────────────────────────────

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  mockFilter.value = { ...DEFAULT_TEST_FILTER };
});

describe('TacticLineExplorer', () => {

  describe('Surface selection (D-05)', () => {
    it('renders Dialog on desktop (wide matchMedia)', async () => {
      mockMatchMedia(false); // desktop: (max-width: 767px) = false
      vi.mocked(useTacticLines).mockReturnValue({
        data: BOTH_LINES_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      await waitFor(() => {
        expect(screen.queryByTestId('tactic-explorer-dialog')).not.toBeNull();
        expect(screen.queryByTestId('tactic-explorer-drawer')).toBeNull();
      });
    });

    it('renders Drawer on mobile (narrow matchMedia)', async () => {
      mockMatchMedia(true); // mobile: (max-width: 767px) = true
      vi.mocked(useTacticLines).mockReturnValue({
        data: BOTH_LINES_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      await waitFor(() => {
        expect(screen.queryByTestId('tactic-explorer-drawer')).not.toBeNull();
        expect(screen.queryByTestId('tactic-explorer-dialog')).toBeNull();
      });
    });
  });

  describe('Missed/Allowed toggle', () => {
    beforeEach(() => {
      mockMatchMedia(false); // desktop for simplicity
    });

    it('hides the toggle when only one line exists', async () => {
      vi.mocked(useTacticLines).mockReturnValue({
        data: MISSED_ONLY_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      await waitFor(() => {
        expect(screen.queryByTestId('tactic-toggle-missed')).toBeNull();
        expect(screen.queryByTestId('tactic-toggle-allowed')).toBeNull();
      });
    });

    it('still shows the single tag when only one line exists', async () => {
      vi.mocked(useTacticLines).mockReturnValue({
        data: MISSED_ONLY_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      // The decorative missed motif chip is rendered so the user sees the tactic
      // being explored even without a switch.
      await waitFor(() => {
        expect(screen.getByTestId('chip-tactic-missed-fork-42')).toBeDefined();
      });
    });

    it('allowed-only flaw shows the refutation line, not the always-present missed PV', async () => {
      // Regression (Phase 135 UAT): missed_moves is non-null (engine PV always exists)
      // but missed_motif is null, so only the allowed tactic is tagged. The explorer
      // must render the allowed refutation (e5, Qh5, d6), NOT the missed PV (Nf6, Nc3).
      vi.mocked(useTacticLines).mockReturnValue({
        data: ALLOWED_ONLY_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      await waitFor(() => {
        expect(screen.getByTestId('chip-tactic-allowed-fork-42')).toBeDefined();
      });
      // Allowed line is shown (refutation move present), missed PV is not.
      expect(screen.getByText('Qh5')).toBeDefined();
      expect(screen.queryByText('Nc3')).toBeNull();
      // No missed tag, no toggle (only the allowed tactic is tagged).
      expect(screen.queryByTestId('chip-tactic-missed-fork-42')).toBeNull();
      expect(screen.queryByTestId('tactic-toggle-missed')).toBeNull();
    });

    it('shows the toggle when both lines exist', async () => {
      vi.mocked(useTacticLines).mockReturnValue({
        data: BOTH_LINES_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      await waitFor(() => {
        expect(screen.getByTestId('tactic-toggle-missed')).toBeDefined();
        expect(screen.getByTestId('tactic-toggle-allowed')).toBeDefined();
      });
    });

    it('clicking a tag switches orientation (active tag marked aria-pressed)', async () => {
      vi.mocked(useTacticLines).mockReturnValue({
        data: BOTH_LINES_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      // Default orientation is 'missed' → missed tag selected, allowed not.
      await waitFor(() => {
        expect(screen.getByTestId('tactic-toggle-missed').getAttribute('aria-pressed')).toBe(
          'true',
        );
      });
      expect(screen.getByTestId('tactic-toggle-allowed').getAttribute('aria-pressed')).toBe(
        'false',
      );

      // Click the red Allowed tag — it becomes the active (white-border) line.
      fireEvent.click(screen.getByTestId('tactic-toggle-allowed'));

      await waitFor(() => {
        expect(screen.getByTestId('tactic-toggle-allowed').getAttribute('aria-pressed')).toBe(
          'true',
        );
        expect(screen.getByTestId('tactic-toggle-missed').getAttribute('aria-pressed')).toBe(
          'false',
        );
      });
    });
  });

  describe('Flaw-move severity glyph', () => {
    beforeEach(() => {
      mockMatchMedia(false); // desktop
    });

    it('renders the severity glyph on the allowed flaw-move row, not on the missed line', async () => {
      vi.mocked(useTacticLines).mockReturnValue({
        data: BOTH_LINES_RESPONSE, // flaw_severity: 'blunder'
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(<TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />);

      // Missed line is the default; it has no prepended flaw move → no glyph.
      await waitFor(() => {
        expect(screen.getByTestId('tactic-toggle-missed').getAttribute('aria-pressed')).toBe(
          'true',
        );
      });
      expect(screen.queryByTestId('tactic-san-flaw-severity-blunder')).toBeNull();

      // Switch to the allowed line → the prepended flaw move shows the blunder glyph.
      fireEvent.click(screen.getByTestId('tactic-toggle-allowed'));
      await waitFor(() => {
        expect(screen.getByTestId('tactic-san-flaw-severity-blunder')).toBeDefined();
      });
    });
  });

  describe('Eval readout', () => {
    beforeEach(() => {
      mockMatchMedia(false); // desktop
    });

    it('shows the decision eval at ply 0 and updates to the post-flaw eval when stepping the allowed line', async () => {
      vi.mocked(useTacticLines).mockReturnValue({
        data: BOTH_LINES_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      // White-POV, never flipped. Ply 0 (decision position) → missed_eval_cp=150 → "+1.5".
      await waitFor(() => {
        expect(screen.getByTestId('tactic-eval').textContent).toContain('+1.5');
      });

      // Switching to the allowed line does NOT change the eval at ply 0: the board is
      // still the shared pre-flaw decision position → decision eval +1.5.
      fireEvent.click(screen.getByTestId('tactic-toggle-allowed'));
      await waitFor(() => {
        expect(screen.getByTestId('tactic-eval').textContent).toContain('+1.5');
      });

      // Step forward past the flaw move (ply 1, post-flaw board) → allowed_eval_cp=-80 → "-0.8".
      fireEvent.click(screen.getByTestId('board-btn-forward'));
      await waitFor(() => {
        expect(screen.getByTestId('tactic-eval').textContent).toContain('-0.8');
      });

      // Stepping back to the decision position restores the decision eval.
      fireEvent.click(screen.getByTestId('board-btn-back'));
      await waitFor(() => {
        expect(screen.getByTestId('tactic-eval').textContent).toContain('+1.5');
      });
    });

    it('does not flip eval sign for a Black-to-move flaw (white-POV)', async () => {
      // flaw_ply odd (Black moved); eval must stay white-POV (positive = white ahead).
      vi.mocked(useTacticLines).mockReturnValue({
        data: { ...BOTH_LINES_RESPONSE, flaw_ply: 11 },
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={11} />,
      );

      // missed_eval_cp=150 → "+1.5" (NOT negated to -1.5).
      await waitFor(() => {
        expect(screen.getByTestId('tactic-eval').textContent).toContain('+1.5');
      });
    });

    it('omits the eval readout when no eval is available', async () => {
      vi.mocked(useTacticLines).mockReturnValue({
        data: { ...MISSED_ONLY_RESPONSE, missed_eval_cp: null, missed_eval_mate: null },
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      await waitFor(() => {
        expect(screen.getByTestId('chip-tactic-missed-fork-42')).toBeDefined();
      });
      expect(screen.queryByTestId('tactic-eval')).toBeNull();
    });
  });

  describe('Flaw filter applied to the modal', () => {
    beforeEach(() => {
      mockMatchMedia(false); // desktop
    });

    it("orientation='missed' hides the allowed tag and line", async () => {
      mockFilter.value = { ...DEFAULT_TEST_FILTER, tacticOrientation: 'missed' };
      vi.mocked(useTacticLines).mockReturnValue({
        data: BOTH_LINES_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      // Only the missed tag shows; no switch, no allowed tag.
      await waitFor(() => {
        expect(screen.getByTestId('chip-tactic-missed-fork-42')).toBeDefined();
      });
      expect(screen.queryByTestId('tactic-toggle-missed')).toBeNull();
      expect(screen.queryByTestId('tactic-toggle-allowed')).toBeNull();
      expect(screen.queryByTestId('chip-tactic-allowed-fork-42')).toBeNull();
      // Active line eval is the missed line (white-POV +1.5).
      expect(screen.getByTestId('tactic-eval').textContent).toContain('+1.5');
    });

    it("orientation='allowed' hides the missed tag and shows the allowed line", async () => {
      mockFilter.value = { ...DEFAULT_TEST_FILTER, tacticOrientation: 'allowed' };
      vi.mocked(useTacticLines).mockReturnValue({
        data: BOTH_LINES_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      await waitFor(() => {
        expect(screen.getByTestId('chip-tactic-allowed-fork-42')).toBeDefined();
      });
      expect(screen.queryByTestId('chip-tactic-missed-fork-42')).toBeNull();
      // Ply 0 is the shared decision position, so even the allowed line reads the
      // decision eval (white-POV +1.5) until you step past the flaw move.
      expect(screen.getByTestId('tactic-eval').textContent).toContain('+1.5');
    });

    it('family filter excluding both motifs shows the empty state', async () => {
      // Both motifs are 'fork'; narrowing to 'pin' filters both lines out.
      mockFilter.value = { ...DEFAULT_TEST_FILTER, tacticFamilies: ['pin'] };
      vi.mocked(useTacticLines).mockReturnValue({
        data: BOTH_LINES_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      await waitFor(() => {
        expect(
          screen.getByText('Tactic line not available for this flaw.'),
        ).toBeDefined();
      });
    });
  });

  describe('Empty and error states', () => {
    beforeEach(() => {
      mockMatchMedia(false); // desktop
    });

    it('shows empty state copy when active line is null', async () => {
      vi.mocked(useTacticLines).mockReturnValue({
        data: NULL_LINE_RESPONSE,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      await waitFor(() => {
        expect(
          screen.getByText('Tactic line not available for this flaw.'),
        ).toBeDefined();
      });
    });

    it('shows error copy on query failure (CLAUDE.md isError pattern)', async () => {
      vi.mocked(useTacticLines).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
      } as ReturnType<typeof useTacticLines>);

      render(
        <TacticLineExplorer open={true} onOpenChange={() => {}} gameId={42} ply={10} />,
      );

      await waitFor(() => {
        expect(
          screen.getByText('Failed to load tactic line. Please try again.'),
        ).toBeDefined();
      });
    });
  });
});
