// Phase 62 — TypeScript types mirroring app/schemas/admin.py.

export interface ImpersonationContext {
  admin_id: number;
  target_email: string;
}

export interface ImpersonateResponse {
  access_token: string;
  token_type: 'bearer';
  target_email: string;
  target_id: number;
}

export interface UserSearchResult {
  id: number;
  email: string;
  chess_com_username: string | null;
  lichess_username: string | null;
  is_guest: boolean;
  last_login: string | null;
}
