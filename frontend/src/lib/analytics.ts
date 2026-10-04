/**
 * Umami custom-event helper.
 *
 * Prefer the plain `data-umami-event` attribute wherever it works: the tracker
 * binds `<button>` elements and outbound `<a target="_blank">` links itself,
 * with no code.
 *
 * Use this helper for INTERNAL react-router links. On an `<a href>` without
 * `target="_blank"` umami calls `preventDefault()` and then assigns
 * `location.href` itself, which downgrades a client-side navigation into a
 * full page reload — so the attribute must never go on a `<Link>`.
 *
 * No-ops when the tracker is absent (local dev, ad blockers, the
 * `data-domains` gate), so callers never need to guard.
 */
import { consumeAutoReloadMarker } from '@/lib/autoReload';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { BotSetupSettings } from '@/lib/botSetupSettings';
import type { TimeControlPresetLabel } from '@/lib/botTimeControlPresets';
import type { PlayStylePreset } from '@/lib/playStyle';
import type { TacticFamily } from '@/lib/tacticComparisonMeta';
import type { TacticDepthPreset } from '@/lib/tacticDepth';
import type {
  MatchSide,
  OpponentStrengthPreset,
  OpponentType,
  Platform,
  RecencyPreset,
  TimeControl,
} from '@/types/api';
import type { EndgameClass } from '@/types/endgames';
import type { FlawSeverity, FlawTag, TacticOrientation } from '@/types/library';

/** The subset of an outgoing tracker payload this module rewrites. */
interface UmamiPayload {
  url?: string;
  referrer?: string;
  [key: string]: unknown;
}

declare global {
  interface Window {
    umami?: {
      track: (eventName: string, eventData?: Record<string, string>) => void;
      identify: (distinctId: string, data?: Record<string, string>) => void;
    };
    /** Named by `data-before-send` on the tracker tag in index.html. Null cancels the send. */
    umamiBeforeSend?: (type: string, payload: UmamiPayload) => UmamiPayload | null;
  }
}

export function trackEvent(eventName: string, eventData?: Record<string, string>): void {
  window.umami?.track(eventName, eventData);
}

/**
 * Query params that carry credentials. /auth/reset-password?token=<reset JWT>
 * was stored verbatim in website_event.url_query (and in the next pageview's
 * referrer). `data-exclude-search` would also drop the utm_* tags, so the
 * params are removed one by one instead. Fragments (`#token=`) are already
 * dropped by `data-exclude-hash`.
 */
const SENSITIVE_QUERY_PARAMS: readonly string[] = ['token'];

/**
 * The Google OAuth round trip returns through accounts.google.* (any ccTLD), so
 * every Google sign-in was recorded as a pageview referred by it, making it the
 * top "referrer" and hiding the real acquisition sources.
 */
const OAUTH_REFERRER_HOST = /^accounts\.google\.[a-z.]+$/;

function stripSensitiveParams(value: string): string {
  if (!value) return value;
  try {
    // Internal referrers arrive origin-stripped ("/auth/..."): keep them relative.
    const isRelative = value.startsWith('/');
    const url = new URL(value, window.location.origin);
    const present = SENSITIVE_QUERY_PARAMS.filter((param) => url.searchParams.has(param));
    if (present.length === 0) return value;
    present.forEach((param) => url.searchParams.delete(param));
    return isRelative ? `${url.pathname}${url.search}${url.hash}` : url.toString();
  } catch {
    return value;
  }
}

function isOAuthReferrer(referrer: string): boolean {
  if (!referrer || referrer.startsWith('/')) return false;
  try {
    return OAUTH_REFERRER_HOST.test(new URL(referrer).hostname.toLowerCase());
  } catch {
    return false;
  }
}

/** Rewrite every outgoing tracker payload (pageviews, events, identify). */
export function scrubUmamiPayload(_type: string, payload: UmamiPayload): UmamiPayload {
  const scrubbed: UmamiPayload = { ...payload };
  if (typeof scrubbed.url === 'string') scrubbed.url = stripSensitiveParams(scrubbed.url);
  if (typeof scrubbed.referrer === 'string') {
    scrubbed.referrer = isOAuthReferrer(scrubbed.referrer) ? '' : stripSensitiveParams(scrubbed.referrer);
  }
  return scrubbed;
}

