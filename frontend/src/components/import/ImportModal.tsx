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
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { useImportTrigger } from '@/hooks/useImport';
import type { Platform } from '@/types/api';
import { toast } from 'sonner';

interface ImportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportStarted: (jobId: string) => void;
}

function getStoredUsername(platform: Platform): string {
  return localStorage.getItem(`${platform}_username`) ?? '';
}

function setStoredUsername(platform: Platform, username: string) {
  localStorage.setItem(`${platform}_username`, username);
}

export function ImportModal({ open, onOpenChange, onImportStarted }: ImportModalProps) {
  const [platform, setPlatform] = useState<Platform>('chess.com');
  const [username, setUsername] = useState<string>(() => getStoredUsername('chess.com'));

  const trigger = useImportTrigger();

  const handlePlatformChange = (p: Platform) => {
    setPlatform(p);
    setUsername(getStoredUsername(p));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = username.trim();
    if (!trimmed) return;

    try {
      const result = await trigger.mutateAsync({ platform, username: trimmed });
      setStoredUsername(platform, trimmed);
      localStorage.setItem(`${platform}_last_sync`, new Date().toISOString());
      onOpenChange(false);
      onImportStarted(result.job_id);
    } catch {
      toast.error('Failed to start import. Please try again.');
    }
  };

  const storedUsername = getStoredUsername(platform);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" data-testid="import-modal">
        <DialogHeader>
          <DialogTitle>Import Games</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Platform selector */}
          <div className="space-y-2">
            <Label>Platform</Label>
            <ToggleGroup
              type="single"
              value={platform}
              onValueChange={(v) => v && handlePlatformChange(v as Platform)}
              variant="outline"
              className="w-full"
            >
              <ToggleGroupItem value="chess.com" className="flex-1" data-testid="import-platform-chess-com">
                chess.com
              </ToggleGroupItem>
              <ToggleGroupItem value="lichess" className="flex-1" data-testid="import-platform-lichess">
                lichess
              </ToggleGroupItem>
            </ToggleGroup>
          </div>

          {/* Username */}
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              type="text"
              placeholder={`Your ${platform} username`}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="off"
              autoFocus
              data-testid="import-username"
            />
          </div>

          {/* Re-sync hint */}
          {storedUsername && storedUsername !== username && (
            <p className="text-xs text-muted-foreground">
              Last used:{' '}
              <button
                type="button"
                className="underline hover:text-foreground"
                onClick={() => setUsername(storedUsername)}
              >
                {storedUsername}
              </button>
            </p>
          )}

          {storedUsername && (
            <p className="text-xs text-muted-foreground">
              Last sync:{' '}
              {localStorage.getItem(`${platform}_last_sync`)
                ? new Date(localStorage.getItem(`${platform}_last_sync`)!).toLocaleDateString()
                : 'never'}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={trigger.isPending}
              data-testid="btn-import-cancel"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={trigger.isPending || !username.trim()} data-testid="btn-import-start">
              {trigger.isPending ? 'Starting...' : 'Import'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
