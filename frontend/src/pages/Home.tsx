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
import { ArrowRightLeft, Scale, Filter, TrophyIcon, DownloadIcon, Loader2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

// Feature sections — imagePosition alternates right/left so text and image swap sides on desktop.
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
    icon: ArrowRightLeft,
    heading: 'Interactive Opening Explorer',
    desc: [
      "Step through any opening and see your win/draw/loss rate for every move you\u2019ve played.",
      "Discover which moves you struggle against and which traps and gambits work for you.",
      "Scout your opponents\u2019 weaknesses and tendencies before a match."
    ],
    screenshot: { src: '/screenshots/opening-explorer.png', alt: 'Board with move explorer showing win/draw/loss bars per candidate move' },
    imagePosition: 'right',
  },
  {
    slug: 'opening-comparison',
    icon: Scale,
    heading: 'Opening Comparison and Tracking',
    desc: [
        'Bookmark your favorite openings and compare their performance.',
        'Find out how your opening study impacts your win rate over time.',
        'Use the filters to see which openings work best for which time controls.'

    ],

    screenshot: { src: '/screenshots/opening-comparison.png', alt: 'Win rate trends over time for multiple openings' },
    imagePosition: 'left',
  },
  {
    slug: 'system-openings',
    icon: Filter,
    heading: 'System Opening Filter',
    desc: [
        "You play the London, but your analysis tool scatters your games across 5 different opening names.",
        "FlawChess lets you filter by your pieces only, ignoring your opponent\u2019s responses.",
        "Calculate win/draw/loss rates for your system openings across all variations."
    ],
    screenshot: { src: '/screenshots/system-openings.png', alt: 'Position bookmarks grouping system opening variations' },
    imagePosition: 'right',
  },
  {
    slug: 'endgame-analysis',
    icon: TrophyIcon,
    heading: 'Endgame Statistics',
    desc: [
        'Measure your endgame performance, conversion, and recovery ability.',
        'Track your win/draw/loss rates by endgame type \u2014 rook, minor piece, pawn, queen, and more.',
        'Find out for each endgame type how often you convert material advantages and recover from deficits.',
    ],
    screenshot: { src: '/screenshots/endgame-analysis.png', alt: 'Endgame analytics showing WDL rates by endgame category' },
    imagePosition: 'left',
  },
  {
    slug: 'cross-platform',
    icon: DownloadIcon,
    heading: 'Cross-Platform Import',
    desc: [
        "Import games from chess.com and lichess into one place.",
        "Add your most recent games with the sync button.",
        "Import your opponent's games to prepare for an upcoming match.",
    ],
    screenshot: { src: '/screenshots/cross-platform.png', alt: 'Import page with chess.com and lichess plus filter controls' },
    imagePosition: 'right',
  },
];

// ─── Homepage content (unauthenticated) ───────────────────────────────────────

export function HomePageContent() {
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
          Import games from chess.com and lichess. Explore openings move by move, track endgame performance, and find exactly where you win and lose.
        </p>
        <p
          className="mt-4 mx-auto max-w-lg rounded-lg border border-yellow-500/30 bg-yellow-500/5 px-4 py-3 text-sm text-muted-foreground"
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
            Mobile app
          </span>
          <span className="bg-muted text-muted-foreground min-w-32 rounded-full px-3 py-1 text-center text-sm">
            Opening explorer
          </span>
          <span className="bg-muted text-muted-foreground min-w-32 rounded-full px-3 py-1 text-center text-sm">
            Progress tracking
          </span>
          <span className="bg-muted text-muted-foreground min-w-32 rounded-full px-3 py-1 text-center text-sm">
            Endgame stats
          </span>
          <span className="bg-muted text-muted-foreground min-w-32 rounded-full px-3 py-1 text-center text-sm">
            Cross-platform
          </span>
        </div>
      </section>

      {/* Feature sections — alternating image left/right */}
      <div id="features" data-testid="screenshots-section" className="scroll-mt-16">
        {FEATURES.map(({ slug, icon: Icon, heading, desc, screenshot, imagePosition }, index) => {
          const isCharcoal = index % 2 === 0;
          const gridCols = imagePosition === 'left'
            ? 'lg:grid-cols-[3fr_2fr]'
            : 'lg:grid-cols-[2fr_3fr]';

          const textBlock = (
            <div className="flex flex-col justify-center">
              <div className="flex gap-4">
                <div className="shrink-0 mt-1">
                  <Icon className="h-10 w-10 text-muted-foreground" strokeWidth={1.5} />
                </div>
                <div>
                  <h2 className="text-2xl font-bold">{heading}</h2>
                  {Array.isArray(desc) ? (
                    <ul className="mt-3 list-disc pl-5 space-y-1 text-base leading-relaxed text-muted-foreground">
                      {desc.map((item, i) => <li key={i}>{item}</li>)}
                    </ul>
                  ) : (
                    <p className="mt-3 text-base leading-relaxed text-muted-foreground">{desc}</p>
                  )}
                </div>
              </div>
            </div>
          );
          const imageBlock = (
            <div className="flex items-center justify-center">
              <img
                src={screenshot.src}
                alt={screenshot.alt}
                className="rounded-lg border border-border shadow-md w-full"
              />
            </div>
          );
          return (
            <section
              key={slug}
              data-testid={`feature-${slug}`}
              className={cn(
                'py-12 lg:py-16',
                isCharcoal ? 'bg-[#1a1a1a]' : '',
              )}
            >
              <div className={cn('max-w-5xl mx-auto px-4 grid gap-8 lg:gap-12 items-center', gridCols)}>
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
              </div>
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
          <AccordionItem value="endgames" data-testid="faq-item-endgames">
            <AccordionTrigger>What endgame analytics does FlawChess offer?</AccordionTrigger>
            <AccordionContent>
              FlawChess tracks your win/draw/loss rates by endgame type (rook, minor piece, pawn,
              queen, and more), plus conversion rates when you&apos;re up material and recovery rates
              when you&apos;re down. All statistics are filterable by time control, color, and recency.
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
