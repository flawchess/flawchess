// @vitest-environment jsdom
/**
 * ImpersonationPill.test.tsx — the x ends the impersonation and returns the admin
 * to their own session (endImpersonation), it must not fall through to logout.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

const { endImpersonation, logout } = vi.hoisted(() => ({
  endImpersonation: vi.fn(),
  logout: vi.fn(),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ endImpersonation, logout }),
}));

import { ImpersonationPill } from '@/components/admin/ImpersonationPill';

afterEach(() => {
  cleanup();
  endImpersonation.mockClear();
  logout.mockClear();
});

describe('ImpersonationPill', () => {
  it('x calls endImpersonation, not logout', () => {
    render(<ImpersonationPill impersonation={{ admin_id: 1, target_email: 'target@example.com' }} />);
    const button = screen.getByTestId('btn-impersonation-pill-logout');
    expect(button.getAttribute('aria-label')).toBe('End impersonation session');
    fireEvent.click(button);
    expect(endImpersonation).toHaveBeenCalledTimes(1);
    expect(logout).not.toHaveBeenCalled();
  });
});
