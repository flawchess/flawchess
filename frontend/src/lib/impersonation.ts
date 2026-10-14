import type { UserProfile } from '@/types/users';

/**
 * localStorage key that holds the superuser's own JWT while an impersonation token
 * occupies `auth_token`. useAuth.impersonate writes it, useAuth.endImpersonation
 * consumes it, and every session start/end path clears it.
 */
export const ADMIN_RETURN_TOKEN_STORAGE_KEY = 'admin_return_token';

/**
 * Returns true when the user profile indicates an active impersonation session.
 *
 * Centralized so components don't reach for `profile?.impersonation != null` directly —
 * keeps the truthiness check consistent and gives us a single place to evolve if the
 * backend shape changes (e.g. adding expires_at).
 */
export function isImpersonating(profile: UserProfile | undefined): boolean {
  if (!profile) return false;
  return profile.impersonation != null;
}
