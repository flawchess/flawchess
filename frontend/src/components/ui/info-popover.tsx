import * as React from "react"
import { Popover as PopoverPrimitive } from "radix-ui"
import { Info } from "lucide-react"
import { cn } from "@/lib/utils"

interface InfoPopoverProps {
  children: React.ReactNode
  ariaLabel: string
  testId: string
  side?: "top" | "bottom" | "left" | "right"
}

function InfoPopover({ children, ariaLabel, testId, side = "top" }: InfoPopoverProps) {
  const [open, setOpen] = React.useState(false)
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null)

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
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground focus:outline-none"
          aria-label={ariaLabel}
          data-testid={testId}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <Info className="h-3.5 w-3.5" />
        </button>
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
