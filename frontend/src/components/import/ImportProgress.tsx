import { useEffect } from 'react';
import { X } from 'lucide-react';
import { useImportPolling } from '@/hooks/useImport';

interface ImportProgressItemProps {
  jobId: string;
  onDone: (jobId: string) => void;
}

function ImportProgressItem({ jobId, onDone }: ImportProgressItemProps) {
  const { data } = useImportPolling(jobId);

  useEffect(() => {
    if (data?.status === 'completed' || data?.status === 'failed') {
      const timeout = setTimeout(() => onDone(jobId), 5000);
      return () => clearTimeout(timeout);
    }
  }, [data?.status, jobId, onDone]);

  if (!data) return null;

  const isDone = data.status === 'completed';
  const isError = data.status === 'failed';
  const isActive = !isDone && !isError;

  return (
    <div
      className={`flex items-center justify-between gap-3 rounded border px-4 py-3 text-sm shadow-lg backdrop-blur-sm ${
        isDone
          ? 'border-green-600/30 bg-green-950/80 text-green-300'
          : isError
            ? 'border-red-600/30 bg-red-950/80 text-red-300'
            : 'border-border bg-background/90 text-foreground'
      }`}
    >
      <div className="flex items-center gap-2">
        {isActive && (
          <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
        )}
        <span>
          {isDone
            ? `Imported ${data.games_imported} games from ${data.platform}`
            : isError
              ? `Import failed: ${data.error ?? 'Unknown error'}`
              : `Importing ${data.username} (${data.platform})... ${data.games_fetched} fetched, ${data.games_imported} saved`}
        </span>
      </div>

      {(isDone || isError) && (
        <button
          onClick={() => onDone(jobId)}
          className="shrink-0 text-current opacity-70 hover:opacity-100"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

interface ImportProgressProps {
  jobIds: string[];
  onJobDone: (jobId: string) => void;
}

export function ImportProgress({ jobIds, onJobDone }: ImportProgressProps) {
  if (jobIds.length === 0) return null;

  return (
    <div data-testid="import-progress" className="fixed bottom-4 left-1/2 z-50 flex w-full max-w-sm -translate-x-1/2 flex-col gap-2 px-4">
      {jobIds.map((id) => (
        <ImportProgressItem key={id} jobId={id} onDone={onJobDone} />
      ))}
    </div>
  );
}
