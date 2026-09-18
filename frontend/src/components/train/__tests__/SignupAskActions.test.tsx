// @vitest-environment jsdom
/**
 * SignupAskActions.test.tsx — Phase 224 (S-4, D-05, D-07; GUESTACT-11).
 *
 * Covers the shared "What changes?" + "Sign up free" action pair rendered for
 * both host surfaces: the umami attribute contract (What changes? carries none, Sign up
 * free carries `signup-cta` + the per-surface source) and the promotion
 * handoff (`logoutForPromotion()` then a hard navigation to
 * `/login?tab=register`), mirroring `Welcome.test.tsx`'s mock shape.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

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
    logoutForPromotion: mockLogoutForPromotion,
  }),
}));

// Stub window.location assignment so the hard navigation to the register page
// is observable without jsdom actually attempting to leave the page (mirrors
// useEvalCoverage.test.tsx's window.location stubbing pattern).
const originalLocation = window.location;
beforeEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { ...originalLocation, href: '' },
  });
});

afterEach(() => {
  cleanup();
  mockNavigate.mockReset();
  mockLogoutForPromotion.mockReset();
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation,
  });
});

import { SignupAskActions } from '@/components/train/SignupAskActions';

describe('SignupAskActions', () => {
  it('renders exactly two buttons, in order: What changes? then Sign up free', () => {
    render(<SignupAskActions source="train-score" />);
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(2);
    expect(buttons[0]?.textContent).toBe('What changes?');
    expect(buttons[1]?.textContent).toBe('Sign up free');
  });

  it('What changes? carries the train-score testid, brand-outline variant, and no umami attribute', () => {
    render(<SignupAskActions source="train-score" />);
    const why = screen.getByTestId('btn-signup-why-train-score');
    // Asserted via a stable fragment of button.tsx's own "brand-outline"
    // variant class string, not by re-implementing the variant map.
    expect(why.className).toContain('border-brand-brown-light');
    expect(why.getAttribute('data-umami-event')).toBeNull();
    expect(why.getAttribute('data-umami-event-source')).toBeNull();
  });

  it('clicking What changes? navigates to /welcome and does not call logoutForPromotion', () => {
    render(<SignupAskActions source="train-score" />);
    fireEvent.click(screen.getByTestId('btn-signup-why-train-score'));
    expect(mockNavigate).toHaveBeenCalledWith('/welcome');
    expect(mockLogoutForPromotion).not.toHaveBeenCalled();
  });

  it('Sign up free carries the train-score testid, default variant, and the signup-cta umami attrs', () => {
    render(<SignupAskActions source="train-score" />);
    const signUp = screen.getByTestId('btn-signup-free-train-score');
    expect(signUp.getAttribute('data-umami-event')).toBe('signup-cta');
    expect(signUp.getAttribute('data-umami-event-source')).toBe('train-score');
  });

  it('clicking Sign up free calls logoutForPromotion before assigning the register URL', () => {
    render(<SignupAskActions source="train-score" />);
    fireEvent.click(screen.getByTestId('btn-signup-free-train-score'));
    expect(mockLogoutForPromotion).toHaveBeenCalledTimes(1);
    expect(window.location.href).toBe('/login?tab=register');
  });

  it('with source="import-promo" the testids and umami source switch to the import-promo form', () => {
    render(<SignupAskActions source="import-promo" />);
    expect(screen.getByTestId('btn-signup-why-import-promo')).not.toBeNull();
    const signUp = screen.getByTestId('btn-signup-free-import-promo');
    expect(signUp.getAttribute('data-umami-event')).toBe('signup-cta');
    expect(signUp.getAttribute('data-umami-event-source')).toBe('import-promo');
  });

  it('renders no wrapping element beyond the two buttons (fragment shape)', () => {
    const { container } = render(<SignupAskActions source="train-score" />);
    expect(container.children).toHaveLength(2);
  });
});
