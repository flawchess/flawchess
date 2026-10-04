import { LeaderboardPrivacyCard } from '@/components/settings/LeaderboardPrivacyCard';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { trackEvent } from '@/lib/analytics';
import {
  ARROW_COUNT_OPTIONS,
  DEFAULT_ARROWS,
  DEFAULT_LINES,
  LINE_COUNT_OPTIONS,
  resetAllSettings,
  setCountSetting,
  useEngineDisplaySettings,
  type CountSettingId,
  type SettingId,
} from '@/lib/engineSettings';
import { setMuted, useMuted } from '@/lib/sounds';

/** Umami `setting` value for the sound switch; typed so the event vocabulary stays in SettingId. */
const SOUND_SETTING_ID: SettingId = 'sound';
const ZERO_ARROWS_HELPER = "0 arrows hides this engine's arrows, the card stays.";

interface CountToggleGroupProps {
  id: CountSettingId;
  label: string;
  value: number;
  options: readonly number[];
  testId: string;
}

/** One single-select row of count buttons. Writes on every real change. */
function CountToggleGroup({ id, label, value, options, testId }: CountToggleGroupProps) {
  const handleChange = (next: string): void => {
    // Radix single-select emits '' when the active item is re-tapped: keep the
    // current value and fire nothing (no write, no Umami event).
    if (next === '') return;
    const parsed = Number(next);
    if (parsed === value) return;
    setCountSetting(id, parsed);
    trackEvent('settings-change', { setting: id, value: String(parsed) });
  };

  return (
    <div>
      <p className="mb-1 text-sm text-foreground">{label}</p>
      <ToggleGroup
        type="single"
        value={String(value)}
        onValueChange={handleChange}
        variant="outline"
        size="sm"
        className="w-full"
        aria-label={label}
        data-testid={testId}
      >
        {options.map((option) => (
          <ToggleGroupItem
            key={option}
            value={String(option)}
            data-testid={`${testId}-${option}`}
            className="flex-1 min-h-11 sm:min-h-0 text-sm"
          >
            {option}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  );
}

interface EngineSectionProps {
  testId: string;
  title: string;
  linesHelper: string;
  linesId: CountSettingId;
  arrowsId: CountSettingId;
  lines: number;
  arrows: number;
  groupPrefix: string;
}

function EngineSection({
  testId,
  title,
  linesHelper,
  linesId,
  arrowsId,
  lines,
  arrows,
  groupPrefix,
}: EngineSectionProps) {
  return (
    <Card as="section" data-testid={testId}>
      <CardHeader as="h2" size="compact">{title}</CardHeader>
      <CardBody className="space-y-3">
        <CountToggleGroup
          id={linesId}
          label="Lines"
          value={lines}
          options={LINE_COUNT_OPTIONS}
          testId={`${groupPrefix}-lines`}
        />
        <p className="text-sm text-muted-foreground">{linesHelper}</p>
        <CountToggleGroup
          id={arrowsId}
          label="Arrows"
          value={arrows}
          options={ARROW_COUNT_OPTIONS}
          testId={`${groupPrefix}-arrows`}
        />
        <p className="text-sm text-muted-foreground">{ZERO_ARROWS_HELPER}</p>
      </CardBody>
    </Card>
  );
}

/** The one settings panel, rendered by the desktop settings dialog and the mobile settings sheet. */
export function SettingsPanel() {
  const muted = useMuted();
  const { fcLines, fcArrows, sfLines, sfArrows } = useEngineDisplaySettings();

  const isAtDefaults =
    !muted &&
    fcLines === DEFAULT_LINES &&
    sfLines === DEFAULT_LINES &&
    fcArrows === DEFAULT_ARROWS &&
    sfArrows === DEFAULT_ARROWS;

  const handleSoundChange = (on: boolean): void => {
    setMuted(!on);
    trackEvent('settings-change', { setting: SOUND_SETTING_ID, value: on ? 'on' : 'off' });
  };

  const handleReset = (): void => {
    resetAllSettings();
    trackEvent('settings-reset');
  };

  return (
    <div data-testid="settings-panel" className="space-y-4">
      <Card as="section" data-testid="settings-section-sound">
        <CardHeader as="h2" size="compact">Sound</CardHeader>
        <CardBody className="flex items-center gap-2">
          <Switch
            data-testid="settings-sound-switch"
            aria-label="Sound effects"
            checked={!muted}
            onCheckedChange={handleSoundChange}
          />
          <p className="text-sm text-muted-foreground">Move and game sounds on every board.</p>
        </CardBody>
      </Card>

      <EngineSection
        testId="settings-section-flawchess"
        title="FlawChess engine"
        linesHelper="Shows up to this many lines. In forcing positions the engine may find fewer candidate moves."
        linesId="fcLines"
        arrowsId="fcArrows"
        lines={fcLines}
        arrows={fcArrows}
        groupPrefix="settings-fc"
      />

      <EngineSection
        testId="settings-section-stockfish"
        title="Stockfish"
        linesHelper="More lines means a shallower search for each line."
        linesId="sfLines"
        arrowsId="sfArrows"
        lines={sfLines}
        arrows={sfArrows}
        groupPrefix="settings-sf"
      />

      <Button
        type="button"
        variant="brand-outline"
        onClick={handleReset}
        disabled={isAtDefaults}
        data-testid="btn-settings-reset"
      >
        Reset to defaults
      </Button>

      {/* Server-persisted privacy choice (Phase 230 D-16), deliberately outside
          isAtDefaults and Reset, which only cover localStorage display
          preferences. The card hides itself for guests. */}
      <LeaderboardPrivacyCard />
    </div>
  );
}
