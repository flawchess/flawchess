import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import * as Sentry from '@sentry/react';
import axios from 'axios';

/** Upper bound on the `detail` text copied into a Sentry event. FastAPI error
 * bodies are small, but a proxy/CDN can substitute an arbitrarily long HTML
 * error page — this keeps one bad response from bloating every event. */
const MAX_CAPTURED_DETAIL_LENGTH = 500;

/**
 * Extracts the FastAPI `detail` field from an error response body.
 *
 * ONLY `detail` is read — never the whole body. An error body is the one part
 * of a response guaranteed to be about the failure rather than about the user,
 * so this stays clear of shipping user data into Sentry (CLAUDE.md Sentry
 * rules). A dict detail (e.g. `POST /bots/games`' `{reason, message}`) is
 * JSON-stringified so its reason code survives into the event.
 */
function extractResponseDetail(data: unknown): string | undefined {
  if (typeof data !== 'object' || data === null || !('detail' in data)) return undefined;
  const { detail } = data as { detail: unknown };
  if (detail === undefined || detail === null) return undefined;
  const text = typeof detail === 'string' ? detail : JSON.stringify(detail);
  return text.slice(0, MAX_CAPTURED_DETAIL_LENGTH);
}

/**
 * Sentry `extra` describing an axios failure: status, method, path, and the
 * server's own `detail`.
 *
 * WHY (FLAWCHESS-64): a bare `AxiosError: Request failed with status code 422`
 * carries no clue as to WHICH validation rule the server applied, so every
 * rejection of a given endpoint grouped into one indistinguishable issue and
 * the cause had to be inferred from the code. Returns `{}` for a non-axios
 * error so the caller can spread it unconditionally.
 */
export function axiosErrorExtra(error: unknown): Record<string, unknown> {
  if (!axios.isAxiosError(error)) return {};
  const detail = extractResponseDetail(error.response?.data);
  return {
    httpStatus: error.response?.status,
    httpMethod: error.config?.method?.toUpperCase(),
    httpUrl: error.config?.url,
    ...(detail === undefined ? {} : { responseDetail: detail }),
  };
}

declare module '@tanstack/react-query' {
  interface Register {
    mutationMeta: {
      /** 409 `detail` values the caller recovers from by itself (never reported to Sentry). */
      expectedConflictDetails?: readonly string[];
    };
  }
}

const HTTP_CONFLICT = 409;

/**
 * Whether a mutation failure is a 409 its caller declared as expected and handles itself.
 *
 * WHY (FLAWCHESS-DJ): a blunder-check session played on two devices answers 409 to the
 * device that fell behind. The drill resyncs from the server, so the 409 is a normal outcome
 * and reporting it would only add noise.
 */
export function isExpectedConflict(
  error: unknown,
  expectedDetails: readonly string[] | undefined,
): boolean {
  if (expectedDetails === undefined) return false;
  if (!axios.isAxiosError(error) || error.response?.status !== HTTP_CONFLICT) return false;
  const detail = extractResponseDetail(error.response.data);
  return detail !== undefined && expectedDetails.includes(detail);
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      Sentry.captureException(error, {
        tags: { source: 'tanstack-query' },
        extra: { queryKey: query.queryKey, ...axiosErrorExtra(error) },
      });
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      if (isExpectedConflict(error, mutation.options.meta?.expectedConflictDetails)) return;
      Sentry.captureException(error, {
        tags: { source: 'tanstack-mutation' },
        extra: { mutationKey: mutation.options.mutationKey, ...axiosErrorExtra(error) },
      });
    },
  }),
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});
