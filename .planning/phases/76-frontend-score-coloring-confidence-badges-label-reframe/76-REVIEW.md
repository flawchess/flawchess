---
phase: 76
review_date: 2026-04-28
depth: standard
status: issues_found
files_reviewed: 12
findings:
  blocker: 0
  high: 0
  medium: 2
  low: 4
  info: 5
recommendation: "Fix MD-01 before merge (mobile parity vs locked D-10). MD-02 is latent — harden when convenient. Everything else is polish."
---

# Phase 76 — Code Review

Reviewed 12 source files (excluding tests) on branch `gsd/phase-76-frontend-score-coloring-confidence-badges-label-reframe` vs `main`. Backend math is faithfully migrated; arrow-color thresholds match the locked ≥0.60 / ≥0.55 / ≤0.45 / ≤0.40 boundaries; type contracts on both sides are aligned. Two MEDIUM findings worth addressing; remainder is optional polish.

## MEDIUM

### MD-01: Confidence-line tooltip is mouse-only — breaks D-10 / D-25 mobile parity

**File:** `frontend/src/components/insights/OpeningFindingCard.tsx:88-98`

`confidenceLine` wraps the `<p>Confidence: …</p>` in the shared `Tooltip` component (`frontend/src/components/ui/tooltip.tsx:33-43`), which **explicitly suppresses** open transitions when `pointerType !== "mouse"`. On phones/tablets the level-specific copy ("small sample, treat as a hint" / "enough games to trust the direction" / "sample is large enough to trust the magnitude") is unreachable. CONTEXT.md D-10 mandates "the existing tap-friendly tooltip pattern (matches the FilterPanel/charts InfoPopover and the MoveExplorer TranspositionInfo popover styling)"; D-25 lists D-10 under mobile parity. Section-title popovers in `OpeningInsightsBlock.tsx` correctly use `InfoPopover`; the card was missed.

Bonus issue: wrapping a non-interactive `<p>` as the Radix Tooltip trigger via `asChild` provides no tab/keyboard focus path either — also unreachable for keyboard users.

**Suggested fix:** Replace the `Tooltip` wrap with an `InfoPopover` next to the level word, matching the section-title pattern at `OpeningInsightsBlock.tsx:229-235`:

```tsx
const confidenceLine = (
  <p
    className="text-xs text-muted-foreground flex items-center gap-1"
    data-testid={`opening-finding-card-${idx}-confidence`}
  >
    Confidence: <span className="font-medium">{finding.confidence}</span>
    <InfoPopover
      ariaLabel={`Confidence ${finding.confidence} explainer`}
      testId={`opening-finding-card-${idx}-confidence-info`}
      side="top"
    >
      {CONFIDENCE_TOOLTIP[finding.confidence]}
    </InfoPopover>
  </p>
);
```

Tests in `OpeningFindingCard.test.tsx` will need to be updated from "hover" assertions to "click and verify popover" assertions.

---

### MD-02: `compute_confidence_bucket(... n=0)` raises ZeroDivisionError; one caller has inconsistent guards

**Files:** `app/services/score_confidence.py:41`, `app/services/openings_service.py:447-448`

`score_confidence.compute_confidence_bucket` divides by `n` on line 41 with no zero-guard. In `openings_service.get_next_moves` lines 447-448 the score expression guards `gc > 0`, but the next line passes `gc` to `compute_confidence_bucket` unconditionally. Today this is safe (the `query_next_moves` query only returns rows with `gc >= 1`), but the asymmetry between line 447 and 448 is a latent crash hazard if that contract changes (e.g. a new JOIN producing zero-game rows). `opening_insights_service._classify_row` (line 82) doesn't guard either, but at least there's no inconsistent guard right next to it. Sentry would catch the crash, so user-visible impact is bounded.

**Suggested fix:** Either guard the helper:

```python
if n <= 0:
    return "low", 1.0
```

…or drop the inconsistent `if gc > 0 else 0.5` on `openings_service.py:447` and assert the upstream invariant uniformly. Pick one.

## LOW

### LO-01: `_rank_section` indexes a dict that could KeyError on contract drift

**File:** `app/services/opening_insights_service.py:280`

`_CONFIDENCE_RANK[f.confidence]` raises `KeyError` if a finding ever carries an unexpected confidence value. Pydantic Literal validation makes this unreachable today, but `.get(f.confidence, 99)` would survive future widening (e.g. adding "very_high") without crashing the entire endpoint.

**Suggested fix:**

```python
key=lambda f: (_CONFIDENCE_RANK.get(f.confidence, 99), -abs(f.score - 0.5)),
```

---

### LO-02: `OpeningFindingCard` `wouldContradict` comment describes an unreachable case

**File:** `frontend/src/components/insights/OpeningFindingCard.tsx:43-50`

The comment frames the rounding-edge guard as covering "a weakness with score=0.499 rounding to 50%". Backend `_classify_row` only emits weakness for `score <= 0.45` and strength for `score >= 0.55`. A kept finding can therefore round to at most 45 (weakness) or at least 55 (strength) — never to 50 contradicting the section. The defensive code is harmless, but the rationale is wrong and will mislead future readers.

**Suggested fix:** Update comment to reflect the actual purpose:

```tsx
// Defensive: with the current ±0.05 effect-size gate this branch is
// unreachable (kept findings always round to ≤45 or ≥55), but if the
// gate is ever loosened we don't want a "weakness" card showing 50%.
```

---

### LO-03: Hard-coded `50` magic number for the score pivot

