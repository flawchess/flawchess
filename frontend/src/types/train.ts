/**
 * TypeScript mirrors of the Train API Pydantic schemas
 * (app/schemas/train.py). Field-for-field, literal unions instead of bare
 * `string` per CLAUDE.md's type-safety rule.
 *
 * `TrainPuzzle` carries the server answer key (`key_move_uci`), the puzzle
 * type and the sharp runner-up so the phone grades against the key. They are
 * read only to start grading and are never displayed before the attempt. The
 * pre-attempt payload also carries the server-graded set
 * (`server_graded_moves`), read only after the move.
 * `last_move_uci` is the position's arrival, the prior half-move, never what
 * to play next.
 */

import type { TrainMoveTier } from '@/lib/trainScore';
import type { TrainPuzzleType } from '@/lib/trainArrows';

export interface TrainPuzzle {
  position: number;
  game_id: number | null;
  ply: number;
  fen: string;
  side_to_move: 'white' | 'black';
  last_move_uci: string | null;
  /**
   * The server-picked solution move. The think-time search evaluates the
   * position AFTER it, and the reveal names it. All three fields are OPTIONAL
   * on purpose: a stale server (or an old trainRevealCache entry) omits them,
   * and every consumer defaults with a single `?? null` (the
   * `SolveResponse.vetted_moves?` precedent). null means no usable key, which
   * keeps the legacy root-search grading.
   */
  key_move_uci?: string | null;
  /** The puzzle type, known before the attempt but never displayed until the reveal. */
  puzzle_type?: TrainPuzzleType | null;
  /** The sharp runner-up move, null for non-sharp puzzles; never displayed pre-attempt. */
  runner_up_uci?: string | null;
  /**
   * The moves whose grade the server owns, read only AFTER the move (never
   * displayed before the attempt). OPTIONAL because a stale server or an old
   * reveal-cache entry omits it; the one consumer defaults with a single
   * `?? []`. Empty for sharp fillers and the no-key path; includes the key for
   * soft and herring puzzles.
   */
  server_graded_moves?: ServerGradedMove[];
}

/** A move whose grade the server owns; read only after the move, never displayed pre-attempt. */
export interface ServerGradedMove {
  uci: string;
  tier: TrainMoveTier;
}

/**
 * One recorded solve's outcome, part of `TrainSessionResponse.solved_results`.
 *
 * One entry per `drill_solves` row with `solved_at IS NOT NULL`, in
 * `position` order. The client aggregates these with `scorePuzzle` +
 * `aggregateSessionScore` from `@/lib/trainScore` — that module stays the
 * single source of truth for scoring; this response
 * deliberately carries NO precomputed score integer.
 */
export interface SolvedResult {
  correct_guess: boolean;
  move_quality: TrainMoveTier;
  /**
   * The same three values `SolveResponse` already returned for this exact
   * position at the moment it was attempted — NOT a new answer-key leak
   * (mirrors this interface's own docstring rule above).
   * Entries here still carry no `position`, `game_id`, `ply` or best-move
   * field. `source` mirrors `SolveResponse.source` (required); `item_status`
   * and `due_date` mirror `SolveResponse.item_status`/`due_date` (nullable —
   * `null` for `red_herring`/`sharp_filler` sources).
   */
  source: 'sr_item' | 'red_herring' | 'sharp_filler';
  item_status: 'active' | 'mastered' | 'parked' | null;
  due_date: string | null;
}

/**
 * Response for POST /train/sessions — a composed or resumed session.
 *
 * `solved_results` is what makes "Scored today" correct on a device that
 * never saw the original solve responses — see `SolvedResult`'s docstring.
 * Empty for a freshly composed session and for the no-eligible-material
 * (`session_id === null`) case.
 *
 * `is_warmup` is frozen at composition and derived purely from material
 * scarcity — true iff the session contains zero surviving SR_ITEM puzzles at
 * the moment it was (re-)composed. Never derived from session ordinal,
 * session count, or account age. The client performs no arithmetic over it —
 * a single equality read.
 */
