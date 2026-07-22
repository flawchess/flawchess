/**
 * useBotPersonaWins — fetches the per-persona win counts for the
 * authenticated user (Phase 185, `GET /bots/persona-wins`). Mirrors
 * `useUserProfile.ts`'s shape exactly: one `useQuery` call, 5-minute
 * `staleTime` (win counts only change on game-finish).
 *
 * Called ONCE at `Bots.tsx` page level and prop-drilled through
 * `PersonaGrid` -> `PersonaCard` (single-fetch-then-prop-drill, Pattern 3) —
 * never called from either of those components directly, which would break
 * their existing no-`QueryClientProvider` render tests.
 *
 * CR-01: `BOT_PERSONA_WINS_QUERY_KEY` is exported so the store-on-finish call
 * sites (`Bots.tsx`'s finish-time store effect, `useStoreBotGame.ts`'s
 * `useDrainPendingStore`) can `queryClient.invalidateQueries()` this EXACT
 * key on a successful store — without it, this query's 5-minute `staleTime`
 * meant the win stars on `PersonaCard` never refreshed after a persona game
 * in the normal finish -> "New game" -> back-to-roster flow (only a hard
 * reload or the 5-minute window forced a refetch).
 */

import { useQuery } from '@tanstack/react-query';
import { botsApi } from '@/api/client';
import type { PersonaWinsResponse } from '@/types/bots';

export const BOT_PERSONA_WINS_QUERY_KEY = ['botPersonaWins'] as const;

export function useBotPersonaWins() {
  return useQuery<PersonaWinsResponse>({
    queryKey: BOT_PERSONA_WINS_QUERY_KEY,
    // WR-02: call the existing `botsApi.getPersonaWins` rather than
    // re-implementing the same `apiClient.get` call inline — the duplicate
    // was dead code invisible to knip (an object-literal property, not a
    // bare module export) and a maintenance trap (two implementations of the
    // same endpoint call that could silently diverge).
    queryFn: () => botsApi.getPersonaWins(),
    staleTime: 300_000, // 5 minutes
  });
}
