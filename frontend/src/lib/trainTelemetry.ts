/**
 * trainTelemetry.ts — Phase 233 per-puzzle telemetry constants and builders.
 *
 * The two numeric constants mirror app/schemas/train.py and are CI-locked by
 * tests/schemas/test_train_telemetry_parity.py. Keep them plain integer
 * literals (the parity test reads `export const NAME = <digits>;` by regex).
 * Telemetry is a recorded outcome only; it never feeds grading or scoring (D-05).
 */

import type { ReviewExit, ReviewTelemetry, SolveTelemetry, TelemetryClient } from '@/types/train';
import type { StopwatchTotals } from '@/lib/visibleStopwatch';

// Mirrors app/schemas/train.py TELEMETRY_SCHEMA_VERSION, guarded by tests/schemas/test_train_telemetry_parity.py.
export const TELEMETRY_SCHEMA_VERSION = 1;

// 30 minutes (D-04). Mirrors app/schemas/train.py TELEMETRY_DURATION_CAP_MS, guarded by tests/schemas/test_train_telemetry_parity.py.
export const TELEMETRY_DURATION_CAP_MS = 1800000;

// 50 line-stepper clicks (D-14). Mirrors app/schemas/train.py TELEMETRY_LINE_STEPS_CAP, guarded by tests/schemas/test_train_telemetry_parity.py.
export const TELEMETRY_LINE_STEPS_CAP = 50;

// 50 free-play moves (D-14). Mirrors app/schemas/train.py TELEMETRY_EXPLORE_MOVES_CAP, guarded by tests/schemas/test_train_telemetry_parity.py.
export const TELEMETRY_EXPLORE_MOVES_CAP = 50;

// 10 cards (D-12): the line boxes plus Also-fine never exceed this. Mirrors app/schemas/train.py TELEMETRY_CARDS_CAP, guarded by tests/schemas/test_train_telemetry_parity.py.
export const TELEMETRY_CARDS_CAP = 10;

// D-11: a desktop hover shorter than this is a pointer fly-over on the way to
// Next, not engagement. Frontend-only (the server never sees the hover), so it
// is not mirrored.
export const REVIEW_CARD_HOVER_MIN_MS = 800;

/** How a reveal card was engaged: a tap/click that opens it, or a desktop hover span. */
export type CardEngageKind = 'open' | 'hover-start' | 'hover-end';

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
  exploreMoves: number;
  analyzeOpened: boolean;
  walkthrough: boolean;
  /** Distinct cards opened (D-11/D-12); identity stays client-side, only the count is sent. */
  cardKeys: ReadonlySet<string>;
  /** The largest number of cards (line boxes plus Also-fine) shown on this reveal. */
  cardsTotal: number;
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
    v: TELEMETRY_SCHEMA_VERSION,
    exit,
    review_ms: clampTelemetryCount(totals.visibleMs, TELEMETRY_DURATION_CAP_MS),
    review_hidden_ms: clampTelemetryCount(totals.hiddenMs, TELEMETRY_DURATION_CAP_MS),
    review_line_steps: clampTelemetryCount(counters.lineSteps, TELEMETRY_LINE_STEPS_CAP),
    review_explored: counters.exploreMoves > 0,
    review_explore_moves: clampTelemetryCount(counters.exploreMoves, TELEMETRY_EXPLORE_MOVES_CAP),
    review_analyze_opened: counters.analyzeOpened,
    review_walkthrough: counters.walkthrough,
    review_cards_opened: clampTelemetryCount(counters.cardKeys.size, TELEMETRY_CARDS_CAP),
    review_cards_total: clampTelemetryCount(counters.cardsTotal, TELEMETRY_CARDS_CAP),
  };
}

/**
 * The review totals already flushed for a reveal, as folded numbers only (never
 * a running timestamp), plus the engagement counters. Persisted in the reveal
 * cache so a restored reveal continues ONE review timer and cumulative counters.
 * The counter fields are optional: an entry written before they existed has none.
 */
export interface ReviewTelemetrySnapshot {
  visibleMs: number;
  hiddenMs: number;
  lineSteps?: number;
  exploreMoves?: number;
  analyzeOpened?: boolean;
  walkthrough?: boolean;
  cardKeys?: string[];
  cardsTotal?: number;
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
    isAbsentOrBoolean(v.analyzeOpened) &&
    isAbsentOrBoolean(v.walkthrough) &&
    isAbsentOrStringArray(v.cardKeys) &&
    isAbsentOrCount(v.cardsTotal)
  );
}
