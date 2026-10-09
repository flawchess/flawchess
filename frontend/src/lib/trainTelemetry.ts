/**
 * trainTelemetry.ts — Phase 233 per-puzzle telemetry constants and builders.
 *
 * The numeric constants mirror app/schemas/train.py and are CI-locked by
 * tests/schemas/test_train_telemetry_parity.py. Keep them plain integer
 * literals (the parity test reads `export const NAME = <digits>;` by regex).
 * Telemetry is a recorded outcome only; it never feeds grading or scoring (D-05).
 */

import type { ReviewExit, ReviewTelemetry, SolveTelemetry, TelemetryClient } from '@/types/train';
import type { StopwatchTotals } from '@/lib/visibleStopwatch';

// Mirrors app/schemas/train.py TELEMETRY_SCHEMA_VERSION, guarded by tests/schemas/test_train_telemetry_parity.py.
export const TELEMETRY_SCHEMA_VERSION = 1;

// Phase 237 (D-12): the REVIEW patch is v2 (chips selected / chips total / strip
// expanded replace the card keys). The solve patch keeps TELEMETRY_SCHEMA_VERSION
// (1), so the two patches carry separate constants (RESEARCH Pitfall 4). Mirrors
// app/schemas/train.py REVIEW_TELEMETRY_SCHEMA_VERSION, guarded by tests/schemas/test_train_telemetry_parity.py.
export const REVIEW_TELEMETRY_SCHEMA_VERSION = 2;

// 30 minutes (D-04). Mirrors app/schemas/train.py TELEMETRY_DURATION_CAP_MS, guarded by tests/schemas/test_train_telemetry_parity.py.
export const TELEMETRY_DURATION_CAP_MS = 1800000;

// 50 line-stepper clicks (D-14). Mirrors app/schemas/train.py TELEMETRY_LINE_STEPS_CAP, guarded by tests/schemas/test_train_telemetry_parity.py.
export const TELEMETRY_LINE_STEPS_CAP = 50;

// 50 free-play moves (D-14). Mirrors app/schemas/train.py TELEMETRY_EXPLORE_MOVES_CAP, guarded by tests/schemas/test_train_telemetry_parity.py.
export const TELEMETRY_EXPLORE_MOVES_CAP = 50;

// 10 chips (D-12): the reveal chips never exceed this (it also clamps the v2 chip counts). Mirrors app/schemas/train.py TELEMETRY_CARDS_CAP, guarded by tests/schemas/test_train_telemetry_parity.py.
export const TELEMETRY_CARDS_CAP = 10;

/**
 * Where a user-played free-play move came from (quick 261007-axc): a move played
 * on the board by hand (desktop drag or mobile tap-to-move, both reach the
 * board's onPieceDrop) or a click on a Stockfish engine-line move.
 */
export type ExploreMoveSource = 'board' | 'engine-line';

/** sessionStorage key marking the (session, puzzle) a think timer already started for. */
export const THINK_MARKER_STORAGE_KEY = 'train_think_started';

/** Round, then clamp into [0, cap]. Non-finite input collapses to 0. */
export function clampTelemetryCount(value: number, cap: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(cap, Math.max(0, Math.round(value)));
}

export interface BuildSolveTelemetryInput {
  guessMs: number | null;
  moveMs: number | null;
  thinkHiddenMs: number | null;
  client: TelemetryClient;
  resumed: boolean;
}

/**
 * Build the solve patch. `v`, `client` and `resumed` are always present so a
 * row from this client version is distinguishable from an old one; a null
 * duration omits its key.
 */
export function buildSolveTelemetry(input: BuildSolveTelemetryInput): SolveTelemetry {
  const telemetry: SolveTelemetry = {
    v: TELEMETRY_SCHEMA_VERSION,
    client: input.client,
    resumed: input.resumed,
  };
  if (input.guessMs !== null) {
    telemetry.guess_ms = clampTelemetryCount(input.guessMs, TELEMETRY_DURATION_CAP_MS);
  }
  if (input.moveMs !== null) {
    telemetry.move_ms = clampTelemetryCount(input.moveMs, TELEMETRY_DURATION_CAP_MS);
  }
  if (input.thinkHiddenMs !== null) {
    telemetry.think_hidden_ms = clampTelemetryCount(input.thinkHiddenMs, TELEMETRY_DURATION_CAP_MS);
  }
  return telemetry;
}

/**
 * True when sessionStorage already holds this (session, puzzle) marker, i.e. a
 * reload/remount resumed the puzzle; then writes the marker. Storage failure
 * (private mode) reports false.
 */
export function noteThinkStarted(sessionId: number, position: number): boolean {
  const key = `${sessionId}:${position}`;
  try {
    const already = window.sessionStorage.getItem(THINK_MARKER_STORAGE_KEY) === key;
    window.sessionStorage.setItem(THINK_MARKER_STORAGE_KEY, key);
    return already;
  } catch {
    return false;
  }
}

