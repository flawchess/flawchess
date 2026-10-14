// @vitest-environment jsdom
/**
 * AuthFormErrors.test.tsx — server error handling in LoginForm and RegisterForm.
 *
 * Security review 2026-10-14 added a backend password policy and a login failure
 * limiter. Covers: the 429 message on login, a rejected guest-promotion password
 * keeping the guest token (it used to fall through to plain registration and orphan
 * the guest's games), and register errors showing readable messages.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

const mockLogin = vi.fn();
const mockRegister = vi.fn();
const mockLoginWithToken = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    register: mockRegister,
    loginWithToken: mockLoginWithToken,
  }),
}));
vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    apiClient: {
      get: vi.fn(() => Promise.resolve({ data: { available: false } })),
      post: vi.fn(),
    },
  };
});

import * as Sentry from '@sentry/react';
import { toast } from 'sonner';
import { apiClient } from '@/api/client';
import { LoginForm } from '../LoginForm';
import { RegisterForm } from '../RegisterForm';

const REASON = 'Password must be at least 8 characters.';

function axiosError(status: number, detail?: unknown): Error {
  return Object.assign(new Error(`http ${status}`), {
    isAxiosError: true,
    response: { status, data: detail !== undefined ? { detail } : {} },
  });
}

function fill(testId: string, value: string) {
  fireEvent.change(screen.getByTestId(testId), { target: { value } });
}

function submitRegister() {
  fill('register-email', 'new@example.com');
  fill('register-password', 'longenough1');
  fireEvent.change(screen.getByLabelText('Confirm Password'), { target: { value: 'longenough1' } });
  fireEvent.click(screen.getByTestId('btn-register'));
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  localStorage.clear();
});

describe('LoginForm', () => {
  it('explains the lockout on 429 without reporting to Sentry', async () => {
    mockLogin.mockRejectedValueOnce(axiosError(429, 'LOGIN_RATE_LIMITED'));
    render(<MemoryRouter><LoginForm /></MemoryRouter>);
    fill('login-email', 'a@example.com');
    fill('login-password', 'whatever1');
    fireEvent.click(screen.getByTestId('btn-login'));

    await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1));
    expect(vi.mocked(toast.error).mock.calls[0][0]).toContain('Too many failed login attempts');
    expect(Sentry.captureException).not.toHaveBeenCalled();
  });
});

describe('RegisterForm', () => {
  it('keeps the guest token and shows the reason when promotion rejects the password', async () => {
    localStorage.setItem('guest_token', 'guest-jwt');
    vi.mocked(apiClient.post).mockRejectedValueOnce(
      axiosError(400, { code: 'REGISTER_INVALID_PASSWORD', reason: REASON }),
    );
    render(<MemoryRouter><RegisterForm /></MemoryRouter>);
    submitRegister();

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith(REASON));
    expect(localStorage.getItem('guest_token')).toBe('guest-jwt');
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it('shows the server reason for an invalid password on plain registration', async () => {
    mockRegister.mockRejectedValueOnce(
      axiosError(400, { code: 'REGISTER_INVALID_PASSWORD', reason: REASON }),
    );
    render(<MemoryRouter><RegisterForm /></MemoryRouter>);
    submitRegister();

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith(REASON));
  });

  it('shows a readable message instead of the raw already-exists code', async () => {
    mockRegister.mockRejectedValueOnce(axiosError(400, 'REGISTER_USER_ALREADY_EXISTS'));
    render(<MemoryRouter><RegisterForm /></MemoryRouter>);
    submitRegister();

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('An account with this email already exists.'),
    );
  });
});
