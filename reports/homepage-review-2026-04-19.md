# Homepage Review — 2026-04-19

Reviewed: http://localhost:5173/ (desktop viewport 1206×1002)

## What's good

- **Tagline lands.** "Engines are flawless, humans play FlawChess" is a strong, memorable hook with clear positioning.
- **Hero layout works.** Illustration + tagline + two CTAs (Sign up free / Use as Guest) + trust badges gives a complete above-the-fold story.
- **Feature sections have real product previews**, not generic stock shots. Endgame gauges, move explorer with WDL bars, and time management charts show concrete value.
- **Alternating dark/slightly-lighter section backgrounds** (`#1a1a1a`) give good visual rhythm.
- **Acknowledgements section** crediting Lichess, chess.com, python-chess, FastAPI, etc., is a nice open-source signal.
- **Responsive duplication done right.** Desktop/mobile variants are both in the DOM with proper `lg:hidden` / `max-lg:*` visibility toggles.

## What's bad

- **Preview images get clipped on the right.** At 1206px viewport the Endgame Metrics/ELO panel is cut mid-"Recovery" gauge, and the Opening Explorer preview clips inside the right column. On smaller desktops this will look broken, not intentional.
- **Endgame ELO Timeline preview has duplicated/jumped x-axis labels** (e.g. "Oct '23, Oct '23 … Jan '24, Oct '25, Dec '25"). Looks like a real screenshot bug in the source image, which reduces trust in the product.
- **"Under active development" notice is mid-page in a single cramped line** with a construction emoji. Feels apologetic rather than a confident "early access" signal.
- **"Use as Guest" CTA meaning is unclear** from the hero alone. What can a guest do? Import games? Just poke around with sample data? No answer until you click.
- **FAQ is entirely collapsed.** No default-open answer, so users who skim learn nothing without clicking.
- **Feature ordering feels arbitrary.** Endgame → Openings → Time → Opening Comparison → System Filter reads as two unrelated pillars intermixed. Consider grouping all opening features together, then endgame, then time.
- **Mobile nav affordance not obvious.** On desktop it's fine; worth checking at <640px whether there's a hamburger (the `hidden sm:flex` classes imply yes, but verify).
- **"Free to use / Mobile friendly / Cross-Platform" pill badges** wrap awkwardly (Cross-Platform drops to its own row), and "Mobile friendly" is a weak claim vs. a real benefit.

## Suggestions

1. **Replace the Endgame ELO screenshot** with a cleaner version. Fix the x-axis label duplication and ensure the image fits the container without clipping (use `object-contain` or crop to the right aspect ratio upfront).
2. **Widen the right-column preview or switch to a centered layout at the `lg` breakpoint**, so gauges/panels aren't sliced by the column edge.
3. **Rewrite the hero sub-bullets as benefit pairs**, e.g. "Free forever • Works on mobile • chess.com + lichess". Don't let "Cross-Platform" wrap alone.
4. **Clarify "Use as Guest".** Either change the label to "Try with sample data" or add a one-line tooltip/caption under the button.
5. **Open the first FAQ by default** (most likely: "Is it free?" or "What data do you access?"). Makes the section scannable.
6. **Reorder features**: Opening Explorer → System Opening Filter → Opening Comparison → Endgame Analytics → Time Management Stats. Groups cognate features and builds from simple to analytical.
7. **Upgrade the "Under active development" line** to a small badge near the hero ("Early access — v1.2, ~1k users") rather than a mid-page warning. Frames it as momentum, not a caveat.
8. **Add one trust element.** Either GitHub star count, a one-line testimonial, or an "X games analyzed" counter. The site is technically credible but feels empty of social proof.
9. **Consider a short looping demo GIF/video** at the top of the Opening Explorer section showing click-through on the board. Static screenshots under-sell the "interactive" promise.