/** The tracker sends pageviews as type 'event' without a name; custom events carry one. */
function isPageview(type: string, payload: UmamiPayload): boolean {
  return type === 'event' && payload.name === undefined;
}

/**
 * Quick 261004-rmc: set at boot when this page load came from an automatic
 * reload (see autoReload.ts); its landing pageview is a duplicate. Consumed at
 * boot rather than at send time so a marker left behind by a blocked tracker
 * can never swallow a later, real pageview.
 */
let dropLandingPageview = false;

/** The installed hook: drop an automatic reload's landing pageview, scrub everything else. */
export function umamiBeforeSend(type: string, payload: UmamiPayload): UmamiPayload | null {
  if (dropLandingPageview && isPageview(type, payload)) {
    dropLandingPageview = false;
    return null; // a falsy return cancels the send
  }
  return scrubUmamiPayload(type, payload);
}

/**
 * Register the hook the tracker looks up by name at send time. Must run before
 * the first pageview: the deferred tracker only sends once the document is
 * complete, after main.tsx has executed.
 */
export function installUmamiBeforeSend(): void {
  dropLandingPageview = consumeAutoReloadMarker();
  window.umamiBeforeSend = umamiBeforeSend;
}

export type UmamiAccountType = 'guest' | 'registered';

/** The key useAuth.ts writes the JWT under. guest_token is deliberately never
 * read here: logout keeps it for guest reuse, so it can outlive the session. */
const AUTH_TOKEN_STORAGE_KEY = 'auth_token';

/** A JWT is header.payload.signature; the claims live in the middle segment. */
const JWT_PAYLOAD_SEGMENT = 1;

/** base64 length must be a multiple of 4; JWT segments are unpadded base64url. */
const BASE64_PAD_MODULUS = 4;

/** users.id is an integer, so any other `sub` is rejected rather than sent. */
const DISTINCT_ID_PATTERN = /^\d+$/;

