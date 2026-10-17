/**
 * types — the frozen public contract of the pure search core.
 *
 * These types are shared by every search consumer and change only
 * deliberately. Their shapes encode these decisions:
 *   - The root-only extra-move union with Maia top-k.
 *   - `practicalScore`/`RankedLine` are root-side-to-move expected
 *     score (0-1), never a per-node/per-ply-relative value.
 *   - ELO is color-keyed ({w, b}), never self/opponent-keyed.
 *   - The engine core speaks UCI everywhere (moves, policy keys,
 *     grade keys, paths) and side-to-move is the FEN 'w'/'b' literal.
 *   - One node = one expansion event (the unit `maxNodes` counts).
 */

import type { MoveGrade } from '@/lib/moveQuality';

// Re-exported so the engine core has a single import surface for move
// grading — do NOT redeclare a structurally-duplicate interface here.
export type { MoveGrade };

/** FEN side-to-move literal — 'w' or 'b', never a full-word color. */
export type Side = 'w' | 'b';

/** Provider surface for the search core: test fakes or the real Maia and Stockfish workers. */
export interface EngineProviders {
  /**
   * UCI-keyed Maia move-probability distribution at `elo` for `side` to move.
   * `signal` is OPTIONAL, following `grade`'s own precedent
   * below — every existing 3-parameter implementation (test fakes, the
   * `selectBotMove`/`openingBook` deps, and the Node calibration providers
   * outside the frontend `tsc` project) stays structurally assignable to this
   * interface. Only requests `maiaQueue`'s `policy()` has not yet dispatched
   * to the shared worker are dropped on abort; an in-flight ONNX inference is
   * not interruptible and runs to completion regardless.
   */
  policy(fen: string, elo: number, side: Side, signal?: AbortSignal): Promise<Record<string, number>>;
  /**
   * UCI-keyed Stockfish shallow-eval grades for the candidate UCI moves,
   * white-POV cp. `signal` is OPTIONAL so a
   * two-argument implementation/call site stays structurally assignable to
   * this interface — widening it to required would break every existing
   * fabricated-in-tests provider and the Node calibration providers outside
   * the frontend `tsc` project.
   */
  grade(fen: string, candidateUcis: string[], signal?: AbortSignal): Promise<Map<string, MoveGrade>>;
  /**
   * Root-only grade fan-out: same contract as `grade`, but
   * implemented by a caller that can split the request across multiple idle
   * workers/engines below this boundary (`rootSplit.ts`'s
   * `partitionCandidates`/`mergeShardGrades`) — the fan-out itself is never
   * visible here. OPTIONAL, following `grade`'s own `signal` precedent
   * above: every existing provider (test fakes, `fallbackExpectimax`, and
   * any caller that never sets this) stays structurally assignable to this
   * interface and behaves byte-identically, since `mctsSearch.ts`'s
   * `dispatchExpansion` falls back to `grade` whenever `gradeRoot` is
   * absent. Round 1 of a search is exactly the root expansion
   * (`selectPath`'s root-pending guard), so `gradeRoot` — when present — is
   * called at most once per search, and only for the root.
   */
  gradeRoot?(fen: string, candidateUcis: string[], signal?: AbortSignal): Promise<Map<string, MoveGrade>>;
}

/**
 * Bot-play early-stop knobs — evaluated in the
 * `mctsSearch` canonical apply-order loop against `root.children`'s own
 * `.value` fields (== `RankedLine.practicalScore`), never the findability-
 * sorted `buildRankedLines` output. Optional on `SearchBudget`; `undefined`
 * skips the stop-rule check entirely (today's unchanged full-budget
 * behavior for every existing caller — the analysis board never sets this).
 */
export interface BotStopRule {
  /** Clear-winner margin the top root child's `.value` must lead the runner-up by. */
  marginThreshold: number;
  /** Near-tie-flatness spread ceiling across ALL current root children's `.value`s. */
  epsilonThreshold: number;
  /** Consecutive post-expansion checks the argmax UCI must hold stable before either side of the rule can fire. */
  stabilityWindow: number;
  /** Shared floor gating BOTH the clear-winner and near-tie-flatness checks — neither fires before this many expansions. */
  minNodes: number;
  /**
   * The extra value gap beyond `marginThreshold` within
   * which a root child that is neither visited nor closed blocks the
   * clear-winner branch — it sizes the guard set only and never enters a
   * value. Measured in `reports/engine-search-fixes-225/d02-allowance.md`.
   * Required (not optional) so any `BotStopRule` literal that omits it is a
   * `tsc -b` error — an accidentally-omitted allowance
   * would silently reintroduce the root-comparability bug.
   */
  rootGuardBoostAllowance: number;
}

/**
 * Which dispatch loop `mctsSearch` runs. `'round'` is the
 * existing barrier loop (fill up to `concurrency` expansions, `Promise.all`,
 * apply in canonical order). `'continuous'` is asynchronous dispatch with
 * pending exclusion and arrival-order apply under the relaxed, statistical
 * determinism contract (expected score within a tolerance, checked statistically, not bit-identity).
 */
export type DispatchMode = 'round' | 'continuous';

