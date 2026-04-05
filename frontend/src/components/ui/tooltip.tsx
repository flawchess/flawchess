import * as React from "react"
import { Tooltip as TooltipPrimitive } from "radix-ui"
import { cn } from "@/lib/utils"

/** Global provider — wraps app once. Controls hover delay for all tooltips. */
function TooltipProvider({
  delayDuration = 700,
  ...props
}: React.ComponentProps<typeof TooltipPrimitive.Provider>) {
  return <TooltipPrimitive.Provider delayDuration={delayDuration} {...props} />
}

interface TooltipProps {
  /** Short label shown on hover. */
  content: React.ReactNode
  /** The hoverable element (button, link, etc.). */
  children: React.ReactNode
  side?: "top" | "bottom" | "left" | "right"
  /** Align with the trigger edge. Defaults to "center". */
  align?: "start" | "center" | "end"
}

/** Hover tooltip with white-bg style matching InfoPopover.
 *  Replaces native `title=` attributes for consistent branding. */
function Tooltip({ content, children, side = "top", align = "center" }: TooltipProps) {
  // Suppress tooltip on touch interactions. Radix opens tooltips on hover
  // with a delay (setTimeout), so suppressing at the event level alone isn't
  // enough — the timer fires later and opens the tooltip. Instead we track
  // the last pointer type and block `open` transitions at the state level
  // whenever the interaction was touch/pen. Mouse behaves normally.
  const [open, setOpen] = React.useState(false)
  const lastPointerType = React.useRef<string>("")
  const trackPointer = (e: React.PointerEvent) => {
    lastPointerType.current = e.pointerType
  }
  const handleOpenChange = (next: boolean) => {
    if (next && lastPointerType.current && lastPointerType.current !== "mouse") {
      return
    }
    setOpen(next)
  }

  return (
    <TooltipPrimitive.Root open={open} onOpenChange={handleOpenChange}>
      <TooltipPrimitive.Trigger
        asChild
        onPointerDown={trackPointer}
        onPointerEnter={trackPointer}
        onPointerMove={trackPointer}
      >
        {children}
      </TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          align={align}
          sideOffset={4}
          className={cn(
            "z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background",
            "data-[state=delayed-open]:animate-in data-[state=delayed-open]:fade-in-0 data-[state=delayed-open]:zoom-in-95",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
            "data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2",
            "data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2"
          )}
        >
          {content}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  )
}

export { Tooltip, TooltipProvider }
