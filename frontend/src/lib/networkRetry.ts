import axios, { AxiosError } from 'axios';

/** How many times a mutation is repeated after its first attempt failed on a dropped connection. */
export const MAX_NETWORK_RETRIES = 2;

/**
 * TanStack Query `retry` predicate: repeat a request only when the connection itself dropped.
 *
 * FLAWCHESS-24: a phone's dropped connection failed the whole Train session load or solve save
 * on the first blip, and each failure became a Sentry event. Only `ERR_NETWORK` qualifies,
 * because any other failure (an HTTP status, a timeout such as `ECONNABORTED`, a plain Error)
 * is an answer or a hang that a repeat would not fix. `failureCount` is 0 on the first failure,
 * so the cap allows at most `MAX_NETWORK_RETRIES` repeats (3 requests in all).
 *
 * Callers must be safe to repeat: the request may already have reached the server.
 */
export function retryOnNetworkError(failureCount: number, error: unknown): boolean {
  return (
    axios.isAxiosError(error) &&
    error.code === AxiosError.ERR_NETWORK &&
    failureCount < MAX_NETWORK_RETRIES
  );
}
