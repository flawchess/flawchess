import { useState, useEffect } from 'react';
import { X, Info } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useImportTrigger, useImportPolling } from '@/hooks/useImport';
import { useUserProfile } from '@/hooks/useUserProfile';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { UserProfile } from '@/types/users';

const GAME_COUNT_REFRESH_INTERVAL_MS = 5000;

interface ImportPageProps {
  onImportStarted: (jobId: string) => void;
  activeJobIds: string[];
  onJobDismissed: (jobId: string) => void;
}

function ImportProgressBar({ jobId, onDismiss }: { jobId: string; onDismiss: (jobId: string) => void }) {
  const { data } = useImportPolling(jobId);
  const queryClient = useQueryClient();

  const isDone = data?.status === 'completed';
  const isError = data?.status === 'failed';
  const isActive = !!data && !isDone && !isError;

  // Periodically refresh game counts while import is active
  useEffect(() => {
    if (!isActive) return;
    const interval = setInterval(() => {
      queryClient.invalidateQueries({ queryKey: ['userProfile'] });
      queryClient.invalidateQueries({ queryKey: ['gameCount'] });
    }, GAME_COUNT_REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [isActive, queryClient]);

  if (!data) return null;

  const canDismiss = isDone || isError;

  const progressText = isDone
    ? `Imported ${data.games_imported} games from ${data.platform}`
    : isError
      ? `Import failed: ${data.error ?? 'Unknown error'}`
      : `Importing ${data.username} (${data.platform})... ${data.games_fetched} fetched, ${data.games_imported} saved`;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <p className={`text-sm ${isError ? 'text-destructive' : isDone ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}`}>
          {progressText}
        </p>
        {canDismiss && (
          <button
            onClick={() => onDismiss(jobId)}
            className="shrink-0 rounded-sm p-0.5 text-muted-foreground hover:text-foreground"
            aria-label="Dismiss"
            data-testid={`btn-dismiss-progress-${jobId}`}
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        {isActive ? (
          <div className="h-full w-full origin-left animate-progress-indeterminate rounded-full bg-primary" />
        ) : isDone ? (
          <div className="h-full w-full rounded-full bg-green-600 dark:bg-green-500 transition-all duration-500" />
        ) : (
          <div className="h-full w-full rounded-full bg-destructive" />
        )}
      </div>
      {data.other_importers > 0 && (
        <div
          className="bg-muted border border-border rounded-md px-4 py-3 text-sm text-muted-foreground flex items-center gap-2 mt-3"
          data-testid="import-concurrent-notice"
        >
          <Info className="h-4 w-4 shrink-0" />
          <span>
            {data.other_importers} other {data.other_importers === 1 ? 'user is' : 'users are'} also importing from {data.platform} — progress may be slower than usual.
          </span>
        </div>
      )}
    </div>
  );
}

export function ImportPage({ onImportStarted, activeJobIds, onJobDismissed }: ImportPageProps) {
  const { data: profile, isLoading: profileLoading } = useUserProfile();
  const trigger = useImportTrigger();
  const queryClient = useQueryClient();

  // Username state — always editable, synced from profile
  const [chessComUsername, setChessComUsername] = useState('');
  const [lichessUsername, setLichessUsername] = useState('');

  // Per-platform error state
  const [chessComError, setChessComError] = useState<string | null>(null);
  const [lichessError, setLichessError] = useState<string | null>(null);

  // Track previous profile to detect changes and sync input fields (derived state pattern)
  const [prevProfile, setPrevProfile] = useState<UserProfile | undefined>(undefined);
  if (profile !== prevProfile) {
    setPrevProfile(profile);
    setChessComUsername(profile?.chess_com_username ?? '');
    setLichessUsername(profile?.lichess_username ?? '');
  }

  // Delete all games dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // ── Sync handler ────────────────────────────────────────────────────────────

  const handleSync = async (platform: 'chess.com' | 'lichess') => {
    const username = platform === 'chess.com' ? chessComUsername.trim() : lichessUsername.trim();
    if (!username) return;

    // Clear previous error for this platform
    if (platform === 'chess.com') setChessComError(null);
    else setLichessError(null);

    try {
      const result = await trigger.mutateAsync({ platform, username });
      onImportStarted(result.job_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Import failed. Please check the username and try again.';
      if (platform === 'chess.com') setChessComError(message);
      else setLichessError(message);
    }
  };

  // ── Delete All Games ──────────────────────────────────────────────────────

  const handleDeleteAllGames = async () => {
    setIsDeleting(true);
    try {
      await apiClient.delete('/imports/games');
      setDeleteDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ['games'] });
      queryClient.invalidateQueries({ queryKey: ['gameCount'] });
      queryClient.invalidateQueries({ queryKey: ['userProfile'] });
    } catch {
      // Error handled by axios interceptor
    } finally {
      setIsDeleting(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <main data-testid="import-page" className="mx-auto w-full max-w-2xl px-4 py-6 md:px-6 space-y-8">
      <h1 data-testid="import-page-heading" className="text-2xl font-bold tracking-tight">
        Import Games
      </h1>

      {profileLoading ? (
        <p className="text-sm text-muted-foreground">Loading profile...</p>
      ) : (
        <div className="space-y-4">
          {profile && (
            <p className="text-sm text-muted-foreground" data-testid="import-user-email">
              Logged in as {profile.email}
            </p>
          )}

          {/* chess.com platform row */}
          <div
            data-testid="import-platform-chess-com"
            className="space-y-2 rounded-md border px-3 py-2"
          >
            <div className="flex items-center gap-3">
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <Label htmlFor="chess-com-username" className="text-sm font-medium">chess.com</Label>
                  {profile && (
                    <span className="text-xs text-muted-foreground" data-testid="import-game-count-chess-com">
                      {profile.chess_com_game_count} games
                    </span>
                  )}
                </div>
                <Input
                  id="chess-com-username"
                  type="text"
                  placeholder="chess.com username"
                  value={chessComUsername}
                  onChange={(e) => { setChessComUsername(e.target.value); setChessComError(null); }}
                  onKeyDown={(e) => e.key === 'Enter' && handleSync('chess.com')}
                  autoComplete="off"
                  className="h-8 text-sm"
                  data-testid="import-username-chess-com"
                />
              </div>
              <Button
                size="sm"
                onClick={() => handleSync('chess.com')}
                disabled={trigger.isPending || !chessComUsername.trim()}
                data-testid="btn-sync-chess-com"
                className="self-end"
              >
                Sync
              </Button>
            </div>
            {chessComError && (
              <p className="text-sm text-destructive" data-testid="import-error-chess-com">{chessComError}</p>
            )}
          </div>

          {/* lichess platform row */}
          <div
            data-testid="import-platform-lichess"
            className="space-y-2 rounded-md border px-3 py-2"
          >
            <div className="flex items-center gap-3">
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <Label htmlFor="lichess-username" className="text-sm font-medium">lichess</Label>
                  {profile && (
                    <span className="text-xs text-muted-foreground" data-testid="import-game-count-lichess">
                      {profile.lichess_game_count} games
                    </span>
                  )}
                </div>
                <Input
                  id="lichess-username"
                  type="text"
                  placeholder="lichess username"
                  value={lichessUsername}
                  onChange={(e) => { setLichessUsername(e.target.value); setLichessError(null); }}
                  onKeyDown={(e) => e.key === 'Enter' && handleSync('lichess')}
                  autoComplete="off"
                  className="h-8 text-sm"
                  data-testid="import-username-lichess"
                />
              </div>
              <Button
                size="sm"
                onClick={() => handleSync('lichess')}
                disabled={trigger.isPending || !lichessUsername.trim()}
                data-testid="btn-sync-lichess"
                className="self-end"
              >
                Sync
              </Button>
            </div>
            {lichessError && (
              <p className="text-sm text-destructive" data-testid="import-error-lichess">{lichessError}</p>
            )}
          </div>
        </div>
      )}

      {/* Inline import progress bars */}
      {activeJobIds.length > 0 && (
        <section data-testid="import-progress-section" className="space-y-3">
          {activeJobIds.map((id) => (
            <ImportProgressBar key={id} jobId={id} onDismiss={onJobDismissed} />
          ))}
        </section>
      )}

      {/* Delete All Games */}
      <div data-testid="import-data-management">
        <Button
          variant="destructive"
          size="sm"
          onClick={() => setDeleteDialogOpen(true)}
          data-testid="btn-delete-games"
        >
          Delete All Games
        </Button>
      </div>

      {/* Delete confirmation dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent data-testid="delete-games-modal">
          <DialogHeader>
            <DialogTitle>Delete All Games</DialogTitle>
            <DialogDescription>
              This will delete all your imported games. You can import them again anytime.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              data-testid="btn-delete-cancel"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteAllGames}
              disabled={isDeleting}
              data-testid="btn-delete-confirm"
            >
              {isDeleting ? 'Deleting...' : 'Delete All Games'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
