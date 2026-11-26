import { Link, Navigate, useSearchParams } from 'react-router';

import { useAuth } from '@/hooks/useAuth';
import { LoginForm } from '@/components/auth/LoginForm';
import { RegisterForm } from '@/components/auth/RegisterForm';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export function AuthPage() {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  // Redirect already-authenticated users to the dashboard
  if (token) {
    return <Navigate to="/" replace />;
  }

  const tab = searchParams.get('tab') === 'register' ? 'register' : 'login';

  const handleTabChange = (value: string) => {
    if (value === 'register') {
      setSearchParams({ tab: 'register' });
    } else {
      setSearchParams({});
    }
  };

  return (
    <div
      data-testid="auth-page"
      className="flex min-h-screen flex-col items-center justify-center bg-background px-4 sm:landscape:flex-row sm:landscape:gap-16 sm:landscape:py-6"
    >
      {/* Portrait: logo beside the title and tagline, to save vertical space.
          Landscape: the whole block stacks into its own column left of the card. */}
      <Link
        to="/"
        className="mb-6 flex items-center gap-4 sm:landscape:mb-0 sm:landscape:flex-col sm:landscape:gap-4 sm:landscape:text-center"
        data-testid="auth-logo-home"
      >
        <img src="/icons/logo-256.png" alt="FlawChess logo" className="h-20 w-20 shrink-0 sm:landscape:h-32 sm:landscape:w-32" />
        <div>
          <h1 className="text-4xl tracking-tight text-foreground font-brand">FlawChess</h1>
          <p className="mt-2 text-muted-foreground">Analyze your opening positions</p>
        </div>
      </Link>

      <Tabs value={tab} onValueChange={handleTabChange} className="w-full max-w-sm">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="login" data-testid="auth-tab-login">Sign In</TabsTrigger>
          <TabsTrigger value="register" data-testid="auth-tab-register">Register</TabsTrigger>
        </TabsList>
        <TabsContent value="login" className="mt-4">
          <LoginForm />
        </TabsContent>
        <TabsContent value="register" className="mt-4">
          <RegisterForm />
        </TabsContent>
      </Tabs>
    </div>
  );
}
