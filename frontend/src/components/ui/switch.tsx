import * as React from "react"
import { Switch as SwitchPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

/**
 * Hand-rolled Switch primitive (Phase 155 Plan 01, D-03) — mirrors checkbox.tsx's
 * hand-rolled Radix-wrapper convention (data-slot + cn() className merge + unstyled
 * {...props} passthrough) rather than pulling `npx shadcn add switch`, to match
 * every other ui/ primitive and avoid re-theming a shadcn preset.
 *
 * The checked-track fill defaults to bg-primary but is caller-controllable: pass a
 * `data-[state=checked]:bg-[...]` utility (or style) in `className` and Tailwind's
 * class-merge lets it win over this default, so each engine card (Stockfish blue,
 * Maia violet, FlawChess brown) can tint its own switch without a hardcoded single
 * accent baked into the primitive.
 */
function Switch({
  className,
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
      data-slot="switch"
      className={cn(
        "peer inline-flex h-5 w-9 shrink-0 items-center rounded-full border border-transparent shadow-xs transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 data-[state=unchecked]:bg-input dark:data-[state=unchecked]:bg-input/80 data-[state=checked]:bg-primary",
        className
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb
        data-slot="switch-thumb"
        className="pointer-events-none block size-4 rounded-full bg-background ring-0 transition-transform data-[state=unchecked]:translate-x-0 data-[state=checked]:translate-x-4"
      />
    </SwitchPrimitive.Root>
  )
}

export { Switch }
