---
title: Flaw tag naming — final taxonomy (Phase 107 + 106 backend rename)
date: 2026-06-05
context: /gsd-explore session refining the flaw attribution-tag names before the Phase 107 frontend surfaces them
supersedes: the original tag names locked in Phase 105 / SEED-036
phases: [105 (backend, shipped), 106 (backend, shipped), 107 (frontend, upcoming)]
---

# Flaw tag naming — final

The flaw attribution taxonomy (severity tier + orthogonal tags) was named in Phase 105 and shipped
in Phase 106. Before Phase 107 puts these names on user-facing card chips and the Flaw-Stats panel,
the `/gsd-explore` session on 2026-06-05 renamed the tags that overclaimed or read awkwardly. This
note is the authoritative current taxonomy; it supersedes the names in SEED-036 and the Phase 105
artifacts (those are left as historical records).

## Final rename map

| Family | Old | New | Why renamed |
|--------|-----|-----|-------------|
| Severity | inaccuracy · mistake · blunder | *(unchanged)* | Standard chess terms. |
| Tempo | `time-pressure` | **`low-clock`** | "time-pressure" implies haste; under it you *also* rush, so it overlapped the fast-move tag. `low-clock` is pure clock-amount (forced). |
| Tempo | `hasty` | **`impatient`** | The real meaning is "moved fast *despite having time*" — self-inflicted haste, distinct from forced low-clock. `impatient` carries the voluntary nature. |
| Tempo | `knowledge-gap` | **`considered`** | "knowledge-gap" overclaimed a cause and was the dumping ground for missing-clock data. Now strictly "had time, didn't rush, still erred" — no time excuse. |
| Opportunity | `unpunished` | **`lucky-escape`** | Perspective was ambiguous. It's the one good-news tag (you blundered, opponent didn't capitalize). `lucky-escape` reads clearly player-positive. |
| Opportunity | `miss` | *(unchanged)* | Correct: a tactic only exists because the opponent erred first, so "you erred right after they erred" genuinely is a missed punishment. |
| Impact | `from-winning` | **`while-ahead`** | The flaw doesn't necessarily lose the win (that's `result-changing`); it just marks you were ahead when you slipped. `while-ahead` is state-accurate, doesn't overclaim. |
| Impact | `result-changing` | *(unchanged)* | Descriptive and correct. |
| Phase | `phase-opening` · `phase-middlegame` · `phase-endgame` | **`opening` · `middlegame` · `endgame`** | Dropped the redundant `phase-` prefix. |

### Tempo trio, restated (orthogonality is the point)

A two-level decision: *low on clock?* → `low-clock` (forced). Otherwise, *did you move fast?* →
`impatient` (self-inflicted haste) vs `considered` (took your time, still erred). Three
non-overlapping signals, each a different actionable story (manage the clock / slow down, you had
time / it's not a time problem).

## Structural change: tempo is now optional

The old invariant was "every flaw carries **exactly one** tempo tag," with missing-clock data
falling back to `knowledge-gap`. That conflated "no time excuse" with "we couldn't measure it."

New rule: **at most one** tempo tag. When clock data is unavailable, the flaw carries **no** tempo
tag at all (rather than a misleading fallback).

Implications:
- `_classify_tempo` returns `None` on missing clock/move-time instead of a fallback tag.
- `_build_tags` appends a tempo tag only when one is present.
- `TempoTag` Literal narrows to `low-clock | impatient | considered`.
- The Flaw-Stats panel's tempo stacked bar must show an **unmeasured remainder**
  (`total_mb_flaws − sum(tempo counts)`) so the segments still sum honestly — never normalize the
  three measured segments to 100%.

## Blast radius (this is shipped Phase 106 code)

Tags are computed **on-the-fly**, not persisted, so there is **no DB migration**. The rename is
pure code + docs:

- `app/services/flaws_service.py` — `FlawTag` / `TempoTag` Literals, `_classify_tempo` (optional
  return + names), `_build_tags`, `_phase_tag`, `FROM_WINNING_ES` comment, docstrings.
- `app/schemas/library.py` — `TempoTag` import + `tempo: dict[TempoTag, int]` shape (now sums to
  ≤ M+B flaws; document the unmeasured remainder).
- Phase 106 tests asserting the old tag strings.
- Phase 107 plans/design: `107-UI-SPEC.md`, sketches `001-analyzed-game-card` /
  `002-flaw-stats-panel` (READMEs + index.html), `sketches/themes/default.css` comments — updated
  in this session.
- SEED-036 — amendment block added; historical rationale left intact.

## Sequencing (open)

The backend rename touches shipped 106 code. Two options, user's call: fold it into the start of
Phase 107, or do a standalone `/gsd-quick` rename first so 107 starts on the final names. Not yet
decided.