export interface TrainSessionResponse {
  session_id: number | null;
  session_date: string;
  expires_on: string;
  puzzle_count: number;
  requested_count: number;
  solved_count: number;
  blob_pending_count: number;
  puzzles: TrainPuzzle[];
  solved_results: SolvedResult[];
  is_warmup: boolean;
}

/**
 * Body for POST /train/sessions/{session_id}/solve.
 *
 * The client asserts the three-way `move_quality` tier (grading happens
 * entirely client-side) but NEVER `correct_guess` — that is computed
 * server-side from the live blob classifier. The server derives the ladder
 * verdict as `move_quality != "wrong"`.
 */
export interface SolveRequest {
  position: number;
  guess: 'critical' | 'several';
  /** UCI move string: 4 chars normal ("e2e4"), 5 chars promotion ("e7e8q"). */
  played_move: string;
  move_quality: TrainMoveTier;
  /**
   * Think-time telemetry. Optional so a stale client bundle still solves;
   * never an input to grading or scoring.
   */
  telemetry?: SolveTelemetry;
  /**
   * The disagreement re-check record. Present exactly when a re-check
   * COMPLETED (confirmed or resolved); absent when none ran or it timed out or
   * errored, in which case the 1.5 s grade stands and the server credits
   * nothing. A client claim only: the server re-validates it.
   */
  recheck?: SolveRecheck;
  /**
   * The phone's 1.5 s grading reading, audit data only. Present for a keyed
   * solve graded on the phone, including played == key; absent on the legacy
   * no-key path, on a server-graded move's instant POST and when the after-key
   * search never completed. Frozen with the payload so a retry resends it
   * unchanged.
   */
  phone_grade?: PhoneGrade;
}

/**
 * Mirrors app/schemas/train.py PhoneGrade. ES values are mover-POV expected
 * scores in [0, 1] of the 1.5 s after-key and after-played searches; depths
 * are the engine depths reported with them (0 when no exact line arrived).
 * Audit data only, never a grading input. `v` is PHONE_GRADE_SCHEMA_VERSION
 * in lib/trainPhoneGrade.ts.
 */
export interface PhoneGrade {
  v: 1;
  tier: TrainMoveTier;
  key_es: number;
  played_es: number;
  key_depth: number;
  played_depth: number;
}

/** How a completed re-check ended: the 3 s reading still rates the played move good, or not. */
export type RecheckOutcome = 'confirmed' | 'resolved';

/**
 * Mirrors app/schemas/train.py SolveRecheck. ES values are mover-POV
 * expected scores in [0, 1]: `key_es`/`played_es` are the 1.5 s after-move
 * searches, `*_recheck` the 3 s ones. Depths are the engine depth reported
 * with each reading (0 when no exact line arrived). `v` is
 * RECHECK_SCHEMA_VERSION in lib/trainRecheck.ts.
 */
export interface SolveRecheck {
  v: 1;
  outcome: RecheckOutcome;
  key_es: number;
  played_es: number;
  key_es_recheck: number;
  played_es_recheck: number;
  key_depth: number;
  played_depth: number;
  key_depth_recheck: number;
  played_depth_recheck: number;
}

/** Device class sent with telemetry: a two-value class, never the raw UA string. */
export type TelemetryClient = 'mobile' | 'desktop';

/**
 * Mirrors app/schemas/train.py SolveTelemetry. Durations are integer
 * milliseconds of VISIBLE time; `v` is TELEMETRY_SCHEMA_VERSION.
 * `think_hidden_ms` is the think phase's hidden-tab time, kept distinct from
 * the review flush's `review_hidden_ms` because the server merges per key.
 */
export interface SolveTelemetry {
  v: 1;
  client?: TelemetryClient;
  guess_ms?: number;
  move_ms?: number;
  think_hidden_ms?: number;
  resumed?: boolean;
}

