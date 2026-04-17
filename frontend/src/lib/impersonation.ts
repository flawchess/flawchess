import type { UserProfile } from '@/types/users';

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
