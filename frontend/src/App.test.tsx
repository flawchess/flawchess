// @vitest-environment jsdom
/**
 * App-level nav tests.
 *
 * Purpose: the /bots route is linked into all three nav surfaces
 * (desktop NavHeader, mobile BOTTOM_NAV_ITEMS, mobile MobileMoreDrawer) and
 * exempted from all three duplicated import-lock expressions. The lock rule
 * is copy-pasted with slightly different clause lists per surface — patching
 * one site and missing the other two is exactly the failure mode this file
 * exists to catch.
 *
 * This file (deliberately) also locks in the EXISTING Library/Openings/
 * Endgames lock behavior against silent regression, via the "control"
 * assertion in the zero-game state.
 *
 * A full <App /> render is impractical here: App() owns its own
 * BrowserRouter/AuthProvider/QueryClientProvider stack, which makes route
 * control (MemoryRouter initialEntries) and hook mocking difficult from the
 * outside. Instead, NavHeader/MobileBottomBar/MobileMoreDrawer/MobileHeader
 * are exported (additively) from App.tsx and rendered directly here, each
 * wrapped in its own MemoryRouter + TooltipProvider.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { TooltipProvider } from '@/components/ui/tooltip';
import type { FeatureRouteState, UserProfile } from '@/types/users';

// ── Mock useUserProfile / useReadiness / useAuth so tests control navUnlocked
// state without a real API or QueryClientProvider.
let profileState: Partial<UserProfile> | null = null;
let tier1State = false;

// Partial mock: hasImportedGames (used by useNavUnlocked) stays real, only the
// profile query is replaced.
vi.mock('@/hooks/useUserProfile', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/hooks/useUserProfile')>()),
  useUserProfile: () => ({ data: profileState }),
}));

// The real Privacy card uses useSetLeaderboardHidden (absent from the
// factory above) and a QueryClient; the settings overlay tests do not exercise it.
vi.mock('@/components/settings/LeaderboardPrivacyCard', () => ({
  LeaderboardPrivacyCard: () => null,
}));

vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: () => ({
    tier1: tier1State,
    tier2: false,
    pendingCount: 0,
    totalCount: 0,
    isLoading: false,
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ logout: vi.fn() }),
}));

// Mock useTrainProgress so tests control the badge's resolved data
// without a real API or QueryClientProvider. trainProgressData undefined
// stands in for BOTH the pending and errored states — App.tsx derives the
// badge count from `.data?.pending_count ?? 0` only (D-13), so both states collapse
// to "no resolved data" from the component's point of view.
// pending_count is optional here (not required, unlike the real
// TrainProgressResponse) so a test can omit it to prove the fail-closed `?? 0`
// path in App.tsx; the legacy waiting_count / badge_visible fields are kept
// optional to prove the badge no longer reads them.
let trainProgressData:
  | { pending_count?: number; waiting_count?: number; badge_visible?: boolean }
  | undefined;
const useTrainProgressSpy = vi.fn();

vi.mock('@/hooks/useTrainProgress', () => ({
  useTrainProgress: (options?: { enabled?: boolean }) => {
    useTrainProgressSpy(options);
    // Mirrors real TanStack Query `enabled: false` semantics: the query never
    // fetches, so `.data` stays undefined regardless of what the test primed.
    if (options?.enabled === false) return { data: undefined };
    return { data: trainProgressData };
  },
}));

// jsdom shims required by vaul's Drawer (MobileMoreDrawer).
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
  ResizeObserverStub;

if (!('scrollTo' in window) || typeof window.scrollTo !== 'function') {
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
}

afterEach(() => {
  cleanup();
  profileState = null;
  tier1State = false;
  trainProgressData = undefined;
  useTrainProgressSpy.mockClear();
});

import { NavHeader, MobileBottomBar, MobileMoreDrawer, MobileHeader, MobileTopBar } from './App';
import { usePublishMobileBoardControls } from '@/lib/mobileBoardControls';
import { TOUR_SPOTLIGHT_CLASS } from '@/lib/theme';
import { MUTE_KEY } from '@/lib/sounds';
import { SETTINGS_STORAGE_KEYS } from '@/lib/engineSettings';

// ── Render helpers ──────────────────────────────────────────────────────────────

function renderNavHeader(initialPath = '/library') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <TooltipProvider>
        <NavHeader />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

function renderMobileBottomBar(initialPath = '/library', extra?: React.ReactNode) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <TooltipProvider>
        {extra}
        <MobileBottomBar onMoreClick={() => {}} />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

function renderMobileMoreDrawer(initialPath = '/library') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <TooltipProvider>
        <MobileMoreDrawer open={true} onOpenChange={() => {}} />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

// A tiny probe that publishes a fixture board-controls
// payload for the duration it is mounted, so MobileBottomBar's swap can be
// tested without wiring a real Train solve screen.
function MobileBoardControlsProbe(props: {
  onBack: () => void;
  onForward: () => void;
  onReset: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
  canReset: boolean;
}) {
  usePublishMobileBoardControls(props);
  return null;
}

function renderMobileHeader(initialPath = '/bots') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <TooltipProvider>
        <MobileHeader />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

// ── navUnlocked state table ──────────────────────────────────────────────────────
// A: zero-game user, B: guest (zero games), C: fully-imported user (tier1 + games).
// navUnlocked = importedGameCount > 0 && tier1 — all three /bots assertions must pass in
// EVERY row (A and B are locked, C is unlocked), proving /bots is NEVER gated.

const NAV_STATES: {
  name: string;
  navUnlocked: boolean;
  setup: () => void;
}[] = [
  {
    name: 'zero-game user',
    navUnlocked: false,
    setup: () => {
      profileState = {
        email: 'zero@example.com',
        is_superuser: false,
        is_guest: false,
        chess_com_game_count: 0,
        lichess_game_count: 0,
        impersonation: null,
      } as Partial<UserProfile>;
      tier1State = false;
    },
  },
  {
    name: 'guest (zero games)',
    navUnlocked: false,
    setup: () => {
      profileState = {
        email: 'guest@example.com',
        is_superuser: false,
        is_guest: true,
        chess_com_game_count: 0,
        lichess_game_count: 0,
        impersonation: null,
      } as Partial<UserProfile>;
      tier1State = false;
    },
  },
  {
    name: 'fully-imported user',
    navUnlocked: true,
    setup: () => {
      profileState = {
        email: 'full@example.com',
        is_superuser: false,
        is_guest: false,
        chess_com_game_count: 50,
        lichess_game_count: 0,
        impersonation: null,
      } as Partial<UserProfile>;
      tier1State = true;
    },
  },
];

// ── Tests ──────────────────────────────────────────────────────────────────────

describe.each(NAV_STATES)('nav lock state: $name', ({ setup }) => {
  it('desktop nav (NavHeader): /bots is never aria-disabled or dimmed', () => {
    setup();
    renderNavHeader();
    const link = screen.getByTestId('nav-bots');
    expect(link.getAttribute('aria-disabled')).toBeNull();
    expect(link.className).not.toMatch(/opacity-40/);
  });

  it('mobile bottom bar (MobileBottomBar): /bots is never aria-disabled or dimmed', () => {
    setup();
    renderMobileBottomBar();
    const link = screen.getByTestId('mobile-nav-bots');
    expect(link.getAttribute('aria-disabled')).toBeNull();
    expect(link.className).not.toMatch(/opacity-40/);
  });

  it('more drawer (MobileMoreDrawer): /bots is never aria-disabled or dimmed', () => {
    setup();
    renderMobileMoreDrawer();
    const link = screen.getByTestId('drawer-nav-bots');
    expect(link.getAttribute('aria-disabled')).toBeNull();
    expect(link.className).not.toMatch(/opacity-40/);
  });
});

// /analysis is IMPORT_EXEMPT_ROUTES too — reachable
// and clickable with zero imported games, on every surface it appears on.
describe.each(NAV_STATES)('nav lock state: $name — /analysis', ({ setup }) => {
  it('desktop nav (NavHeader): renders nav-analysis, never aria-disabled or dimmed', () => {
    setup();
    renderNavHeader();
    const link = screen.getByTestId('nav-analysis');
    expect(link.getAttribute('aria-disabled')).toBeNull();
    expect(link.className).not.toMatch(/opacity-40/);
  });

  it('more drawer (MobileMoreDrawer): renders drawer-nav-analysis, never aria-disabled or dimmed', () => {
    setup();
    renderMobileMoreDrawer();
    const link = screen.getByTestId('drawer-nav-analysis');
    expect(link.getAttribute('aria-disabled')).toBeNull();
    expect(link.className).not.toMatch(/opacity-40/);
  });

  it('mobile bottom bar (MobileBottomBar): renders NO analysis entry', () => {
    setup();
    renderMobileBottomBar();
    expect(screen.queryByTestId('mobile-nav-analysis')).toBeNull();
  });
});

describe('control assertion: existing lock behavior is genuinely exercised', () => {
  it('nav-openings and nav-endgames ARE aria-disabled in the zero-game state', () => {
    profileState = {
      email: 'zero@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 0,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = false;

    renderNavHeader();

    expect(screen.getByTestId('nav-openings').getAttribute('aria-disabled')).toBe('true');
    expect(screen.getByTestId('nav-endgames').getAttribute('aria-disabled')).toBe('true');
    // /bots stays unlocked in the exact same render that proves the lock is real.
    expect(screen.getByTestId('nav-bots').getAttribute('aria-disabled')).toBeNull();
  });
});

describe('Bots renders in all three surfaces, second position', () => {
  it('desktop NavHeader: order is Library, Train, Bots, Openings, Endgames', () => {
    profileState = {
      email: 'zero@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 0,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = false;

    renderNavHeader();
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    const links = within(nav).getAllByTestId(/^nav-/);
    const order = links.map((el) => el.getAttribute('data-testid'));
    // /analysis is appended as NAV_ITEMS' last entry — it
    // is absent from BOTTOM_NAV_ITEMS by design, so this desktop-only order
    // check gains it while the mobile bottom-bar check below does not.
    expect(order).toEqual([
      'nav-library',
      'nav-train',
      'nav-bots',
      'nav-openings',
      'nav-endgames',
      'nav-analysis',
    ]);
  });

  it('mobile bottom bar: order is Library, Train, Bots, Openings, Endgames', () => {
    profileState = {
      email: 'zero@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 0,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = false;

    renderMobileBottomBar();
    const nav = screen.getByRole('navigation', { name: 'Mobile navigation' });
    const links = within(nav).getAllByTestId(/^mobile-nav-(?!more)/);
    const order = links.map((el) => el.getAttribute('data-testid'));
    expect(order).toEqual([
      'mobile-nav-library',
      'mobile-nav-train',
      'mobile-nav-bots',
      'mobile-nav-openings',
      'mobile-nav-endgames',
    ]);
  });

  it('more drawer: order is Library, Train, Bots, Openings, Endgames', () => {
    profileState = {
      email: 'zero@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 0,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = false;

    renderMobileMoreDrawer();
    const links = screen.getAllByTestId(/^drawer-nav-/);
    const order = links.map((el) => el.getAttribute('data-testid'));
    // The More drawer reads NAV_ITEMS too, so it also gains
    // drawer-nav-analysis at the end.
    expect(order).toEqual([
      'drawer-nav-library',
      'drawer-nav-train',
      'drawer-nav-bots',
      'drawer-nav-openings',
      'drawer-nav-endgames',
      'drawer-nav-analysis',
    ]);
  });
});

describe('Train renders in all three surfaces, correctly placed', () => {
  it('desktop NavHeader: nav test-id sequence places Train between Library and Bots', () => {
    profileState = {
      email: 'zero@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 0,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = false;

    renderNavHeader();
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    const links = within(nav).getAllByTestId(/^nav-/);
    const order = links.map((el) => el.getAttribute('data-testid'));
    // /analysis is appended last, as in the Bots order test above.
    expect(order).toEqual([
      'nav-library',
      'nav-train',
      'nav-bots',
      'nav-openings',
      'nav-endgames',
      'nav-analysis',
    ]);
  });

  it('mobile bottom bar: nav test-id sequence places Train between Library and Bots', () => {
    profileState = {
      email: 'zero@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 0,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = false;

    renderMobileBottomBar();
    const nav = screen.getByRole('navigation', { name: 'Mobile navigation' });
    const links = within(nav).getAllByTestId(/^mobile-nav-(?!more)/);
    const order = links.map((el) => el.getAttribute('data-testid'));
    expect(order).toEqual([
      'mobile-nav-library',
      'mobile-nav-train',
      'mobile-nav-bots',
      'mobile-nav-openings',
      'mobile-nav-endgames',
    ]);
  });

  it('more drawer: nav test-id sequence places Train between Library and Bots', () => {
    profileState = {
      email: 'zero@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 0,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = false;

    renderMobileMoreDrawer();
    const links = screen.getAllByTestId(/^drawer-nav-/);
    const order = links.map((el) => el.getAttribute('data-testid'));
    // drawer-nav-analysis is appended last, as in the Bots order test above.
    expect(order).toEqual([
      'drawer-nav-library',
      'drawer-nav-train',
      'drawer-nav-bots',
      'drawer-nav-openings',
      'drawer-nav-endgames',
      'drawer-nav-analysis',
    ]);
  });

  it('desktop and bottom-bar nav sequences agree everywhere EXCEPT /analysis', () => {
    profileState = {
      email: 'zero@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 0,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = false;

    const { unmount: unmountDesktop } = renderNavHeader();
    const desktopNav = screen.getByRole('navigation', { name: 'Main navigation' });
    const desktopOrder = within(desktopNav)
      .getAllByTestId(/^nav-/)
      .map((el) => el.getAttribute('data-testid')?.replace(/^nav-/, ''));
    unmountDesktop();

    renderMobileBottomBar();
    const mobileNav = screen.getByRole('navigation', { name: 'Mobile navigation' });
    const mobileOrder = within(mobileNav)
      .getAllByTestId(/^mobile-nav-(?!more)/)
      .map((el) => el.getAttribute('data-testid')?.replace(/^mobile-nav-/, ''));

    // NAV_ITEMS (desktop) and BOTTOM_NAV_ITEMS (mobile
    // bottom bar) intentionally differ by exactly one entry —
    // /analysis is on the desktop surface only. The App.tsx comment on both
    // arrays records this divergence as deliberate, so the test asserts
    // the divergence precisely.
    expect(desktopOrder).toContain('analysis');
    expect(mobileOrder).not.toContain('analysis');
    expect(desktopOrder.filter((id) => id !== 'analysis')).toEqual(mobileOrder);
  });
});

describe('Train gating', () => {
  it('locked state: Train is exempt on all three surfaces; Openings/Endgames stay locked', () => {
    profileState = {
      email: 'zero@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 0,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = false;

    const { unmount: unmountHeader } = renderNavHeader();
    const desktopLink = screen.getByTestId('nav-train');
    expect(desktopLink.getAttribute('aria-disabled')).toBeNull();
    expect(desktopLink.getAttribute('title')).toBeNull();
    // Control assertion: the lock mechanism itself still works for routes
    // that are NOT exempt.
    expect(screen.getByTestId('nav-openings').getAttribute('aria-disabled')).toBe('true');
    expect(screen.getByTestId('nav-endgames').getAttribute('aria-disabled')).toBe('true');
    unmountHeader();

    const { unmount: unmountBar } = renderMobileBottomBar();
    const mobileLink = screen.getByTestId('mobile-nav-train');
    expect(mobileLink.getAttribute('aria-disabled')).toBeNull();
    expect(screen.getByTestId('mobile-nav-openings').getAttribute('aria-disabled')).toBe('true');
    expect(screen.getByTestId('mobile-nav-endgames').getAttribute('aria-disabled')).toBe('true');
    unmountBar();

    renderMobileMoreDrawer();
    const drawerLink = screen.getByTestId('drawer-nav-train');
    expect(drawerLink.getAttribute('aria-disabled')).toBeNull();
    expect(screen.getByTestId('drawer-nav-openings').getAttribute('aria-disabled')).toBe('true');
    expect(screen.getByTestId('drawer-nav-endgames').getAttribute('aria-disabled')).toBe('true');
  });

  it('unlocked state: Train is NOT aria-disabled on all three surfaces', () => {
    profileState = {
      email: 'full@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    const { unmount: unmountHeader } = renderNavHeader();
    expect(screen.getByTestId('nav-train').getAttribute('aria-disabled')).toBeNull();
    unmountHeader();

    const { unmount: unmountBar } = renderMobileBottomBar();
    expect(screen.getByTestId('mobile-nav-train').getAttribute('aria-disabled')).toBeNull();
    unmountBar();

    renderMobileMoreDrawer();
    expect(screen.getByTestId('drawer-nav-train').getAttribute('aria-disabled')).toBeNull();
  });
});

describe('empty profile does not crash and renders Train exempt', () => {
  it('all three surfaces render without throwing, Train exempt, with a null profile', () => {
    profileState = null;
    tier1State = false;

    expect(() => {
      const { unmount } = renderNavHeader();
      expect(screen.getByTestId('nav-train').getAttribute('aria-disabled')).toBeNull();
      expect(screen.getByTestId('nav-openings').getAttribute('aria-disabled')).toBe('true');
      expect(screen.getByTestId('nav-endgames').getAttribute('aria-disabled')).toBe('true');
      unmount();
    }).not.toThrow();

    expect(() => {
      const { unmount } = renderMobileBottomBar();
      expect(screen.getByTestId('mobile-nav-train').getAttribute('aria-disabled')).toBeNull();
      expect(screen.getByTestId('mobile-nav-openings').getAttribute('aria-disabled')).toBe('true');
      expect(screen.getByTestId('mobile-nav-endgames').getAttribute('aria-disabled')).toBe('true');
      unmount();
    }).not.toThrow();

    expect(() => {
      renderMobileMoreDrawer();
      expect(screen.getByTestId('drawer-nav-train').getAttribute('aria-disabled')).toBeNull();
      expect(screen.getByTestId('drawer-nav-openings').getAttribute('aria-disabled')).toBe('true');
      expect(screen.getByTestId('drawer-nav-endgames').getAttribute('aria-disabled')).toBe('true');
    }).not.toThrow();
  });
});

describe('Train active state (adjacency)', () => {
  it('rendered at /train, exactly one nav link is active and it is Train', () => {
    profileState = {
      email: 'full@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    renderNavHeader('/train');
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    const links = within(nav).getAllByTestId(/^nav-/);
    const activeLinks = links.filter((el) => /bg-white\/10/.test(el.className));
    expect(activeLinks).toHaveLength(1);
    expect(activeLinks[0]?.getAttribute('data-testid')).toBe('nav-train');
  });

  it('rendered at /train/anything, Train is active on the sub-route', () => {
    profileState = {
      email: 'full@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    renderNavHeader('/train/anything');
    expect(screen.getByTestId('nav-train').className).toMatch(/bg-white\/10/);
  });

  it('rendered at /library, exactly one nav link is active and it is NOT Train', () => {
    profileState = {
      email: 'full@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    renderNavHeader('/library');
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    const links = within(nav).getAllByTestId(/^nav-/);
    const activeLinks = links.filter((el) => /bg-white\/10/.test(el.className));
    expect(activeLinks).toHaveLength(1);
    expect(activeLinks[0]?.getAttribute('data-testid')).not.toBe('nav-train');
  });
});

describe('mobile bottom-bar target count', () => {
  it('renders six nav links plus the More button, each with visible label text', () => {
    profileState = {
      email: 'full@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    renderMobileBottomBar();
    const nav = screen.getByRole('navigation', { name: 'Mobile navigation' });
    const navLinks = within(nav).getAllByTestId(/^mobile-nav-(?!more)/);
    expect(navLinks).toHaveLength(5);
    for (const link of navLinks) {
      expect(link.textContent?.trim().length).toBeGreaterThan(0);
    }
    const moreButton = within(nav).getByTestId('mobile-nav-more');
    expect(moreButton.textContent?.trim().length).toBeGreaterThan(0);
  });
});

function routeWithDone(ids: string[]): FeatureRouteState {
  return {
    steps: Object.fromEntries(ids.map((id) => [id, { status: 'done' as const, date: '2026-11-15', with_dot: false }])),
    current: null,
  };
}

describe('Train waiting badge', () => {
  const UNLOCKED_PROFILE: Partial<UserProfile> = {
    email: 'badge@example.com',
    is_superuser: false,
    is_guest: false,
    chess_com_game_count: 50,
    lichess_game_count: 0,
    impersonation: null,
  };

  const ZERO_GAME_PROFILE: Partial<UserProfile> = {
    email: 'zero-badge@example.com',
    is_superuser: false,
    is_guest: false,
    chess_com_game_count: 0,
    lichess_game_count: 0,
    impersonation: null,
  };

  const GUEST_PROFILE: Partial<UserProfile> = {
    email: 'guest-badge@example.com',
    is_superuser: false,
    is_guest: true,
    chess_com_game_count: 50,
    lichess_game_count: 0,
    impersonation: null,
  };

  it('unlocked profile with pending_count: 12 -> badge reads 12 on desktop and mobile', () => {
    profileState = UNLOCKED_PROFILE;
    tier1State = true;
    trainProgressData = { pending_count: 12 };

    const { unmount } = renderNavHeader();
    expect(screen.getByTestId('train-notification-badge').textContent).toBe('12');
    unmount();

    renderMobileBottomBar();
    expect(screen.getByTestId('train-notification-badge-mobile').textContent).toBe('12');
  });

  it('pending_count: 0 -> badge absent on both surfaces', () => {
    profileState = UNLOCKED_PROFILE;
    tier1State = true;
    trainProgressData = { pending_count: 0 };

    const { unmount } = renderNavHeader();
    expect(screen.queryByTestId('train-notification-badge')).toBeNull();
    unmount();

    renderMobileBottomBar();
    expect(screen.queryByTestId('train-notification-badge-mobile')).toBeNull();
  });

  it('legacy waiting_count 12 with badge_visible false but pending_count 0 -> badge absent (the badge reads pending_count only, D-13)', () => {
    profileState = UNLOCKED_PROFILE;
    tier1State = true;
    trainProgressData = { pending_count: 0, waiting_count: 12, badge_visible: false };

    const { unmount } = renderNavHeader();
    expect(screen.queryByTestId('train-notification-badge')).toBeNull();
    unmount();

    renderMobileBottomBar();
    expect(screen.queryByTestId('train-notification-badge-mobile')).toBeNull();
  });

  it('payload without pending_count -> badge absent on both surfaces (fails closed)', () => {
    profileState = UNLOCKED_PROFILE;
    tier1State = true;
    trainProgressData = {};

    const { unmount } = renderNavHeader();
    expect(screen.queryByTestId('train-notification-badge')).toBeNull();
    unmount();

    renderMobileBottomBar();
    expect(screen.queryByTestId('train-notification-badge-mobile')).toBeNull();
  });

  it('progress query pending (no resolved data yet) -> badge absent on both surfaces', () => {
    profileState = UNLOCKED_PROFILE;
    tier1State = true;
    trainProgressData = undefined;

    const { unmount } = renderNavHeader();
    expect(screen.queryByTestId('train-notification-badge')).toBeNull();
    unmount();

    renderMobileBottomBar();
    expect(screen.queryByTestId('train-notification-badge-mobile')).toBeNull();
  });

  it('progress query errored (no resolved data) -> badge absent, no nav error text', () => {
    profileState = UNLOCKED_PROFILE;
    tier1State = true;
    trainProgressData = undefined;

    const { unmount } = renderNavHeader();
    expect(screen.queryByTestId('train-notification-badge')).toBeNull();
    expect(screen.queryByText(/failed to load/i)).toBeNull();
    unmount();

    renderMobileBottomBar();
    expect(screen.queryByTestId('train-notification-badge-mobile')).toBeNull();
    expect(screen.queryByText(/failed to load/i)).toBeNull();
  });

  it('pending_count: 150 -> badge reads 99+ on both surfaces, growing to fit (cap logic untouched)', () => {
    profileState = UNLOCKED_PROFILE;
    tier1State = true;
    trainProgressData = { pending_count: 150 };

    const { unmount } = renderNavHeader();
    const desktopBadge = screen.getByTestId('train-notification-badge');
    expect(desktopBadge.textContent).toBe('99+');
    // min-w-3.5 (desktop-only) reduces the badge's protrusion past the
    // header's overflow-hidden clip boundary — see App.tsx's badge
    // className comment.
    expect(desktopBadge.className).toMatch(/min-w-3\.5/);
    unmount();

    renderMobileBottomBar();
    expect(screen.getByTestId('train-notification-badge-mobile').textContent).toBe('99+');
  });

  it('the numeric badge replaces the Train route dot when both apply (pending_count: 12, import done, D-17)', () => {
    profileState = { ...UNLOCKED_PROFILE, feature_route: routeWithDone(['import']) };
    tier1State = true;
    trainProgressData = { pending_count: 12 };

    const { unmount } = renderNavHeader('/bots');
    expect(screen.getByTestId('train-notification-badge').textContent).toBe('12');
    expect(screen.queryByTestId('train-notification-dot')).toBeNull();
    unmount();

    renderMobileBottomBar('/bots');
    expect(screen.getByTestId('train-notification-badge-mobile').textContent).toBe('12');
    expect(screen.queryByTestId('train-notification-dot-mobile')).toBeNull();
  });

  it('the Train route dot shows on both surfaces once import is done and train is open', () => {
    profileState = { ...UNLOCKED_PROFILE, feature_route: routeWithDone(['import']) };
    tier1State = true;
    trainProgressData = { pending_count: 0 };

    const { unmount } = renderNavHeader('/bots');
    expect(screen.queryByTestId('train-notification-dot')).not.toBeNull();
    expect(screen.queryByTestId('train-notification-badge')).toBeNull();
    unmount();

    renderMobileBottomBar('/bots');
    expect(screen.queryByTestId('train-notification-dot-mobile')).not.toBeNull();
  });

  it('with import and train done the dot moves from Train to Bots', () => {
    profileState = { ...UNLOCKED_PROFILE, feature_route: routeWithDone(['import', 'train']) };
    tier1State = true;
    trainProgressData = { pending_count: 0 };

    const { unmount } = renderNavHeader('/library/games');
    expect(screen.queryByTestId('train-notification-dot')).toBeNull();
    expect(screen.queryByTestId('bots-notification-dot')).not.toBeNull();
    unmount();

    renderMobileBottomBar('/library/games');
    expect(screen.queryByTestId('train-notification-dot-mobile')).toBeNull();
    expect(screen.queryByTestId('bots-notification-dot-mobile')).not.toBeNull();
  });

  it('a zero-game account with import done still gets the Train dot (Train is never locked, D-21)', () => {
    profileState = { ...ZERO_GAME_PROFILE, feature_route: routeWithDone(['import']) };
    tier1State = false;
    trainProgressData = undefined;

    renderNavHeader('/bots');
    expect(screen.queryByTestId('train-notification-dot')).not.toBeNull();
  });

  it('zero-game locked profile: useTrainProgress called with enabled: false, no badge renders', () => {
    profileState = ZERO_GAME_PROFILE;
    tier1State = false;
    trainProgressData = { pending_count: 12 };

    renderNavHeader();
    expect(useTrainProgressSpy).toHaveBeenCalledWith({ enabled: false });
    expect(screen.queryByTestId('train-notification-badge')).toBeNull();
  });

  it('guest profile: useTrainProgress called with enabled: false', () => {
    profileState = GUEST_PROFILE;
    tier1State = true;
    trainProgressData = { pending_count: 12 };

    renderNavHeader();
    expect(useTrainProgressSpy).toHaveBeenCalledWith({ enabled: false });
  });

  it('control: zero-game signup with no steps done shows library-notification-dot on both surfaces (D-18; Import completes when games exist)', () => {
    profileState = { ...ZERO_GAME_PROFILE, feature_route: { steps: {}, current: null } };
    tier1State = false;
    trainProgressData = { pending_count: 12 };

    // Rendered at /bots: at /library the import step's dot correctly moves off
    // the nav item onto the Import subtab (D-03).
    const { unmount } = renderNavHeader('/bots');
    expect(screen.getByTestId('library-notification-dot')).toBeTruthy();
    unmount();

    renderMobileBottomBar('/bots');
    expect(screen.getByTestId('library-notification-dot-mobile')).toBeTruthy();
  });

  it('a profile without feature_route (corrupt or not loaded) shows no route dot', () => {
    profileState = { ...ZERO_GAME_PROFILE, feature_route: null };
    tier1State = false;

    renderNavHeader('/bots');
    expect(screen.queryByTestId('library-notification-dot')).toBeNull();
    expect(screen.queryByTestId('train-notification-dot')).toBeNull();
  });
});

describe('Feature route dot', () => {
  const UNLOCKED: Partial<UserProfile> = {
    email: 'route@example.com',
    is_superuser: false,
    is_guest: false,
    chess_com_game_count: 50,
    lichess_game_count: 0,
    impersonation: null,
  };
  const ZERO_GAME: Partial<UserProfile> = { ...UNLOCKED, chess_com_game_count: 0 };
  const ALL_BUT_ENDGAMES = [
    'import',
    'train',
    'bots',
    'openings',
    'openings-played-as',
    'openings-filters',
    'openings-stats',
    'library-stats',
  ];
  // Every route state below uses current: null (routeWithDone), so the three-active-day
  // skip clock added later cannot expire a step under these cases.

  /** Header dot testids rendered for the current state (desktop surface). */
  function headerDotIds(path: string): string[] {
    const { unmount } = renderNavHeader(path);
    const ids = screen
      .queryAllByTestId(/-notification-dot$/)
      .map((el) => el.getAttribute('data-testid') ?? '');
    unmount();
    return ids;
  }

  function drawerDotIds(path: string): string[] {
    const { unmount } = renderMobileMoreDrawer(path);
    const ids = screen
      .queryAllByTestId(/-notification-dot-drawer$/)
      .map((el) => el.getAttribute('data-testid') ?? '');
    unmount();
    return ids;
  }

  it('zero-game with no steps done shows the Library dot on the header, bottom bar and drawer', () => {
    profileState = { ...ZERO_GAME, feature_route: { steps: {}, current: null } };
    tier1State = false;

    expect(headerDotIds('/bots')).toEqual(['library-notification-dot']);
    expect(drawerDotIds('/bots')).toEqual(['library-notification-dot-drawer']);
    renderMobileBottomBar('/bots');
    expect(screen.getByTestId('library-notification-dot-mobile')).toBeTruthy();
  });

  it('zero-game with no steps done shows no route dot at /library/import (header and drawer)', () => {
    profileState = { ...ZERO_GAME, feature_route: { steps: {}, current: null } };
    tier1State = false;

    // D-14 overruled 2026-11-16: the Import page is not completed by a visit and carries no dot.
    expect(headerDotIds('/library/import')).toEqual([]);
    expect(drawerDotIds('/library/import')).toEqual([]);
  });

  it('zero-game with no steps done keeps the Library dot on the header at /train', () => {
    profileState = { ...ZERO_GAME, feature_route: { steps: {}, current: null } };
    tier1State = false;

    expect(headerDotIds('/train')).toEqual(['library-notification-dot']);
  });

  it('with import done the Library dot is gone from all three surfaces', () => {
    profileState = { ...ZERO_GAME, feature_route: routeWithDone(['import']) };
    tier1State = false;

    expect(headerDotIds('/bots')).not.toContain('library-notification-dot');
    expect(drawerDotIds('/bots')).not.toContain('library-notification-dot-drawer');
    renderMobileBottomBar('/bots');
    expect(screen.queryByTestId('library-notification-dot-mobile')).toBeNull();
  });

  it('D-17: the Train badge and the Bots dot show together, and the drawer carries the Bots dot', () => {
    profileState = { ...UNLOCKED, feature_route: routeWithDone(['import', 'train']) };
    tier1State = true;
    trainProgressData = { pending_count: 12 };

    const { unmount } = renderNavHeader('/library/games');
    expect(screen.getByTestId('train-notification-badge').textContent).toBe('12');
    expect(screen.getByTestId('bots-notification-dot')).toBeTruthy();
    unmount();

    expect(drawerDotIds('/library/games')).toEqual(['bots-notification-dot-drawer']);
  });

  it('D-17: with train open and the badge visible the drawer has no Train dot', () => {
    profileState = { ...UNLOCKED, feature_route: routeWithDone(['import']) };
    tier1State = true;
    trainProgressData = { pending_count: 12 };

    expect(drawerDotIds('/bots')).not.toContain('train-notification-dot-drawer');
    expect(headerDotIds('/bots')).not.toContain('train-notification-dot');
  });

  it('the drawer carries the Train dot when train is open and no badge shows', () => {
    profileState = { ...UNLOCKED, feature_route: routeWithDone(['import']) };
    tier1State = true;
    trainProgressData = { pending_count: 0 };

    expect(drawerDotIds('/bots')).toEqual(['train-notification-dot-drawer']);
  });

  it('D-02: the header carries at most one dot and the drawer dot sits on the same nav item', () => {
    const states: { profile: Partial<UserProfile>; done: string[] | null; tier1: boolean }[] = [
      { profile: ZERO_GAME, done: [], tier1: false },
      { profile: ZERO_GAME, done: ['import'], tier1: false },
      { profile: ZERO_GAME, done: ['import', 'train', 'bots'], tier1: false },
      { profile: UNLOCKED, done: ['import', 'train'], tier1: true },
      { profile: UNLOCKED, done: ['import', 'train', 'bots'], tier1: true },
      { profile: UNLOCKED, done: ALL_BUT_ENDGAMES, tier1: true },
      { profile: UNLOCKED, done: null, tier1: true },
    ];
    for (const { profile, done, tier1 } of states) {
      profileState = { ...profile, feature_route: done == null ? null : routeWithDone(done) };
      tier1State = tier1;
      trainProgressData = { pending_count: 0 };

      const header = headerDotIds('/analysis');
      const drawer = drawerDotIds('/analysis');
      expect(header.length).toBeLessThanOrEqual(1);
      expect(drawer.map((id) => id.replace('-drawer', ''))).toEqual(header);
    }
  });

  it('D-23: a zero-game account with import, train and bots done shows no route dot anywhere', () => {
    profileState = { ...ZERO_GAME, feature_route: routeWithDone(['import', 'train', 'bots']) };
    tier1State = false;

    expect(headerDotIds('/bots')).toEqual([]);
    expect(drawerDotIds('/bots')).toEqual([]);
    renderMobileBottomBar('/bots');
    expect(screen.queryByTestId(/-notification-dot-mobile$/)).toBeNull();
  });

  it('D-23: the same account once unlocked shows the Openings dot on all three surfaces', () => {
    profileState = { ...UNLOCKED, feature_route: routeWithDone(['import', 'train', 'bots']) };
    tier1State = true;
    trainProgressData = { pending_count: 0 };

    expect(headerDotIds('/bots')).toEqual(['openings-notification-dot']);
    expect(drawerDotIds('/bots')).toEqual(['openings-notification-dot-drawer']);
    renderMobileBottomBar('/bots');
    expect(screen.getByTestId('openings-notification-dot-mobile')).toBeTruthy();
  });

  it('D-12: with every step but endgames resolved the Endgames nav item carries the dot', () => {
    profileState = { ...UNLOCKED, feature_route: routeWithDone(ALL_BUT_ENDGAMES) };
    tier1State = true;
    trainProgressData = { pending_count: 0 };

    expect(headerDotIds('/bots')).toEqual(['endgames-notification-dot']);
    expect(drawerDotIds('/bots')).toEqual(['endgames-notification-dot-drawer']);
  });

  it('a profile without feature_route shows no route dot on the drawer (fails closed)', () => {
    profileState = { ...ZERO_GAME, feature_route: null };
    tier1State = false;

    expect(drawerDotIds('/bots')).toEqual([]);
  });

  it('D-03: inside the Train section the nav item and the drawer row carry no Train dot', () => {
    profileState = { ...UNLOCKED, feature_route: routeWithDone(['import']) };
    tier1State = true;
    trainProgressData = { pending_count: 0 };

    expect(headerDotIds('/train')).not.toContain('train-notification-dot');
    expect(drawerDotIds('/train')).not.toContain('train-notification-dot-drawer');
  });
});

