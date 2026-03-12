import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';

export function DashboardPage() {
  const { logout } = useAuth();

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight text-foreground">Chessalytics</h1>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => {
              // Placeholder — will be implemented in Plan 03
              alert('Import Games — coming in Plan 03');
            }}>
              Import Games
            </Button>
            <Button variant="ghost" onClick={logout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Body */}
      <main className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="text-center text-muted-foreground">
          <p className="text-lg">Play moves on the board and click Analyze to see your stats</p>
        </div>
      </main>
    </div>
  );
}
