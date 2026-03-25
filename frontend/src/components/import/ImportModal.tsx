import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useImportTrigger } from '@/hooks/useImport';
import { useUserProfile } from '@/hooks/useUserProfile';
import type { UserProfile } from '@/types/users';
import { toast } from 'sonner';
import { PlatformIcon } from '@/components/icons/PlatformIcon';

interface ImportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportStarted: (jobId: string) => void;
}

export function ImportModal({ open, onOpenChange, onImportStarted }: ImportModalProps) {
  const { data: profile, isLoading: profileLoading } = useUserProfile();
  const trigger = useImportTrigger();

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

  // Track previous open value to reset editMode when modal closes (derived state pattern)
  const [prevOpen, setPrevOpen] = useState(open);
  if (open !== prevOpen) {
    setPrevOpen(open);
    if (!open) {
      setEditMode(false);
      setAddingPlatform(null);
      setAddUsername('');
    }
  }

  // Determine which view to show
  const isFirstTime = !profile?.chess_com_username && !profile?.lichess_username;
  const showInputView = isFirstTime || editMode;

  // ── Sync view handlers ──────────────────────────────────────────────────────

  const handleSync = async (platform: 'chess.com' | 'lichess', username: string) => {
    try {
      const result = await trigger.mutateAsync({ platform, username });
      onOpenChange(false);
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
      onOpenChange(false);
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

    let anyStarted = false;

    try {
      if (trimmedChessCom) {
        const result = await trigger.mutateAsync({ platform: 'chess.com', username: trimmedChessCom });
        onImportStarted(result.job_id);
        anyStarted = true;
      }
      if (trimmedLichess) {
        const result = await trigger.mutateAsync({ platform: 'lichess', username: trimmedLichess });
        onImportStarted(result.job_id);
        anyStarted = true;
      }
      if (anyStarted) {
        onOpenChange(false);
      }
    } catch {
      toast.error('Failed to start import. Please try again.');
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" data-testid="import-modal">
        <DialogHeader>
          <DialogTitle>Import Games</DialogTitle>
        </DialogHeader>

        {profileLoading ? (
          <p className="text-sm text-muted-foreground">Loading profile...</p>
        ) : showInputView ? (
          /* Input view: first-time user or edit mode */
          <form onSubmit={handleImport} className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <PlatformIcon platform="chess.com" className="h-4 w-4" />
                <Label htmlFor="chess-com-username">chess.com username</Label>
              </div>
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
              <div className="flex items-center gap-2">
                <PlatformIcon platform="lichess" className="h-4 w-4" />
                <Label htmlFor="lichess-username">lichess username</Label>
              </div>
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
              {editMode ? (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setEditMode(false)}
                  disabled={trigger.isPending}
                  data-testid="btn-edit-cancel"
                >
                  Cancel
                </Button>
              ) : (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => onOpenChange(false)}
                  disabled={trigger.isPending}
                  data-testid="btn-import-cancel"
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
            <div className="flex items-center justify-between rounded-md border px-3 py-2">
              <div>
                <div className="flex items-center gap-1.5">
                  <PlatformIcon platform="chess.com" className="h-4 w-4" />
                  <p className="text-sm font-medium">chess.com</p>
                </div>
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
              ) : (
                addingPlatform === 'chess.com' ? (
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
                )
              )}
            </div>

            {/* lichess platform row */}
            <div className="flex items-center justify-between rounded-md border px-3 py-2">
              <div>
                <div className="flex items-center gap-1.5">
                  <PlatformIcon platform="lichess" className="h-4 w-4" />
                  <p className="text-sm font-medium">lichess</p>
                </div>
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
              ) : (
                addingPlatform === 'lichess' ? (
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
                )
              )}
            </div>

            <div className="flex justify-between">
              <button
                type="button"
                className="text-xs text-muted-foreground underline hover:text-foreground"
                onClick={() => setEditMode(true)}
                data-testid="btn-edit-usernames"
              >
                Edit usernames
              </button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => onOpenChange(false)}
                data-testid="btn-sync-close"
              >
                Close
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
