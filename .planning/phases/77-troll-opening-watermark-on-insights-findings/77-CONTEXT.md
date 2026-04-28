# Phase 77: Troll-opening watermark on Insights findings - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

When an Opening Insights finding card (`OpeningFindingCard`) shows a position the user reached by playing a curated troll opening (Bongcloud, Grob, etc.), render `Troll-Face.svg` as a 30%-opacity watermark behind the card content. Pure visual easter egg — no behavioral change, no scoring/severity adjustments, no badge or label.

In scope:
- Curation script + static TSV + in-memory `frozenset[int]` per color.
- Backend: extend `OpeningInsightFinding` schema with `is_troll_opening: bool`, populate from side-only Zobrist hash (`white_hash`/`black_hash`).
- Frontend: asset move, conditional watermark layer on `OpeningFindingCard`, mobile parity.
- Tests: backend unit test for the boolean flag; frontend snapshot/visual test for the watermark layer.

Out of scope (locked in design notes):
- Move Explorer / Bookmarks / Endgame / time-management surfaces.
- Tooltips, badges, or "Troll Opening Detected" labels.
- Scoring/severity adjustments based on troll status.
- Per-user opt-out.
- DB table for the troll set.

</domain>

<decisions>
## Implementation Decisions

### Curation breadth
- **D-01:** Strict (Bongcloud-tier) only. Curate to unambiguously meme/troll openings — Bongcloud, Grob, Borg, Halloween Gambit, Barnes, Fred, and any clearly non-serious entries from Lichess study `cEDAMVBB`. Exclude "fun but legitimate" gambits (Englund, Latvian, From's, Schliemann, Damiano) so the watermark never feels like an unfair burn on legitimate experimenters. Final TSV will be hand-pruned during the curation script run; downstream agents must surface the pruned candidate list to the user before committing the TSV.

### Visual placement
- **D-02:** Anchored bottom-right inside `OpeningFindingCard`. Sized like a stamp/seal (~60-80px), absolutely positioned, behind text via `z-index`. 30% opacity is locked. Reads as a subtle decorative stamp — lowest contrast risk on mobile (375px) and on the existing `charcoal-texture` card background.
- **D-03:** Mobile parity — same anchor (bottom-right), same opacity, same SVG sizing. Re-verify at 375px that the watermark doesn't clip or fight the prose/links column on the mobile layout (board sits left, prose stacked right; the watermark sits behind the right column's bottom area).
- **D-04:** Watermark must not block clicks on `Moves` / `Games` link buttons — use `pointer-events: none` on the SVG layer (or anchor it strictly outside the link row's interactive box).

### Severity behavior
- **D-05:** Show always. Watermark fires whenever the finding's position is in the troll set, regardless of `classification` or `severity`. The joke lands harder when the user has trolled successfully — no suppression on positive-severity strength cards.

### Data path
- **D-06:** `scripts/seed_troll_openings.py` mirrors `scripts/seed_openings.py`. Scrapes `https://lichess.org/study/cEDAMVBB.pgn`, parses with python-chess, extracts the *defining* position of each chapter (one side-hash per opening per color), and emits `app/data/troll_openings.tsv` with columns `name`, `color`, `side_hash`, plus `defining_moves` for human readability. Hand-pruning to the strict set per D-01 happens during the script run, before commit.
- **D-07:** Backend loads `app/data/troll_openings.tsv` at app startup into two `frozenset[int]` (one per color), matching how `app/data/openings.tsv` is consumed today. No DB table, no migration.
- **D-08:** Schema extension lives on `OpeningInsightFinding` (`app/schemas/insights.py`). `opening_insights_service.py` sets `is_troll_opening` from the finding's user color and entry-position side hash.

### Asset
- **D-09:** Move `temp/Troll-Face.svg` → `frontend/src/assets/troll-face.svg` (kebab-case per repo convention). Delete the `temp/` copy in the same commit. Frontend imports the SVG via Vite's asset pipeline.

### Claude's Discretion
- Exact pixel size of the watermark (the "60-80px" range above is a guideline, not a lock). Tune for visual balance against `MOBILE_BOARD_SIZE = 105` and `DESKTOP_BOARD_SIZE = 100`.
- Whether the watermark sits as a sibling element absolutely positioned via Tailwind (`absolute bottom-2 right-2 opacity-30 pointer-events-none`) or as a CSS `background-image` on the card root. Sibling element is preferred (cleaner SVG accessibility, no CSS background-position math), but planner may pick either.
- Test framing — backend unit test wiring, frontend snapshot vs. visual test choice. Use whichever pattern matches existing `OpeningFindingCard.test.tsx` and `opening_insights_service` tests.
- Curation script's network behavior — caching the scraped PGN locally during development is fine; the script must be re-runnable offline once the PGN is cached.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase-level design
- `.planning/notes/troll-openings-design.md` — full pre-discuss-phase design notes; defines locks (side-only matching, 30% opacity, finding-card-only scope, static TSV, asset move).
- `.planning/milestones/v1.14-ROADMAP.md` § "Phase 77" — phase entry with goal, dependency, sketch of work, and the three open questions resolved by this CONTEXT.md.

### Upstream phases (consumed contracts)
- `.planning/phases/75-backend-score-metric-confidence-annotation/75-CONTEXT.md` — Phase 75 added the score/confidence fields on `OpeningInsightFinding`; Phase 77 adds `is_troll_opening` to the same payload.
- `.planning/phases/76-frontend-score-coloring-confidence-badges-label-reframe/76-CONTEXT.md` — Phase 76 finalized the visual treatment of `OpeningFindingCard` (border-left tint, opacity-on-low-confidence, mobile/desktop layouts) — Phase 77's watermark layers behind that finalized treatment.

### External
- Lichess study `cEDAMVBB` — `https://lichess.org/study/cEDAMVBB/DYKeAEFt` — source for troll-opening curation. PGN endpoint: `https://lichess.org/study/cEDAMVBB.pgn`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/seed_openings.py` + `app/data/openings.tsv` — identical pattern to what Phase 77 needs for `seed_troll_openings.py` + `app/data/troll_openings.tsv`. Reuse the TSV reader, python-chess parsing, and Zobrist hashing utilities.
- `app/schemas/insights.py` — `OpeningInsightFinding` already carries the score/confidence fields from Phase 75; add `is_troll_opening: bool` here.
- `app/services/opening_insights_service.py` — already constructs `OpeningInsightFinding` per finding; this is the single insertion point for the `is_troll_opening` boolean.
- `frontend/src/components/insights/OpeningFindingCard.tsx` — `cardStyle` already mixes `borderLeftColor` + conditional `opacity` for unreliable findings. Watermark is a new absolutely-positioned child of the existing card root `<div>`. Both mobile and desktop layouts share the same outer card div, so a single watermark element covers both layouts.
- `frontend/src/lib/openingInsights.ts` — utility module already used by the card. If any client-side helpers are needed, they belong here.

### Established Patterns
- TSV-as-source-of-truth + in-memory frozenset/dict at startup is the established pattern for static reference data (openings, ECO codes). Phase 77 follows it.
- Side-only Zobrist matching (`white_hash`/`black_hash`) is the same pattern used for the system opening filter — already indexed and well-trodden.
- `data-testid` is required on interactive elements; the watermark is decorative and non-interactive (`pointer-events: none`), so it gets `data-testid="opening-finding-card-{idx}-troll-watermark"` for snapshot tests but no aria-label.

### Integration Points
- Backend: one new field on `OpeningInsightFinding` schema; one new boolean computation per finding inside `opening_insights_service.py`; one new module loading `troll_openings.tsv` into per-color frozensets at startup (place alongside other startup-loaded reference data).
- Frontend: one new asset import; one new conditional `<img>` (or background) child element inside the existing `OpeningFindingCard` outer div, applied to both mobile and desktop layouts via the shared parent.
- API contract: additive only — `is_troll_opening: bool` added to `OpeningInsightFinding`. No breaking changes; older frontends ignore the field.

</code_context>

<specifics>
## Specific Ideas

- The Bongcloud is the canonical example. If the curated set's filtering is unclear, "would the Bongcloud belong here?" is the calibration question. Yes → strict-set candidate. "Could a 1200 player play this with a straight face?" Yes → exclude.
- Lichess study `cEDAMVBB` is the seed list — but it's a starting point, not a contract. Hand-pruning is mandatory.
- The watermark must not visually conflict with the existing severity border-left tint (red for weakness, green for strength). Bottom-right anchor keeps it in the corner farthest from the border, minimizing interaction.

</specifics>

<deferred>
## Deferred Ideas

- Troll-opening watermark on Move Explorer, Bookmarks, Games tab, or Endgame surfaces — explicitly out of scope for v1; could become a follow-on phase if the easter egg lands well.
- LLM narration referencing troll status ("you're 28% with the Bongcloud — bold choice") — future LLM-narration work for opening insights, not this phase.
- Per-user opt-out / settings toggle for the watermark — only worth it if user feedback flags the joke as too loud. Not warranted at v1.
- Suppress-when-winning logic — explicitly rejected (D-05); revisit only if user feedback shows the joke reads as mocking on positive-severity cards.
- Score/severity adjustment for troll openings — explicitly rejected; classification stays unchanged regardless of troll status.

</deferred>

---

*Phase: 77-troll-opening-watermark-on-insights-findings*
*Context gathered: 2026-04-28*
