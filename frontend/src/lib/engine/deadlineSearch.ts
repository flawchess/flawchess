/**
 * deadlineSearch — a `SearchRunner` wrapper that cuts an in-flight search at
 * a wall-clock deadline and returns its best-so-far snapshot.
 *
 * The frozen engine core (`mctsSearch.ts`, `selectBotMove.ts`,
 * `botBudget.ts`'s calibrated constants) is untouched by this module. The
 * deadline is enforced entirely from OUTSIDE, by wrapping any `SearchRunner`
 * (mctsSearch by default) and injecting it through `selectBotMove`'s existing
 * `BotMoveDeps.search?: SearchRunner` seam — `useBotGame`
 * is the only caller that constructs a `createDeadlineSearch`.
 *
 * TWO DISTINCT ABORT SIGNALS (the load-bearing design of this module):
 * this wrapper creates its OWN inner `AbortController` and passes ITS signal
 * to the base search — never the caller's outer signal directly. That means:
 *   - A deadline cut aborts only the INNER signal, which the caller never
 *     sees. `baseSearch` (mctsSearch's abort-as-graceful-stop loop) falls
 *     through to its own `return buildSnapshot(...)` and this wrapper
 *     resolves normally with that best-so-far snapshot — `selectBotMove`
 *     then argmaxes/samples it and resolves a legal UCI move exactly as if
 *     the search had finished on its own budget. `useBotGame`'s outer
 *     `signal.aborted` check therefore keeps meaning exactly one thing: a
 *     cancel.
 *   - An OUTER abort (resign / new game / unmount / bot flagged) is forwarded
 *     straight to the inner controller, unconditionally and immediately —
 *     never delayed by the node floor below. A cancel is not a
 *     deadline.
 * The two reasons can never be confused because they travel on different
 * signals, not because of a reason tag inspected after the fact.
 *
 * MINIMUM-NODE FLOOR: a deadline that fires before the search tree has
 * expanded any meaningful number of root children would hand `selectBotMove`
 * a degenerate snapshot, which falls through to `fallbackMove` — a RANDOM
 * legal move, silently destroying bot strength while still "working". So a
 * deadline expiring before `BOT_MIN_SEARCH_NODES` nodes have been evaluated
 * does NOT abort immediately: it arms the cut to fire from the next
 * `onSnapshot` that crosses the floor instead, accepting a small overrun
 * rather than a degenerate result. The overrun is bounded in BOTH dispatch
 * modes (`SearchBudget.dispatchMode`), never unbounded:
 *   - ROUND mode: mctsSearch checks its signal per applied expansion inside
 *     a `budget.concurrency`-sized round (mctsSearch.ts's canonical
 *     apply-order loop), so the worst case is one round's worth of
 *     expansions past the floor.
 *   - CONTINUOUS mode: the armed cut fires synchronously inside `onSnapshot`,
 *     i.e. inside the apply that crossed the floor; the drain's next check
 *     sees the aborted inner signal and discards every result still queued,
 *     and the loop returns with in-flight work cancelled. The overrun is at
 *     most the time to apply that one expansion. When the floor was already
 *     met as the deadline fires (the common case) the timer macrotask aborts
 *     directly, the abort wakes a loop that is awaiting a settlement, and the
 *     overrun is zero.
 * If the bot is so low on time that even the floor
 * cannot be reached before its clock empties, it flags — that is
 * intended behavior, not a bug to clamp away.
 */

import type { SearchRunner } from './guardrail';
import type { EngineSnapshot } from './types';
import { mctsSearch } from './mctsSearch';
import { FLAWCHESS_BOT_STOP_RULE } from './botBudget';

/**
 * Minimum-node floor, DERIVED from the shipped bot stop rule's own
 * floor (`botBudget.ts`) rather than re-typed here — a hand-maintained
 * mirror of that number is exactly the desync failure mode botBudget.ts's
 * own module header warns against.
 */
export const BOT_MIN_SEARCH_NODES = FLAWCHESS_BOT_STOP_RULE.minNodes;

/** Options for {@link createDeadlineSearch}. */
export interface DeadlineSearchOptions {
  /** Wall-clock ms budget for this think — typically `computeThinkDeadlineMs` (chessClock.ts). */
  deadlineMs: number;
  /** Node floor gating the cut; defaults to `BOT_MIN_SEARCH_NODES`. */
  minNodes?: number;
  /**
   * The `SearchRunner` to wrap. Defaults to the shipped `mctsSearch` engine
   * core; injectable so tests can drive a controllable stub with fake timers
   * instead of spawning real Stockfish workers / ONNX sessions.
   */
  baseSearch?: SearchRunner;
}

/**
 * Wraps `options.baseSearch` (default `mctsSearch`) with a wall-clock
 * deadline, gated by the node floor, and returns a `SearchRunner` that
 * implements the frozen `guardrail.ts` contract exactly — a drop-in for
 * `BotMoveDeps.search`. See the module header for the full two-signal design.
 */
export function createDeadlineSearch(options: DeadlineSearchOptions): SearchRunner {
  const { deadlineMs, minNodes = BOT_MIN_SEARCH_NODES, baseSearch = mctsSearch } = options;

  return async (rootFen, budget, providers, onSnapshot, outerSignal) => {
    // The INNER signal — this, never `outerSignal`, is what `baseSearch`
    // sees. Deadline cuts abort this one; the caller's signal is untouched
    // by a deadline cut.
    const innerController = new AbortController();
    let deadlineExpired = false;
    let latestNodesEvaluated = 0;

    const cutIfFloorMet = (): void => {
      if (deadlineExpired && latestNodesEvaluated >= minNodes && !innerController.signal.aborted) {
        innerController.abort();
      }
    };

    const wrappedOnSnapshot = (snapshot: EngineSnapshot): void => {
      // Forward every snapshot to the caller unchanged BEFORE recording the
      // node count — the caller's view of the search is never delayed or
      // filtered by this wrapper (Test 5: snapshot pass-through).
      onSnapshot(snapshot);
      latestNodesEvaluated = snapshot.nodesEvaluated;
      cutIfFloorMet();
    };

    const onOuterAbort = (): void => {
      // A cancel is not a deadline — forward it straight through,
      // unconditionally and immediately, never gated by the node floor.
      innerController.abort();
    };

    if (outerSignal.aborted) {
      onOuterAbort();
    } else {
      outerSignal.addEventListener('abort', onOuterAbort);
    }

    const timer = setTimeout(() => {
      deadlineExpired = true;
      cutIfFloorMet();
    }, deadlineMs);

    try {
      return await baseSearch(rootFen, budget, providers, wrappedOnSnapshot, innerController.signal);
    } finally {
      // Always clear the timer and detach the outer listener, on every exit
      // path (deadline cut, cancel, or the fast path where baseSearch
      // finishes on its own) — an un-cleared timer/listener per bot turn
      // would accumulate across a long game.
      clearTimeout(timer);
      outerSignal.removeEventListener('abort', onOuterAbort);
    }
  };
}
