import type { ImpersonationContext } from '@/types/admin';

export interface UserProfile {
  email: string;
  is_superuser: boolean;
  is_guest: boolean;
  chess_com_username: string | null;
  lichess_username: string | null;
  created_at: string;
  last_login: string | null;
  chess_com_game_count: number;
  lichess_game_count: number;
  // D-22: populated by backend when the request carries an impersonation JWT.
  // Frontend uses this to render the header pill (Plan 05).
  impersonation: ImpersonationContext | null;
}
