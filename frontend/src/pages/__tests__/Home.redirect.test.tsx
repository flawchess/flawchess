// @vitest-environment jsdom
/**
 * Regression coverage for the Home redirect rule (Phase 224 S-1, ROADMAP SC 1).
 *
 * Every authenticated account, guest or registered, leaves the home CTA for
 * /library/games (has games) or /library/import (zero games) — there is no
 * /welcome destination anymore.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import { HomePage } from '@/pages/Home';

// ── Auth mock — fixed token so HomePage takes the authenticated branch ────────

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ token: 'test-token' }),
}));

// ── Location spy ──────────────────────────────────────────────────────────────

function LocationDisplay() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

// ── Render helper ─────────────────────────────────────────────────────────────

interface ProfileFixture {
  is_guest: boolean;
  chess_com_game_count: number;
  lichess_game_count: number;
}

function renderHome(profile: ProfileFixture) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['userProfile'], profile);
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="*" element={<LocationDisplay />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  localStorage.clear();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('HomePage redirect (Phase 224 S-1)', () => {
  it('zero-game guest resolves to /library/import', () => {
    renderHome({ is_guest: true, chess_com_game_count: 0, lichess_game_count: 0 });
    expect(screen.getByTestId('location').textContent).toBe('/library/import');
  });

  it('zero-game registered account resolves to /library/import', () => {
    renderHome({ is_guest: false, chess_com_game_count: 0, lichess_game_count: 0 });
    expect(screen.getByTestId('location').textContent).toBe('/library/import');
  });

  it('guest with games resolves to /library/games', () => {
    renderHome({ is_guest: true, chess_com_game_count: 10, lichess_game_count: 0 });
    expect(screen.getByTestId('location').textContent).toBe('/library/games');
  });

  it('never produces a /welcome destination for any profile fixture', () => {
    const fixtures: ProfileFixture[] = [
      { is_guest: true, chess_com_game_count: 0, lichess_game_count: 0 },
      { is_guest: false, chess_com_game_count: 0, lichess_game_count: 0 },
      { is_guest: true, chess_com_game_count: 10, lichess_game_count: 0 },
    ];
    for (const profile of fixtures) {
      const { unmount } = renderHome(profile);
      expect(screen.getByTestId('location').textContent).not.toBe('/welcome');
      unmount();
    }
  });
});