/**
 * Why a review flush was sent, closed set mirrored from
 * app/schemas/train.py with no third value. 'next' = the user pressed Next on
 * the reveal; 'pagehide' = the user left the reveal without pressing Next
 * (page hidden or unloaded, in-app route change or screen unmount, leaving
 * via Analyze). "Puzzle N was shown" is derived server-side from the previous
 * puzzle's `exit = 'next'`.
 */
export type ReviewExit = 'next' | 'pagehide';

/**
 * Mirrors app/schemas/train.py ReviewTelemetry. Every value is a CUMULATIVE
 * total for the reveal, because one reveal can be flushed several times
 * (non-Next exits, then Next) and the server merges per key, last write wins.
 * Durations are integer ms of VISIBLE time; hidden-tab time is
 * `review_hidden_ms`, distinct from the solve patch's `think_hidden_ms`.
 *
 * This client always sends v 2: chips selected / chips total / strip expanded
 * replace the v1 card keys, and `review_explored` means "forked at least one
 * sideline". v 1 is what older bundles still send; the server accepts both.
 */
export interface ReviewTelemetry {
  v: 2;
  exit: ReviewExit;
  review_ms?: number;
  review_hidden_ms?: number;
  /** Distinct chips selected beyond the default You chip. */
  review_chips_selected?: number;
  /** The most chips shown on this reveal. */
  review_chips_total?: number;
  /** The phone verdict strip was opened at least once. */
  review_strip_expanded?: boolean;
  review_line_steps?: number;
  review_explore_moves?: number;
  review_board_moves?: number;
  review_explored?: boolean;
  review_analyze_opened?: boolean;
  review_walkthrough?: boolean;
}

/**
 * Body of POST /train/sessions/{session_id}/solves/{position}/review. Mirrors
 * app/schemas/train.py ReviewRequest: the review telemetry keys plus the
 * optional late 1.5 s phone reading of a server-graded move, present only once
 * the background search settled. The server writes it once and never merges it
 * into telemetry.
 */
export interface ReviewRequest extends ReviewTelemetry {
  phone_grade?: PhoneGrade;
}

/**
 * One server-certified "also fine" alternative move — the wire mirror of
 * `app.schemas.train.VettedMove`. Structurally identical to
 * `trainArrows.ts`'s `TrainFineMove`, on purpose: the reveal overlay consumes
 * these entries directly. 'best' marks the deep best move itself, served first
 * on a soft puzzle alongside the certified second-best, so the "Also fine" row
 * always has a displayable entry after the overlay filters out the client's
 * own best/played arrows.
 */
export interface VettedMove {
  uci: string;
  quality: 'best' | 'good' | 'inaccuracy';
}

/**
 * Response for POST /train/sessions/{session_id}/solve.
 *
 * `correct_move` is the SR ladder's pass/fail verdict, also what the reveal's
 * check/cross mark reads. `move_quality` is the three-way scoring tier the
 * client's points formula consumes.
 *
 * `source` mirrors `puzzle_type` — it lands synchronously with this response,
 * so the your-game predicates in TrainReveal.tsx read `verdict.source`, never
 * the separate, asynchronously fetched `PuzzleRevealResponse.source` (which
 * would open a post-solve window where a real SR puzzle misrenders as
 * suppressed).
 */
