import { useState, useEffect } from 'react';
import * as Sentry from '@sentry/react';
import { X, UserX, BookOpenIcon, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Alert } from '@/components/ui/alert';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useImportTrigger, useImportPolling } from '@/hooks/useImport';
import { useUserProfile } from '@/hooks/useUserProfile';
import { useAuth } from '@/hooks/useAuth';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';


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
    ? (data.games_imported === 0 ? 'No new games found since last sync' : `Imported ${data.games_imported} games from ${data.platform}`)
    : isError
      ? `Import failed: ${data.error ?? 'Unknown error'}`
      : `Importing ${data.username} (${data.platform})... ${data.games_fetched} fetched, ${data.games_imported} saved`;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <div className={`flex items-center gap-1.5 text-sm ${isError ? 'text-destructive' : isDone ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}`}>
          <PlatformIcon platform={data.platform} className="h-4 w-4 shrink-0" />
          <span>{progressText}</span>
        </div>
        {canDismiss && (
          <Tooltip content="Dismiss">
            <button
              onClick={() => onDismiss(jobId)}
              className="shrink-0 rounded-sm p-0.5 text-muted-foreground hover:text-foreground"
              aria-label="Dismiss"
              data-testid={`btn-dismiss-progress-${jobId}`}
            >
              <X className="h-4 w-4" />
            </button>
          </Tooltip>
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
      {isDone && data.games_imported > 0 && (
        <div className="flex justify-center pt-2">
          <Button asChild size="sm" data-testid="btn-explore-openings">
            <Link to="/openings">
              <BookOpenIcon className="h-4 w-4" />
              Explore your openings
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      )}
      {data.other_importers > 0 && (
        <Alert variant="info" className="mt-3" data-testid="import-concurrent-notice">
          {data.other_importers} other {data.other_importers === 1 ? 'user is' : 'users are'} also importing from {data.platform} — progress may be slower than usual.
        </Alert>
      )}
    </div>
  );
}

export function ImportPage({ onImportStarted, activeJobIds, onJobDismissed }: ImportPageProps) {
  const { logoutForPromotion } = useAuth();
  const { data: profile, isLoading: profileLoading } = useUserProfile();
  const trigger = useImportTrigger();
  const queryClient = useQueryClient();

  // Username state — always editable, synced from profile on first load only
  const [chessComUsername, setChessComUsername] = useState('');
  const [lichessUsername, setLichessUsername] = useState('');
  // Track whether username fields have been initialized from profile.
  // Without this guard, periodic profile refetches (game count refresh during import)
  // would overwrite whatever the user was typing in the other platform's input.
  const [initialized, setInitialized] = useState(false);

  // Per-platform error state
  const [chessComError, setChessComError] = useState<string | null>(null);
  const [lichessError, setLichessError] = useState<string | null>(null);

  // Track jobId→platform for active imports — disables sync button while running
  const [jobPlatforms, setJobPlatforms] = useState<Map<string, string>>(new Map());

  // Sync usernames from profile only on first load, not on every refetch
  if (profile && !initialized) {
    setInitialized(true);
    setChessComUsername(profile.chess_com_username ?? '');
    setLichessUsername(profile.lichess_username ?? '');
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
      setJobPlatforms((prev) => new Map(prev).set(result.job_id, platform));
    } catch (err) {
      Sentry.captureException(err, {
        tags: { source: 'import' },
        extra: { platform },
      });
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
    } catch (err) {
      Sentry.captureException(err, {
        tags: { source: 'import' },
      });
    } finally {
      setIsDeleting(false);
    }
  };

  // Derive which platforms have a non-dismissed active job
  const activePlatforms = new Set(jobPlatforms.values());

  const handleDismiss = (jobId: string) => {
    setJobPlatforms((prev) => { const next = new Map(prev); next.delete(jobId); return next; });
    onJobDismissed(jobId);
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <main data-testid="import-page" className="mx-auto w-full max-w-2xl px-4 py-6 md:px-6 space-y-8">
      <h1 data-testid="import-page-heading" className="text-2xl font-bold tracking-tight">
        Import Games
      </h1>

      {profile?.is_guest && (
        <Alert variant="info" icon={UserX} data-testid="import-guest-promo-info" className="mb-4">
          <div>
              <p className="font-medium">Welcome, guest! If you like it here, consider{' '}
                <button
                  onClick={() => { logoutForPromotion(); window.location.href = '/login?tab=register'; }}
                  className="font-medium underline underline-offset-2"
                  data-testid="import-guest-promo-link"
                >
                  signing up free
                </button>{' '}
                for these advantages:
              </p>
              <ul className="mt-1 list-disc pl-4 space-y-0.5">
                <li>Access your games from any device</li>
                <li>Prevent losing your imported games and bookmarks after 30 days of inactivity</li>
              </ul>
          </div>
        </Alert>
      )}

      {profileLoading ? (
        <p className="text-sm text-muted-foreground">Loading profile...</p>
      ) : (
        <div className="space-y-4">
          {/* chess.com platform row */}
          <div
            data-testid="import-platform-chess-com"
            className="charcoal-texture space-y-2 rounded-md px-3 py-2"
          >
            <div className="flex items-center gap-3">
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <PlatformIcon platform="chess.com" className="h-4 w-4" />
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
                disabled={trigger.isPending || !chessComUsername.trim() || activePlatforms.has('chess.com')}
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
            className="charcoal-texture space-y-2 rounded-md px-3 py-2"
          >
            <div className="flex items-center gap-3">
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <PlatformIcon platform="lichess" className="h-4 w-4" />
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
                disabled={trigger.isPending || !lichessUsername.trim() || activePlatforms.has('lichess')}
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

      {/* Info box: sync behavior and opponent scouting explanation */}
      <Alert variant="info" data-testid="import-info">
        <p>
          <strong>First sync</strong> imports all your games. Later syncs only fetch new games since the last import.
        </p>
        <p>
          <strong>Opponent scouting:</strong> delete your games, import the opponent's games to analyze their openings, then delete and re-import your own games.
        </p>
      </Alert>

      {/* Inline import progress bars */}
      {activeJobIds.length > 0 && (
        <section data-testid="import-progress-section" className="space-y-3">
          {activeJobIds.map((id) => (
            <ImportProgressBar key={id} jobId={id} onDismiss={handleDismiss} />
          ))}
        </section>
      )}

      {/* Delete All Games */}
      <div data-testid="import-data-management">
        <Button
          variant="destructive"
          size="sm"
          onClick={() => setDeleteDialogOpen(true)}
          disabled={activeJobIds.length > 0}
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
