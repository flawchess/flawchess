export interface UserProfile {
  email: string;
  is_superuser: boolean;
  chess_com_username: string | null;
  lichess_username: string | null;
  created_at: string;
  last_login: string | null;
  chess_com_game_count: number;
  lichess_game_count: number;
}
