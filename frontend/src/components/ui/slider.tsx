import * as React from "react"
import { Slider as SliderPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

/**
 * shadcn-style wrapper around the Radix Slider primitive. Supports both
 * single-thumb (`value={[v]}`) and dual-thumb (`value={[lo, hi]}`) modes.
 *
 * Mobile notes (Spike 001):
 * - `touch-action: none` on the root prevents the page from scrolling while
 *   the user drags a handle on touch devices.
 * - Thumb is sized 24px with a 44px min hit-target (iOS HIG / Material).
 */
function Slider({
  className,
  defaultValue,
  value,
  min = 0,
  max = 100,
  thumbLabels,
  ...props
}: React.ComponentProps<typeof SliderPrimitive.Root> & {
  /** Per-thumb aria-labels. Length must match thumb count. */
  thumbLabels?: readonly string[]
}) {
  const _values = React.useMemo<number[]>(
    () =>
      Array.isArray(value)
        ? value
        : Array.isArray(defaultValue)
          ? defaultValue
          : [min, max],
    [value, defaultValue, min, max],
  )

  return (
    <SliderPrimitive.Root
      data-slot="slider"
      // vaul (Drawer) escape hatch: a horizontal drag inside a `direction="right"`
      // drawer would otherwise be interpreted as swipe-to-close, so the user
      // can't move the slider thumbs on touch. `data-vaul-no-drag` opts the
      // slider out of the drawer's drag handler.
      data-vaul-no-drag=""
      defaultValue={defaultValue}
      value={value}
      min={min}
      max={max}
      className={cn(
        "relative flex w-full touch-none items-center select-none data-[disabled]:opacity-50 data-[orientation=vertical]:h-full data-[orientation=vertical]:min-h-44 data-[orientation=vertical]:w-auto data-[orientation=vertical]:flex-col",
        // 44px min vertical hit area on the root so the thumbs are easy to grab on touch.
        "min-h-11",
        className,
      )}
      {...props}
    >
      <SliderPrimitive.Track
        data-slot="slider-track"
        className={cn(
          "bg-muted relative grow overflow-hidden rounded-full data-[orientation=horizontal]:h-1.5 data-[orientation=horizontal]:w-full data-[orientation=vertical]:h-full data-[orientation=vertical]:w-1.5",
        )}
      >
        <SliderPrimitive.Range
          data-slot="slider-range"
          className={cn(
            "bg-toggle-active absolute data-[orientation=horizontal]:h-full data-[orientation=vertical]:w-full",
          )}
        />
      </SliderPrimitive.Track>
      {Array.from({ length: _values.length }, (_, index) => (
        <SliderPrimitive.Thumb
          data-slot="slider-thumb"
          aria-label={thumbLabels?.[index]}
          key={index}
          className="border-toggle-active bg-background ring-ring/50 block size-6 shrink-0 rounded-full border-2 shadow-sm transition-[color,box-shadow] hover:ring-4 focus-visible:ring-4 focus-visible:outline-hidden disabled:pointer-events-none disabled:opacity-50"
        />
      ))}
    </SliderPrimitive.Root>
  )
}

export { Slider }
