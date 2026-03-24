import { Navigate } from 'react-router-dom';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
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
import { PRIMARY_BUTTON_CLASS } from '@/lib/theme';
import { cn } from '@/lib/utils';
import { Target, Eye, ArrowRightLeft, Layers, SlidersHorizontal, Swords, Loader2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

// USPs with screenshots — order alternates landscape/portrait for visual rhythm.
// imagePosition alternates right/left so text and image swap sides on desktop.
const FEATURES: {
  slug: string;
  icon: LucideIcon;
  heading: string;
  desc: string;
  screenshot: { src: string; alt: string; orientation: 'landscape' | 'portrait' };
  imagePosition: 'left' | 'right';
}[] = [
  {
    slug: 'move-explorer',
    icon: ArrowRightLeft,
    heading: 'Interactive move explorer',
    desc: "Step through any opening and see your win/draw/loss rate for every move you\u2019ve played.",
    screenshot: { src: '/screenshots/board-and-move-explorer.png', alt: 'Board with move explorer showing win/draw/loss bars per move', orientation: 'landscape' },
    imagePosition: 'right',
  },
  {
    slug: 'scout',
    icon: Eye,
    heading: 'Scout your opponents',
    desc: 'Prepare for a match by exploring their opening weaknesses and tendencies.',
    screenshot: { src: '/screenshots/chess-board-and-moves.png', alt: 'Chess board with move analysis and opening classification', orientation: 'portrait' },
    imagePosition: 'left',
  },
  {
    slug: 'weaknesses',
    icon: Target,
    heading: 'Find weaknesses in your openings',
    desc: 'Discover which moves you struggle against, which traps and gambits you fall for or work for you, and how your opening repertoire performs over time.',
    screenshot: { src: '/screenshots/win-rate-over-time.png', alt: 'Win rate trends over time for multiple openings', orientation: 'landscape' },
    imagePosition: 'right',
  },
  {
    slug: 'filters',
    icon: SlidersHorizontal,
    heading: 'Powerful filters',
    desc: "Slice your games by color, time control, and recency to find exactly the patterns you\u2019re looking for.",
    screenshot: { src: '/screenshots/filters.png', alt: 'Filter panel with time control, platform, rating, and opponent options', orientation: 'portrait' },
    imagePosition: 'left',
  },
  {
    slug: 'system-openings',
    icon: Swords,
    heading: 'System opening analysis',
    desc: "Analyze your performance with system openings like the London, where opponents respond in different ways.",
    screenshot: { src: '/screenshots/position-bookmarks.png', alt: 'Position bookmarks with Mine/Opponent/Both piece filter', orientation: 'portrait' },
    imagePosition: 'right',
  },
  {
    slug: 'cross-platform',
    icon: Layers,
    heading: 'Cross-platform analysis',
    desc: "Import games from chess.com and lichess into one place \u2014 analyze your complete history regardless of platform.",
    screenshot: { src: '/screenshots/game-import.png', alt: 'Import page showing chess.com and lichess with sync buttons', orientation: 'landscape' },
    imagePosition: 'left',
  },
];

// ─── Homepage content (unauthenticated) ───────────────────────────────────────

function HomePageContent() {
  return (
    <>
      <PublicHeader />

      {/* Hero */}
      <section data-testid="hero-section" className="max-w-3xl mx-auto px-4 py-8 lg:py-24 text-center">
        <img
          src="/icons/logo-384.png"
          alt="FlawChess logo"
          className="mx-auto mb-6 h-28 w-28 lg:h-36 lg:w-36"
        />
        <h1 className="text-4xl lg:text-5xl font-bold leading-tight font-brand">
          Engines are flawless, humans play FlawChess
        </h1>
        <p className="mt-4 text-base leading-relaxed text-muted-foreground">
          Analyze your opening positions by move, not just name. Import games from chess.com and
          lichess to discover where you really lose.
        </p>
        <Button
          size="lg"
          asChild
          className={cn(PRIMARY_BUTTON_CLASS, 'min-h-11 min-w-48 mt-8')}
          data-testid="hero-cta-signup"
        >
          <Link to="/login?tab=register">Sign up free</Link>
        </Button>
        {/* Callout pills */}
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <span className="bg-muted text-muted-foreground min-w-32 rounded-full px-3 py-1 text-center text-sm">
            Free to use
          </span>
          <span className="bg-muted text-muted-foreground min-w-32 rounded-full px-3 py-1 text-center text-sm">
            Open source
          </span>
          <span className="bg-muted text-muted-foreground min-w-32 rounded-full px-3 py-1 text-center text-sm">
            Mobile friendly
          </span>
        </div>
      </section>

      {/* Feature sections — alternating image left/right */}
      <div id="features" data-testid="screenshots-section" className="max-w-5xl mx-auto px-4 py-4 lg:py-8 space-y-16 lg:space-y-24 scroll-mt-16">
        {FEATURES.map(({ slug, icon: Icon, heading, desc, screenshot, imagePosition }) => {
          const isLandscape = screenshot.orientation === 'landscape';
          // Landscape: 40% text / 60% image. Portrait: 55% text / 45% image (capped width).
          const gridCols = isLandscape
            ? 'lg:grid-cols-[2fr_3fr]'
            : 'lg:grid-cols-[11fr_9fr]';
          // Flip the ratio when image is on the left
          const gridColsFlipped = isLandscape
            ? 'lg:grid-cols-[3fr_2fr]'
            : 'lg:grid-cols-[9fr_11fr]';

          const textBlock = (
            <div className="flex flex-col justify-center">
              <div className="flex gap-4">
                <div className="shrink-0 mt-1">
                  <Icon className="h-10 w-10 text-muted-foreground" strokeWidth={1.5} />
                </div>
                <div>
                  <h2 className="text-2xl font-bold">{heading}</h2>
                  <p className="mt-3 text-base leading-relaxed text-muted-foreground">{desc}</p>
                </div>
              </div>
            </div>
          );
          const imageBlock = (
            <div className="flex items-center justify-center">
              <img
                src={screenshot.src}
                alt={screenshot.alt}
                className={cn(
                  'rounded-lg border border-border shadow-md',
                  isLandscape ? 'w-full' : 'w-full max-w-xs',
                )}
              />
            </div>
          );
          return (
            <section
              key={slug}
              data-testid={`feature-${slug}`}
              className={cn(
                'grid gap-8 lg:gap-12 items-center',
                imagePosition === 'left' ? gridColsFlipped : gridCols,
              )}
            >
              {/* On mobile: always text first, image second.
                  On desktop: alternate via order classes. */}
              {imagePosition === 'left' ? (
                <>
                  <div className="order-2 lg:order-1">{imageBlock}</div>
                  <div className="order-1 lg:order-2">{textBlock}</div>
                </>
              ) : (
                <>
                  <div>{textBlock}</div>
                  <div>{imageBlock}</div>
                </>
              )}
            </section>
          );
        })}
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

      {/* Footer CTA */}
      <section className="text-center py-16" data-testid="footer-cta">
        <p className="text-muted-foreground mb-4">Free to use. No credit card required.</p>
        <Button
          size="lg"
          asChild
          className={cn(PRIMARY_BUTTON_CLASS, 'min-h-11 min-w-48')}
          data-testid="footer-cta-signup"
        >
          <Link to="/login?tab=register">Sign up free</Link>
        </Button>
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
    return <Navigate to={hasGames ? '/openings' : '/import'} replace />;
  }

  return <HomePageContent />;
}