export interface SolveResponse {
  correct_guess: boolean;
  correct_move: boolean;
  move_quality: TrainMoveTier;
  puzzle_type: 'sharp' | 'soft' | 'herring';
  source: 'sr_item' | 'red_herring' | 'sharp_filler';
  item_status: 'active' | 'mastered' | 'parked' | null;
  streak: number | null;
  due_date: string | null;
  session_complete: boolean;
  /**
   * The server's certified "also fine" set and the graded-eval pair for a
   * key-move override (non-null exactly when the server overrode the client's
   * tier). All three fields are OPTIONAL on purpose: a `trainRevealCache`
   * entry written by an older bundle restores a `verdict` object with none of
   * these keys at runtime even though the compiler sees them — the same
   * graceful-degradation pattern `GradeResult.lines?` uses. Exactly one
   * nullish default per seam, at the consumption site.
   */
  vetted_moves?: VettedMove[];
  graded_es_before?: number | null;
  graded_es_after?: number | null;
  /**
   * True only when the server accepted a confirmed phone re-check, crediting
   * either guess. Optional for older trainRevealCache entries and a
   * not-yet-deployed server; read with a single `?? false`.
   */
  disagreement?: boolean;
}

/**
 * Response for GET /train/sessions/{session_id}/puzzles/{position}/reveal.
 * Reachable ONLY after the attempt is recorded (409 otherwise).
 *
 * Deliberately thin — NO `best_move`/`best_move_san`/`pv` fields. The best
 * move, the best line, and every eval shown in the reveal panel are computed
 * CLIENT-SIDE by the grading engine (`useTrainGradingEngine.ts`), never
 * derived or stored server-side (a server-stored Stockfish eval and the
 * client's own WASM search are not guaranteed to agree bit-for-bit). Do not
 * re-add these fields as a "fallback". The server picks the solution MOVE
 * (`TrainPuzzle.key_move_uci`); the phone still supplies every number.
 *
 * `played_in_game_move_uci` is the UCI counterpart of `played_in_game_san`,
 * behind the identical gate — used to dispatch the client's reveal-time engine
 * search.
 *
 * `game_id` is `number | null`: a red herring's source game can be nulled by
 * the OWNER deleting it (a global pool row survives independently) — never by
 * the solving user. A null `game_id` degrades the reveal's game footer to
 * nothing and hides the Analyze deep-link rather than disabling it.
 */
export interface PuzzleRevealResponse {
  game_id: number | null;
  ply: number;
  fen: string;
  played_in_game_san: string | null;
  played_in_game_move_uci: string | null;
  puzzle_type: 'sharp' | 'soft' | 'herring';
  source: 'sr_item' | 'red_herring' | 'sharp_filler';
  has_tactic_lines: boolean;
  /** The sharp filler's motif label ("Fork", "Skewer", ...), read straight
   * from the committed data file. null for every
   * sr_item/red_herring reveal — no motif taxonomy exists for those today. */
  motif: string | null;
}

/** Finished reveal-tour parts, 0..3; 3 means the whole tour is done. */
export type RevealTourStage = 0 | 1 | 2 | 3;

/** Response for GET /train/settings.
 *
 * The backend CHECK bound on `reminder_hour` is 0..23 inclusive
 * (`REMINDER_HOUR_MIN`/`REMINDER_HOUR_MAX` in `app/services/train_scheduler.py`).
 *
 * `reminder_intent_at` is an ISO instant string, or null if the user has never
 * expressed install intent.
 */
export interface TrainSettingsResponse {
  timezone: string;
  weekday_mask: number;
  puzzles_per_session: number;
  reminder_enabled: boolean;
  reminder_hour: number;
  reminder_intent_at: string | null;
  /**
   * Server-stamped, read-only "seen" watermarks for the intro and
   * score-explanation steppers (`intro_seen_at`, `sr_explained_at`), stamped
   * by `POST /train/onboarding/{step}` only on a COMPLETED stepper (an
   * abandoned one replays). The first-reveal tour is a forward-only count of
   * finished parts instead, `reveal_tour_stage` (0 = none, 3 = whole tour
   * done). None of these is writable via `TrainSettingsUpdate`: a PUT body can
   * never smuggle a server-owned field, same rule as `reminder_last_sent_on`.
   */
  intro_seen_at: string | null;
  reveal_tour_stage: RevealTourStage;
  sr_explained_at: string | null;
  /**
   * Whether ANY of the account's push subscriptions
   * came from a mobile browser (server-side User-Agent check). Account-wide,
   * unlike the per-device subscription probe — the desktop score screen uses
   * it to swap the phone QR handoff for a "reminders on your phone" line.
   */
  has_mobile_subscription: boolean;
}

