import { Navigate } from 'react-router-dom';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
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

// ─── Homepage content (unauthenticated) ───────────────────────────────────────

function HomePageContent() {
  return (
    <>
      <PublicHeader />

      {/* Hero */}
      <section data-testid="hero-section" className="max-w-3xl mx-auto px-4 py-16 lg:py-24 text-center">
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
          className={cn(PRIMARY_BUTTON_CLASS, 'min-h-11 mt-8')}
          data-testid="hero-cta-signup"
        >
          <Link to="/login?tab=register">Sign up free</Link>
        </Button>
        {/* Callout pills */}
        <div className="mt-4 flex justify-center gap-2">
          <span className="bg-muted text-muted-foreground rounded-full px-3 py-1 text-sm">
            Open source and free
          </span>
          <span className="bg-muted text-muted-foreground rounded-full px-3 py-1 text-sm">
            Mobile friendly
          </span>
        </div>
      </section>

      {/* Screenshots */}
      <div data-testid="screenshots-section" className="max-w-5xl mx-auto px-4 py-12">
        <p className="text-center text-muted-foreground text-sm">Screenshots coming soon</p>
      </div>

      {/* Feature sections */}
      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-8">
          <section data-testid="feature-weaknesses">
            <h2 className="text-xl font-bold">Find weaknesses in your openings</h2>
            <p className="mt-2 text-base leading-relaxed text-muted-foreground">
              Discover which moves you struggle against, which gambits work for you, and how your
              repertoire performs at different rating levels.
            </p>
          </section>
          <section data-testid="feature-scout">
            <h2 className="text-xl font-bold">Scout your opponents</h2>
            <p className="mt-2 text-base leading-relaxed text-muted-foreground">
              Prepare for a match by exploring their opening weaknesses and tendencies.
            </p>
          </section>
          <section data-testid="feature-move-explorer">
            <h2 className="text-xl font-bold">Interactive move explorer</h2>
            <p className="mt-2 text-base leading-relaxed text-muted-foreground">
              Step through any position and see your win/draw/loss rate for every move
              you&rsquo;ve played.
            </p>
          </section>
          <section data-testid="feature-cross-platform">
            <h2 className="text-xl font-bold">Cross-platform analysis</h2>
            <p className="mt-2 text-base leading-relaxed text-muted-foreground">
              Import games from chess.com and lichess into one place &mdash; analyze your complete
              history regardless of platform.
            </p>
          </section>
          <section data-testid="feature-filters">
            <h2 className="text-xl font-bold">Powerful filters</h2>
            <p className="mt-2 text-base leading-relaxed text-muted-foreground">
              Slice your games by time control, rating range, color, opponent type, and time period
              to find exactly the patterns you&rsquo;re looking for.
            </p>
          </section>
        </div>
      </div>

      {/* FAQ */}
      <section className="max-w-2xl mx-auto px-4 py-12">
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
              FlawChess is an open source project developed independently. Find the code, contribute,
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
          className={cn(PRIMARY_BUTTON_CLASS, 'min-h-11')}
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
  if (token) return <Navigate to="/openings" replace />;
  return <HomePageContent />;
}
