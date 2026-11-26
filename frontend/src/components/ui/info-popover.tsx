import * as React from "react"
import { Popover as PopoverPrimitive } from "radix-ui"
import { HelpCircle } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { useTrackedPopoverOpen } from "@/hooks/useTrackedOpen"

interface InfoPopoverProps {
  children: React.ReactNode
  ariaLabel: string
  testId: string
  side?: "top" | "bottom" | "left" | "right"
  /** Trigger glyph. Defaults to HelpCircle; pass e.g. Tag for the tag legends. */
  icon?: LucideIcon
  /**
   * Custom trigger content, overriding the default `icon` glyph — e.g. a
   * self-colored SVG badge (GemIcon) that isn't a LucideIcon. When set, the
   * trigger drops the default brown tint so the glyph keeps its own color.
   */
  triggerContent?: React.ReactNode
  /**
   * Close when a container holding the trigger scrolls. For badges inside a
   * scrolling list (the analysis move list), where the anchored popover would
   * otherwise ride over neighbouring UI. Leave off for long-text popovers that
   * the user scrolls the page to read.
   */
  closeOnScroll?: boolean
}

function InfoPopover({ children, ariaLabel, testId, side = "top", icon: Icon = HelpCircle, triggerContent, closeOnScroll = false }: InfoPopoverProps) {
  const [open, setOpen] = useTrackedPopoverOpen(testId)
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  const triggerRef = React.useRef<HTMLSpanElement>(null)

  // BUG FIX: Radix Popover keeps the open content anchored to its trigger while an
  // ancestor scrolls, so a badge popover opened by a tap in the mobile move list
  // rode along over the chessboard when the user then dragged the list. Opt-in only:
  // long-text popovers (e.g. the game card accuracy info) must keep scrolling with
  // the page so the user can read them. With closeOnScroll, any scroll of a container
  // holding the trigger closes it (what Radix Tooltip does); scrolling inside the
  // popover content itself does not contain the trigger and is ignored.
  React.useEffect(() => {
    if (!open || !closeOnScroll) return
    const handleScroll = (event: Event) => {
      const target = event.target
      const trigger = triggerRef.current
      if (trigger && target instanceof Node && target.contains(trigger)) setOpen(false)
    }
    window.addEventListener("scroll", handleScroll, { capture: true, passive: true })
    return () => window.removeEventListener("scroll", handleScroll, { capture: true })
  }, [open, closeOnScroll, setOpen])

  const handleMouseEnter = () => {
    hoverTimeout.current = setTimeout(() => setOpen(true), 100)
  }

  const handleMouseLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current)
    setOpen(false)
  }

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        {/* Use span instead of button to avoid nested <button> when inside CollapsibleTrigger */}
        <span
          ref={triggerRef}
          role="button"
          tabIndex={0}
          className={cn(
            "focus:outline-none cursor-pointer",
            triggerContent ? "inline-flex items-center" : "text-brand-brown-light/70 hover:text-brand-brown",
          )}
          aria-label={ariaLabel}
          data-testid={testId}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          {triggerContent ?? <Icon className="h-4 w-4" />}
        </span>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side={side}
          sideOffset={4}
          onMouseEnter={() => { if (hoverTimeout.current) clearTimeout(hoverTimeout.current) }}
          onMouseLeave={handleMouseLeave}
          className={cn(
            "z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background",
            "data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
            "data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2",
            "data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2"
          )}
        >
          {children}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  )
}

export { InfoPopover }