**File:** `frontend/src/components/insights/OpeningFindingCard.tsx:48-49`

CLAUDE.md prohibits magic numbers. The two `50` literals are `SCORE_PIVOT * 100`. `SCORE_PIVOT` is already exported from `@/lib/arrowColor`.

**Suggested fix:**

```tsx
import { SCORE_PIVOT } from '@/lib/arrowColor';
const PIVOT_PERCENT = SCORE_PIVOT * 100;
const wouldContradict =
  (finding.classification === 'weakness' && Math.round(rawPercent) >= PIVOT_PERCENT) ||
  (finding.classification === 'strength' && Math.round(rawPercent) <= PIVOT_PERCENT);
```

---

### LO-04: `compute_confidence_bucket` accepts `losses` but ignores it

**File:** `app/services/score_confidence.py:22-25, 38-40`

`losses` is documented as "accepted for API consistency … but is not used in the Wald formula". An unused parameter is a lint hazard (ruff `ARG001` would flag) and creates a future-bug surface where someone "fixes" the formula by introducing `losses` and breaks the math.

**Suggested fix:** Smaller diff — assert the WDL invariant:

```python
def compute_confidence_bucket(w: int, d: int, losses: int, n: int) -> tuple[Literal["low","medium","high"], float]:
    assert w + d + losses == n, f"WDL counts inconsistent: {w}+{d}+{losses} != {n}"
    ...
```

Larger but cleaner: drop `losses` and update both call sites to pass `(w, d, n)`.

## INFO

### IN-01: `score = (w + 0.5*d) / n` is computed in three places

**Files:** `app/services/opening_insights_service.py:98-100, 387`, `app/services/openings_service.py:447`

Phase 75 D-09 designated `score` as the canonical metric — it should have a single derivation. Either expose a `compute_score(w, d, n)` helper from `score_confidence.py`, or have `compute_confidence_bucket` return a 3-tuple `(score, confidence, p_value)`. The latter would eliminate the inconsistent guard noted in MD-02.

---

### IN-02: Section-title popover copy claims "probably not random" — overstates the statistical guarantee

**File:** `frontend/src/components/insights/OpeningInsightsBlock.tsx:14-27`

D-16 explicitly accepts a single shared copy for all four sections, so identical text is on-spec. But the second paragraph reads "a finding shows up when your score sits at least 5% from 50%, enough of a gap that it's probably not random" — a 5% gap with n=10 *is* random-compatible (that's why the confidence badge exists). The copy contradicts the third paragraph's confidence-badge framing.

**Suggested fix (copy nit):**

> A finding shows up when your score sits at least 5% from 50% — wide enough to be worth a look. Whether it's stable or noise depends on the **Confidence** badge below.

---

### IN-03: `sectionStartIdxs` reduce body is awkward

**File:** `frontend/src/components/insights/OpeningInsightsBlock.tsx:173-178`

The reduce body uses `prev = acc[i - 1] ?? 0` plus a separate `prevCount` ternary. A two-line `for` loop with a running counter is clearer:

```tsx
const sectionStartIdxs: number[] = [];
let running = 0;
for (const section of SECTIONS) {
  sectionStartIdxs.push(running);
  running += data[section.findingsKey].length;
}
```

Pure readability — not a bug.

---

### IN-04: `data-testid` collision between mobile and desktop branches inside one card

**File:** `frontend/src/components/insights/OpeningFindingCard.tsx:93, 107, 119, 132`

Both `sm:hidden` mobile branch and `hidden sm:flex` desktop branch render simultaneously (Tailwind toggles `display: none` only). Each `data-testid` therefore renders twice. Pre-existing for moves/games testids; Phase 76 extends the pattern with `-confidence`. Tests already adapt via `getAllByTestId`, but Browser Automation Rule #1 in CLAUDE.md implies stable, viewport-independent testids.

**Suggested fix (out of Phase 76 scope):** suffix testids with `-mobile`/`-desktop`, or render only one branch via JS responsive logic.

---

### IN-05: Docstring drift in `score_confidence.py`

**File:** `app/services/score_confidence.py:7-9`

Docstring says "Body migrated verbatim from app/services/opening_insights_service.py:105-152" — that line range no longer exists in `opening_insights_service.py` (the function was deleted there per D-06). The reference rots on first reformat.

**Suggested fix:** drop the line-range or replace with a SHA-anchored note ("originally introduced in 75-…").

## Items deliberately not flagged

- **Arrow-color boundary IEEE-754 concerns:** backend has a comment explaining literal-equality at boundaries; frontend uses identical arithmetic. Tests cover the cases.
- **`data-testid` on the new Conf `<td>`:** cells are non-interactive per CLAUDE.md rule; column header testid covers column-existence.
- **Sentry capture:** no new exception handlers added in this phase.
- **Security:** no new external inputs; popover copy is a static React tree.
- **`Openings.tsx:407` getArrowColor call site:** confirmed using new 3-arg signature with `entry.score` (build-restoration commit `d17a774`).

## Summary

| Severity | Count | IDs |
|---|---|---|
| BLOCKER | 0 | — |
| HIGH | 0 | — |
| MEDIUM | 2 | MD-01, MD-02 |
| LOW | 4 | LO-01, LO-02, LO-03, LO-04 |
| INFO | 5 | IN-01..IN-05 |

Phase is technically mergeable — no blockers, no security findings. MD-01 (mobile-parity tooltip vs popover) is the highest-priority follow-up because it directly violates locked decision D-10. Run `/gsd-code-review-fix 76` to dispatch the fixes, or address them inline.
