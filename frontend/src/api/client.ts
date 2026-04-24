import axios from 'axios';
import { queryClient } from '@/lib/queryClient';
import type {
  PositionBookmarkResponse, PositionBookmarkCreate, PositionBookmarkUpdate,
  PositionBookmarkReorderRequest, TimeSeriesRequest, TimeSeriesResponse,
  MatchSideUpdateRequest
} from '@/types/position_bookmarks';
import type { RatingHistoryResponse, GlobalStatsResponse, MostPlayedOpeningsResponse } from '@/types/stats';
import type { EndgameGamesResponse, EndgameOverviewResponse } from '@/types/endgames';

/**
 * Central Axios instance.
 *
 * Uses relative URLs so the Vite dev-server proxy forwards requests to the
 * FastAPI backend at http://localhost:8000.  In production the same relative
 * paths work because the frontend is served from the same origin as the API.
 */
export const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  // FastAPI expects repeated keys for array params (e.g. time_control=blitz&time_control=rapid),
  // not bracket notation (time_control[]=blitz) which is axios's default.
  // Bug fix: without this, array query params like time_control and platform were silently
  // ignored by the backend, causing filters to have no effect on GET endpoints.
  paramsSerializer: {
    indexes: null,
  },
});

// ─── Request interceptor: attach Bearer token ─────────────────────────────

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ─── Response interceptor: handle 401 ────────────────────────────────────

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401
    ) {
      const onLoginPage = window.location.pathname === '/login';
      const isAuthRoute = (error.config?.url ?? '').startsWith('/api/auth/');

      if (!onLoginPage && !isAuthRoute) {
        queryClient.clear();
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

// ─── Filter Params Builder ────────────────────────────────────────────────────

/** Build query params object from standard filter parameters, omitting empty/default values. */
export function buildFilterParams(params: {
  time_control?: string[] | null;
  platform?: string[] | null;
  recency?: string | null;
  rated?: boolean | null;
  opponent_type?: string;
  opponent_strength?: string;
  window?: number;
}): Record<string, string | string[] | number | boolean> {
  const result: Record<string, string | string[] | number | boolean> = {};
  if (params.time_control) result.time_control = params.time_control;
  if (params.platform) result.platform = params.platform;
  if (params.recency && params.recency !== 'all') result.recency = params.recency;
  if (params.rated !== null && params.rated !== undefined) result.rated = params.rated;
  if (params.opponent_type && params.opponent_type !== 'all') result.opponent_type = params.opponent_type;
  if (params.opponent_strength && params.opponent_strength !== 'any') result.opponent_strength = params.opponent_strength;
  if (params.window) result.window = params.window;
  return result;
}

// ─── Position Bookmarks API ───────────────────────────────────────────────────

export const positionBookmarksApi = {
  list: () =>
    apiClient.get<PositionBookmarkResponse[]>('/position-bookmarks').then(r => r.data),
  create: (data: PositionBookmarkCreate) =>
    apiClient.post<PositionBookmarkResponse>('/position-bookmarks', data).then(r => r.data),
  updateLabel: (id: number, data: PositionBookmarkUpdate) =>
    apiClient.put<PositionBookmarkResponse>(`/position-bookmarks/${id}`, data).then(r => r.data),
  remove: (id: number) =>
    apiClient.delete(`/position-bookmarks/${id}`),
  reorder: (req: PositionBookmarkReorderRequest) =>
    apiClient.put<PositionBookmarkResponse[]>('/position-bookmarks/reorder', req).then(r => r.data),
  updateMatchSide: (id: number, data: MatchSideUpdateRequest) =>
    apiClient.patch<PositionBookmarkResponse>(`/position-bookmarks/${id}/match-side`, data).then(r => r.data),
};

// ─── Time Series API ──────────────────────────────────────────────────────────

export const timeSeriesApi = {
  fetch: (req: TimeSeriesRequest) =>
    apiClient.post<TimeSeriesResponse>('/openings/time-series', req).then(r => r.data),
};

// ─── Stats API ────────────────────────────────────────────────────────────────

export const statsApi = {
  getRatingHistory: (
    recency: string | null,
    platform: string | null,
    opponentType: string,
    opponentStrength: string,
  ) =>
    apiClient.get<RatingHistoryResponse>('/stats/rating-history', {
      params: buildFilterParams({
        recency,
        platform: platform ? [platform] : null,
        opponent_type: opponentType,
        opponent_strength: opponentStrength,
      }),
    }).then(r => r.data),

  getGlobalStats: (
    recency: string | null,
    platform: string | null,
    opponentType: string,
    opponentStrength: string,
  ) =>
    apiClient.get<GlobalStatsResponse>('/stats/global', {
      params: buildFilterParams({
        recency,
        platform: platform ? [platform] : null,
        opponent_type: opponentType,
        opponent_strength: opponentStrength,
      }),
    }).then(r => r.data),

  getMostPlayedOpenings: (params?: {
    recency?: string | null;
    time_control?: string[] | null;
    platform?: string[] | null;
    rated?: boolean | null;
    opponent_type?: string;
    opponent_strength?: string;
  }) =>
    apiClient.get<MostPlayedOpeningsResponse>('/stats/most-played-openings', {
      params: buildFilterParams(params ?? {}),
    }).then(r => r.data),
};

// ─── Endgame Analytics API ────────────────────────────────────────────────────

// No color parameter passed — endgame stats are color-agnostic per D-02.
export const endgameApi = {
  getOverview: (params: {
    time_control?: string[] | null;
    platform?: string[] | null;
    recency?: string | null;
    rated?: boolean | null;
    opponent_type?: string;
    opponent_strength?: string;
    window?: number;
  }) =>
    apiClient.get<EndgameOverviewResponse>('/endgames/overview', {
      params: buildFilterParams(params),
    }).then(r => r.data),

  getGames: (params: {
    endgame_class: string;
    time_control?: string[] | null;
    platform?: string[] | null;
    recency?: string | null;
    rated?: boolean | null;
    opponent_type?: string;
    opponent_strength?: string;
    offset?: number;
    limit?: number;
  }) =>
    apiClient.get<EndgameGamesResponse>('/endgames/games', {
      params: {
        endgame_class: params.endgame_class,
        ...buildFilterParams(params),
        offset: params.offset ?? 0,
        limit: params.limit ?? 20,
      },
    }).then(r => r.data),
};
