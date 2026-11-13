/**
 * blunderCheckSolutionCache: sessionStorage cache of the blunder-check solution on screen
 * (Phase 249 UAT).
 *
 * Written when the user leaves a solution through its Analyze deep link, so the browser back
 * button lands on the SAME solution instead of the start screen (the personalized-puzzle
 * behaviour, see `trainRevealCache.ts`). The drill reducer lives only in memory and a resumed
 * session opens at the next window, so without this cache the solution is gone once the Train
 * page unmounts.
 *
 * sessionStorage on purpose: a per-tab navigation aid, not durable data. The tab validates
 * `state.session.sessionId` against the caller's open session and drops a mismatch. The entry
 * is cleared as soon as the drill leaves the solution (Next, reset).
 */

import type { DrillState } from '@/lib/blunderCheckDrill';
import type { PersonaId } from '@/lib/personas/personaRegistry';
import { isRevealTreeSnapshot } from '@/lib/trainRevealCache';
import type { RevealTreeSnapshot } from '@/lib/trainRevealLines';

const STORAGE_KEY = 'blunder_check_solution_cache';

type SolutionDrillState = Extract<DrillState, { phase: 'solution' }>;

export interface CachedBlunderCheckSolution {
  /** The whole solution-phase drill state: plain JSON (UCIs, FENs, numbers). */
  state: SolutionDrillState;
  /** The window's host, so the restored solution shows the same bot. */
  personaId: PersonaId;
  /** The focused chip, sidelines and shown node; absent for a solution without lines. */
  revealTree?: RevealTreeSnapshot;
}

export function saveBlunderCheckSolutionCache(cached: CachedBlunderCheckSolution): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(cached));
  } catch {
    // Best-effort: a storage failure only means Back lands on the start screen.
  }
}

export function readBlunderCheckSolutionCache(): CachedBlunderCheckSolution | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw === null) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!isCachedSolution(parsed)) return null;
    // A malformed tree snapshot costs only itself: the solution still restores at its root.
    if (parsed.revealTree !== undefined && !isRevealTreeSnapshot(parsed.revealTree)) {
      const stripped: CachedBlunderCheckSolution = { ...parsed };
      delete stripped.revealTree;
      return stripped;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function clearBlunderCheckSolutionCache(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Best-effort, see saveBlunderCheckSolutionCache.
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/** Shallow shape check: enough to reject a corrupt or foreign payload. */
function isCachedSolution(value: unknown): value is CachedBlunderCheckSolution {
  if (!isRecord(value) || typeof value.personaId !== 'string') return false;
  const state = value.state;
  if (!isRecord(state) || state.phase !== 'solution') return false;
  const { session, window, solution } = state;
  return (
    isRecord(session) &&
    typeof session.sessionId === 'number' &&
    typeof session.windowCount === 'number' &&
    typeof state.sessionPoints === 'number' &&
    isRecord(window) &&
    typeof window.position === 'number' &&
    typeof window.startFen === 'string' &&
    isRecord(solution) &&
    typeof solution.kind === 'string' &&
    typeof solution.fen === 'string' &&
    // The entry is untrusted sessionStorage JSON: a blunder solution must carry the graded
    // moves array the solution board reads.
    (solution.kind !== 'blunder' || Array.isArray(solution.server_graded_moves))
  );
}
