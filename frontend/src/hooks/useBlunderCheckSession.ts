/**
 * useBlunderCheckSession: the open-session query and the drill's seven mutations.
 *
 * Thin transport only. The drill state machine (`lib/blunderCheckDrill.ts`) owns what
 * happens next, and every grade and point total comes from the server (Pitfall 13), so
 * nothing here derives a score. No Sentry calls: the global QueryCache / MutationCache
 * handlers in `lib/queryClient.ts` already report failures (frontend/CLAUDE.md).
 */

import { useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { blunderCheckApi } from '@/api/client';
import { TRAIN_PROGRESS_QUERY_KEY } from '@/hooks/useTrainProgress';
import { RECOVERABLE_CONFLICT_DETAILS } from '@/lib/blunderCheckDrill';
import type {
  AnswerRequest,
  AnswerResponse,
  BetterMoveRequest,
  BetterMoveResponse,
  BlunderCheckSessionResponse,
  SessionResultResponse,
  WindowSolution,
  WindowStartResponse,
} from '@/types/blunderCheck';

const OPEN_SESSION_QUERY_KEY = ['blunder-check', 'open-session'] as const;
/** The drill recovers from these 409s by itself, so they stay out of Sentry (`lib/queryClient.ts`). */
const DRILL_MUTATION_META = { expectedConflictDetails: RECOVERABLE_CONFLICT_DETAILS };

interface WindowRef {
  sessionId: number;
  position: number;
}

interface AnswerVariables extends WindowRef {
  body: AnswerRequest;
}

interface BetterMoveVariables extends WindowRef {
  body: BetterMoveRequest;
}

export function useBlunderCheckSession() {
  const queryClient = useQueryClient();
  // Composing and finishing change the Today card's Blunder Check row (pending, in progress,
  // done) and the nav badge, so both refresh the shared train progress query too.
  const refreshOpenSession = async (): Promise<void> => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: OPEN_SESSION_QUERY_KEY }),
      queryClient.invalidateQueries({ queryKey: TRAIN_PROGRESS_QUERY_KEY }),
    ]);
  };

  // The server's progress right now, bypassing the cache: what the drill resyncs from when
  // another device moved the session on.
  const fetchOpenSession = useCallback(
    (): Promise<BlunderCheckSessionResponse | null> =>
      queryClient.fetchQuery({
        queryKey: OPEN_SESSION_QUERY_KEY,
        queryFn: blunderCheckApi.getOpenSession,
        staleTime: 0,
      }),
    [queryClient],
  );

  const openSession = useQuery<BlunderCheckSessionResponse | null>({
    queryKey: OPEN_SESSION_QUERY_KEY,
    queryFn: blunderCheckApi.getOpenSession,
  });

  const compose = useMutation<BlunderCheckSessionResponse>({
    mutationFn: blunderCheckApi.composeOrResumeSession,
    onSuccess: refreshOpenSession,
  });

  const startWindow = useMutation<WindowStartResponse, Error, WindowRef>({
    mutationFn: ({ sessionId, position }) => blunderCheckApi.startWindow(sessionId, position),
    meta: DRILL_MUTATION_META,
  });

  const beginWindow = useMutation<WindowStartResponse, Error, WindowRef>({
    mutationFn: ({ sessionId, position }) => blunderCheckApi.beginWindow(sessionId, position),
    meta: DRILL_MUTATION_META,
  });

  const answer = useMutation<AnswerResponse, Error, AnswerVariables>({
    mutationFn: ({ sessionId, position, body }) =>
      blunderCheckApi.answer(sessionId, position, body),
    meta: DRILL_MUTATION_META,
  });

  const betterMove = useMutation<BetterMoveResponse, Error, BetterMoveVariables>({
    mutationFn: ({ sessionId, position, body }) =>
      blunderCheckApi.submitBetterMove(sessionId, position, body),
  });

  // A mutation (not a query) so the solution is fetched exactly when the drill asks for it,
  // never cached or refetched in the background (it is only valid once its window ended).
  const solution = useMutation<WindowSolution, Error, WindowRef>({
    mutationFn: ({ sessionId, position }) => blunderCheckApi.getSolution(sessionId, position),
  });

  const finish = useMutation<SessionResultResponse, Error, number>({
    mutationFn: blunderCheckApi.finishSession,
    onSuccess: refreshOpenSession,
  });

  return {
    openSession,
    refreshOpenSession,
    fetchOpenSession,
    compose,
    startWindow,
    beginWindow,
    answer,
    betterMove,
    solution,
    finish,
  };
}
