# Phase 77: Troll-opening watermark on Insights findings - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 77-troll-opening-watermark-on-insights-findings
**Areas discussed:** Curation breadth, Visual placement, Severity behavior, Backend-vs-frontend matching, Move Explorer surface

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

## Backend-vs-frontend matching (post-questions revision)

| Option | Description | Selected |
|--------|-------------|----------|
| Backend Zobrist matching | Side-only Zobrist hash computed in `opening_insights_service.py`; new `is_troll_opening: bool` on `OpeningInsightFinding`; static TSV + frozenset at startup; Python curation script. | |
| Frontend-only via opening name | `Set<string>` of troll opening names matched against `finding.opening_name`. Simplest possible. Risk: misses transpositions where opening identification doesn't catch them. | |
| Frontend-only via user-side FEN key | Strip opponent pieces from `entry_fen` / `result_fen` placement field, canonicalize, match against pre-computed `Set<string>`. Preserves the "all opponent variations" capture property without backend changes. Curation runs once offline as a Node/TS script over `cEDAMVBB.pgn`. | ✓ |

**User's choice:** Frontend-only via user-side FEN key.
**Notes:** User correctly pushed back on the backend plan as over-engineered for a 30%-opacity decorative element. The user-side-FEN-key approach drops the schema field, the TSV, the frozenset, the Python script, and the API contract change while preserving the design-note property that the watermark fires across all opponent variations.

---

## Move Explorer surface (post-questions revision)

| Option | Description | Selected |
|--------|-------------|----------|
| Insights cards only (original design) | Watermark only on `OpeningFindingCard`. Move Explorer explicitly excluded in design notes. | |
| Insights cards + Move Explorer (desktop + mobile) | Add inline troll icon to `MoveList` rows on both breakpoints. | |
| Insights cards + Move Explorer (desktop only) | Add inline troll icon to `MoveList` rows on desktop. Suppress on mobile due to row-height constraint (`h-12` vs `h-18` desktop). | ✓ |

**User's choice:** Insights cards + Move Explorer (desktop only).
**Notes:** Extending Phase 77 to cover Move Explorer overrides the design-note v1 scope but is a deliberate decision, not drift. Mobile suppression is driven by space — the `MoveList` mobile row at `h-12` doesn't have room for an additional inline icon next to the WDL bar and SAN. Visual register intentionally diverges between the two surfaces: 30%-opacity ambient watermark on cards vs. small fully-opaque inline icon on move-list rows.

---

## Claude's Discretion

- Exact pixel size of the watermark within the bottom-right anchor (60-80px guideline).
- Exact pixel size of the inline Move Explorer icon (likely `h-3.5 w-3.5` or `h-4 w-4` to match adjacent lucide icons).
- Whether the watermark is rendered as an absolutely-positioned `<img>` sibling element vs. a CSS `background-image` on the card root. Sibling preferred for cleaner asset/accessibility handling, but planner may pick either.
- Where exactly the Move Explorer icon sits within the row (left of SAN, right of SAN, or end of row).
- Test framing — frontend unit test for the user-side-key utility; snapshot/visual tests for both surfaces. Match the patterns already in `OpeningFindingCard.test.tsx` and the Move Explorer tests.
- Local caching of the scraped Lichess study PGN during curation script development.

## Deferred Ideas

- Troll-opening icon on Bookmarks / Games / Endgame surfaces — out of scope for v1; potential follow-on phase if the easter egg lands well.
- Mobile rendering of the Move Explorer icon — explicit space-constraint exclusion; revisit only if move-list mobile layout is re-thought.
- LLM narration referencing troll status — future LLM-narration work for opening insights, not this phase.
- Per-user opt-out / settings toggle for the watermark — not warranted at v1.
- Suppress-when-winning logic — explicitly rejected (D-05); revisit only on user feedback.
- Score/severity adjustment for troll openings — explicitly rejected; classification stays unchanged regardless of troll status.
- Backend matching via Zobrist hash — explicitly rejected in favor of frontend-only user-side-FEN-key matching. Revisit only if a future surface lacks the FEN in its payload.
