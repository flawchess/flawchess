import type { ReactElement, ReactNode } from 'react';
import { SkipBack, ChevronLeft, ChevronRight, Repeat2, FastForward } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface BoardControlsProps {
  onBack: () => void;
  onForward: () => void;
  onReset: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  /** Enable state for the Reset button. Defaults to `canGoBack` when omitted. */
  canReset?: boolean;
  canGoForward: boolean;
  /**
   * Fast-forward handler (Quick 260831-s4y). The button renders ONLY when this
   * is supplied — Openings, Bots, Train and the App.tsx mobile board bar all
   * render BoardControls without it and deliberately keep four buttons (D-07).
   */
  onFastForward?: () => void;
  /** Enable state for the fast-forward button. Ignored when onFastForward is omitted. */
  canFastForward?: boolean;
  /** Optional slot for an info icon rendered at the end of the bar */
  infoSlot?: React.ReactNode;
  /** Render buttons in a vertical column (used on mobile beside the board) */
  vertical?: boolean;
  /**
   * Flat surface (Quick 260628-dgv): drop the rounded charcoal pill so the buttons
   * sit directly on the parent bar, reading like the main nav buttons. Used by the
   * mobile /analysis board-controls footer; desktop/Openings keep the pill.
   */
  flat?: boolean;
  /**
   * Phase 223 UAT: render a visible text label under each icon, the icon-over-label
   * column shape `BotGameMobileBar` and the main nav already use. Opt-in, and only
   * meaningful together with `flat` — the mobile /analysis footer is the one caller;
   * every desktop/vertical caller stays icon-only with its tooltip.
   */
  labels?: boolean;
  /** Button size. 'sm' = h-8 w-8 (desktop), 'md' = h-9 w-9 (mobile slim row), 'lg' = h-11 w-11 (mobile vertical column), 'xl' = each button fills an equal share of the bar at a 48px tap target (bot play, matching that page's other action buttons). Defaults to 'lg' when vertical, 'sm' otherwise. */
  size?: 'sm' | 'md' | 'lg' | 'xl';
  /** Explicit Tailwind size classes for the buttons. Overrides `size` when provided — use when width and height need to be decoupled (e.g. `h-9 w-11`). */
  buttonClassName?: string;
  /** Additional CSS classes for the root container */
  className?: string;
}

const SIZE_CLASSES: Record<'sm' | 'md' | 'lg' | 'xl', string> = {
  sm: 'h-8 w-8',
  md: 'h-9 w-9',
  lg: 'h-11 w-11',
  xl: 'flex-1 h-12',
};

/**
 * Icon-over-label column, byte-identical to `BotGameMobileBar`'s own button
 * class so the two mobile bars read as the same furniture (Phase 223 UAT).
 */
const LABELLED_BUTTON_CLASS = 'h-auto flex-1 flex-col gap-1 px-1 py-2';

interface BoardControlsLayout {
  buttonSizeClass: string;
  surfaceClass: string;
  iconSize: string;
}

/**
 * All of the bar's class-resolution branching, pulled out of the component
 * body: `BoardControls.tsx` is pinned at cyclomatic complexity 16 in
 * `frontend/eslint.config.js`, so the `labels` arm could not be added inline.
 */
function resolveLayout(
  props: Pick<BoardControlsProps, 'flat' | 'labels' | 'vertical' | 'size' | 'buttonClassName'>,
): BoardControlsLayout {
  const { flat = false, labels = false, vertical = false, size, buttonClassName } = props;
  const resolvedSize = size ?? (vertical ? 'lg' : 'sm');
  // flat (mobile /analysis footer) reads like the main nav bar: each control fills an
  // equal share of the width (flex-1) with a tall 48px tap target, unless the caller
  // pins an explicit size/buttonClassName (Quick 260628-cjp — larger tap targets).
  const navStyle = flat && !buttonClassName && !size;
  // flat drops the charcoal pill so the bar reads like the main nav (Quick 260628-dgv).
  const surfaceClass = flat ? '' : 'rounded-lg charcoal-texture';
  // Match the main nav icon size (h-5) on the flat mobile bar and the 48px 'xl'
  // bar; keep h-4 on the smaller desktop/vertical pills.
  const iconSize = labels || navStyle || resolvedSize === 'xl' ? 'h-5 w-5' : 'h-4 w-4';
  if (labels) return { buttonSizeClass: LABELLED_BUTTON_CLASS, surfaceClass, iconSize };
  const buttonSizeClass =
    buttonClassName ?? (navStyle ? 'flex-1 h-12' : SIZE_CLASSES[resolvedSize]);
  return { buttonSizeClass, surfaceClass, iconSize };
}

