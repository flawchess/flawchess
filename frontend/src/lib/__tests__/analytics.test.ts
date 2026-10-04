// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { installUmamiBeforeSend, scrubUmamiPayload, umamiBeforeSend } from '@/lib/analytics';
import { reloadAutomatically } from '@/lib/autoReload';

const ORIGIN = window.location.origin;

describe('scrubUmamiPayload', () => {
  it('strips the password-reset token from the url and keeps other params', () => {
    const out = scrubUmamiPayload('event', {
      url: `${ORIGIN}/auth/reset-password?token=abc.def.ghi&utm_source=mail`,
    });
    expect(out.url).toBe(`${ORIGIN}/auth/reset-password?utm_source=mail`);
  });

  it('strips the token from an origin-relative internal referrer and keeps it relative', () => {
    const out = scrubUmamiPayload('event', { referrer: '/auth/reset-password?token=abc' });
    expect(out.referrer).toBe('/auth/reset-password');
  });

  it.each(['https://accounts.google.com/', 'https://accounts.google.fr/', 'https://accounts.google.co.uk/'])(
    'blanks the Google OAuth referrer %s',
    (referrer) => {
      expect(scrubUmamiPayload('event', { referrer }).referrer).toBe('');
    },
  );

  it('keeps real search and external referrers untouched', () => {
    expect(scrubUmamiPayload('event', { referrer: 'https://www.google.com/' }).referrer).toBe(
      'https://www.google.com/',
    );
    expect(scrubUmamiPayload('event', { referrer: 'https://lichess.org/@/someone' }).referrer).toBe(
      'https://lichess.org/@/someone',
    );
  });

  it('leaves tokenless urls byte-identical and passes other fields through', () => {
    const payload = { url: `${ORIGIN}/analysis?game_id=5&ply=12`, name: 'guest-start', website: 'w' };
    expect(scrubUmamiPayload('event', payload)).toEqual(payload);
  });
});

describe('Umami globals', () => {
  afterEach(() => {
    delete window.umami;
    delete window.umamiBeforeSend;
  });

  it('installs the hook under the name index.html references', () => {
    installUmamiBeforeSend();
    expect(window.umamiBeforeSend).toBe(umamiBeforeSend);
  });
});

describe('umamiBeforeSend after an automatic reload (Quick 261004-rmc)', () => {
  const PAGEVIEW = { website: 'w', url: '/train' };
  const originalLocation = window.location;

  beforeEach(() => {
    window.sessionStorage.clear();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { reload: vi.fn(), origin: originalLocation.origin },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation });
    delete window.umamiBeforeSend;
  });

  it('drops exactly one landing pageview after an automatic reload', () => {
    reloadAutomatically();
    installUmamiBeforeSend();
    expect(umamiBeforeSend('event', PAGEVIEW)).toBeNull();
    expect(umamiBeforeSend('event', PAGEVIEW)).toEqual(PAGEVIEW);
  });

  it('passes identify calls and custom events while a pageview is pending drop', () => {
    reloadAutomatically();
    installUmamiBeforeSend();
    expect(umamiBeforeSend('identify', { website: 'w', id: '42' })).toEqual({ website: 'w', id: '42' });
    expect(umamiBeforeSend('event', { ...PAGEVIEW, name: 'toggle' })).toEqual({ ...PAGEVIEW, name: 'toggle' });
    expect(umamiBeforeSend('event', PAGEVIEW)).toBeNull();
  });

  it('keeps every pageview on a normal page load, scrubbed', () => {
    installUmamiBeforeSend();
    expect(umamiBeforeSend('event', { url: '/auth/reset-password?token=abc' })).toEqual({
      url: '/auth/reset-password',
    });
  });
});

const FIXED_HEADER = 'eyJhbGciOiJIUzI1NiJ9';
const FIXED_SIGNATURE = 'c2lnbmF0dXJl';