/** The engagement counters of one reveal (D-14): cumulative totals, never deltas. */
export interface ReviewCounters {
  lineSteps: number;
  /** Every user-played free-play move, board and engine-line alike. */
  exploreMoves: number;
  /** Board moves only (quick 261007-axc), a subset of exploreMoves. */
  boardMoves: number;
  analyzeOpened: boolean;
  walkthrough: boolean;
  /** At least one sideline was forked (D-13): a hand-played move that matches a known line is NOT a fork. */
  forked: boolean;
  /**
   * Distinct chips selected beyond the default You chip (D-12), by tap or by a
   * line-matching move from the puzzle position. Identity stays client-side,
   * only the count is sent (T-237-18).
   */
  chipKeys: ReadonlySet<string>;
  /** The largest number of chips shown on this reveal (a late game chip raises it). */
  chipsTotal: number;
  /** The phone verdict strip was opened at least once (D-12). */
  stripExpanded: boolean;
}

/**
 * Build one review flush body from the stopwatch totals and the engagement
 * counters. Everything is cumulative for the reveal and clamped to its cap. The
 * counter keys are ALWAYS present, so their absence on a row means "older client".
 */
export function buildReviewTelemetry(
  totals: StopwatchTotals,
  counters: ReviewCounters,
  exit: ReviewExit,
): ReviewTelemetry {
  return {
    v: REVIEW_TELEMETRY_SCHEMA_VERSION,
    exit,
    review_ms: clampTelemetryCount(totals.visibleMs, TELEMETRY_DURATION_CAP_MS),
    review_hidden_ms: clampTelemetryCount(totals.hiddenMs, TELEMETRY_DURATION_CAP_MS),
    review_line_steps: clampTelemetryCount(counters.lineSteps, TELEMETRY_LINE_STEPS_CAP),
    // D-13: explored means forked at least one sideline, not "played any move".
    review_explored: counters.forked,
    review_explore_moves: clampTelemetryCount(counters.exploreMoves, TELEMETRY_EXPLORE_MOVES_CAP),
    review_board_moves: clampTelemetryCount(counters.boardMoves, TELEMETRY_EXPLORE_MOVES_CAP),
    review_analyze_opened: counters.analyzeOpened,
    review_walkthrough: counters.walkthrough,
    review_chips_selected: clampTelemetryCount(counters.chipKeys.size, TELEMETRY_CARDS_CAP),
    review_chips_total: clampTelemetryCount(counters.chipsTotal, TELEMETRY_CARDS_CAP),
    review_strip_expanded: counters.stripExpanded,
  };
}

/**
 * The review totals already flushed for a reveal, as folded numbers only (never
 * a running timestamp), plus the engagement counters. Persisted in the reveal
 * cache so a restored reveal continues ONE review timer and cumulative counters.
 * The counter fields are optional: an entry written before they existed has none,
 * and legacy v1 fields (card keys) are simply ignored.
 */
export interface ReviewTelemetrySnapshot {
  visibleMs: number;
  hiddenMs: number;
  lineSteps?: number;
  exploreMoves?: number;
  boardMoves?: number;
  analyzeOpened?: boolean;
  walkthrough?: boolean;
  forked?: boolean;
  chipKeys?: string[];
  chipsTotal?: number;
  stripExpanded?: boolean;
}

function isAbsentOrCount(value: unknown): boolean {
  return value === undefined || (typeof value === 'number' && Number.isFinite(value) && value >= 0);
}

function isAbsentOrStringArray(value: unknown): boolean {
  return value === undefined || (Array.isArray(value) && value.every((item) => typeof item === 'string'));
}

function isAbsentOrBoolean(value: unknown): boolean {
  return value === undefined || typeof value === 'boolean';
}

/** Guards the sessionStorage seed: finite, non-negative numbers only (T-233-15). */
export function isUsableReviewSnapshot(value: unknown): value is ReviewTelemetrySnapshot {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  const { visibleMs, hiddenMs } = v;
  return (
    typeof visibleMs === 'number' &&
    Number.isFinite(visibleMs) &&
    visibleMs >= 0 &&
    typeof hiddenMs === 'number' &&
    Number.isFinite(hiddenMs) &&
    hiddenMs >= 0 &&
    isAbsentOrCount(v.lineSteps) &&
    isAbsentOrCount(v.exploreMoves) &&
    isAbsentOrCount(v.boardMoves) &&
    isAbsentOrBoolean(v.analyzeOpened) &&
    isAbsentOrBoolean(v.walkthrough) &&
    isAbsentOrBoolean(v.forked) &&
    isAbsentOrStringArray(v.chipKeys) &&
    isAbsentOrCount(v.chipsTotal) &&
    isAbsentOrBoolean(v.stripExpanded)
  );
}
