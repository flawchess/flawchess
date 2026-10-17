import type { ImpersonationContext } from '@/types/admin';
import type { Platform, TimeControl } from '@/types/api';

/** Provenance of a recent-games-derived current-strength estimate.
 * `converted` is False only for a native Lichess blitz rung; every other rung
 * was mapped onto the Lichess blitz scale. */
export interface CurrentStrengthRung {
  platform: Platform;
  time_control_bucket: TimeControl;
  n_games: number;
  window_days: number;
  converted: boolean;
}

/** The opponent-matching current-strength estimate. `rung` is non-null
 * exactly when `source === 'recent_games'`. */
export interface CurrentStrength {
  rating: number;
  source: 'recent_games' | 'rating_anchor';
  rung: CurrentStrengthRung | null;
}

/** The server-decided milestone feedback ask. There is no round field because
 * one copy serves both rounds; the client only renders when `active` is true
 * (false for guests and impersonation). */
export interface FeedbackAskView {
  active: boolean;
}

/** Body of POST /users/me/feedback-ask. */
export type FeedbackAskAction = 'view' | 'snooze' | 'done';

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
  chess_com_last_sync_at: string | null;
  lichess_last_sync_at: string | null;
  // Populated by backend when the request carries an impersonation JWT.
  // Frontend uses this to render the header pill.
  impersonation: ImpersonationContext | null;
  // Beta feature flag (e.g. Endgame Insights). Default false; flipped via direct DB op.
  beta_enabled: boolean;
  // Opt-out from the weekly Train leaderboards, written via PUT /users/me/profile.
  leaderboard_hidden: boolean;
  // The opponent-matching current-strength estimate. Null for guests, for
  // users with no anchor at all, and for users with anchors only in non-blitz
  // buckets and no qualifying recent games — the frontend falls back to 1500.
  // UI DEFAULT ONLY — never fed into bot move selection.
  current_strength: CurrentStrength | null;
  // Distinct UTC activity days up to and including today, the number quoted
  // in the ask copy.
  active_days: number;
  // Whether Hilda's feedback ask should show right now.
  feedback_ask: FeedbackAskView;
}
