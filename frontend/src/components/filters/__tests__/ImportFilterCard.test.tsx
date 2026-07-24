// @vitest-environment jsdom
/**
 * Phase 186 Plan 03 — ImportFilterCard component test.
 *
 * Mocks useImportSettings/useUpdateImportSettings (preserving the real
 * tcSettingsKey helper + types via vi.importActual) so the component can be
 * rendered without a QueryClientProvider or a real apiClient.
 *
 * Covers:
 * - TC grid + cap ToggleGroup render with the expected data-testids and aria-pressed states.
 * - Toggling a TC calls the update mutation with the new TC set (D-09 auto-save).
 * - Last-one-standing guard: deselecting the final active TC is a no-op (no mutate call).
 * - Selecting a different cap calls the mutation with the new game_cap.
 * - Inline helper copy + InfoPopover trigger presence.
 * - PATCH failure: inline text-destructive save-error line appears (verification-gap fix),
 *   and clears once a subsequent mutation attempt starts.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import type { Mock } from 'vitest';

vi.mock('@/hooks/useImportSettings', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/useImportSettings')>(
    '@/hooks/useImportSettings',
  );
  return {
    ...actual,
    useImportSettings: vi.fn(),
    useUpdateImportSettings: vi.fn(),
  };
});

import { useImportSettings, useUpdateImportSettings, type ImportSettings } from '@/hooks/useImportSettings';
import { ImportFilterCard } from '../ImportFilterCard';

const BASE_SETTINGS: ImportSettings = {
  tc_bullet: false,
  tc_blitz: true,
  tc_rapid: true,
  tc_classical: true,
  game_cap: 1000,
  imported_counts: {},
};

function mockSettings(overrides: Partial<ImportSettings> = {}) {
  (useImportSettings as Mock).mockReturnValue({
    data: { ...BASE_SETTINGS, ...overrides },
    isLoading: false,
    isError: false,
  });
}

function mockUpdateMutation(overrides: { isError?: boolean; error?: Error | null } = {}) {
  const mutate = vi.fn();
  (useUpdateImportSettings as Mock).mockReturnValue({
    mutate,
    isError: overrides.isError ?? false,
    error: overrides.error ?? null,
  });
  return mutate;
}

describe('ImportFilterCard', () => {
  afterEach(() => {
    cleanup();
    vi.resetAllMocks();
  });

  it('renders the TC grid and cap ToggleGroup with expected data-testids and aria-pressed states', () => {
    mockSettings();
    mockUpdateMutation();

    render(<ImportFilterCard />);

    expect(screen.getByTestId('import-filter-card')).toBeTruthy();
    expect(screen.getByText('Import filters')).toBeTruthy();

    // TC grid: bullet inactive, blitz/rapid/classical active per BASE_SETTINGS.
    expect(screen.getByTestId('import-filter-time-control-bullet').getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByTestId('import-filter-time-control-blitz').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('import-filter-time-control-rapid').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('import-filter-time-control-classical').getAttribute('aria-pressed')).toBe('true');

    // Cap row: 1000/3000/5000 present, 1000 active per BASE_SETTINGS.
    expect(screen.getByTestId('import-filter-cap-1000').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('import-filter-cap-3000').getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByTestId('import-filter-cap-5000').getAttribute('aria-pressed')).toBe('false');
  });

  it('toggling an inactive TC calls the update mutation with the new TC set (auto-save)', () => {
    mockSettings();
    const mutate = mockUpdateMutation();

    render(<ImportFilterCard />);
    fireEvent.click(screen.getByTestId('import-filter-time-control-bullet'));

    expect(mutate).toHaveBeenCalledTimes(1);
    expect(mutate).toHaveBeenCalledWith({
      tc_bullet: true,
      tc_blitz: true,
      tc_rapid: true,
      tc_classical: true,
      game_cap: 1000,
    });
  });

  it('toggling an active TC (not the last one) calls the mutation with it deselected', () => {
    mockSettings();
    const mutate = mockUpdateMutation();

    render(<ImportFilterCard />);
    fireEvent.click(screen.getByTestId('import-filter-time-control-blitz'));

    expect(mutate).toHaveBeenCalledTimes(1);
    expect(mutate).toHaveBeenCalledWith({
      tc_bullet: false,
      tc_blitz: false,
      tc_rapid: true,
      tc_classical: true,
      game_cap: 1000,
    });
  });

  it('last-one-standing guard: deselecting the final active TC is a no-op (no mutation)', () => {
    // Only classical is active — attempting to deselect it must not empty the TC set.
    mockSettings({ tc_bullet: false, tc_blitz: false, tc_rapid: false, tc_classical: true });
    const mutate = mockUpdateMutation();

    render(<ImportFilterCard />);
    fireEvent.click(screen.getByTestId('import-filter-time-control-classical'));

    expect(mutate).not.toHaveBeenCalled();
    // Stays visually active — the guard is a UI no-op, not a mutation that re-applies it.
    expect(screen.getByTestId('import-filter-time-control-classical').getAttribute('aria-pressed')).toBe('true');
  });

  it('selecting a different cap calls the mutation with the new game_cap', () => {
    mockSettings();
    const mutate = mockUpdateMutation();

    render(<ImportFilterCard />);
    fireEvent.click(screen.getByTestId('import-filter-cap-5000'));

    expect(mutate).toHaveBeenCalledTimes(1);
    expect(mutate).toHaveBeenCalledWith({
      tc_bullet: false,
      tc_blitz: true,
      tc_rapid: true,
      tc_classical: true,
      game_cap: 5000,
    });
  });

  it('renders the Backlog cap label and the InfoPopover trigger beside it', () => {
    mockSettings();
    mockUpdateMutation();

    render(<ImportFilterCard />);

    expect(screen.getByText('Backlog cap')).toBeTruthy();
    expect(screen.getByTestId('import-filter-info-popover')).toBeTruthy();
  });

  it('renders the CLAUDE.md-mandated isError copy on settings-fetch failure', () => {
    (useImportSettings as Mock).mockReturnValue({ data: undefined, isLoading: false, isError: true });
    mockUpdateMutation();

    render(<ImportFilterCard />);

    expect(screen.getByTestId('import-filter-error').textContent).toBe(
      'Failed to load import settings. Something went wrong. Please try again in a moment.',
    );
  });

  it('renders nothing while loading (no separate spinner/skeleton, UI-SPEC loading state)', () => {
    (useImportSettings as Mock).mockReturnValue({ data: undefined, isLoading: true, isError: false });
    mockUpdateMutation();

    const { container } = render(<ImportFilterCard />);

    expect(container.firstChild).toBeNull();
  });

  it('shows an inline text-destructive save error when the PATCH mutation fails (verification gap)', () => {
    mockSettings();
    mockUpdateMutation({ isError: true, error: new Error('Network error') });

    render(<ImportFilterCard />);

    const errorEl = screen.getByTestId('import-filter-save-error');
    expect(errorEl.textContent).toBe(
      "Couldn't save your import settings. Your change was undone — please try again.",
    );
    expect(errorEl.className).toContain('text-destructive');
    // No toggle appears when the query itself succeeded — only the mutation failed.
    expect(screen.queryByTestId('import-filter-error')).toBeNull();
  });

  it('does not show the save error when the last mutation succeeded (default state)', () => {
    mockSettings();
    mockUpdateMutation();

    render(<ImportFilterCard />);

    expect(screen.queryByTestId('import-filter-save-error')).toBeNull();
  });

  it('clears the save error once a subsequent mutation attempt starts', () => {
    mockSettings();
    mockUpdateMutation({ isError: true, error: new Error('Network error') });

    const { rerender } = render(<ImportFilterCard />);
    expect(screen.getByTestId('import-filter-save-error')).toBeTruthy();

    // A new mutate() call resets TanStack Query's isError/error before the
    // next attempt resolves (dispatches a fresh 'pending' status) — simulate
    // that by re-rendering with the hook reporting the cleared state.
    mockUpdateMutation({ isError: false, error: null });
    rerender(<ImportFilterCard />);

    expect(screen.queryByTestId('import-filter-save-error')).toBeNull();
  });
});