/** Body for PUT /train/settings — a separate shape so a PUT can never smuggle
 * a server-owned field (mirrors the backend's `TrainSettingsUpdate`).
 *
 * This is a full-replace body with exactly one call site
 * (`useTrainSettings.ts`'s `mutationFn`) — every field here must be sent on
 * every save, or an existing save 422s the moment the backend requires it.
 * `reminder_intent_at` is required-but-nullable — an ISO instant
 * string or null, never omitted. */
export interface TrainSettingsUpdate {
  timezone: string;
  weekday_mask: number;
  puzzles_per_session: number;
  reminder_enabled: boolean;
  reminder_hour: number;
  reminder_intent_at: string | null;
}

/**
 * The server-computed empty-state discriminant (mirrors the
 * backend `_pool_state`). `'no_material'` = never had any qualifying
 * material (cold start); `'exhausted'` = material existed but nothing is
 * waiting and nothing is still analyzing; `'available'` = every other case,
 * including a zero-`drill_items` user whose blunders are still being
 * analyzed ("catching up", not a cold start). The client performs no
 * arithmetic to pick between the two empty states — this field is the
 * single source of truth.
 */
export type TrainPoolState = 'no_material' | 'exhausted' | 'available';

/**
 * Response for GET /train/progress.
 *
 * `session_streak_count` and `shield_level` (a plain 0-7 number) mirror the
 * persisted per-scheduled-day tick snapshot on `train_settings`; the returned
 * values are always exactly what is persisted. `current_week_required` is
 * null when `weekday_mask === 0` ("train anytime" has no denominator to
 * show). `mastered_count`/`parked_count` are computed on the fly from
 * `drill_items` (unaffected by the tick snapshot).
 *
 * `waiting_count` is an upper-bound attention-signal estimate, never a
 * promise of exact session size — the start screen's own "N puzzles
 * waiting" line still comes from the real composed session. `next_due_date`
 * is the earliest date an ACTIVE item will next resurface, or null when
 * nothing will (the "All caught up!" empty state's date).
 *
 * `streak_reset_notice` is derived from the
 * RESULTING state (never from "did this call settle the reset"), so it
 * survives a page reload.
 *
 * `badge_visible` is a DISPLAY HINT ONLY — it gates no server-side
 * authorization, and the number the nav badge shows still comes
 * from `waiting_count`. The client MUST NEVER attempt its own day-of-week or
 * timezone math here — it has no `weekday_mask` and no clean way to
 * reproduce the backend's `local_today` — this field is the single source
 * of truth for whether the badge should show.
 */
export interface TrainProgressResponse {
  session_streak_count: number;
  shield_level: number;
  current_week_completed: number;
  current_week_required: number | null;
  streak_reset_notice: boolean;
  mastered_count: number;
  parked_count: number;
  waiting_count: number;
  pool_state: TrainPoolState;
  next_due_date: string | null;
  badge_visible: boolean;
}

// ─── Weekly leaderboards ─────────────────────────────────────────

/** Which weekly board a payload or tab refers to. Mirrors app/schemas/train.py. */
export type LeaderboardBoardKind = 'points' | 'accuracy';

/**
 * Row visibility. `'public'` for every row except the viewer's own private
 * would-be row: `'hidden'` (opted out) or `'guest'` (ghost row).
 * Mirrors app/schemas/train.py.
 */
export type LeaderboardVisibility = 'public' | 'hidden' | 'guest';

/** Medal types, best first. Mirrors app/schemas/train.py. */
export type MedalKind = 'gold' | 'silver' | 'bronze';

/** Lifetime medal counts of one row's user. Mirrors app/schemas/train.py. */
export interface LeaderboardMedals {
  gold: number;
  silver: number;
  bronze: number;
}

