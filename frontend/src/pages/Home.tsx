import { Navigate, useNavigate } from 'react-router-dom';
import { Link } from 'react-router-dom';
import * as Sentry from '@sentry/react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/api/client';
import type { UserProfile } from '@/types/users';
import { PublicHeader } from '@/components/layout/PublicHeader';
import { Button } from '@/components/ui/button';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { cn } from '@/lib/utils';
import { Scale, Filter, TrophyIcon, Timer, Compass, Loader2, UserPlus, DoorOpen } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

// Feature sections — the first entry is rendered in the hero (desktop right column +
// mobile standalone section); the rest alternate image left/right below.
// All screenshots are landscape orientation with a 2fr/3fr text/image ratio.
const FEATURES: {
  slug: string;
  icon: LucideIcon;
  heading: string;
  desc: string | string[];
  screenshot: { src: string; alt: string };
  imagePosition: 'left' | 'right';
}[] = [
  {
    slug: 'opening-explorer',
    icon: Compass,
    heading: 'Opening Explorer & Insights',
    desc: [
        'Get a detailed statistical analysis for every move you’ve played.',
        'Compare your win/draw/loss rate to the Stockfish evaluation at the end of the opening.',
        'Scan the first 8 moves of all your games to surface opening strengths and weaknesses.',
        'Scout your opponent\'s repertoire before a match.',
    ],
    screenshot: { src: '/screenshots/opening-explorer.png', alt: 'Board with move explorer showing win/draw/loss rate and stockfish evaluation per candidate move' },
    imagePosition: 'right',
  },
  {
    slug: 'endgame-analytics',
    icon: TrophyIcon,
    heading: 'Endgame Analytics',
    desc: [
      'Measure how well you convert winning endgames and recover from losing ones.',
      'Track your Endgame ELO over time by platform and time control.',
      'Get personalized feedback on what your stats mean.',
    ],
    screenshot: { src: '/screenshots/endgame-metrics-and-elo-llm-badge.png', alt: 'Endgame metrics and Endgame ELO timeline over time' },
    imagePosition: 'left',
  },
  {
    slug: 'time-management',
    icon: Timer,
    heading: 'Time Management Stats',
    desc: [
        'See your average time advantage or deficit when entering the endgame.',
        'Find out if you crack under time pressure more than your opponents.',
        'Compare your flag rate to your opponents\' per time control.',
    ],
    screenshot: { src: '/screenshots/time-management-stats.png', alt: 'Average clock difference over time and time-pressure-vs-performance charts' },
    imagePosition: 'right',
  },
  {
    slug: 'opening-comparison',
    icon: Scale,
    heading: 'Opening Comparison and Tracking',
    desc: [
        'Bookmark your favorite openings and compare their performance.',
        'See how your opening study impacts your win rate over time.',
        'Filter by time control to find which openings work best where.',
    ],
    screenshot: { src: '/screenshots/opening-comparison.png', alt: 'Win rate trends over time for multiple openings' },
    imagePosition: 'left',
  },
  {
    slug: 'system-openings',
    icon: Filter,
    heading: 'System Opening Filter',
    desc: [
        'Group system openings (like the London) across all variations.',
        'Filter by your pieces only, ignoring opponents\' responses.',
        'Get win/draw/loss rates for the entire system, not scattered names.',
    ],
    screenshot: { src: '/screenshots/system-openings.png', alt: 'Opening bookmarks grouping system opening variations' },
    imagePosition: 'right',
  },
];

// ─── Homepage content (unauthenticated) ───────────────────────────────────────

// Hero shows the first feature in its right column (desktop) and as a standalone
// charcoal section (mobile). The remaining features render in the alternating
// screenshots grid below.
const heroFeature = FEATURES[0]!;
const featureSections = FEATURES.slice(1);
const HeroIcon = heroFeature.icon;
const heroDescItems = Array.isArray(heroFeature.desc) ? heroFeature.desc : [heroFeature.desc];

