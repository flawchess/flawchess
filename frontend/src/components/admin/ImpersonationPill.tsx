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
 * The × ends the impersonation session and returns to the admin's own session on
 * /admin (useAuth().endImpersonation), falling back to a full logout when no admin
 * token was stashed. The regular Logout button next to it stays a full sign-out.
 */
export function ImpersonationPill({ impersonation, emailMaxWidthClass = 'max-w-[12rem]' }: Props) {
  const { endImpersonation } = useAuth();

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="impersonation-pill"
      aria-label={`Impersonating ${impersonation.target_email}`}
      className="flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium"
      style={{
        backgroundColor: IMPERSONATION_PILL_BG,
        color: IMPERSONATION_PILL_FG,
        borderColor: IMPERSONATION_PILL_BORDER,
      }}
    >
      <span className={`truncate ${emailMaxWidthClass}`}>
        {impersonation.target_email}
      </span>
      <button
        type="button"
        onClick={endImpersonation}
        aria-label="End impersonation session"
        data-testid="btn-impersonation-pill-logout"
        className="rounded-full p-0.5 hover:bg-black/20 focus:outline-none focus:ring-2 focus:ring-offset-1"
      >
        <X className="h-3 w-3" aria-hidden="true" />
      </button>
    </div>
  );
}
