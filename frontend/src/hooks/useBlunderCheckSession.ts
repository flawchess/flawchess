/**
 * useBlunderCheckSession: the open-session query and the drill's six mutations.
 *
 * Thin transport only. The drill state machine (`lib/blunderCheckDrill.ts`) owns what
 * happens next, and every grade and point total comes from the server (Pitfall 13), so
 * nothing here derives a score. No Sentry calls: the global QueryCache / MutationCache
 * handlers in `lib/queryClient.ts` already report failures (frontend/CLAUDE.md).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { blunderCheckApi } from '@/api/client';
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
  const refreshOpenSession = (): Promise<void> =>
    queryClient.invalidateQueries({ queryKey: OPEN_SESSION_QUERY_KEY });

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
  });

  const answer = useMutation<AnswerResponse, Error, AnswerVariables>({
    mutationFn: ({ sessionId, position, body }) =>
      blunderCheckApi.answer(sessionId, position, body),
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
    compose,
    startWindow,
    answer,
    betterMove,
    solution,
    finish,
  };
}