/** Build an unsigned JWT-shaped string whose payload carries the given claims. */
function makeToken(claims: Record<string, unknown>): string {
  const payload = btoa(JSON.stringify(claims)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  return `${FIXED_HEADER}.${payload}.${FIXED_SIGNATURE}`;
}

describe('analytics identity', () => {
  let analytics: typeof import('@/lib/analytics');
  let identify: ReturnType<typeof vi.fn>;

  // Fresh module per test: lastIdentifyKey is module state. Imported here, never
  // inside a test body (heavy-test timeout flake).
  beforeEach(async () => {
    vi.resetModules();
    analytics = await import('@/lib/analytics');
    identify = vi.fn();
  });

  afterEach(() => {
    delete window.umami;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('guest_token');
    vi.restoreAllMocks();
  });

  function installTracker(): void {
    window.umami = { track: vi.fn(), identify };
  }

  describe('distinctIdFromToken', () => {
    it('returns the sub for a regular token', () => {
      expect(analytics.distinctIdFromToken(makeToken({ sub: '123', aud: ['fastapi-users:auth'] }))).toBe('123');
    });

    it('returns the sub for a guest token of the same shape', () => {
      expect(analytics.distinctIdFromToken(makeToken({ sub: '9', aud: ['fastapi-users:auth'] }))).toBe('9');
    });

    it('returns null for an impersonation token', () => {
      expect(analytics.distinctIdFromToken(makeToken({ sub: '123', is_impersonation: true }))).toBeNull();
    });

    it.each([null, '', 'abc', 'a.b.c', 'a.!!!.c'])('returns null for malformed token %j', (token) => {
      expect(analytics.distinctIdFromToken(token)).toBeNull();
    });

    it('returns null for a middle segment that is not JSON', () => {
      expect(analytics.distinctIdFromToken(`h.${btoa('not json')}.s`)).toBeNull();
    });

    it('returns null for a non-numeric sub and for a missing sub', () => {
      expect(analytics.distinctIdFromToken(makeToken({ sub: 'abc' }))).toBeNull();
      expect(analytics.distinctIdFromToken(makeToken({ aud: ['x'] }))).toBeNull();
    });

    it('decodes an unpadded payload containing base64url characters', () => {
      // '>>>' encodes to 'Pj4+' and '???' to 'Pz8/': both force '+' / '/' in plain base64.
      const claims = { sub: '77', pad: '>>>???>>>>' };
      const token = makeToken(claims);
      const segment = token.split('.')[1] ?? '';
      expect(segment).toMatch(/[-_]/);
      expect(segment).not.toContain('=');
      expect(analytics.distinctIdFromToken(token)).toBe('77');
    });
  });

  describe('identifyUser', () => {
    it('uses the string form once and dedupes identical pairs', () => {
      installTracker();
      analytics.identifyUser('123', 'guest');
      analytics.identifyUser('123', 'guest');
      expect(identify).toHaveBeenCalledTimes(1);
      expect(identify).toHaveBeenCalledWith('123', { account: 'guest' });
    });

    it('sends again when the account type changes', () => {
      installTracker();
      analytics.identifyUser('123', 'guest');
      analytics.identifyUser('123', 'registered');
      expect(identify).toHaveBeenCalledTimes(2);
      expect(identify).toHaveBeenLastCalledWith('123', { account: 'registered' });
    });

    it('passes undefined data when no account type is given', () => {
      installTracker();
      analytics.identifyUser('7');
      expect(identify).toHaveBeenCalledWith('7', undefined);
    });

    it('does not throw without a tracker and still identifies once the tracker appears', () => {
      expect(() => analytics.identifyUser('123', 'guest')).not.toThrow();
      installTracker();
      analytics.identifyUser('123', 'guest');
      expect(identify).toHaveBeenCalledTimes(1);
      expect(identify).toHaveBeenCalledWith('123', { account: 'guest' });
    });
  });

  describe('identifyFromStoredToken', () => {
    it('identifies from auth_token without account data', () => {
      installTracker();
      localStorage.setItem('auth_token', makeToken({ sub: '42' }));
      analytics.identifyFromStoredToken();
      expect(identify).toHaveBeenCalledWith('42', undefined);
    });

    it('ignores guest_token', () => {
      installTracker();
      localStorage.setItem('guest_token', makeToken({ sub: '42' }));
      analytics.identifyFromStoredToken();
      expect(identify).not.toHaveBeenCalled();
    });

    it('skips an impersonation token', () => {
      installTracker();
      localStorage.setItem('auth_token', makeToken({ sub: '42', is_impersonation: true }));
      analytics.identifyFromStoredToken();
      expect(identify).not.toHaveBeenCalled();
    });

    it('does not throw when localStorage throws', () => {
      installTracker();
      vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new Error('denied');
      });
      expect(() => analytics.identifyFromStoredToken()).not.toThrow();
      expect(identify).not.toHaveBeenCalled();
    });
  });

  describe('scrubUmamiPayload with identify', () => {
    it('passes the id and data of an identify payload through unchanged', () => {
      const out = analytics.scrubUmamiPayload('identify', {
        id: '5',
        data: { account: 'guest' },
        url: `${ORIGIN}/library`,
      });
      expect(out.id).toBe('5');
      expect(out.data).toEqual({ account: 'guest' });
    });
  });
});

