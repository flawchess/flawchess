import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { PRIMARY_BUTTON_CLASS } from '@/lib/theme';

export function PublicHeader() {
  return (
    <header
      data-testid="public-header"
      className="sticky top-0 z-40 border-b border-border bg-background px-6"
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between py-2">
        {/* Logo + brand name */}
        <Link to="/" className="flex items-center gap-1.5">
          <img src="/icons/logo-128.png" alt="" className="h-10 w-10" aria-hidden="true" />
          <span className="text-lg tracking-tight font-brand">FlawChess</span>
        </Link>

        {/* Auth buttons */}
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" asChild data-testid="nav-login">
            <Link to="/login">Log in</Link>
          </Button>
          <Button size="sm" asChild className={PRIMARY_BUTTON_CLASS} data-testid="nav-signup">
            <Link to="/login?tab=register">Sign up free</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