/** One medal on last week's podium. Mirrors app/schemas/train.py. */
export interface LeaderboardPodiumEntry {
  medal: MedalKind;
  /** Read-time masked by the server ("Anonymous" / "Deleted user"); render as text only. */
  name: string;
  /** True only on the viewer's own entry; carries no user id. */
  is_viewer: boolean;
}

/** Last week's podium plus the viewer's own non-medal rank. Mirrors app/schemas/train.py. */
export interface LeaderboardLastWeek {
  /** ISO date of the previous Monday (UTC). */
  week_start: string;
  /** Server-ordered gold to bronze, every tied name listed; empty means no podium line. */
  podium: LeaderboardPodiumEntry[];
  /** Set only for the viewer's own row that earned no medal. */
  viewer_final_rank: number | null;
}

/** One ranked row of a weekly board. Mirrors app/schemas/train.py. */
export interface LeaderboardRow {
  /**
   * Null marks a tentative Accuracy entry: listed below every qualified row,
   * without a rank.
   */
  rank: number | null;
  name: string;
  /** Points, or the floored accuracy percent. */
  value: number;
  /** All solves (points board) or non-filler solves (accuracy board). */
  puzzles: number;
  /** Accuracy board only: fewer than 20 qualifying puzzles this week. */
  tentative: boolean;
  is_viewer: boolean;
  visibility: LeaderboardVisibility;
  /** True when a gap marker belongs before this row. */
  gap_before: boolean;
  /** True on the last shown row when ranks below it are cut: a gap marker follows it. */
  gap_after: boolean;
  /** Lifetime medals of this row's owner on this board; all zero when none. */
  medals: LeaderboardMedals;
}

/** The viewer's own standing on one board. Mirrors app/schemas/train.py. */
export interface LeaderboardViewer {
  /** Null while the viewer is a tentative Accuracy entry. */
  rank: number | null;
  /**
   * Rank without the given session's solves (score screen only), else null.
   * Also null when the viewer is tentative with or without the session.
   */
  rank_without_session: number | null;
  tentative: boolean;
  puzzles_to_qualify: number;
  visibility: LeaderboardVisibility;
}

/** The nearest strictly better Points row. Mirrors app/schemas/train.py. */
export interface LeaderboardPassTarget {
  name: string;
  points_needed: number;
}

/** One board: rows, the viewer's standing and (points board only) a pass target. */
export interface LeaderboardBoard {
  rows: LeaderboardRow[];
  viewer: LeaderboardViewer | null;
  pass_target: LeaderboardPassTarget | null;
  /** Previous ISO week only; null means there is nothing to show. */
  last_week: LeaderboardLastWeek | null;
}

/** Response for GET /train/leaderboard. Mirrors app/schemas/train.py. */
export interface TrainLeaderboardResponse {
  week_start: string;
  week_end: string;
  /** Server-computed remainder to week_end; the client never does its own week math. */
  seconds_remaining: number;
  points: LeaderboardBoard;
  accuracy: LeaderboardBoard;
}

// ─── Medal claim ─────────────────────────────────────────────────

/** One unclaimed medal awaiting the claim dialog. Mirrors app/schemas/train.py. */
export interface UnclaimedMedal {
  /** ISO date of the week's Monday (UTC); render with parseISO, never `new Date`. */
  week_start: string;
  board: LeaderboardBoardKind;
  medal: MedalKind;
  /** Final points, or the floored accuracy percent. */
  value: number;
  /** Another user holds the same medal on the same week and board. */
  shared: boolean;
}

/** Response for GET /train/medals/unclaimed: newest week first, Points before Accuracy. */
export interface UnclaimedMedalsResponse {
  medals: UnclaimedMedal[];
}

/** Natural per-user key of a medal, the body item of POST /train/medals/claim. Mirrors app/schemas/train.py. */
export interface MedalKey {
  week_start: string;
  board: LeaderboardBoardKind;
}
