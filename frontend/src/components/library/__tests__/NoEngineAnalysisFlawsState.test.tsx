// @vitest-environment jsdom
/**
 * NoEngineAnalysisFlawsState guest CTA: the button used to
 * navigate('/login?tab=register') while the guest was still signed in, so AuthPage
 * bounced them to / and nothing happened. It must drop the guest session first
 * (keeping guest_token for promotion) and hard-navigate to the register tab.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { NoEngineAnalysisFlawsState } from '../NoEngineAnalysisFlawsState';

const mockLogoutForPromotion = vi.fn();

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ logoutForPromotion: mockLogoutForPromotion }),
}));

const originalLocation = window.location;

beforeEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { ...originalLocation, href: '' },
  });
});

afterEach(() => {
  cleanup();
  mockLogoutForPromotion.mockReset();
  Object.defineProperty(window, 'location', { configurable: true, value: originalLocation });
});

describe('NoEngineAnalysisFlawsState', () => {
  it('guest CTA drops the guest session and hard-navigates to the register tab', () => {
    render(
      <MemoryRouter>
        <NoEngineAnalysisFlawsState isGuest />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByTestId('btn-signup-for-analysis-flaws'));

    expect(mockLogoutForPromotion).toHaveBeenCalledTimes(1);
    expect(window.location.href).toBe('/login?tab=register');
  });

  it('shows no sign-up CTA for a registered user', () => {
    render(
      <MemoryRouter>
        <NoEngineAnalysisFlawsState isGuest={false} />
      </MemoryRouter>,
    );

    expect(screen.queryByTestId('btn-signup-for-analysis-flaws')).toBeNull();
  });
});
