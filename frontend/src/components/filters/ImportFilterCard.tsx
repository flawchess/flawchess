import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { InfoPopover } from '@/components/ui/info-popover';
import { TimeControlIcon } from '@/components/icons/TimeControlIcon';
import { cn } from '@/lib/utils';
import type { TimeControl } from '@/types/api';
import {
  useImportSettings,
  useUpdateImportSettings,
  tcSettingsKey,
  type GameCap,
  type ImportSettings,
  type ImportSettingsUpdate,
} from '@/hooks/useImportSettings';

// Exported for reuse by Import.tsx's per-platform budget-chip rows (Task 2),
// which must label/order TCs identically to this card's own TC row.
export const TIME_CONTROLS: TimeControl[] = ['bullet', 'blitz', 'rapid', 'classical'];
export const TIME_CONTROL_LABELS: Record<TimeControl, string> = {
  bullet: 'Bullet',
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Classic',
};

const GAME_CAPS: GameCap[] = [1000, 3000, 5000];

function infoPopoverBody(cap: GameCap): string {
  return `Each time control you enable gets its own ${cap}-game backlog budget per platform. New games always import regardless of budget. Lowering a setting never deletes games you already have.`;
}

// Exported for reuse by Import.tsx (Task 2) so budget chips render only for
// currently-selected TCs (D-11), matching this card's own toggle state.
export function isTcActive(settings: ImportSettings, tc: TimeControl): boolean {
  return settings[tcSettingsKey(tc)];
}

/** Builds the full PATCH payload with a single TC's boolean flipped, keeping the other fields as-is. */
function withTcToggle(settings: ImportSettings, tc: TimeControl, active: boolean): ImportSettingsUpdate {
  return {
    tc_bullet: tc === 'bullet' ? active : settings.tc_bullet,
    tc_blitz: tc === 'blitz' ? active : settings.tc_blitz,
    tc_rapid: tc === 'rapid' ? active : settings.tc_rapid,
    tc_classical: tc === 'classical' ? active : settings.tc_classical,
    game_cap: settings.game_cap,
  };
}

/**
 * "Import filters" card (D-08): TC multiselect + backlog-cap single-select, auto-saving
 * on every change (D-09 — no Save button, no dirty state). Takes no `isGuest` prop —
 * guests and registered users share the identical UI and code path (D-16).
 */
// UI-SPEC error state (PATCH failure): a small inline line near the toggled
// control, not a modal — the toggle itself already reverted via the hook's
// optimistic-rollback onError.
const SAVE_ERROR_COPY = "Couldn't save your import settings. Your change was undone — please try again.";

export function ImportFilterCard() {
  const { data: settings, isLoading, isError } = useImportSettings();
  const updateSettings = useUpdateImportSettings();

  if (isError) {
    return (
      <Card data-testid="import-filter-card">
        <CardHeader size="compact">Import filters</CardHeader>
        <CardBody>
          <p className="text-sm text-destructive" data-testid="import-filter-error">
            Failed to load import settings. Something went wrong. Please try again in a moment.
          </p>
        </CardBody>
      </Card>
    );
  }

  // Rides the same profile/settings fetch that already gates the Import page —
  // no separate spinner/skeleton (UI-SPEC loading state). Render nothing until data lands.
  if (isLoading || !settings) return null;

  const handleToggleTc = (tc: TimeControl) => {
    const activeCount = TIME_CONTROLS.filter((t) => isTcActive(settings, t)).length;
    const currentlyActive = isTcActive(settings, tc);
    // Last-one-standing guard (UI-SPEC zero-one-many): deselecting the final
    // active TC is a no-op — at least one TC must always stay enabled.
    if (currentlyActive && activeCount === 1) return;
    updateSettings.mutate(withTcToggle(settings, tc, !currentlyActive));
  };

  const handleCapChange = (value: string) => {
    if (!value) return;
    const cap = Number(value) as GameCap;
    updateSettings.mutate({
      tc_bullet: settings.tc_bullet,
      tc_blitz: settings.tc_blitz,
      tc_rapid: settings.tc_rapid,
      tc_classical: settings.tc_classical,
      game_cap: cap,
    });
  };

  return (
    <Card data-testid="import-filter-card">
      <CardHeader size="compact">Import filters</CardHeader>
      <CardBody className="space-y-2">
        <div>
          <p className="mb-1 text-sm text-muted-foreground">Time controls</p>
          <div className="grid grid-cols-4 gap-1">
            {TIME_CONTROLS.map((tc) => {
              const active = isTcActive(settings, tc);
              return (
                <button
                  key={tc}
                  type="button"
                  onClick={() => handleToggleTc(tc)}
                  data-testid={`import-filter-time-control-${tc}`}
                  aria-label={`${TIME_CONTROL_LABELS[tc]} time control`}
                  aria-pressed={active}
                  className={cn(
                    'rounded border h-11 sm:h-7 text-sm transition-colors',
                    active
                      ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground pointer-fine:hover:bg-toggle-active-hover'
                      : 'border-border bg-inactive-bg text-muted-foreground pointer-fine:hover:bg-inactive-bg-hover pointer-fine:hover:text-foreground',
                  )}
                >
                  <span className="flex items-center justify-center gap-1">
                    <TimeControlIcon timeControl={tc} className="h-3.5 w-3.5" />
                    {TIME_CONTROL_LABELS[tc]}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <div className="mb-1 flex items-center gap-2">
            <p className="text-sm text-muted-foreground">Backlog cap</p>
            <InfoPopover ariaLabel="Import filter details" testId="import-filter-info-popover" side="top">
              {infoPopoverBody(settings.game_cap)}
            </InfoPopover>
          </div>
          <ToggleGroup
            type="single"
            value={String(settings.game_cap)}
            onValueChange={handleCapChange}
            variant="outline"
            size="sm"
            data-testid="import-filter-cap"
            className="w-full"
          >
            {GAME_CAPS.map((cap) => (
              <ToggleGroupItem
                key={cap}
                value={String(cap)}
                data-testid={`import-filter-cap-${cap}`}
                aria-pressed={settings.game_cap === cap}
                className="min-h-11 sm:min-h-0 flex-1 text-sm"
              >
                {cap.toLocaleString()}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>

        {updateSettings.isError && (
          <p className="text-sm text-destructive" data-testid="import-filter-save-error">
            {SAVE_ERROR_COPY}
          </p>
        )}
      </CardBody>
    </Card>
  );
}
