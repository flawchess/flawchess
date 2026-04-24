import { describe, it, expect } from 'vitest';
import { isImpersonating } from './impersonation';
import type { UserProfile } from '@/types/users';

describe('isImpersonating', () => {
  const base: UserProfile = {
    email: 'a@b.c',
    is_superuser: false,
    is_guest: false,
    chess_com_username: null,
    lichess_username: null,
    created_at: '2026-01-01T00:00:00Z',
    last_login: null,
    chess_com_game_count: 0,
    lichess_game_count: 0,
    impersonation: null,
    beta_enabled: false,
  };

  it('returns true when impersonation is an object', () => {
    expect(
      isImpersonating({ ...base, impersonation: { admin_id: 1, target_email: 'x@y' } }),
    ).toBe(true);
  });

  it('returns false when impersonation is null', () => {
    expect(isImpersonating({ ...base, impersonation: null })).toBe(false);
  });

  it('returns false when profile is undefined', () => {
    expect(isImpersonating(undefined)).toBe(false);
  });

  it('returns false when profile is missing impersonation field', () => {
    // Intentional cast: simulate a backward-compat response shape without the new field
    const partial: Record<string, unknown> = { ...base };
    delete partial.impersonation;
    expect(isImpersonating(partial as unknown as UserProfile)).toBe(false);
  });
});
