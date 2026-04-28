# Phase 77: Troll-opening watermark on Insights findings - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 77-troll-opening-watermark-on-insights-findings
**Areas discussed:** Curation breadth, Visual placement, Severity behavior

---

## Curation breadth

| Option | Description | Selected |
|--------|-------------|----------|
| Strict (Bongcloud-tier) | Only unambiguous meme/troll openings: Bongcloud, Grob, Borg-as-troll, Halloween, Barnes, Fred. Smaller set (~6-12 entries per color). Avoids burning legitimate experimenters. | ✓ |
| Broad (include fun gambits) | Adds Englund, Latvian, From's, Schliemann, Damiano. Larger set (~20-30 entries per color); higher false-fire rate on serious low-rated players. | |
| Strict + curate during script run | Start strict in TSV; script emits candidate list with names/PGNs and user hand-prunes before commit. Final breadth resolved at script-execution time. | |

**User's choice:** Strict (Bongcloud-tier)
**Notes:** Calibration heuristic adopted: "Could a 1200 player play this with a straight face?" — yes → exclude. Hand-pruning during the curation script run is still expected (planner should surface the candidate list before committing the TSV).

---

## Visual placement

| Option | Description | Selected |
|--------|-------------|----------|
| Anchored bottom-right | Stamp/seal style at bottom-right corner, ~60-80px, behind text. Lowest mobile contrast risk. | ✓ |
| Centered behind text | Diploma-style watermark dead-center at ~40-50% of card height. Most "watermark-y" look but highest text-contrast risk on mobile. | |
| Filling the card | Cover full card area at 30%. Boldest but real risk text becomes hard to read against severity tints. | |

**User's choice:** Anchored bottom-right
**Notes:** Bottom-right anchor keeps the watermark in the corner farthest from the severity border-left tint (red for weakness, green for strength), minimizing visual conflict. Watermark layer must use `pointer-events: none` so it never blocks clicks on `Moves` / `Games` link buttons.

---

## Severity behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Show always | Watermark fires regardless of classification/severity. Joke lands harder when user has trolled successfully. | ✓ |
| Suppress when winning | Skip watermark if classification = strength + severity = major (positive side). Avoids appearing to mock a legitimate winning result. | |
| Suppress on any strength card | Skip whenever classification = strength. Watermark only on weakness cards — strict "don't mock wins" stance. | |

**User's choice:** Show always
**Notes:** Aligns with the design-note default. Revisit only if user feedback flags the joke as mocking on positive-severity cards.

---

## Claude's Discretion

- Exact pixel size of the watermark within the bottom-right anchor (60-80px guideline).
- Whether the watermark is rendered as an absolutely-positioned `<img>` sibling element vs. a CSS `background-image` on the card root. Sibling preferred for cleaner asset/accessibility handling, but planner may pick either.
- Test framing — backend unit test for the boolean field; frontend snapshot vs. visual test for the watermark layer. Match the patterns already in `OpeningFindingCard.test.tsx` and `opening_insights_service` tests.
- Local caching of the scraped Lichess study PGN during curation script development.

## Deferred Ideas

- Troll-opening watermark on Move Explorer / Bookmarks / Games / Endgame surfaces — out of scope for v1; potential follow-on phase if the easter egg lands well.
- LLM narration referencing troll status — future LLM-narration work for opening insights, not this phase.
- Per-user opt-out / settings toggle for the watermark — not warranted at v1.
- Suppress-when-winning logic — explicitly rejected (D-05); revisit only on user feedback.
- Score/severity adjustment for troll openings — explicitly rejected; classification stays unchanged regardless of troll status.
