# Phase 183: Persona Registry & Bots Page - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-22
**Phase:** 183-Persona Registry & Bots Page
**Areas discussed:** Bots page structure, Persona start & in-game presence, Names/bios & tone, Avatar pipeline

---

## Bots page structure

| Option | Description | Selected |
|--------|-------------|----------|
| Grid-first, Custom as escape hatch | Persona grid is the default /bots view; Custom is a visible entry opening the unchanged SetupScreen | ✓ |
| Tabs: Personas / Custom | Equal-billing tabs at the top of /bots | |
| SetupScreen stays default | Keep the custom form as landing view, personas linked above it | |

| Option | Description | Selected |
|--------|-------------|----------|
| By style: 4 sections × 6 rungs | Style sections telling each identity story, rungs ascending 800→1800 | ✓ |
| By rung: ELO ladder | Six strength rows, 4 styles per row | |
| Flat grid + filter chips | One grid with style/rung filters | |

| Option | Description | Selected |
|--------|-------------|----------|
| Compact card + detail on tap | Avatar/name/ELO on card; bio + Play in a detail surface | ✓ |
| Full cards with visible bio | Complete bio inline on every card | |
| Compact card, Play directly on card | One-tap start, bio nearly invisible | |

| Option | Description | Selected |
|--------|-------------|----------|
| Tilde: ~1200 | Honest approximate signal; format survives Phase 184 swap | ✓ |
| Bare number: 1200 | Cleaner but overstates provisional precision | |
| Rating range: 1100–1300 | Most honest, too noisy on compact cards | |

**User's choice:** All recommended options.

---

## Persona start & in-game presence

| Option | Description | Selected |
|--------|-------------|----------|
| In the detail surface | Bio + compact color/TC chips (last-used defaults) + Play in one surface | ✓ |
| Instant start, last-used settings | Immediate start with persisted settings | |
| Global controls above the grid | One color/TC row applying to all personas | |

| Option | Description | Selected |
|--------|-------------|----------|
| Avatar + name at bot clock | Persona present in clock strip and result surfaces | ✓ |
| Name only | Clock strip shows name, no avatar | |
| Game view unchanged | Persona only on the Bots page | |

| Option | Description | Selected |
|--------|-------------|----------|
| Inline banner + Accept/Decline | Non-blocking draw-offer banner near board/clocks | ✓ |
| Modal dialog | Blocking accept/decline dialog | |
| Toast notification | Transient toast with actions | |

| Option | Description | Selected |
|--------|-------------|----------|
| Rematch persona + back to grid | Result surfaces offer Rematch (same config) + New opponent | ✓ |
| Always back to grid | All "New game" actions return to grid | |
| Rematch + suggest next rung | Additionally nudge the next rung up after a win | |

**User's choice:** All recommended options.

---

## Names, bios & tone

| Option | Description | Selected |
|--------|-------------|----------|
| Name + epithet | Human first name + style epithet (e.g. "Greta the Grinder") | |
| Plain human names | chess.com style bare names | |
| Thematic handles | Non-human gimmick names | |
| **Other (user)** | **Animal-themed bots matching the horse logo: small-to-medium animals for 800–1800, large animals for future >2000; style-influenced avatars (crazy Trickster) with accessories; square face-and-shoulders portraits** | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| 24 distinct species, size grows with rung | Species per slot fitting the style vibe, body size increasing 800→1800 | ✓ |
| One species per style | 6 individuals per species differentiated by accessories | |
| Species tier per rung | Shared size tier across styles per rung | |

| Option | Description | Selected |
|--------|-------------|----------|
| Name + species | "Riko the Raccoon" — species doubles as size/strength cue | ✓ |
| First name only | Species visible only in the avatar | |
| Species + style epithet | "The Grinding Badger" style-first naming | |

| Option | Description | Selected |
|--------|-------------|----------|
| Playful third-person, 2-3 sentences | Character sketch with per-tier story | ✓ |
| In-character first person | Each animal introduces itself | |
| Neutral trainer notes | Informative style description | |

| Option | Description | Selected |
|--------|-------------|----------|
| Claude drafts all, review in UAT | Full roster drafted at execute time, user swaps in UAT | ✓ |
| Roster sheet first | Species/name table approved before execution | |
| You provide the roster | User hand-picks species/names | |

**Notes:** During wrap-up the user additionally locked: rename the style display name to simply "the Wall" (drop "Great Wall"/"Solid Wall" phrasing).

---

## Avatar pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| Claude writes prompts, you generate | Master style prompt + 24 descriptors committed in-repo; user generates & curates | ✓ |
| Claude generates via API | Batch-generate via image API script | |
| You handle art fully | User produces portraits independently | |

| Option | Description | Selected |
|--------|-------------|----------|
| Placeholders in code, art via UAT | Placeholder mechanism, real art before merge | |
| Art before merge, no placeholder code | HUMAN-UAT gate until all portraits exist | |
| Ship with placeholders, art later | Merge with placeholders; portraits arrive asynchronously | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| 256px WebP in src/assets | Vite-imported hashed assets with build-time existence check | ✓ |
| public/ static folder | Path-convention static serving | |
| Claude decides | Planner/executor discretion | |

| Option | Description | Selected |
|--------|-------------|----------|
| Species emoji on style color | Emoji + per-style tint placeholder, publicly shippable | ✓ |
| Monogram initials | Initials on style-colored disc | |
| Single mascot silhouette | One shared silhouette tinted per style | |

**Notes:** User deviated from the recommended placeholder option: chose to merge with placeholders and let AVAT-01 complete asynchronously rather than gating the merge on art.

## Claude's Discretion

- 1600-rung Light-vs-Deep preset choice per persona (from measured ranges)
- Registry file shape/location; per-style accent colors (theme.ts)
- Snapshot/resume persona-id plumbing; detail-surface component choice; mobile grid columns
- Exact roster content (species/names/bios) and avatar prompt file format/location

## Deferred Ideas

- Large-animal personas above 2000 ELO (SEED-114)
- Calibrated ELO labels + honesty constraints (Phase 184)
- "Suggest next rung up" post-win nudge
- Final curated avatar art (asynchronous, post-merge)
