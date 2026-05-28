// @vitest-environment jsdom
/**
 * Phase 96 Plan 02 — Import page readiness state machine tests.
 *
 * Verifies:
 * 1. At Tier 1 (tier1=true, tier2=false): btn-explore-openings CTA renders
 *    and the page copy does not contain the word "complete".
 * 2. At Tier 1 with pendingCount>0: "Analyzing endgames (X / Y)" text renders.
 * 3. The hot-import "done" message no longer says "Imported N games from {platform}".
 * 4. The polling invalidation set includes ['imports','readiness'].
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

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
      <ImportPage
        onImportStarted={vi.fn()}
        activeJobIds={[]}
        onJobDismissed={vi.fn()}
      />
    </MemoryRouter>,
  );
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('Import page readiness state machine', () => {
  it('renders Explore Openings CTA at Tier 1 (tier1=true, tier2=false)', () => {
    readinessState.tier1 = true;
    readinessState.tier2 = false;
    readinessState.pendingCount = 0;
    readinessState.totalCount = 100;

    renderImport();

    const cta = screen.getByTestId('btn-explore-openings');
    expect(cta).toBeTruthy();
    expect(cta.textContent).toBe('Explore Openings');
  });

  it('does not contain "complete" in the page at Tier 1 hot-import-done state', () => {
    readinessState.tier1 = true;
    readinessState.tier2 = false;

    renderImport();

    // The readiness section shows "Games imported. Openings ready." — no "complete"
    const readinessSection = screen.getByTestId('import-readiness-section');
    expect(readinessSection.textContent?.toLowerCase()).not.toContain('complete');
  });

  it('renders analyzing endgames text when tier1=true and pendingCount>0', () => {
    readinessState.tier1 = true;
    readinessState.tier2 = false;
    readinessState.pendingCount = 150;
    readinessState.totalCount = 500;

    renderImport();

    const analyzingEl = screen.getByTestId('import-analyzing-endgames');
    expect(analyzingEl).toBeTruthy();
    // analysedCount = 500 - 150 = 350
    expect(analyzingEl.textContent).toContain('350');
    expect(analyzingEl.textContent).toContain('500');
    expect(analyzingEl.textContent).toContain('Analyzing endgames');
  });

  it('does not render analyzing text when pendingCount=0 at Tier 1', () => {
    readinessState.tier1 = true;
    readinessState.tier2 = false;
    readinessState.pendingCount = 0;
    readinessState.totalCount = 500;

    renderImport();

    expect(screen.queryByTestId('import-analyzing-endgames')).toBeNull();
  });

  it('does not render Explore Openings CTA when tier1=false', () => {
    readinessState.tier1 = false;
    readinessState.tier2 = false;

    renderImport();

    expect(screen.queryByTestId('btn-explore-openings')).toBeNull();
  });
});