interface ControlButtonProps {
  layout: BoardControlsLayout;
  /** Rendered under the icon only when the bar is in `labels` mode. */
  label: string | null;
  /** Tooltip text, and the button's `aria-label` in every mode — a visible
   * label never replaces it, so existing `getByLabelText` assertions hold. */
  tooltip: string;
  testId: string;
  icon: ReactNode;
  onClick: () => void;
  disabled?: boolean;
}

/**
 * One control in the bar. Extracted from the five near-identical Button blocks
 * this file used to repeat so the visible-label arm lives in exactly one place.
 */
function ControlButton({
  layout,
  label,
  tooltip,
  testId,
  icon,
  onClick,
  disabled = false,
}: ControlButtonProps): ReactElement {
  return (
    <Tooltip content={tooltip}>
      <Button
        variant="ghost"
        // A labelled control is a column, not a square, so it must not take the
        // fixed-size `icon` variant.
        size={label === null ? 'icon' : undefined}
        className={cn(layout.buttonSizeClass, 'hover:bg-accent')}
        onClick={onClick}
        disabled={disabled}
        aria-label={tooltip}
        data-testid={testId}
      >
        {icon}
        {label !== null && <span className="text-sm">{label}</span>}
      </Button>
    </Tooltip>
  );
}

export function BoardControls({
  onBack,
  onForward,
  onReset,
  onFlip,
  canGoBack,
  canReset,
  canGoForward,
  onFastForward,
  canFastForward,
  infoSlot,
  vertical = false,
  size,
  buttonClassName,
  className,
  flat = false,
  labels = false,
}: BoardControlsProps) {
  const layout = resolveLayout({ flat, labels, vertical, size, buttonClassName });
  // Short one-word labels: the mobile footer fits five columns on a 360px phone,
  // so "Fast forward to next key moment" reads as "Jump" there while the full
  // wording stays on the tooltip and the aria-label.
  const label = (text: string): string | null => (labels ? text : null);
  return (
    <div
      className={cn(
        'flex items-center justify-evenly',
        layout.surfaceClass,
        vertical && 'flex-col',
        className,
      )}
    >
      <ControlButton
        layout={layout}
        label={label('Start')}
        tooltip="Reset to start"
        testId="board-btn-reset"
        icon={<SkipBack className={layout.iconSize} />}
        onClick={onReset}
        disabled={!(canReset ?? canGoBack)}
      />
      <ControlButton
        layout={layout}
        label={label('Back')}
        tooltip="Previous move"
        testId="board-btn-back"
        icon={<ChevronLeft className={layout.iconSize} />}
        onClick={onBack}
        disabled={!canGoBack}
      />
      <ControlButton
        layout={layout}
        label={label('Next')}
        tooltip="Next move"
        testId="board-btn-forward"
        icon={<ChevronRight className={layout.iconSize} />}
        onClick={onForward}
        disabled={!canGoForward}
      />
      {onFastForward && (
        <ControlButton
          layout={layout}
          label={label('Jump')}
          tooltip="Fast forward to next key moment"
          testId="board-btn-fast-forward"
          icon={<FastForward className={layout.iconSize} />}
          onClick={onFastForward}
          disabled={!canFastForward}
        />
      )}
      <ControlButton
        layout={layout}
        label={label('Flip')}
        tooltip="Flip board"
        testId="board-btn-flip"
        icon={<Repeat2 className={layout.iconSize} />}
        onClick={onFlip}
      />
      {infoSlot}
    </div>
  );
}
