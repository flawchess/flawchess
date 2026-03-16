import { useState } from 'react';
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
import { useImportTrigger } from '@/hooks/useImport';
import { useUserProfile } from '@/hooks/useUserProfile';
import { ImportProgress } from '@/components/import/ImportProgress';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { toast } from 'sonner';
import type { UserProfile } from '@/types/users';

interface ImportPageProps {
  onImportStarted: (jobId: string) => void;
  activeJobIds: string[];
}

export function ImportPage({ onImportStarted, activeJobIds }: ImportPageProps) {
  const { data: profile, isLoading: profileLoading } = useUserProfile();
  const trigger = useImportTrigger();
  const queryClient = useQueryClient();

  // Input view state — initialized from profile, re-synced on profile changes via derived state
  const [chessComUsername, setChessComUsername] = useState('');
  const [lichessUsername, setLichessUsername] = useState('');
  const [editMode, setEditMode] = useState(false);

  // Track previous profile to detect changes and sync input fields (derived state pattern)
  const [prevProfile, setPrevProfile] = useState<UserProfile | undefined>(undefined);
  if (profile !== prevProfile) {
    setPrevProfile(profile);
    setChessComUsername(profile?.chess_com_username ?? '');
    setLichessUsername(profile?.lichess_username ?? '');
  }

  // Add flow state for unconfigured platforms in sync view
  const [addingPlatform, setAddingPlatform] = useState<'chess.com' | 'lichess' | null>(null);
  const [addUsername, setAddUsername] = useState('');

  // Delete all games dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Determine which view to show
  const isFirstTime = !profile?.chess_com_username && !profile?.lichess_username;
  const showInputView = isFirstTime || editMode;

  // ── Sync view handlers ──────────────────────────────────────────────────────

  const handleSync = async (platform: 'chess.com' | 'lichess', username: string) => {
    try {
      const result = await trigger.mutateAsync({ platform, username });
      onImportStarted(result.job_id);
    } catch {
      toast.error('Failed to start import. Please try again.');
    }
  };

  // ── Add flow handler (sync view inline add for unconfigured platforms) ──────

  const handleAdd = async (platform: 'chess.com' | 'lichess') => {
    const trimmed = addUsername.trim();
    if (!trimmed) return;
    try {
      const result = await trigger.mutateAsync({ platform, username: trimmed });
      setAddingPlatform(null);
      setAddUsername('');
      onImportStarted(result.job_id);
    } catch {
      toast.error('Failed to start import. Please try again.');
    }
  };

  // ── Input view handler ──────────────────────────────────────────────────────

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedChessCom = chessComUsername.trim();
    const trimmedLichess = lichessUsername.trim();

    if (!trimmedChessCom && !trimmedLichess) return;

    try {
      if (trimmedChessCom) {
        const result = await trigger.mutateAsync({ platform: 'chess.com', username: trimmedChessCom });
        onImportStarted(result.job_id);
      }
      if (trimmedLichess) {
        const result = await trigger.mutateAsync({ platform: 'lichess', username: trimmedLichess });
        onImportStarted(result.job_id);
      }
      if (trimmedChessCom || trimmedLichess) {
        setEditMode(false);
      }
    } catch {
      toast.error('Failed to start import. Please try again.');
    }
  };

  // ── Delete All Games ────────────────────────────────────────────────────────

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

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <main data-testid="import-page" className="mx-auto w-full max-w-2xl px-4 py-6 md:px-6 space-y-8">
      <h1 data-testid="import-page-heading" className="text-2xl font-bold tracking-tight">
        Import Games
      </h1>

      {/* Platform rows */}
      {profileLoading ? (
        <p className="text-sm text-muted-foreground">Loading profile...</p>
      ) : showInputView ? (
        /* Input view: first-time user or edit mode */
        <form onSubmit={handleImport} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="chess-com-username">chess.com username</Label>
            <Input
              id="chess-com-username"
              type="text"
              placeholder="Your chess.com username"
              value={chessComUsername}
              onChange={(e) => setChessComUsername(e.target.value)}
              autoComplete="off"
              autoFocus
              data-testid="import-username-chess-com"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="lichess-username">lichess username</Label>
            <Input
              id="lichess-username"
              type="text"
              placeholder="Your lichess username"
              value={lichessUsername}
              onChange={(e) => setLichessUsername(e.target.value)}
              autoComplete="off"
              data-testid="import-username-lichess"
            />
          </div>

          <div className="flex justify-end gap-2">
            {editMode && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => setEditMode(false)}
                disabled={trigger.isPending}
                data-testid="btn-edit-cancel"
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              disabled={trigger.isPending || (!chessComUsername.trim() && !lichessUsername.trim())}
              data-testid="btn-import-start"
            >
              {trigger.isPending ? 'Starting...' : 'Import'}
            </Button>
          </div>
        </form>
      ) : (
        /* Sync view: returning user with stored usernames */
        <div className="space-y-4">
          {/* chess.com platform row */}
          <div
            data-testid="import-platform-chess-com"
            className="flex items-center justify-between rounded-md border px-3 py-2"
          >
            <div>
              <p className="text-sm font-medium">chess.com</p>
              {profile?.chess_com_username ? (
                <p className="text-xs text-muted-foreground">{profile.chess_com_username}</p>
              ) : (
                <p className="text-xs text-muted-foreground">Not set</p>
              )}
            </div>
            {profile?.chess_com_username ? (
              <Button
                size="sm"
                onClick={() => handleSync('chess.com', profile.chess_com_username!)}
                disabled={trigger.isPending}
                data-testid="btn-sync-chess-com"
              >
                Sync
              </Button>
            ) : addingPlatform === 'chess.com' ? (
              <div className="flex items-center gap-2">
                <Input
                  type="text"
                  placeholder="chess.com username"
                  value={addUsername}
                  onChange={(e) => setAddUsername(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAdd('chess.com')}
                  autoFocus
                  className="h-8 w-40 text-sm"
                  data-testid="import-add-username-chess-com"
                />
                <Button
                  size="sm"
                  onClick={() => handleAdd('chess.com')}
                  disabled={trigger.isPending || !addUsername.trim()}
                  data-testid="btn-add-import-chess-com"
                >
                  {trigger.isPending ? 'Starting...' : 'Import'}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => { setAddingPlatform(null); setAddUsername(''); }}
                  data-testid="btn-add-cancel-chess-com"
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={() => { setAddingPlatform('chess.com'); setAddUsername(''); }}
                data-testid="btn-add-chess-com"
              >
                Add
              </Button>
            )}
          </div>

          {/* lichess platform row */}
          <div
            data-testid="import-platform-lichess"
            className="flex items-center justify-between rounded-md border px-3 py-2"
          >
            <div>
              <p className="text-sm font-medium">lichess</p>
              {profile?.lichess_username ? (
                <p className="text-xs text-muted-foreground">{profile.lichess_username}</p>
              ) : (
                <p className="text-xs text-muted-foreground">Not set</p>
              )}
            </div>
            {profile?.lichess_username ? (
              <Button
                size="sm"
                onClick={() => handleSync('lichess', profile.lichess_username!)}
                disabled={trigger.isPending}
                data-testid="btn-sync-lichess"
              >
                Sync
              </Button>
            ) : addingPlatform === 'lichess' ? (
              <div className="flex items-center gap-2">
                <Input
                  type="text"
                  placeholder="lichess username"
                  value={addUsername}
                  onChange={(e) => setAddUsername(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAdd('lichess')}
                  autoFocus
                  className="h-8 w-40 text-sm"
                  data-testid="import-add-username-lichess"
                />
                <Button
                  size="sm"
                  onClick={() => handleAdd('lichess')}
                  disabled={trigger.isPending || !addUsername.trim()}
                  data-testid="btn-add-import-lichess"
                >
                  {trigger.isPending ? 'Starting...' : 'Import'}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => { setAddingPlatform(null); setAddUsername(''); }}
                  data-testid="btn-add-cancel-lichess"
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={() => { setAddingPlatform('lichess'); setAddUsername(''); }}
                data-testid="btn-add-lichess"
              >
                Add
              </Button>
            )}
          </div>

          <div>
            <button
              type="button"
              className="text-xs text-muted-foreground underline hover:text-foreground"
              onClick={() => setEditMode(true)}
              data-testid="btn-edit-usernames"
            >
              Edit usernames
            </button>
          </div>
        </div>
      )}

      {/* Inline import progress — floating toasts from ImportProgress, shown when jobs active */}
      {activeJobIds.length > 0 && (
        <ImportProgress jobIds={activeJobIds} onJobDone={() => {}} />
      )}

      {/* Data management */}
      <section data-testid="import-data-management" className="space-y-3">
        <h2 className="text-base font-semibold">Data Management</h2>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => setDeleteDialogOpen(true)}
          data-testid="btn-delete-games"
        >
          Delete All Games
        </Button>
      </section>

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
