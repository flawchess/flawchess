/**
 * guardrail — the frozen `SearchRunner` type (ENGINE-06 / D-06).
 *
 * `mctsSearch` (the primary orchestrator) and `fallbackExpectimax` (the
 * guardrail's backup path) both implement this EXACT function type with no
 * call-site differences — `useFlawChessEngine.ts` (Phase 155) imports
 * exactly one of them behind this single signature. This module intentionally
 * contains no logic, only the type.
 */

import type { SearchBudget, EngineProviders, EngineSnapshot } from './types';

export type SearchRunner = (
  rootFen: string,
  budget: SearchBudget,
  providers: EngineProviders,
  onSnapshot: (snapshot: EngineSnapshot) => void,
  signal: AbortSignal,
) => Promise<EngineSnapshot>;
