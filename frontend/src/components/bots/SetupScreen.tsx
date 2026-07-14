/**
 * SetupScreen — the pre-game setup screen for the Bots page (Phase 171 D-09,
 * PLAY-02). Composes the ELO, play-style, color, and time-control controls
 * and emits a fully-resolved `BotGameSettings` on Start.
 *
 * This is a pure, self-contained form: it takes a profile-derived ELO
 * default and an `onStart` callback as props (it does NOT call
 * `useUserProfile()` itself — `Bots.tsx` already has the profile and passes
 * `ownerKey` + `normalizedRating` down), so it stays trivially testable
 * without a QueryClient.
 *
 * Replaces the D-14 hardcoded start-settings stub that Phase 170
 * deliberately left behind. Plan 06 wires this component into `Bots.tsx`.
 */

import { useCallback, useState } from 'react';
import type { ReactElement } from 'react';
import { Button } from '@/components/ui/button';
import { InfoPopover } from '@/components/ui/info-popover';
import { EloSelector } from '@/components/analysis/EloSelector';
import { MAIA_ELO_LADDER } from '@/lib/maiaEncoding';
import { PlayStyleControl } from '@/components/bots/PlayStyleControl';
import {
  CHIP_BASE_CLASS,
  CHIP_ACTIVE_CLASS,
  CHIP_INACTIVE_CLASS,
} from '@/components/bots/chipStyles';
import {
  readSetupSettings,
  writeSetupSettings,
  resolveDefaultBotElo,
  DEFAULT_BOT_SETUP_SETTINGS,
  type BotSetupSettings,
} from '@/lib/botSetupSettings';
import {
  TIME_CONTROL_PRESETS,
  DEFAULT_TC_PRESET_LABEL,
  findPresetByLabel,
  type TimeControlPreset,
} from '@/lib/botTimeControlPresets';
import type { BotGameSettings } from '@/hooks/useBotGame';
import type { MoverColor } from '@/lib/liveFlaw';
import { cn } from '@/lib/utils';

export interface SetupScreenProps {
  /** Owner-scoped localStorage key (D-10) — `null` degrades to the shared `'anon'` bucket. */
  ownerKey: string | null;
  /** The caller's lichess-blitz-equivalent rating, or `null` for no anchor. */
  normalizedRating: number | null;
  onStart: (settings: BotGameSettings) => void;
}

type ColorPreference = BotSetupSettings['colorPreference'];

const TC_BUCKET_ORDER: readonly TimeControlPreset['bucket'][] = ['blitz', 'rapid', 'classical'];

const TC_BUCKET_LABELS: Record<TimeControlPreset['bucket'], string> = {
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Classical',
};

const COLOR_OPTIONS: ReadonlyArray<{ key: ColorPreference; label: string }> = [
  { key: 'white', label: 'White' },
  { key: 'black', label: 'Black' },
  { key: 'random', label: 'Random' },
];

/** Reverse lookup: seconds -> the matching lichess-style display label, used
 * only to seed the TC chip grid's initial selection from persisted seconds. */
function labelForSeconds(baseSeconds: number, incrementSeconds: number): string {
  const match = TIME_CONTROL_PRESETS.find(
    (preset) => preset.baseSeconds === baseSeconds && preset.incrementSeconds === incrementSeconds,
  );
  return match?.label ?? DEFAULT_TC_PRESET_LABEL;
}

/** `data-testid` for a TC chip, e.g. `setup-tc-rapid-15-10` — `+`/`.` become `-`. */
function tcPresetTestId(bucket: string, label: string): string {
  return `setup-tc-${bucket}-${label.replace(/[+.]/g, '-')}`;
}

interface SetupScreenState {
  botElo: number;
  blend: number;
  colorPreference: ColorPreference;
  tcLabel: string;
  setBotElo: (elo: number) => void;
  setBlend: (blend: number) => void;
  setColorPreference: (pref: ColorPreference) => void;
  setTcLabel: (label: string) => void;
  /** The profile-derived ELO default (or the 1500 no-anchor fallback). */
  defaultElo: number;
  /** Resolves every control into a fully-resolved `BotGameSettings`. */
  buildSettings: () => BotGameSettings;
}

/** All data shaping for `SetupScreen`, kept out of the JSX so the component
 * body stays declarative. */
