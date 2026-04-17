import { X } from 'lucide-react';

import { useAuth } from '@/hooks/useAuth';
import {
  IMPERSONATION_PILL_BG,
  IMPERSONATION_PILL_FG,
  IMPERSONATION_PILL_BORDER,
} from '@/lib/theme';
import type { ImpersonationContext } from '@/types/admin';

interface Props {
  impersonation: ImpersonationContext;
  /** Constrain truncation width — defaults to 12rem (desktop). Mobile passes a smaller cap. */
  emailMaxWidthClass?: string;
}

/**
 * Header pill shown when the authenticated request is an impersonation session.
 * The × is the SOLE logout control during impersonation (D-20): clicking it
 * calls useAuth().logout which clears the token and redirects to the login
 * screen. Per D-21, this pill is the only visual indicator — no banner, no
 * sticky-layout displacement, no tab title change.
 */
export function ImpersonationPill({ impersonation, emailMaxWidthClass = 'max-w-[12rem]' }: Props) {
  const { logout } = useAuth();

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="impersonation-pill"
      className="flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium"
      style={{
        backgroundColor: IMPERSONATION_PILL_BG,
        color: IMPERSONATION_PILL_FG,
        borderColor: IMPERSONATION_PILL_BORDER,
      }}
    >
      <span className={`truncate ${emailMaxWidthClass}`}>
        Impersonating {impersonation.target_email}
      </span>
      <button
        type="button"
        onClick={logout}
        aria-label="End impersonation session"
        data-testid="btn-impersonation-pill-logout"
        className="rounded-full p-0.5 hover:bg-black/20 focus:outline-none focus:ring-2 focus:ring-offset-1"
      >
        <X className="h-3 w-3" aria-hidden="true" />
      </button>
    </div>
  );
}