describe('/bots active state + mobile header title', () => {
  it('desktop NavHeader marks /bots active when on /bots', () => {
    profileState = {
      email: 'full@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    renderNavHeader('/bots');
    const link = screen.getByTestId('nav-bots');
    expect(link.className).toMatch(/bg-white\/10/);
  });

  it('desktop NavHeader marks /bots active on a /bots/anything sub-route', () => {
    profileState = {
      email: 'full@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    renderNavHeader('/bots/anything');
    const link = screen.getByTestId('nav-bots');
    expect(link.className).toMatch(/bg-white\/10/);
  });

  it('mobile header shows the title "Bots" on /bots', () => {
    profileState = {
      email: 'full@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    renderMobileHeader('/bots');
    expect(screen.getByTestId('mobile-header-page-title').textContent).toBe('Bots');
  });
});

describe('MobileTopBar: no phone header on Library and Endgames', () => {
  const IMPERSONATION = { admin_id: 1, target_email: 'target@example.com' };

  function renderTopBar(path: string, impersonating: boolean) {
    profileState = {
      email: 'full@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: impersonating ? IMPERSONATION : null,
    } as Partial<UserProfile>;
    return render(
      <MemoryRouter initialEntries={[path]}>
        <TooltipProvider>
          <MobileTopBar />
        </TooltipProvider>
      </MemoryRouter>,
    );
  }

  it.each(['/library/import', '/library/flaws', '/endgames/stats', '/endgames/games'])(
    '%s: only the notch inset, hidden on desktop',
    (path) => {
      renderTopBar(path, false);
      expect(screen.queryByTestId('mobile-header')).toBeNull();
      expect(screen.queryByTestId('impersonation-pill')).toBeNull();
      const top = screen.getByTestId('mobile-headerless-top');
      expect(Array.from(top.classList)).toEqual(expect.arrayContaining(['pt-safe', 'lg:hidden']));
    },
  );

  it.each(['/library/flaws', '/endgames/games'])('%s: impersonating keeps the pill and its ×', (path) => {
    renderTopBar(path, true);
    expect(screen.queryByTestId('mobile-header')).toBeNull();
    expect(screen.getByTestId('impersonation-pill').textContent).toContain('target@example.com');
    expect(screen.getByTestId('btn-impersonation-pill-logout')).toBeTruthy();
  });

  it.each(['/train', '/bots', '/admin'])('%s keeps the header, with the pill once', (path) => {
    renderTopBar(path, true);
    expect(screen.getByTestId('mobile-header')).toBeTruthy();
    expect(screen.queryByTestId('mobile-headerless-top')).toBeNull();
    expect(screen.getAllByTestId('impersonation-pill')).toHaveLength(1);
  });
});

describe('MobileBottomBar swaps main nav for board controls', () => {
  const FULL_PROFILE = {
    email: 'full@example.com',
    is_superuser: false,
    is_guest: false,
    chess_com_game_count: 50,
    lichess_game_count: 0,
    impersonation: null,
  } as Partial<UserProfile>;

  it('with nothing published, renders the unchanged main-nav bar', () => {
    profileState = FULL_PROFILE;
    tier1State = true;

    renderMobileBottomBar();
    expect(screen.getByTestId('mobile-bottom-bar')).toBeTruthy();
    expect(screen.getByTestId('mobile-nav-bots')).toBeTruthy();
    expect(screen.queryByTestId('mobile-board-controls-bar')).toBeNull();
  });

  it('while a payload is published, renders the board-controls bar and no nav links', () => {
    profileState = FULL_PROFILE;
    tier1State = true;

    renderMobileBottomBar(
      '/library',
      <MobileBoardControlsProbe
        onBack={vi.fn()}
        onForward={vi.fn()}
        onReset={vi.fn()}
        onFlip={vi.fn()}
        canGoBack
        canGoForward
        canReset
      />,
    );

    expect(screen.getByTestId('mobile-board-controls-bar')).toBeTruthy();
    expect(screen.queryByTestId('mobile-bottom-bar')).toBeNull();
    expect(screen.queryByTestId('mobile-nav-bots')).toBeNull();
    expect(screen.queryByTestId('mobile-nav-more')).toBeNull();
    expect(screen.getByTestId('board-btn-reset')).toBeTruthy();
    expect(screen.getByTestId('board-btn-back')).toBeTruthy();
    expect(screen.getByTestId('board-btn-forward')).toBeTruthy();
    expect(screen.getByTestId('board-btn-flip')).toBeTruthy();
  });

  it('clicking each footer control invokes its matching published callback exactly once', () => {
    profileState = FULL_PROFILE;
    tier1State = true;
    const onBack = vi.fn();
    const onForward = vi.fn();
    const onReset = vi.fn();
    const onFlip = vi.fn();

    renderMobileBottomBar(
      '/library',
      <MobileBoardControlsProbe
        onBack={onBack}
        onForward={onForward}
        onReset={onReset}
        onFlip={onFlip}
        canGoBack
        canGoForward
        canReset
      />,
    );

    fireEvent.click(screen.getByTestId('board-btn-reset'));
    fireEvent.click(screen.getByTestId('board-btn-back'));
    fireEvent.click(screen.getByTestId('board-btn-forward'));
    fireEvent.click(screen.getByTestId('board-btn-flip'));

    expect(onReset).toHaveBeenCalledTimes(1);
    expect(onBack).toHaveBeenCalledTimes(1);
    expect(onForward).toHaveBeenCalledTimes(1);
    expect(onFlip).toHaveBeenCalledTimes(1);
  });

  it('canGoBack: false disables back and reset; canGoForward: false disables forward; flip stays enabled', () => {
    profileState = FULL_PROFILE;
    tier1State = true;

    renderMobileBottomBar(
      '/library',
      <MobileBoardControlsProbe
        onBack={vi.fn()}
        onForward={vi.fn()}
        onReset={vi.fn()}
        onFlip={vi.fn()}
        canGoBack={false}
        canGoForward={false}
        canReset={false}
      />,
    );

    expect(screen.getByTestId('board-btn-back')).toHaveProperty('disabled', true);
    expect(screen.getByTestId('board-btn-reset')).toHaveProperty('disabled', true);
    expect(screen.getByTestId('board-btn-forward')).toHaveProperty('disabled', true);
    expect(screen.getByTestId('board-btn-flip')).toHaveProperty('disabled', false);
  });

  it('unmounting the publisher restores the main-nav bar', () => {
    profileState = FULL_PROFILE;
    tier1State = true;

    const { unmount } = render(
      <MemoryRouter initialEntries={['/library']}>
        <TooltipProvider>
          <MobileBoardControlsProbe
            onBack={vi.fn()}
            onForward={vi.fn()}
            onReset={vi.fn()}
            onFlip={vi.fn()}
            canGoBack
            canGoForward
            canReset
          />
          <MobileBottomBar onMoreClick={() => {}} />
        </TooltipProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId('mobile-board-controls-bar')).toBeTruthy();

    unmount();

    renderMobileBottomBar();
    expect(screen.getByTestId('mobile-bottom-bar')).toBeTruthy();
  });
});

// A payload carrying a resign action is the
// bot game's — MobileBottomBar swaps in the four-action BotGameMobileBar
// instead of the shared BoardControls row.
describe('MobileBottomBar swaps to the bot four-action bar', () => {
  const FULL_PROFILE = {
    email: 'full@example.com',
    is_superuser: false,
    is_guest: false,
    chess_com_game_count: 50,
    lichess_game_count: 0,
    impersonation: null,
  } as Partial<UserProfile>;

  function MobileBoardControlsResignProbe(props: {
    onResign: () => void;
    onBack: () => void;
    onForward: () => void;
    onFlip: () => void;
    canGoBack: boolean;
    canGoForward: boolean;
  }) {
    usePublishMobileBoardControls(props);
    return null;
  }

  it('renders the bot bar with no main-nav links when the payload carries onResign', () => {
    profileState = FULL_PROFILE;
    tier1State = true;

    renderMobileBottomBar(
      '/bots',
      <MobileBoardControlsResignProbe
        onResign={vi.fn()}
        onBack={vi.fn()}
        onForward={vi.fn()}
        onFlip={vi.fn()}
        canGoBack
        canGoForward
      />,
    );

    expect(screen.getByTestId('mobile-board-controls-bar')).toBeTruthy();
    expect(screen.getByTestId('bot-game-mobile-bar')).toBeTruthy();
    expect(screen.getByTestId('board-btn-resign')).toBeTruthy();
    expect(screen.queryByTestId('mobile-bottom-bar')).toBeNull();
    expect(screen.queryByTestId('mobile-nav-bots')).toBeNull();
    expect(screen.queryByTestId('mobile-nav-more')).toBeNull();
    expect(screen.queryByTestId('board-btn-reset')).toBeNull();
  });

  it('regression: a payload WITHOUT onResign still renders the shared BoardControls row', () => {
    profileState = FULL_PROFILE;
    tier1State = true;

    renderMobileBottomBar(
      '/library',
      <MobileBoardControlsProbe
        onBack={vi.fn()}
        onForward={vi.fn()}
        onReset={vi.fn()}
        onFlip={vi.fn()}
        canGoBack
        canGoForward
        canReset
      />,
    );

    expect(screen.getByTestId('mobile-board-controls-bar')).toBeTruthy();
    expect(screen.getByTestId('board-btn-reset')).toBeTruthy();
    expect(screen.queryByTestId('bot-game-mobile-bar')).toBeNull();
    expect(screen.queryByTestId('board-btn-resign')).toBeNull();
  });
});

describe('MobileBottomBar swaps to the Train reveal bar', () => {
  const FULL_PROFILE = {
    email: 'full@example.com',
    is_superuser: false,
    is_guest: false,
    chess_com_game_count: 50,
    lichess_game_count: 0,
    impersonation: null,
  } as Partial<UserProfile>;

  function MobileBoardControlsRevealProbe(props: {
    onNext: () => void;
    analyzeTo: string | null;
    onAnalyzeClick: () => void;
    onReset?: () => void;
    spotlightAnalyze?: boolean;
  }) {
    usePublishMobileBoardControls({
      onBack: vi.fn(),
      onForward: vi.fn(),
      onReset: props.onReset ?? vi.fn(),
      onFlip: vi.fn(),
      canGoBack: true,
      canGoForward: true,
      canReset: true,
      onNext: props.onNext,
      analyzeTo: props.analyzeTo,
      onAnalyzeClick: props.onAnalyzeClick,
      spotlightAnalyze: props.spotlightAnalyze,
    });
    return null;
  }

  it('a Train reveal payload renders the reveal bar: board buttons, Analyze link with its href, Next; clicking Next / Analyze calls the published callbacks', () => {
    profileState = FULL_PROFILE;
    tier1State = true;
    const onNext = vi.fn();
    const onAnalyzeClick = vi.fn();
    const onReset = vi.fn();

    renderMobileBottomBar(
      '/train',
      <MobileBoardControlsRevealProbe
        onNext={onNext}
        analyzeTo="/analysis/100?ply=19"
        onAnalyzeClick={onAnalyzeClick}
        onReset={onReset}
      />,
    );

    expect(screen.getByTestId('mobile-board-controls-bar')).toBeTruthy();
    expect(screen.getByTestId('train-reveal-action-bar')).toBeTruthy();
    expect(screen.queryByTestId('mobile-bottom-bar')).toBeNull();
    expect(screen.queryByTestId('bot-game-mobile-bar')).toBeNull();
    expect(screen.getByTestId('board-btn-reset')).toBeTruthy();
    expect(screen.getByTestId('board-btn-back')).toBeTruthy();
    expect(screen.getByTestId('board-btn-forward')).toBeTruthy();
    // The reveal bar has no flip control (Phase 249 UAT).
    expect(screen.queryByTestId('board-btn-flip')).toBeNull();
    expect(screen.getByTestId('btn-train-analyze').getAttribute('href')).toBe('/analysis/100?ply=19');

    fireEvent.click(screen.getByTestId('btn-train-next'));
    fireEvent.click(screen.getByTestId('btn-train-analyze'));
    fireEvent.click(screen.getByTestId('board-btn-reset'));
    expect(onNext).toHaveBeenCalledTimes(1);
    expect(onAnalyzeClick).toHaveBeenCalledTimes(1);
    expect(onReset).toHaveBeenCalledTimes(1);
  });

  it('with analyzeTo null no Analyze renders', () => {
    profileState = FULL_PROFILE;
    tier1State = true;

    renderMobileBottomBar(
      '/train',
      <MobileBoardControlsRevealProbe onNext={vi.fn()} analyzeTo={null} onAnalyzeClick={vi.fn()} />,
    );

    expect(screen.getByTestId('btn-train-next')).toBeTruthy();
    expect(screen.queryByTestId('btn-train-analyze')).toBeNull();
  });

  // The tour's Analyze step spotlights the fixed bar's Analyze
  // button alone (never the whole bar), exactly while the payload says so.
  it('a payload with spotlightAnalyze true spotlights the Analyze button, not the bar', () => {
    profileState = FULL_PROFILE;
    tier1State = true;

    renderMobileBottomBar(
      '/train',
      <MobileBoardControlsRevealProbe
        onNext={vi.fn()}
        analyzeTo="/analysis/100?ply=19"
        onAnalyzeClick={vi.fn()}
        spotlightAnalyze
      />,
    );

    expect(screen.getByTestId('btn-train-analyze').classList.contains(TOUR_SPOTLIGHT_CLASS)).toBe(true);
    expect(screen.getByTestId('train-reveal-action-bar').classList.contains(TOUR_SPOTLIGHT_CLASS)).toBe(false);
  });

  it.each([{ spotlightAnalyze: false }, {}])('a payload with spotlightAnalyze %o spotlights nothing', (extra) => {
    profileState = FULL_PROFILE;
    tier1State = true;

    renderMobileBottomBar(
      '/train',
      <MobileBoardControlsRevealProbe
        onNext={vi.fn()}
        analyzeTo="/analysis/100?ply=19"
        onAnalyzeClick={vi.fn()}
        {...extra}
      />,
    );

    expect(screen.getByTestId('btn-train-analyze').classList.contains(TOUR_SPOTLIGHT_CLASS)).toBe(false);
    expect(screen.getByTestId('train-reveal-action-bar').classList.contains(TOUR_SPOTLIGHT_CLASS)).toBe(false);
  });
});

// The hosted Activity Pulse dashboard's nav entry
// mirrors ADMIN_NAV_ITEM's conditional-append pattern on both nav surfaces —
// present for superusers on both NavHeader and MobileMoreDrawer, absent on
// both for everyone else.
describe('/activity nav entry (superuser-only)', () => {
  it('desktop NavHeader: is_superuser true -> renders nav-activity', () => {
    profileState = {
      email: 'admin@example.com',
      is_superuser: true,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    renderNavHeader();

    expect(screen.getByTestId('nav-activity')).toBeTruthy();
  });

  it('more drawer (MobileMoreDrawer): is_superuser true -> renders drawer-nav-activity', () => {
    profileState = {
      email: 'admin@example.com',
      is_superuser: true,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    renderMobileMoreDrawer();

    expect(screen.getByTestId('drawer-nav-activity')).toBeTruthy();
  });

  it('desktop NavHeader: is_superuser false -> renders NO activity entry', () => {
    profileState = {
      email: 'regular@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    renderNavHeader();

    expect(screen.queryByTestId('nav-activity')).toBeNull();
  });

  it('more drawer (MobileMoreDrawer): is_superuser false -> renders NO activity entry', () => {
    profileState = {
      email: 'regular@example.com',
      is_superuser: false,
      is_guest: false,
      chess_com_game_count: 50,
      lichess_game_count: 0,
      impersonation: null,
    } as Partial<UserProfile>;
    tier1State = true;

    renderMobileMoreDrawer();

    expect(screen.queryByTestId('drawer-nav-activity')).toBeNull();
  });
});

// ── Settings overlay entry (no /settings page) ────────────────────────────────

describe('settings overlay entry', () => {
  afterEach(() => {
    localStorage.removeItem(MUTE_KEY);
    Object.values(SETTINGS_STORAGE_KEYS).forEach((key) => localStorage.removeItem(key));
  });

  it('tracer: header cogwheel opens the settings modal in place and the panel writes the store', async () => {
    render(
      <MemoryRouter initialEntries={['/library']}>
        <TooltipProvider>
          <NavHeader />
          <Routes>
            <Route path="/library" element={<div data-testid="library-sentinel" />} />
          </Routes>
        </TooltipProvider>
      </MemoryRouter>,
    );

    const cogwheel = screen.getByTestId('nav-settings');
    expect(cogwheel.getAttribute('aria-label')).toBe('Settings');
    expect(cogwheel.getAttribute('title')).toBe('Settings');
    expect(cogwheel.getAttribute('href')).toBeNull();

    fireEvent.click(cogwheel);
    const dialog = await screen.findByTestId('settings-dialog');
    // aria-modal gates useBoardNavigationInput's arrow-key suppression.
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(screen.getByTestId('library-sentinel')).toBeTruthy();

    fireEvent.click(screen.getByTestId('settings-sound-switch'));
    expect(localStorage.getItem(MUTE_KEY)).toBe('1');

    fireEvent.click(screen.getByTestId('settings-sf-lines-3'));
    expect(localStorage.getItem(SETTINGS_STORAGE_KEYS.sfLines)).toBe('3');
    expect(screen.getByTestId('settings-sf-lines-3').getAttribute('data-state')).toBe('on');
  });

  it('nav-settings is not part of the main navigation (NAV_ITEMS untouched)', () => {
    renderNavHeader();
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    expect(screen.getByTestId('nav-settings')).toBeTruthy();
    expect(within(nav).queryByTestId('nav-settings')).toBeNull();
  });

  it('more drawer: drawer-settings opens the settings sheet, precedes drawer-logout, and is not a drawer-nav entry', async () => {
    renderMobileMoreDrawer();
    const row = screen.getByTestId('drawer-settings');
    expect(row.getAttribute('href')).toBeNull();
    const logout = screen.getByTestId('drawer-logout');
    expect(row.compareDocumentPosition(logout) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const navTestIds = Array.from(document.querySelectorAll('[data-testid^="drawer-nav-"]')).map((el) =>
      el.getAttribute('data-testid'),
    );
    expect(navTestIds.some((id) => id?.includes('settings'))).toBe(false);

    fireEvent.click(row);
    expect(await screen.findByTestId('settings-sheet')).toBeTruthy();
  });
});

// ── Nav and drawer tracking ─────────────────────────────────────────────────
// trackFeature derives `page` from window.location (not the MemoryRouter), so the
// path is set with history.pushState. Events reach window.umami.track via the real
// analytics module.
describe('nav and drawer tracking', () => {
  const track = vi.fn();
  const fullProfile = (isSuperuser: boolean): Partial<UserProfile> => ({
    email: 'tracked@example.com',
    is_superuser: isSuperuser,
    is_guest: false,
    chess_com_game_count: 50,
    lichess_game_count: 0,
    impersonation: null,
  });

  beforeEach(() => {
    track.mockClear();
    window.umami = { track, identify: vi.fn() };
    window.history.pushState({}, '', '/library');
  });

  afterEach(() => {
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  it('MobileBottomBar: tapping More calls onMoreClick and sends one panel-open more-drawer', () => {
    profileState = fullProfile(false);
    tier1State = true;
    const onMoreClick = vi.fn();
    render(
      <MemoryRouter initialEntries={['/library']}>
        <TooltipProvider>
          <MobileBottomBar onMoreClick={onMoreClick} />
        </TooltipProvider>
      </MemoryRouter>,
    );
    expect(track).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('mobile-nav-more'));
    expect(onMoreClick).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('panel-open', { page: 'library', target: 'more-drawer' });
  });

  it('MobileMoreDrawer: a nav item sends one nav-click with value more-drawer', () => {
    profileState = fullProfile(false);
    tier1State = true;
    renderMobileMoreDrawer();
    expect(track).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('drawer-nav-library'));
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('nav-click', {
      page: 'library',
      target: 'library',
      value: 'more-drawer',
    });
  });

  it('MobileMoreDrawer: a locked item sends nothing', () => {
    profileState = {
      ...fullProfile(false),
      chess_com_game_count: 0,
      lichess_game_count: 0,
    };
    tier1State = false;
    renderMobileMoreDrawer();

    const locked = screen.getByTestId('drawer-nav-openings');
    expect(locked.getAttribute('aria-disabled')).toBe('true');
    fireEvent.click(locked);
    expect(track).not.toHaveBeenCalled();
  });

  it('MobileMoreDrawer: superuser Admin and Activity items never send nav-click', () => {
    profileState = fullProfile(true);
    tier1State = true;
    renderMobileMoreDrawer();

    fireEvent.click(screen.getByTestId('drawer-nav-admin'));
    fireEvent.click(screen.getByTestId('drawer-nav-activity'));
    expect(track).not.toHaveBeenCalled();
  });

  it('MobileMoreDrawer: the Settings row sends one panel-open settings', () => {
    profileState = fullProfile(false);
    tier1State = true;
    renderMobileMoreDrawer();
    expect(track).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('drawer-settings'));
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('panel-open', { page: 'library', target: 'settings' });
  });
});