function useSetupScreenState(
  ownerKey: string | null,
  normalizedRating: number | null,
): SetupScreenState {
  // BOT-03 (UI DEFAULT ONLY, not a bot-adaptivity signal): this default is
  // user-visible, user-overridable, and fixed for the game once chosen — it
  // is never fed into the bot's own move selection (selectBotMove's ELO
  // stays symmetric and non-adaptive per its own D-07 invariant). D-06: no
  // harness-table rung correction is applied here either — the ladder value
  // from `resolveDefaultBotElo` passes straight through.
  const defaultElo = resolveDefaultBotElo(normalizedRating);

  // Lazy initializer — read the persisted settings ONCE at first render. The
  // saved ELO wins over the profile default when present (mirrors
  // useMaiaEloDefault's user-override-wins rule).
  const [initial] = useState<BotSetupSettings>(
    () => readSetupSettings(ownerKey) ?? { ...DEFAULT_BOT_SETUP_SETTINGS, botElo: defaultElo },
  );

  const [botElo, setBotElo] = useState(initial.botElo);
  const [blend, setBlend] = useState(initial.blend);
  const [colorPreference, setColorPreference] = useState<ColorPreference>(initial.colorPreference);
  const [tcLabel, setTcLabel] = useState(() =>
    labelForSeconds(initial.baseSeconds, initial.incrementSeconds),
  );

  const buildSettings = useCallback((): BotGameSettings => {
    const preset = findPresetByLabel(tcLabel) ?? findPresetByLabel(DEFAULT_TC_PRESET_LABEL);
    const baseSeconds = preset?.baseSeconds ?? DEFAULT_BOT_SETUP_SETTINGS.baseSeconds;
    const incrementSeconds = preset?.incrementSeconds ?? DEFAULT_BOT_SETUP_SETTINGS.incrementSeconds;

    // D-12: an unresolved 'random' preference must NEVER reach `useBotGame` —
    // it is resolved to a concrete color HERE, before `onStart` fires, so the
    // snapshot and the exported PGN always carry the color actually played.
    const userColor: MoverColor =
      colorPreference === 'random' ? (Math.random() < 0.5 ? 'white' : 'black') : colorPreference;

    return { botElo, blend, baseSeconds, incrementSeconds, userColor };
  }, [botElo, blend, tcLabel, colorPreference]);

  return {
    botElo,
    blend,
    colorPreference,
    tcLabel,
    setBotElo,
    setBlend,
    setColorPreference,
    setTcLabel,
    defaultElo,
    buildSettings,
  };
}

interface TcBucketGroupProps {
  bucket: TimeControlPreset['bucket'];
  activeLabel: string;
  onSelect: (label: string) => void;
}

