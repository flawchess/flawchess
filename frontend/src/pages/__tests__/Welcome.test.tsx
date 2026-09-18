// @vitest-environment jsdom
/**
 * Tests for the /welcome page (Phase 224 S-5, GUESTACT-08).
 *
 * Covers:
 * 1. Page container and the four-delta list render
 * 2. Guest fixture renders the Sign up free button; clicking it calls
 *    logoutForPromotion
 * 3. Registered fixture renders no Sign up free button
 * 4. The Back affordance is present for both fixtures and carries no umami
 *    attribute
 * 5. The dismissal checkbox no longer exists
 * 6. Button order (224 UAT round 1): Back on the left, Sign up free on the right
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockNavigate = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockLogoutForPromotion = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    token: 'test-token',
    logoutForPromotion: mockLogoutForPromotion,
  }),
}));

const profileState: { is_guest: boolean } = { is_guest: true };
vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => ({ data: { ...profileState } }),
}));

// ── Setup / teardown ──────────────────────────────────────────────────────────

afterEach(() => {
  cleanup();
  mockNavigate.mockReset();
  mockLogoutForPromotion.mockReset();
  profileState.is_guest = true;
});

// ── Import after mocks are set up ─────────────────────────────────────────────

import { WelcomePage } from '@/pages/Welcome';

// ── Render helper ──────────────────────────────────────────────────────────────

function renderWelcome() {
  return render(
    <MemoryRouter>
      <WelcomePage />
    </MemoryRouter>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('WelcomePage rendering', () => {
  it('renders the page container and exactly four delta items', () => {
    renderWelcome();
    expect(screen.getByTestId('welcome-page')).not.toBeNull();
    const list = screen.getByTestId('welcome-delta-list');
    expect(list.querySelectorAll('li').length).toBe(4);
    expect(screen.getByTestId('welcome-delta-1')).not.toBeNull();
    expect(screen.getByTestId('welcome-delta-2')).not.toBeNull();
    expect(screen.getByTestId('welcome-delta-3')).not.toBeNull();
    expect(screen.getByTestId('welcome-delta-4')).not.toBeNull();
  });

  it('guest fixture renders the Sign up free button with signup-cta umami attrs', () => {
    profileState.is_guest = true;
    renderWelcome();
    const btn = screen.getByTestId('welcome-btn-signup');
    expect(btn).not.toBeNull();
    expect(btn.getAttribute('data-umami-event')).toBe('signup-cta');
    expect(btn.getAttribute('data-umami-event-source')).toBe('welcome');
  });

  it('clicking Sign up free calls logoutForPromotion', () => {
    profileState.is_guest = true;
    renderWelcome();
    fireEvent.click(screen.getByTestId('welcome-btn-signup'));
    expect(mockLogoutForPromotion).toHaveBeenCalled();
  });

  it('registered fixture renders no Sign up free button', () => {
    profileState.is_guest = false;
    renderWelcome();
    expect(screen.queryByTestId('welcome-btn-signup')).toBeNull();
  });

  it('renders the Back affordance for both fixtures with no umami attribute', () => {
    profileState.is_guest = true;
    const { unmount } = renderWelcome();
    const backGuest = screen.getByTestId('welcome-btn-back');
    expect(backGuest).not.toBeNull();
    expect(backGuest.getAttribute('data-umami-event')).toBeNull();
    unmount();

    profileState.is_guest = false;
    renderWelcome();
    const backRegistered = screen.getByTestId('welcome-btn-back');
    expect(backRegistered).not.toBeNull();
    expect(backRegistered.getAttribute('data-umami-event')).toBeNull();
  });

  it('renders Back before Sign up free in the actions row (UAT round 1: Back left, Sign up right)', () => {
    profileState.is_guest = true;
    renderWelcome();
    const buttons = screen.getByTestId('welcome-actions').querySelectorAll('button');
    expect(buttons).toHaveLength(2);
    expect(buttons[0]?.getAttribute('data-testid')).toBe('welcome-btn-back');
    expect(buttons[1]?.getAttribute('data-testid')).toBe('welcome-btn-signup');
  });

  it('has no dismissal checkbox', () => {
    renderWelcome();
    expect(screen.queryByTestId('welcome-checkbox-dont-show')).toBeNull();
  });
});