describe('feature-event registry', () => {
  let analytics: typeof import('@/lib/analytics');
  let track: ReturnType<typeof vi.fn>;

  // Imported here, never inside a test body (heavy-test timeout flake).
  beforeEach(async () => {
    analytics = await import('@/lib/analytics');
    track = vi.fn();
    window.umami = { track, identify: vi.fn() };
  });

  afterEach(() => {
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  // Events that predate the registry: D-05 forbids renaming or reusing them.
  const LEGACY_EVENT_NAMES = [
    'signup-cta',
    'import-cta',
    'guest-start',
    'pwa-installed',
    'pwa-install-outcome',
    'pwa-install-offer-shown',
    'settings-change',
    'settings-reset',
    'engine-gate-shown',
    'engine-gate-started',
    'engine-gate-abandoned',
  ];

  it('defines exactly 9 well-formed event names that collide with no legacy event', () => {
    expect(analytics.FEATURE_EVENT_NAMES).toHaveLength(9);
    expect([...analytics.FEATURE_EVENT_NAMES].sort()).toEqual(
      [
        'action',
        'board-tool',
        'filter-change',
        'nav-click',
        'option-change',
        'panel-open',
        'popover-open',
        'tab-switch',
        'toggle',
      ].sort(),
    );
    for (const name of analytics.FEATURE_EVENT_NAMES) {
      expect(name).toMatch(/^[a-z]+(-[a-z]+)*$/);
      expect(name.length).toBeLessThanOrEqual(analytics.UMAMI_EVENT_NAME_MAX_LENGTH);
      expect(LEGACY_EVENT_NAMES).not.toContain(name);
      expect(name.startsWith('outbound-')).toBe(false);
    }
  });

  it('keeps every enumerated target a kebab-case slug', () => {
    const lists: readonly (readonly string[])[] = [
      analytics.PAGE_IDS,
      analytics.ANALYSIS_TAB_IDS,
      analytics.LEADERBOARD_TAB_IDS,
      analytics.TOGGLE_TARGETS,
      analytics.BOARD_TOOL_TARGETS,
      analytics.PANEL_TARGETS,
      analytics.ACTION_TARGETS,
      analytics.NAV_DESTINATIONS,
      analytics.NAV_SOURCES,
      analytics.FILTER_TARGETS,
      analytics.OPTION_TARGETS,
    ];
    for (const list of lists) {
      for (const entry of list) expect(entry).toMatch(/^[a-z0-9]+(-[a-z0-9]+)*$/);
    }
  });

  it.each([
    ['/', 'home'],
    ['/library/stats', 'library'],
    ['/openings/explorer', 'openings'],
    ['/endgames', 'endgames'],
    ['/analysis', 'analysis'],
    ['/train', 'train'],
    ['/bots/persona', 'bots'],
    ['/welcome', 'welcome'],
    ['/privacy', 'other'],
  ])('currentPage(%s) is %s', (path, page) => {
    expect(analytics.currentPage(path)).toBe(page);
  });

  it.each(['/admin', '/activity', '/login', '/auth/callback'])('excludes %s from tracking', (path) => {
    expect(analytics.isTrackingExcludedPath(path)).toBe(true);
  });

  it('does not exclude /library', () => {
    expect(analytics.isTrackingExcludedPath('/library')).toBe(false);
  });

  it('trackFeature sends page plus the typed props through window.umami.track', () => {
    window.history.pushState({}, '', '/analysis');
    analytics.trackFeature('board-tool', { target: 'flip' });
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('board-tool', { page: 'analysis', target: 'flip' });
  });

  it('trackFeature sends value when the event carries one', () => {
    window.history.pushState({}, '', '/openings');
    analytics.trackFeature('filter-change', { target: 'time-control', value: 'blitz' });
    expect(track).toHaveBeenCalledWith('filter-change', { page: 'openings', target: 'time-control', value: 'blitz' });
  });

  it.each(['leaderboard-points', 'leaderboard-accuracy'] as const)(
    'trackFeature sends the %s tab-switch target with page train (Phase 230)',
    (target) => {
      window.history.pushState({}, '', '/train');
      analytics.trackFeature('tab-switch', { target });
      expect(track).toHaveBeenCalledTimes(1);
      expect(track).toHaveBeenCalledWith('tab-switch', { page: 'train', target });
    },
  );

  it.each(['/admin', '/activity', '/login', '/auth/callback'])('trackFeature sends nothing on %s', (path) => {
    window.history.pushState({}, '', path);
    analytics.trackFeature('board-tool', { target: 'flip' });
    expect(track).not.toHaveBeenCalled();
  });

  it('trackFeature does not throw when the tracker is absent', () => {
    delete window.umami;
    window.history.pushState({}, '', '/analysis');
    expect(() => analytics.trackFeature('board-tool', { target: 'flip' })).not.toThrow();
  });

  it.each([
    ['tag-legend-tactic-missed-48213', 'tag-legend-tactic-missed'],
    ['tag-legend-48213', 'tag-legend'],
    ['opening-finding-card-3-score-popover', 'opening-finding-card-score-popover'],
    ['piece-filter-info-mobile', 'piece-filter-info'],
    ['time-pressure-card-blitz-clock-gap-info', 'time-pressure-card-clock-gap-info'],
    ['metrics-tc-rapid-conversion-title-info', 'metrics-tc-conversion-title-info'],
    ['type-card-classical-rook-title-info', 'type-card-rook-title-info'],
    ['score-bullet-popover-trigger', 'score-bullet-popover-trigger'],
    ['opening-finding-card-3-bullet-popover', 'opening-finding-card-bullet-popover'],
    ['persona-elo-disclosure', 'persona-elo-disclosure'],
  ])('popoverTargetFromTestId(%s) is %s', (testId, expected) => {
    expect(analytics.popoverTargetFromTestId(testId)).toBe(expected);
  });

  it.each(['Bad Value!', '123', '', '-mobile', 'has_underscore'])('popoverTargetFromTestId(%j) is null', (testId) => {
    expect(analytics.popoverTargetFromTestId(testId)).toBeNull();
  });

  it('maps nav paths to destinations and refuses internal pages', () => {
    expect(analytics.navDestinationOf('/library')).toBe('library');
    expect(analytics.navDestinationOf('/analysis')).toBe('analysis');
    expect(analytics.navDestinationOf('/admin')).toBeNull();
    expect(analytics.navDestinationOf('/activity')).toBeNull();
  });

  it('converts booleans with onOff and narrows tab ids', () => {
    expect(analytics.onOff(true)).toBe('on');
    expect(analytics.onOff(false)).toBe('off');
    expect(analytics.isAnalysisTabId('eval')).toBe(true);
    expect(analytics.isAnalysisTabId('nope')).toBe(false);
  });
});