function TcBucketGroup({ bucket, activeLabel, onSelect }: TcBucketGroupProps): ReactElement {
  const presets = TIME_CONTROL_PRESETS.filter((preset) => preset.bucket === bucket);

  return (
    // Density pass (171 UAT gap 3, Task 2): mb-1 (was mb-2, -12px across 3
    // groups). The sub-header moves INLINE, to the left of the chip grid
    // (was stacked above it, -72px total across all 3 groups) — the 3-group
    // structure and per-group labelling are unchanged, only the layout axis.
    <div className="mb-1 flex items-center gap-2">
      {/* whitespace-nowrap: the label column is a fixed 80px, and "Classical"
          at text-sm is close enough to that budget on real device fonts that it
          would otherwise wrap to a second line, pushing this row taller than the
          h-10 chip grid it aligns with. jsdom does no layout, so no test can
          catch that (WR-02). */}
      <p className="w-20 shrink-0 whitespace-nowrap text-sm text-muted-foreground">
        {TC_BUCKET_LABELS[bucket]}
      </p>
      {/* WR-06: the track count is DERIVED from the bucket's own preset count,
          not read from a hand-maintained `{ blitz: 'grid-cols-4', ... }` lookup
          whose "matching each bucket's preset count" invariant nothing enforced
          — adding a 5th blitz preset silently wrapped the grid to a second row
          of 1. An inline `gridTemplateColumns` (rather than a `grid-cols-N`
          class) is required because Tailwind cannot generate class names from a
          runtime value; this one cannot drift from TIME_CONTROL_PRESETS. */}
      <div
        className="grid flex-1 gap-1"
        style={{ gridTemplateColumns: `repeat(${presets.length}, minmax(0, 1fr))` }}
      >
        {presets.map((preset) => {
          const isActive = activeLabel === preset.label;
          return (
            <button
              key={preset.label}
              type="button"
              data-testid={tcPresetTestId(bucket, preset.label)}
              aria-pressed={isActive}
              onClick={() => onSelect(preset.label)}
              className={cn(CHIP_BASE_CLASS, isActive ? CHIP_ACTIVE_CLASS : CHIP_INACTIVE_CLASS)}
            >
              {preset.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function SetupScreen({ ownerKey, normalizedRating, onStart }: SetupScreenProps): ReactElement {
  const state = useSetupScreenState(ownerKey, normalizedRating);

  const handleStart = (): void => {
    const settings = state.buildSettings();
    // Persist the UNRESOLVED color PREFERENCE (D-10/D-12) — a returning
    // Random user stays on Random next visit, never pinned to whichever side
    // this game's coin flip drew.
    writeSetupSettings(ownerKey, {
      botElo: settings.botElo,
      blend: settings.blend,
      baseSeconds: settings.baseSeconds,
      incrementSeconds: settings.incrementSeconds,
      colorPreference: state.colorPreference,
    });
    onStart(settings);
  };

  return (
    // Bottom-nav clearance (171 UAT gap 3, Task 1): the fixed mobile bottom
    // bar is `4rem` + `env(safe-area-inset-bottom)` -> ~64-98px worst case in
    // an installed PWA. Total clearance = 80px (this `pb-20`) + 64px
    // (App.tsx:567's `<main className="pb-16 sm:pb-0">`) = 144px, comfortably
    // clearing the 98px worst case. These two terms are on TWO DIFFERENT
    // elements (this page root and `<main>`) and therefore add — `pb-20`
    // itself OVERRIDES (not adds to) this root's own `p-4`'s padding-bottom,
    // since Tailwind emits the shorthand before the longhand. This costs zero
    // vertical space above the CTA; the padding is entirely below it.
    <div
      data-testid="setup-screen"
      // Density pass (171 UAT gap 3, Task 2): gap-4 -> gap-3 (-16px across the
      // 4 inter-group gaps). The `[&_[data-slot=slider]]:min-h-10` descendant
      // override scopes the ELO/Play-style sliders' hit target to 40px on
      // THIS screen only (-8px total) — the shared `ui/slider.tsx` root's
      // `min-h-11` (44px, app-wide iOS-HIG/Material contract) is left
      // untouched; only this one page takes the deviation, and only because
      // the CTA must clear the fold.
      className="mx-auto flex max-w-md flex-col gap-3 p-4 pb-20 sm:pb-4 [&_[data-slot=slider]]:min-h-10"
    >
      <div data-testid="setup-elo">
        <div className="mb-1 flex items-center gap-1">
          <span className="text-sm text-muted-foreground">Bot strength (ELO)</span>
          <InfoPopover ariaLabel="About the bot ELO setting" testId="setup-elo-info" side="bottom">
            <p>
              This is the rating band whose <strong>style</strong> the bot imitates — not a
              measured strength. The bot&apos;s real strength also depends on the play-style
              setting below. Calibration is still in progress.
            </p>
          </InfoPopover>
        </div>
        <EloSelector
          value={state.botElo}
          onChange={state.setBotElo}
          defaultElo={state.defaultElo}
          onReset={() => state.setBotElo(state.defaultElo)}
          ladder={MAIA_ELO_LADDER}
        />
      </div>

      <PlayStyleControl blend={state.blend} onChange={state.setBlend} />

      <div data-testid="setup-color">
        <p className="mb-1 text-sm text-muted-foreground">Play as</p>
        <div className="grid grid-cols-3 gap-1">
          {COLOR_OPTIONS.map((option) => {
            const isActive = state.colorPreference === option.key;
            return (
              <button
                key={option.key}
                type="button"
                data-testid={`setup-color-${option.key}`}
                aria-pressed={isActive}
                onClick={() => state.setColorPreference(option.key)}
                className={cn(CHIP_BASE_CLASS, isActive ? CHIP_ACTIVE_CLASS : CHIP_INACTIVE_CLASS)}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>

      <div data-testid="setup-tc">
        <p className="mb-1 text-sm text-muted-foreground">Time control</p>
        {TC_BUCKET_ORDER.map((bucket) => (
          <TcBucketGroup
            key={bucket}
            bucket={bucket}
            activeLabel={state.tcLabel}
            onSelect={state.setTcLabel}
          />
        ))}
      </div>

      {/* Density pass (171 UAT gap 3, Task 2): h-12 (48px) — the Start CTA was
          the SHORTEST control on a screen where every chip was 44px, backwards
          for the primary CTA. Now it is the tallest control on the screen. */}
      <Button
        variant="default"
        data-testid="btn-start-game"
        className="h-12 w-full"
        onClick={handleStart}
      >
        Start
      </Button>
    </div>
  );
}