export function HomePageContent() {
  const { loginAsGuest, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleGuestLogin = async () => {
    try {
      await loginAsGuest();
      navigate('/');
    } catch (error) {
      Sentry.captureException(error, { tags: { source: 'guest-login-home' } });
      toast.error('Failed to start guest session. Please try again.');
    }
  };

  return (
    <>
      <PublicHeader />

      {/* Hero — radial bronze glow is centered on just the hero content (not the
          stacked Opening Explorer below, which has its own charcoal section) */}
      <div className="bg-[radial-gradient(ellipse_at_center,rgba(205,127,50,0.12),transparent_65%)]">
      <section data-testid="hero-section" className="max-w-6xl mx-auto px-4 py-8 lg:py-12">
        <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-8 lg:gap-12 items-center">
          {/* Left column: existing hero content — centered at all breakpoints. */}
          <div className="text-center" data-testid="hero-left-column">
            <img
              src="/icons/logo-384.png"
              alt="FlawChess logo"
              className="mx-auto mb-2 h-32 w-32 lg:h-36 lg:w-36"
            />
            <h1 className="text-3xl lg:text-4xl font-bold leading-tight font-brand">
              Engines are flawless, humans play{' '}
              <span className="bg-gradient-to-r from-brand-brown-light to-brand-brown bg-clip-text text-transparent">
                FlawChess
              </span>
            </h1>
            {/* Decorative light-burst divider — golden bronze glow matching the hero radial. Desktop only. */}
            <div
              aria-hidden="true"
              className="relative mx-auto mt-6 hidden h-10 w-full max-w-lg lg:block"
              data-testid="hero-divider"
            >
              {/* Thin line, transparent → bronze → bright center → bronze → transparent */}
              <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-[linear-gradient(to_right,transparent,rgba(205,127,50,0.85)_25%,#FFE9B8_50%,rgba(205,127,50,0.85)_75%,transparent)]" />
              {/* Outer wide soft halo */}
              <div className="absolute left-1/2 top-1/2 h-10 w-72 -translate-x-1/2 -translate-y-1/2 bg-[radial-gradient(ellipse_at_center,rgba(205,127,50,0.35),transparent_70%)] blur-md" />
            </div>
            <p className="mt-4 text-base leading-relaxed text-muted-foreground">
              Free analysis across your chess.com and lichess games, with AI-narrated insights. Find leaks in your openings, endgames, and time management.
            </p>
            <div className="mt-8 flex flex-row items-center justify-center gap-3">
              <Button
                size="lg"
                asChild
                className="min-h-11 min-w-40"
                data-testid="hero-cta-signup"
              >
                <Link to="/login?tab=register">
                  <UserPlus className="mr-1.5 h-4 w-4" />
                  Sign up free
                </Link>
              </Button>
              <Button
                size="lg"
                variant="brand-outline"
                className="min-h-11 min-w-40"
                data-testid="btn-guest"
                onClick={handleGuestLogin}
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <DoorOpen className="mr-1.5 h-4 w-4" />
                    Use as Guest
                  </>
                )}
              </Button>
            </div>
            {/* Callout pills — desktop only (hidden on mobile / small desktop) */}
            <div className="mt-10 hidden lg:flex flex-wrap justify-center gap-2">
              <span className="bg-muted text-muted-foreground w-44 rounded-full px-4 py-1 text-center text-sm">
                All features free
              </span>
              <span className="bg-muted text-muted-foreground w-44 rounded-full px-4 py-1 text-center text-sm">
                No signup required
              </span>
            </div>
          </div>

          {/* Right column: hero feature preview — lg and up only.
              Title → image → bullets stacking matches the feature sections below.
              Below lg the preview renders as a standalone charcoal section further down. */}
          <div data-testid="hero-feature-preview" className="hidden lg:block">
            <div className="flex items-center gap-4 mb-4">
              <HeroIcon className="h-7 w-7 lg:h-10 lg:w-10 text-muted-foreground shrink-0" strokeWidth={1.5} />
              <h2 className="text-xl lg:text-2xl font-bold">{heroFeature.heading}</h2>
            </div>
            <img
              src={heroFeature.screenshot.src}
              alt={heroFeature.screenshot.alt}
              className="rounded-lg border border-[rgba(205,127,50,0.85)] shadow-[0_0_24px_rgba(205,127,50,0.35)] w-full mb-4"
            />
            <ul className="list-disc pl-5 space-y-1 text-base leading-relaxed text-muted-foreground">
              {heroDescItems.map((item, i) => <li key={i}>{item}</li>)}
            </ul>
          </div>
        </div>
      </section>
      </div>

      {/* Hero feature — standalone section (mobile / small desktop only).
          Title → image → bullets, matching the feature sections below. Hidden on lg+
          because the hero's right column already shows the same content there. */}
      <section
        data-testid={`feature-${heroFeature.slug}-mobile`}
        className="lg:hidden bg-[#1a1a1a] py-12"
      >
        <div className="max-w-5xl mx-auto px-4 flex flex-col gap-6">
          <div className="flex items-center gap-4">
            <HeroIcon className="h-7 w-7 lg:h-10 lg:w-10 text-muted-foreground shrink-0" strokeWidth={1.5} />
            <h2 className="text-xl lg:text-2xl font-bold">{heroFeature.heading}</h2>
          </div>
          <img
            src={heroFeature.screenshot.src}
            alt={heroFeature.screenshot.alt}
            className="rounded-lg border border-[rgba(205,127,50,0.85)] shadow-[0_0_24px_rgba(205,127,50,0.35)] w-full"
          />
          <ul className="list-disc pl-5 space-y-1 text-base leading-relaxed text-muted-foreground">
            {heroDescItems.map((item, i) => <li key={i}>{item}</li>)}
          </ul>
        </div>
      </section>

      {/* Feature sections — alternating image left/right (skips the hero feature) */}
      <div id="features" data-testid="screenshots-section" className="scroll-mt-16">
        {featureSections.map(({ slug, icon: Icon, heading, desc, screenshot, imagePosition }, index) => {
          // On desktop, even-indexed features get charcoal bg. On mobile the Interactive
          // Opening Explorer (charcoal) sits in front of the feature list, so the mobile
          // alternation is flipped: odd-indexed features get charcoal on mobile to avoid
          // two consecutive charcoal bands at the top of the stack.
          const bgClass = index % 2 === 0
            ? 'lg:bg-[#1a1a1a]'
            : 'max-lg:bg-[#1a1a1a]';
          const gridCols = imagePosition === 'left'
            ? 'lg:grid-cols-[3fr_2fr]'
            : 'lg:grid-cols-[2fr_3fr]';

          const titleBlock = (
            <div className="flex items-center gap-4">
              <Icon className="h-7 w-7 lg:h-10 lg:w-10 text-muted-foreground shrink-0" strokeWidth={1.5} />
              <h2 className="text-xl lg:text-2xl font-bold">{heading}</h2>
            </div>
          );
          const bulletsBlock = Array.isArray(desc) ? (
            <ul className="list-disc pl-5 space-y-1 text-base leading-relaxed text-muted-foreground">
              {desc.map((item, i) => <li key={i}>{item}</li>)}
            </ul>
          ) : (
            <p className="text-base leading-relaxed text-muted-foreground">{desc}</p>
          );
          const imageBlock = (
            <img
              src={screenshot.src}
              alt={screenshot.alt}
              className="rounded-lg border border-[rgba(205,127,50,0.85)] shadow-[0_0_24px_rgba(205,127,50,0.35)] w-full lg:transition-transform lg:duration-300 lg:hover:scale-[1.02] lg:hover:shadow-[0_0_32px_rgba(205,127,50,0.5)]"
            />
          );
          const desktopTextCol = (
            <div>
              {titleBlock}
              <div className="mt-3">{bulletsBlock}</div>
            </div>
          );
          return (
            <section
              key={slug}
              data-testid={`feature-${slug}`}
              className={cn('py-12 lg:py-16', bgClass)}
            >
              {/* Mobile layout: title → image → bullets stacked in a single column. */}
              <div className="lg:hidden max-w-5xl mx-auto px-4 flex flex-col gap-6">
                {titleBlock}
                {imageBlock}
                {bulletsBlock}
              </div>
              {/* Desktop layout: 2-col grid alternating image left/right, text column
                  stacks title above bullets. */}
              <div className={cn('hidden lg:grid max-w-5xl mx-auto px-4 gap-12 items-center', gridCols)}>
                {imagePosition === 'left' ? (
                  <>
                    {imageBlock}
                    {desktopTextCol}
                  </>
                ) : (
                  <>
                    {desktopTextCol}
                    {imageBlock}
                  </>
                )}
              </div>
            </section>
          );
        })}
      </div>

      {/* Development banner */}
      <div className="max-w-2xl mx-auto px-4 pt-12">
        <p
          className="mx-auto max-w-lg rounded-lg border border-[rgba(205,127,50,0.85)] shadow-[0_0_24px_rgba(205,127,50,0.35)] px-4 py-3 text-sm text-muted-foreground text-center"
          data-testid="beta-badge"
        >
          🏗️ Under active development. Bug
          reports and feature requests are welcome on{' '}
          <a
            href="https://github.com/flawchess/flawchess"
            className="text-primary underline-offset-4 hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>{' '}
          or via{' '}
          <a
            href="mailto:support@flawchess.com"
            className="text-primary underline-offset-4 hover:underline"
          >
            support@flawchess.com
          </a>.
        </p>
      </div>

      {/* FAQ */}
      <section id="faq" className="max-w-2xl mx-auto px-4 py-12 scroll-mt-16">
        <h2 className="text-xl font-bold mb-6">Frequently asked questions</h2>
        <Accordion type="single" collapsible data-testid="faq-accordion">
          <AccordionItem value="data" data-testid="faq-item-data">
            <AccordionTrigger>
              What data do you access from my chess.com or lichess account?
            </AccordionTrigger>
            <AccordionContent>
              Only your games &mdash; no passwords or personal information. Your games are publicly
              accessible via their APIs, and FlawChess reads them just like any other analysis tool.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="free" data-testid="faq-item-free">
            <AccordionTrigger>Is it free?</AccordionTrigger>
            <AccordionContent>Yes, FlawChess is completely free to use.</AccordionContent>
          </AccordionItem>
          <AccordionItem value="mobile" data-testid="faq-item-mobile">
            <AccordionTrigger>Can I use it on mobile?</AccordionTrigger>
            <AccordionContent>
              Yes. FlawChess is a Progressive Web App &mdash; install it from your browser for a
              native-like experience on iPhone and Android.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="endgames" data-testid="faq-item-endgames">
            <AccordionTrigger>What endgame analytics does FlawChess offer?</AccordionTrigger>
            <AccordionContent>
              FlawChess tracks your win/draw/loss rates by Endgame Type (rook, minor piece, pawn,
              queen, and more), plus conversion rates when you enter the endgame ahead and recovery
              rates when you enter behind, scored against Stockfish evaluation. All statistics are
              filterable by time control, color, and recency.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="engine" data-testid="faq-item-engine">
            <AccordionTrigger>Does FlawChess use a chess engine?</AccordionTrigger>
            <AccordionContent>
              Yes. Stockfish 18 evaluates key transition positions in your games (end of opening,
              endgame entry) so we can compare your actual results against the engine's
              verdict.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="requests" data-testid="faq-item-requests">
            <AccordionTrigger>Where can I make feature requests?</AccordionTrigger>
            <AccordionContent>
              Open an issue on{' '}
              <a
                href="https://github.com/flawchess/flawchess"
                className="text-primary underline-offset-4 hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
              . Contributions and feedback are welcome.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="who" data-testid="faq-item-who">
            <AccordionTrigger>Who develops FlawChess?</AccordionTrigger>
            <AccordionContent>
              FlawChess is an open source project developed independently. Find the code on{' '}
              <a
                href="https://github.com/flawchess/flawchess"
                className="text-primary underline-offset-4 hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub
              </a>, contribute,
              or reach out at{' '}
              <a
                href="mailto:support@flawchess.com"
                className="text-primary underline-offset-4 hover:underline"
              >
                support@flawchess.com
              </a>
              .
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </section>

      {/* Acknowledgements */}
      <section data-testid="acknowledgements-section" className="max-w-2xl mx-auto px-4 py-12">
        <h2 className="text-xl font-bold mb-6">Acknowledgements</h2>
        <p className="text-base text-muted-foreground leading-relaxed mb-4">
          FlawChess is built with and inspired by these projects:
        </p>
        <ul className="list-disc pl-5 space-y-1.5 text-base text-muted-foreground">
          <li>
            <a
              href="https://lichess.org"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Lichess
            </a>{' '}
            &mdash; open-source chess platform and game data API
          </li>
          <li>
            <a
              href="https://chess.com"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Chess.com
            </a>{' '}
            &mdash; chess platform and game data API
          </li>
          <li>
            <a
              href="https://www.openingtree.com"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              OpeningTree.com
            </a>{' '}
            &mdash; inspiration for position-based opening analysis
          </li>
          <li>
            <a
              href="https://chessgoals.com/rating-comparison"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              ChessGoals
            </a>{' '}
            &mdash; cross-platform rating comparison data
          </li>
          <li>
            <a
              href="https://python-chess.readthedocs.io"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              python-chess
            </a>{' '}
            &mdash; chess logic, move generation, and Zobrist hashing
          </li>
          <li>
            <a
              href="https://stockfishchess.org"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Stockfish
            </a>{' '}
            &mdash; open-source chess engine for position evaluation
          </li>
          <li>
            <a
              href="https://fastapi.tiangolo.com"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              FastAPI
            </a>{' '}
            &mdash; async Python web framework
          </li>
          <li>
            <a
              href="https://github.com/jhlywa/chess.js"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              chess.js
            </a>{' '}
            &mdash; chess move validation and game state
          </li>
          <li>
            <a
              href="https://github.com/Clariity/react-chessboard"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              react-chessboard
            </a>{' '}
            &mdash; interactive chessboard component
          </li>
          <li>
            <a
              href="https://recharts.org"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Recharts
            </a>{' '}
            &mdash; composable chart library
          </li>
        </ul>
      </section>

      {/* Footer CTA */}
      <section className="text-center py-16" data-testid="footer-cta">
        <p className="text-muted-foreground mb-4">Free to use. No credit card required.</p>
        <div className="flex flex-row items-center justify-center gap-3">
          <Button
            size="lg"
            asChild
            className="min-h-11 min-w-40"
            data-testid="footer-cta-signup"
          >
            <Link to="/login?tab=register">
              <UserPlus className="mr-1.5 h-4 w-4" />
              Sign up free
            </Link>
          </Button>
          <Button
            size="lg"
            variant="brand-outline"
            className="min-h-11 min-w-40"
            data-testid="footer-btn-guest"
            onClick={handleGuestLogin}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <DoorOpen className="mr-1.5 h-4 w-4" />
                Use as Guest
              </>
            )}
          </Button>
        </div>
      </section>

      {/* Page footer */}
      <footer
        className="text-sm text-muted-foreground text-center py-6 border-t border-border"
        data-testid="page-footer"
      >
        &copy; {new Date().getFullYear()} FlawChess
        <Link to="/privacy" className="ml-4 text-primary underline-offset-4 hover:underline">
          Privacy Policy
        </Link>
      </footer>
    </>
  );
}

// ─── Public export ────────────────────────────────────────────────────────────

export function HomePage() {
  const { token } = useAuth();
  // Only fetch profile when authenticated to avoid a 401 that would trigger
  // the response interceptor's redirect-to-login on the public homepage.
  const { data: profile, isLoading } = useQuery<UserProfile>({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const res = await apiClient.get<UserProfile>('/users/me/profile');
      return res.data;
    },
    enabled: !!token,
    staleTime: 300_000,
  });

  if (token) {
    // Wait for profile to load to avoid flashing the wrong page. For returning
    // users the cache is warm (staleTime 5 min) so this is near-instant.
    if (isLoading) {
      return (
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      );
    }
    // New users (0 games on both platforms) land on /import for onboarding.
    const hasGames =
      (profile?.chess_com_game_count ?? 0) + (profile?.lichess_game_count ?? 0) > 0;
    return <Navigate to={hasGames ? '/openings' : '/library/import'} replace />;
  }

  return <HomePageContent />;
}
