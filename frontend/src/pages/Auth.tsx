import { Navigate, useSearchParams } from 'react-router-dom';

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
    <div data-testid="auth-page" className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-foreground">Chessalytics</h1>
        <p className="mt-2 text-muted-foreground">Analyze your opening positions</p>
      </div>

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
