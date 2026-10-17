/**
 * useBotPersonaWins — fetches the per-persona win counts for the
 * authenticated user (`GET /bots/persona-wins`). Mirrors
 * `useUserProfile.ts`'s shape exactly: one `useQuery` call, 5-minute
 * `staleTime` (win counts only change on game-finish).
 *
 * Called ONCE at `Bots.tsx` page level and prop-drilled through
 * `PersonaGrid` -> `PersonaCard` (single fetch, then prop-drill) — never
 * called from either of those components directly, which would break their
 * existing no-`QueryClientProvider` render tests.
 *
 * `BOT_PERSONA_WINS_QUERY_KEY` is exported so the store-on-finish call sites
 * (`Bots.tsx`'s finish-time store effect, `useStoreBotGame.ts`'s
 * `useDrainPendingStore`) can `queryClient.invalidateQueries()` this EXACT
 * key on a successful store. Without it, this query's 5-minute `staleTime`
 * keeps the win stars on `PersonaCard` stale after a persona game in the
 * normal finish -> "New game" -> back-to-roster flow (only a hard reload or
 * the 5-minute window would force a refetch).
 */

import { useQuery } from '@tanstack/react-query';
import { botsApi } from '@/api/client';
import type { PersonaWinsResponse } from '@/types/bots';

export const BOT_PERSONA_WINS_QUERY_KEY = ['botPersonaWins'] as const;

export function useBotPersonaWins() {
  return useQuery<PersonaWinsResponse>({
    queryKey: BOT_PERSONA_WINS_QUERY_KEY,
    queryFn: () => botsApi.getPersonaWins(),
    staleTime: 300_000, // 5 minutes
  });
}