/** Decode the JWT payload segment; null on any malformed input. No signature
 * check: the value only labels the caller's own analytics session. */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const segment = token.split('.')[JWT_PAYLOAD_SEGMENT];
  if (!segment) return null;
  try {
    const base64 = segment.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(Math.ceil(base64.length / BASE64_PAD_MODULUS) * BASE64_PAD_MODULUS, '=');
    const parsed: unknown = JSON.parse(window.atob(padded));
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return null;
    return parsed as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * The analytics distinct id for a stored JWT: its `sub` claim (users.id as a
 * string) when that is all digits. Null for a missing/malformed token, a
 * non-numeric sub, or an impersonation token.
 */
export function distinctIdFromToken(token: string | null): string | null {
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  if (payload === null) return null;
  // Impersonation tokens carry the TARGET's sub; the admin's browser must never
  // be attributed to the impersonated user (Phase 229 D-11).
  if (payload.is_impersonation === true) return null;
  const sub = payload.sub;
  return typeof sub === 'string' && DISTINCT_ID_PATTERN.test(sub) ? sub : null;
}

/** Last (id|account) pair sent. Lives per page load: it resets with the tracker
 * on reload, which is exactly when the tracker's in-memory identity resets. */
let lastIdentifyKey: string | null = null;

/**
 * Identify the Umami session with the account id (users.id from the JWT sub)
 * plus, when known, the coarse guest/registered tag. The id lives only in
 * tracker memory (Phase 229 D-08). String form only: the object form copies
 * the id into session_data (D-09). Deduped per page load.
 */
export function identifyUser(distinctId: string, accountType?: UmamiAccountType): void {
  // Bail BEFORE recording the dedupe key: a tracker that loads late must still
  // receive this identify on a later attempt (RESEARCH Pitfall 7).
  if (!window.umami) return;
  const key = `${distinctId}|${accountType ?? ''}`;
  if (key === lastIdentifyKey) return;
  lastIdentifyKey = key;
  window.umami.identify(distinctId, accountType ? { account: accountType } : undefined);
}

/**
 * Boot-time identify from the stored token, called from main.tsx before the
 * deferred tracker's first pageview so the landing pageview carries the id.
 */
export function identifyFromStoredToken(): void {
  let token: string | null;
  try {
    token = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    return;
  }
  const distinctId = distinctIdFromToken(token);
  if (distinctId !== null) identifyUser(distinctId);
}

// ---------------------------------------------------------------------------
// Feature-event registry (Phase 229 D-01, D-04, D-14, D-15)
//
// ONE typed vocabulary for in-app feature analytics. Every call site goes
// through `trackFeature`, so an event name, target or value outside this
// registry fails `npm run build`. Values are literal unions imported from their
// source types: no FEN, username, opening name, game id or free text can be
// expressed. The const arrays below are the durable inventory (D-15).
//
// Adding a UI feature: add its target here, then call `trackFeature` from the
// user-initiated handler (D-03). Never from an effect on a value: that fires on
// mount and on state restore, not on a user action.
// ---------------------------------------------------------------------------

/** Umami rejects event names longer than this (its FIELD_LENGTH.eventName). */
export const UMAMI_EVENT_NAME_MAX_LENGTH = 50;

export type OnOff = 'on' | 'off';

export function onOff(on: boolean): OnOff {
  return on ? 'on' : 'off';
}

export const PAGE_IDS = ['home', 'library', 'openings', 'endgames', 'analysis', 'train', 'bots', 'welcome', 'other'] as const;
export type PageId = (typeof PAGE_IDS)[number];

/** First path segment to page id. '' is the Home route; anything unknown is 'other'. */
const PAGE_BY_SEGMENT: Readonly<Record<string, PageId>> = {
  '': 'home',
  library: 'library',
  openings: 'openings',
  endgames: 'endgames',
  analysis: 'analysis',
  train: 'train',
  bots: 'bots',
  welcome: 'welcome',
};

/** D-14: admin/activity are internal tooling, auth outcomes are already DB-known. */
const EXCLUDED_PAGE_SEGMENTS: readonly string[] = ['admin', 'activity', 'login', 'auth'];

function firstPathSegment(pathname: string): string {
  return pathname.split('/')[1] ?? '';
}

/** Coarse page label from the first path segment only, never the full path or query. */
export function currentPage(pathname: string = window.location.pathname): PageId {
  return PAGE_BY_SEGMENT[firstPathSegment(pathname)] ?? 'other';
}

/** True on routes that must send no feature events even from shared components (D-14). */
export function isTrackingExcludedPath(pathname: string): boolean {
  return EXCLUDED_PAGE_SEGMENTS.includes(firstPathSegment(pathname));
}

export const ANALYSIS_TAB_IDS = ['moves', 'eval', 'human', 'flawchess', 'stats'] as const;
export type AnalysisTabId = (typeof ANALYSIS_TAB_IDS)[number];

/** Train weekly leaderboard tabs (Phase 230), sent as `tab-switch` targets. */
export const LEADERBOARD_TAB_IDS = ['leaderboard-points', 'leaderboard-accuracy'] as const;
export type LeaderboardTabId = (typeof LEADERBOARD_TAB_IDS)[number];

export function isAnalysisTabId(value: string): value is AnalysisTabId {
  return (ANALYSIS_TAB_IDS as readonly string[]).includes(value);
}

export const TOGGLE_TARGETS = [
  'engine-stockfish',
  'engine-maia',
  'engine-flawchess',
  'bookmark-chart',
  'elo-timeline-legend',
  'flaw-trend-legend',
] as const;
type ToggleTarget = (typeof TOGGLE_TARGETS)[number];

export const BOARD_TOOL_TARGETS = ['flip', 'paste-open', 'paste-load', 'line-expand', 'line-delete', 'elo-reset'] as const;
type BoardToolTarget = (typeof BOARD_TOOL_TARGETS)[number];

export const PANEL_TARGETS = [
  'filters',
  'tags',
  'bookmarks',
  'bookmark-suggestions',
  'settings',
  'more-drawer',
  'train-schedule',
  'endgame-type-tc',
  'endgame-metrics-tc',
  'time-pressure-tc',
  'opening-insights-more',
  'opening-stats-more',
  'tactic-motifs-more',
  'tactic-grid-more',
  'move-stats-expand',
] as const;
type PanelTarget = (typeof PANEL_TARGETS)[number];
export type SidebarPanelId = Extract<PanelTarget, 'filters' | 'tags' | 'bookmarks'>;

export const ACTION_TARGETS = [
  'chip-cycle',
  'bookmark-load',
  'analyze',
  'train-solution',
  'train-solve-retry',
  'train-explore-exit',
  'reminder-banner-dismiss',
  'persona-open',
  'custom-setup-open',
  'bot-resume',
  'bot-discard',
  'bot-rematch',
  'bot-new-game',
  'bot-draw-decline',
  'bot-return-live',
] as const;
type ActionTarget = (typeof ACTION_TARGETS)[number];

export const NAV_DESTINATIONS = ['library', 'train', 'bots', 'openings', 'endgames', 'analysis'] as const;
type NavDestination = (typeof NAV_DESTINATIONS)[number];

export const NAV_SOURCES = ['more-drawer'] as const;
type NavSource = (typeof NAV_SOURCES)[number];

/** Map a nav link path to its destination; null for anything else (admin and activity can never be named, D-14). */
export function navDestinationOf(path: string): NavDestination | null {
  const segment = firstPathSegment(path);
  return NAV_DESTINATIONS.find((destination) => destination === segment) ?? null;
}

export const FILTER_TARGETS = [
  'played-as',
  'piece-filter',
  'recency',
  'time-control',
  'platform',
  'opponent-type',
  'opponent-strength',
  'rated',
  'endgame-type',
  'severity',
  'flaw-tag',
  'tactic-family',
  'tactic-orientation',
  'tactic-depth',
  'has-gem',
  'has-great',
  'reset',
  'apply',
] as const;

export const OPTION_TARGETS = ['elo', 'temperature', 'play-style', 'bot-tc', 'bot-color'] as const;

/** FilterPanel's Rated ToggleGroup item values. */
export type RatedFilterValue = 'all' | 'rated' | 'casual';

/** Play-style temperature relative to TEMPERATURE_DEFAULT. */
export type TemperatureBucket = 'lower' | 'default' | 'higher';

export type FilterChangeProps =
  | { target: 'played-as'; value: FilterState['playedAs'] }
  | { target: 'piece-filter'; value: MatchSide }
  | { target: 'recency'; value: RecencyPreset | 'custom' }
  | { target: 'time-control'; value: TimeControl }
  | { target: 'platform'; value: Platform | 'pasted' }
  | { target: 'opponent-type'; value: OpponentType }
  | { target: 'opponent-strength'; value: OpponentStrengthPreset | 'custom' }
  | { target: 'rated'; value: RatedFilterValue }
  | { target: 'endgame-type'; value: EndgameClass }
  | { target: 'severity'; value: Extract<FlawSeverity, 'blunder' | 'mistake'> }
  | { target: 'flaw-tag'; value: FlawTag }
  | { target: 'tactic-family'; value: TacticFamily }
  | { target: 'tactic-orientation'; value: TacticOrientation }
  | { target: 'tactic-depth'; value: TacticDepthPreset | 'custom' }
  | { target: 'has-gem' | 'has-great'; value: OnOff }
  | { target: 'reset' | 'apply' };

export type OptionChangeProps =
  | { target: 'elo'; value: `${number}` } // always a MAIA_ELO_LADDER rung
  | { target: 'temperature'; value: TemperatureBucket }
  | { target: 'play-style'; value: PlayStylePreset }
  | { target: 'bot-tc'; value: TimeControlPresetLabel }
  | { target: 'bot-color'; value: BotSetupSettings['colorPreference'] };

export interface FeatureEventMap {
  'tab-switch': { target: AnalysisTabId | LeaderboardTabId };
  toggle: { target: ToggleTarget; value: OnOff };
  'filter-change': FilterChangeProps;
  'option-change': OptionChangeProps;
  'board-tool': { target: BoardToolTarget };
  /** Only ever built from `popoverTargetFromTestId`. */
  'popover-open': { target: string };
  'panel-open': { target: PanelTarget };
  action: { target: ActionTarget };
  'nav-click': { target: NavDestination; value: NavSource };
}
export type FeatureEventName = keyof FeatureEventMap;

/** Exhaustive by construction: adding an event to FeatureEventMap without listing it here fails the build. */
const FEATURE_EVENT_NAME_SET: Record<FeatureEventName, true> = {
  'tab-switch': true,
  toggle: true,
  'filter-change': true,
  'option-change': true,
  'board-tool': true,
  'popover-open': true,
  'panel-open': true,
  action: true,
  'nav-click': true,
};
export const FEATURE_EVENT_NAMES = Object.keys(FEATURE_EVENT_NAME_SET) as FeatureEventName[];

/**
 * Send one typed feature event. `page` is derived from the route so shared
 * components (InfoPopover, FilterPanel, BoardControls) need not thread it.
 * Goes through `trackEvent` so existing trackEvent spies see feature events.
 *
 * Deferred senders (see `useDebouncedTrackFeature`) pass the pathname captured
 * when the user acted, so a send that happens after navigation is attributed to
 * the right page and still honors the D-14 exclusion for that page.
 */
export function trackFeature<E extends FeatureEventName>(
  name: E,
  props: FeatureEventMap[E],
  pathname: string = window.location.pathname,
): void {
  // D-14: shared components also render on /admin and /auth/*; send nothing there.
  if (isTrackingExcludedPath(pathname)) return;
  // Every registry value is a string literal, which is what Umami event data takes.
  trackEvent(name, { page: currentPage(pathname), ...props } as Record<string, string>);
}

const NUMERIC_SEGMENT = /^\d+$/;

/**
 * Per-TC card popovers (`metrics-tc-rapid-…`, `time-pressure-card-blitz-…`,
 * `type-card-rapid-rook-…`) aggregate into one row per explanation, not one per
 * time control. A TC word is only dropped right after a `tc`/`card` segment,
 * because `bullet` also names bullet charts (`score-bullet-popover-trigger`).
 */
const POPOVER_TC_SEGMENTS: readonly string[] = ['bullet', 'blitz', 'rapid', 'classical'];
const POPOVER_TC_PREFIX_SEGMENTS: readonly string[] = ['tc', 'card'];

/** Desktop/mobile copies of one popover aggregate into one analytics row. */
const POPOVER_VIEW_SUFFIXES: readonly string[] = ['mobile', 'desktop', 'sidebar', 'drawer'];

const POPOVER_TARGET_PATTERN = /^[a-z][a-z0-9-]*$/;

/**
 * Normalize a popover data-testid into an id-free analytics target. TagLegend
 * testIds embed the game id (`tag-legend-48213`) and list cards embed an index
 * (`opening-finding-card-3-score-popover`): numeric segments are dropped, as
 * are per-TC segments and trailing -mobile/-desktop/-sidebar/-drawer view suffixes. Returns null
 * when the result is not a plain kebab-case slug, so a malformed id sends
 * nothing rather than something unbounded.
 */
export function popoverTargetFromTestId(testId: string): string | null {
  const raw = testId.toLowerCase().split('-');
  // TC check runs on the raw segments, before numeric segments are dropped, so
  // `opening-finding-card-3-bullet-popover` keeps its bullet chart segment.
  const segments = raw.filter(
    (segment, i) =>
      !NUMERIC_SEGMENT.test(segment) &&
      !(POPOVER_TC_SEGMENTS.includes(segment) && POPOVER_TC_PREFIX_SEGMENTS.includes(raw[i - 1] ?? '')),
  );
  while (segments.length > 0 && POPOVER_VIEW_SUFFIXES.includes(segments[segments.length - 1] ?? '')) {
    segments.pop();
  }
  const target = segments.join('-');
  return POPOVER_TARGET_PATTERN.test(target) ? target : null;
}
