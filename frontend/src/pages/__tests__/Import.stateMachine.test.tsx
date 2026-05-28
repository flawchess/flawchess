// @vitest-environment jsdom
/**
 * Phase 96 Plan 02 — Import page readiness state machine tests.
 *
 * Verifies (post-UAT):
 * 1. Both Explore CTAs always render; each is enabled only once its tier is ready
 *    (Openings at Tier 1, Endgames at Tier 2).
 * 2. The "Analyzing endgames (X / Y)" indicator is gone (Stockfish banner covers it).
 * 3. The hot-import "done" message no longer says "Imported N games from {platform}".
 * 4. The polling invalidation set includes ['imports','readiness'].
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TooltipProvider } from '@/components/ui/tooltip';

// ── Static contract test: readiness queryKey in polling invalidation ──────────

// Use resolve with __dirname to get an absolute path (import.meta.url is not
// a file:// URL in this vitest environment).
const IMPORT_TSX_PATH = resolve(__dirname, '../Import.tsx');

describe('Import.tsx polling invalidation contract', () => {
  it("invalidates ['imports','readiness'] during active import polling", () => {
    const src = readFileSync(IMPORT_TSX_PATH, 'utf8');
    // Must contain the readiness invalidation call alongside eval-coverage.
    expect(src).toContain("queryKey: ['imports', 'readiness']");
  });

  it('hot-import done message does not contain "Imported" + "games from"', () => {
    const src = readFileSync(IMPORT_TSX_PATH, 'utf8');
    // The old over-claiming copy must be gone.
    expect(src).not.toMatch(/Imported \$\{data\.games_imported\} games from/);
  });
});

// ── Component rendering tests ─────────────────────────────────────────────────

const readinessState: {
  tier1: boolean;
  tier2: boolean;
  pendingCount: number;
  totalCount: number;
  isLoading: boolean;
} = {
  tier1: false,
  tier2: false,
  pendingCount: 0,
  totalCount: 0,
  isLoading: false,
};

vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: () => ({ ...readinessState }),
}));

vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => ({
    data: {
      chess_com_username: 'testuser',
      lichess_username: null,
      chess_com_game_count: 100,
      lichess_game_count: 0,
      chess_com_last_sync_at: '2026-01-01T00:00:00Z',
      lichess_last_sync_at: null,
      is_guest: false,
      is_superuser: false,
      email: 'test@example.com',
    },
    isLoading: false,
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    token: 'test-token',
    logoutForPromotion: vi.fn(),
  }),
}));

vi.mock('@/hooks/useImport', () => ({
  useImportTrigger: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useImportPolling: () => ({ data: null }),
}));

vi.mock('@/hooks/useEvalCoverage', () => ({
  useEvalCoverage: () => ({
    pendingCount: 0,
    totalCount: 0,
    pct: 100,
    isPending: false,
    isLoading: false,
  }),
}));

// Mock react-router-dom's useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock QueryClient to avoid provider requirement
vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query');
  return {
    ...actual,
    useQueryClient: () => ({
      invalidateQueries: vi.fn(),
    }),
  };
});

vi.mock('@/api/client', () => ({
  apiClient: { delete: vi.fn() },
}));

afterEach(() => {
  cleanup();
  readinessState.tier1 = false;
  readinessState.tier2 = false;
  readinessState.pendingCount = 0;
  readinessState.totalCount = 0;
  readinessState.isLoading = false;
  mockNavigate.mockReset();
});

import { ImportPage } from '../Import';

// ── Render helper ──────────────────────────────────────────────────────────────
function renderImport() {
  return render(
    <MemoryRouter>
      <TooltipProvider>
        <ImportPage
          onImportStarted={vi.fn()}
          activeJobIds={[]}
          onJobDismissed={vi.fn()}
        />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('Import page readiness state machine', () => {
  it('always renders both Explore CTAs regardless of tier', () => {
    readinessState.tier1 = false;
    readinessState.tier2 = false;

    renderImport();

    const openings = screen.getByTestId('btn-explore-openings');
    const endgames = screen.getByTestId('btn-explore-endgames');
    expect(openings.textContent).toBe('Openings');
    expect(endgames.textContent).toBe('Endgames');
  });

  it('disables both CTAs before either tier is ready', () => {
    readinessState.tier1 = false;
    readinessState.tier2 = false;

    renderImport();

    expect(screen.getByTestId('btn-explore-openings')).toHaveProperty('disabled', true);
    expect(screen.getByTestId('btn-explore-endgames')).toHaveProperty('disabled', true);
  });

  it('enables Explore Openings at Tier 1 while Endgames stays disabled', () => {
    readinessState.tier1 = true;
    readinessState.tier2 = false;

    renderImport();

    expect(screen.getByTestId('btn-explore-openings')).toHaveProperty('disabled', false);
    expect(screen.getByTestId('btn-explore-endgames')).toHaveProperty('disabled', true);
  });

  it('enables both CTAs at Tier 2', () => {
    readinessState.tier1 = true;
    readinessState.tier2 = true;

    renderImport();

    expect(screen.getByTestId('btn-explore-openings')).toHaveProperty('disabled', false);
    expect(screen.getByTestId('btn-explore-endgames')).toHaveProperty('disabled', false);
  });

  it('no longer renders the analyzing-endgames indicator', () => {
    readinessState.tier1 = true;
    readinessState.tier2 = false;
    readinessState.pendingCount = 150;
    readinessState.totalCount = 500;

    renderImport();

    expect(screen.queryByTestId('import-analyzing-endgames')).toBeNull();
  });
});
