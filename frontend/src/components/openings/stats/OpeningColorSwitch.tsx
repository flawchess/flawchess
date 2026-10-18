import { Button } from '@/components/ui/button';
import { trackFeature } from '@/lib/analytics';
import { cn } from '@/lib/utils';
import type { Color } from '@/types/api';

const COLOR_OPTIONS: readonly { color: Color; label: string; swatchClass: string }[] = [
  { color: 'white', label: 'White', swatchClass: 'bg-white' },
  { color: 'black', label: 'Black', swatchClass: 'bg-zinc-900' },
];

interface OpeningColorSwitchProps {
  /** Testid prefix: `opening-color-switch-{idPrefix}` on the group, `...-{idPrefix}-{color}` per button. */
  idPrefix: string;
  selected: Color;
  onSelect: (color: Color) => void;
}

/**
 * The one White | Black switch of the Openings Stats tab. Selection is the Played-as filter
 * (D-26); the Umami option-change event fires from a click on the other
 * colour only, never on mount or restore.
 */
export function OpeningColorSwitch({ idPrefix, selected, onSelect }: OpeningColorSwitchProps) {
  const handleClick = (color: Color): void => {
    if (color === selected) return;
    onSelect(color);
    trackFeature('option-change', { target: 'opening-stats-color', value: color });
  };

  return (
    <div
      role="group"
      aria-label="Playing as"
      className="inline-flex gap-1"
      data-testid={`opening-color-switch-${idPrefix}`}
    >
      {COLOR_OPTIONS.map(({ color, label, swatchClass }) => {
        const isSelected = color === selected;
        return (
          <Button
            key={color}
            type="button"
            variant={isSelected ? 'default' : 'brand-outline'}
            aria-pressed={isSelected}
            className="min-h-11 gap-1.5 px-2.5 sm:min-h-0"
            onClick={() => handleClick(color)}
            data-testid={`opening-color-switch-${idPrefix}-${color}`}
          >
            <span
              className={cn('inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground', swatchClass)}
              aria-hidden="true"
            />
            {label}
          </Button>
        );
      })}
    </div>
  );
}
