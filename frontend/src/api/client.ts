import axios from 'axios';
import type {
  BookmarkResponse, BookmarkCreate, BookmarkUpdate,
  BookmarkReorderRequest, TimeSeriesRequest, TimeSeriesResponse
} from '@/types/bookmarks';
import type { RatingHistoryResponse, GlobalStatsResponse } from '@/types/stats';

/**
 * Central Axios instance.
 *
 * Uses relative URLs so the Vite dev-server proxy forwards requests to the
 * FastAPI backend at http://localhost:8000.  In production the same relative
 * paths work because the frontend is served from the same origin as the API.
 */
export const apiClient = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
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
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

// ─── Bookmarks API ────────────────────────────────────────────────────────────

export const bookmarksApi = {
  list: () =>
    apiClient.get<BookmarkResponse[]>('/bookmarks').then(r => r.data),
  create: (data: BookmarkCreate) =>
    apiClient.post<BookmarkResponse>('/bookmarks', data).then(r => r.data),
  updateLabel: (id: number, data: BookmarkUpdate) =>
    apiClient.put<BookmarkResponse>(`/bookmarks/${id}`, data).then(r => r.data),
  remove: (id: number) =>
    apiClient.delete(`/bookmarks/${id}`),
  reorder: (req: BookmarkReorderRequest) =>
    apiClient.put<BookmarkResponse[]>('/bookmarks/reorder', req).then(r => r.data),
};

// ─── Time Series API ──────────────────────────────────────────────────────────

export const timeSeriesApi = {
  fetch: (req: TimeSeriesRequest) =>
    apiClient.post<TimeSeriesResponse>('/analysis/time-series', req).then(r => r.data),
};

// ─── Stats API ────────────────────────────────────────────────────────────────

export const statsApi = {
  getRatingHistory: (recency: string | null) =>
    apiClient.get<RatingHistoryResponse>('/stats/rating-history', {
      params: recency ? { recency } : {},
    }).then(r => r.data),
  getGlobalStats: (recency: string | null) =>
    apiClient.get<GlobalStatsResponse>('/stats/global', {
      params: recency ? { recency } : {},
    }).then(r => r.data),
};