/** Bounds one `SearchRunner` invocation. */
export interface SearchBudget {
  /** One node = one expansion event; the unit this budget counts. */
  maxNodes: number;
  /** Color-keyed ELO, never self/opponent-keyed. */
  elo: { w: number; b: number };
  /** Locked 6-10 ply band. */
  maxPlies: number;
  /** In-flight expansion concurrency, >=1. */
  concurrency: number;
  /** Root-only UCI moves unioned with Maia top-k at the root. */
  extraRootMoves?: string[];
  /** Reshapes the user's-side policy before truncation; omitted/1 = no-op. */
  policyTemperature?: number;
  /** Optional bot-play early-stop rule; omitted/undefined = today's unchanged full-budget behavior. */
  stopRule?: BotStopRule;
  /**
   * Dispatch loop selector. Omitted/undefined = `'round'`,
   * the byte-identical barrier loop, so every existing caller, test and
   * fixture gate is unchanged with zero edits. `'continuous'` = asynchronous
   * dispatch with pending exclusion and arrival-order apply under the relaxed,
   * statistical contract (see `DispatchMode`).
   */
  dispatchMode?: DispatchMode;
}

/**
 * Per-ply display stats for one move in a line's `modalPath`, index-aligned
 * with it (`modalStats[i]` describes `modalPath[i]`). Surfaced for the
 * move-chip hover preview so each miniboard can annotate the position it
 * shows; NOT consumed by the search itself. Both fields are read straight off
 * the search-tree node the modal path walks through.
 */
export interface ModalPlyStat {
  /** White-POV Stockfish eval (cp) of the position AFTER this move, if graded. */
  objectiveEvalCp: number | null;
  /**
   * White-POV Stockfish mate distance of the position AFTER this move, if the
   * grade was a forced mate (e.g. -4 for "mate in 4 against the mover"). Carried
   * alongside `objectiveEvalCp` so a forced-mate leaf renders `#-4` instead of the
   * `…` placeholder a null cp would print. Mutually exclusive with a
   * non-null `objectiveEvalCp` — exactly one is set for a graded position.
   */
  objectiveEvalMate: number | null;
  /**
   * Raw Maia policy probability (0-1) of this move at its parent position —
   * the un-truncated, un-temperature-reshaped value, so it matches the raw
   * Maia % shown in the prose move popovers rather than the search's
   * renormalized `prior`.
   */
  maiaProb: number | null;
}

/** One ranked root candidate line in an `EngineSnapshot`. */
export interface RankedLine {
  /** The root candidate move, UCI. */
  rootMove: string;
  /** Root-side-to-move expected score, 0-1 — never per-ply-relative. */
  practicalScore: number;
  /** Objective white-POV Stockfish eval (cp) of the root candidate (the position after `rootMove`), if graded. */
  objectiveEvalCp: number | null;
  /**
   * Objective white-POV Stockfish mate distance at the root candidate, when the
   * grade is a forced mate (e.g. -4). Set instead of `objectiveEvalCp` for a
   * mate leaf so the FlawChess card + agreement verdict can render `#-4` rather
   * than the `…` a null cp would print.
   */
  objectiveEvalMate: number | null;
  /**
   * The line's most-visited continuation, UCI sequence.
   * Constructed as a LAZY accessor property (a getter, not a data
   * property) — computed only on first read, memoized thereafter. TypeScript
   * cannot distinguish an accessor from a data property in this type
   * declaration, so this comment is the only signal a future editor gets:
   * spreading (`{ ...line }`), `structuredClone`-ing, or otherwise cloning a
   * `RankedLine` FORCES this getter to evaluate immediately, defeating the
   * laziness this field exists for. Copy property DESCRIPTORS
   * (`Object.getOwnPropertyDescriptors`), never spread, when building a
   * derived `RankedLine` — see `botStyle.ts`'s `applyStyleScoreShaping`.
   */
  modalPath: string[];
  /**
   * Per-ply display stats index-aligned with `modalPath`.
   * Same lazy-accessor caveat as `modalPath` above — shares ONE
   * memoized computation with it, so reading both costs exactly one
   * `buildModalPath` call, not two. Never spread a `RankedLine`.
   */
  modalStats: ModalPlyStat[];
  /** Total expansion visits attributed to this root candidate. */
  visits: number;
  /**
   * Variance/"sharpness" proxy for this root candidate: the
   * max−min spread across the candidate's OWN children's backed-up expected
   * scores (i.e. the grandchildren of the search root) — the per-candidate
   * signal the variance-preference style lever reads. `null` when the
   * candidate has 0 or 1 own children (no meaningful spread to report; never
   * 0-as-a-signal for that empty case). Only comparable within a single
   * `SearchBudget.concurrency` level — differing concurrency can grow
   * different subtrees under the same root candidate, so values are not
   * meant to be compared across concurrency settings.
   */
  childScoreSpread: number | null;
}

/** The output a `SearchRunner` reports — both at completion and per `onSnapshot` tick. */
export interface EngineSnapshot {
  rankedLines: RankedLine[];
  /** Count of expansion events consumed so far. */
  nodesEvaluated: number;
  /** True once `SearchBudget.maxNodes`/`maxPlies` stopped the search (not an abort). */
  budgetExhausted: boolean;
  /**
   * Why the search stopped, as a sibling of
   * `budgetExhausted` (never overloading that boolean, which stays
   * maxNodes/maxPlies-only). `'early-stop'` when `SearchBudget.stopRule`
   * ended the search early, `'budget'` when maxNodes/maxPlies did, `null`
   * otherwise (natural tree completion, or an abort).
   */
  stopReason: 'budget' | 'early-stop' | null;
}
