---
phase: 102-endgame-llm-statistical-reasoning-rework-v1-23
plan: 03
type: human-uat
version: endgame_v37
---

# Phase 102 UAT: endgame_v37 Narration Quality

**Purpose:** Confirm that the endgame_v37 payload + prompt changes land an observable narration
improvement and that all guards hold before the phase ships.

**No DB reset required.** UAT runs against existing prod data via admin impersonation. The prod
DB is never mutated. The dev DB is not involved.

---

## Decision Reference (what this UAT must confirm)

| ID | Locked Decision | Observable in Report |
|----|----------------|----------------------|
| D-03 | Percentile fields in payload for **all 11** percentile-bearing metrics (not just score_gap), enriched with anchor + n_games + value | `pctl=N (vs ~A-rated {tc} peers \| n_games=M \| value=V)` on summary lines |
| D-04 **(REVERSED v37)** | Percentile is a **primary, preferred** narration signal. Narrate when zone non-typical **OR** pctl extreme (`<25`/`>75`) with adequate/rich quality. Lead with percentile framing. | An extreme-pctl metric **IS** narrated even when its zone is typical; percentile framing leads, zone is supporting context |
| D-05 | Cohort framing: "vs ~{anchor}-rated {tc} players", never "globally" | Framing matches the chip on the page |
| D-06 | Time-pressure narration when gated: Score-Gap-by-time chart, Clock Gap, Net Flag Rate (each with its per-TC pctl) | All three appear when gated; Net Flag Rate no longer NaN/missing; per-TC pctl uses that TC's anchor |
| (new v37) | No double-narration: a metric's ΔES-gap pctl and raw-rate pctl are not both narrated for the same metric in one bullet | Conv/Parity/Recovery narrated once, picking the more informative angle |
| D-08 | Longer Data Analysis (up to ~500 words / 5 paragraphs) only when ≥3 distinct signals exist; sparse stays concise | Full-history report may be longer; sparse report stays short, no padding |
| D-10 | Vocabulary aligned to concepts accordion + tooltip popovers | No contradiction between report text and tooltip/accordion definitions |

---

## How to Run (step-by-step)

### Prerequisites

1. The backend is running the Phase 102 build (locally or on prod post-deploy). Confirm:
   ```bash
   grep "_PROMPT_VERSION" app/services/insights_llm.py
   # must return: _PROMPT_VERSION = "endgame_v37"
   ```

2. For local testing, start the dev server (no reset needed):
   ```bash
   docker compose -f docker-compose.dev.yml -p flawchess-dev up -d
   uv run uvicorn app.main:app --reload
   ```
   For prod testing (post-deploy), open the prod SSH tunnel:
   ```bash
   bin/prod_db_tunnel.sh
   ```

3. The app must have the prod data or sufficient dev data to represent all three cohorts.
   **Prod is the gold standard** for UAT — the three cohort candidates in §Cohorts below are
   identified for prod. For local testing, substitute the dev users listed as alternatives.

### Impersonation workflow

1. Log in as admin (your own account, which is a superuser).
2. Use the admin panel at `/admin` or the API endpoint:
   ```
   POST /api/admin/impersonate/{user_id}
   Authorization: Bearer <admin-token>
   ```
   This returns a 1-hour impersonation JWT.
3. Use the impersonation token to call the endgame insights endpoint:
   ```
   POST /api/insights/endgame
   Authorization: Bearer <impersonation-token>
   Content-Type: application/json

   {"opponent_strength": "all"}
   ```
   Or open the Endgames tab in the UI with the impersonation token set.

### Forcing a fresh report (bypassing cache)

The cache key is `(user_id, prompt_version, model, opponent_strength)`. Because this is a new
prompt version (`endgame_v37`), there should be no cached report for any user on this version.

To verify the report version, check `llm_logs`:
```sql
SELECT user_id, prompt_version, created_at, status
FROM llm_logs
WHERE prompt_version = 'endgame_v37'
ORDER BY created_at DESC
LIMIT 10;
```

If a cached v36 report exists for a user and you want a fresh generation (e.g. to retest), you
can temporarily set a unique `notes` field or wait for a new game import to invalidate the cache.
The standard path is: new prompt version = no cache hit = fresh LLM call.

### Confirm report version in the response

The `POST /api/insights/endgame` response includes:
```json
{
  "status": "fresh",     // or "cache_hit" if already generated
  "prompt_version": "endgame_v37",
  ...
}
```
Confirm `prompt_version == "endgame_v37"` and `status == "fresh"` for the first generation.

---

## Candidate User Selection (Prod)

Since the prod DB tunnel was closed at scaffold-build time, run these queries against prod
after opening the tunnel (`bin/prod_db_tunnel.sh`), then pick the best candidates:

```sql
-- Query 1: Short-history cohort candidates
-- Target: few weekly buckets across time controls; span < 90 days OR < 200 total games
SELECT
    u.id,
    u.email,
    COUNT(DISTINCT g.id) AS total_games,
    COUNT(DISTINCT g.time_control_bucket) AS tc_count,
    EXTRACT(DAYS FROM MAX(g.played_at) - MIN(g.played_at)) AS span_days,
    MIN(g.played_at) AS oldest_game,
    MAX(g.played_at) AS newest_game
FROM users u
JOIN games g ON g.user_id = u.id
WHERE u.is_superuser = false
  AND u.is_verified = true
  AND g.played_at IS NOT NULL
GROUP BY u.id, u.email
HAVING COUNT(DISTINCT g.id) BETWEEN 50 AND 300
   AND EXTRACT(DAYS FROM MAX(g.played_at) - MIN(g.played_at)) < 120
ORDER BY span_days ASC, total_games ASC
LIMIT 10;

-- Query 2: Sparse-section cohort candidates
-- Target: decent total game count but thin time-pressure or type-breakdown data
-- (some endgame sections have few sequences, e.g. < 30 time-pressure games per TC)
SELECT
    u.id,
    u.email,
    COUNT(DISTINCT g.id) AS total_games,
    COUNT(DISTINCT g.time_control_bucket) AS tc_count,
    -- Check time-pressure coverage: count endgame games where clock data is available
    SUM(CASE WHEN gp.phase = 2 THEN 1 ELSE 0 END) AS endgame_positions
FROM users u
JOIN games g ON g.user_id = u.id
LEFT JOIN game_positions gp ON gp.game_id = g.id
WHERE u.is_superuser = false
  AND u.is_verified = true
  AND g.played_at IS NOT NULL
GROUP BY u.id, u.email
HAVING COUNT(DISTINCT g.id) BETWEEN 300 AND 1500
   AND COUNT(DISTINCT g.time_control_bucket) = 1  -- single TC reduces section coverage
ORDER BY total_games ASC
LIMIT 10;

-- Query 3: Full-history cohort candidates
-- Target: rich data across multiple TCs, long history (>12 months), many endgame games
SELECT
    u.id,
    u.email,
    COUNT(DISTINCT g.id) AS total_games,
    COUNT(DISTINCT g.time_control_bucket) AS tc_count,
    EXTRACT(MONTHS FROM MAX(g.played_at) - MIN(g.played_at)) AS span_months
FROM users u
JOIN games g ON g.user_id = u.id
WHERE u.is_superuser = false
  AND u.is_verified = true
  AND g.played_at IS NOT NULL
GROUP BY u.id, u.email
HAVING COUNT(DISTINCT g.id) > 3000
   AND COUNT(DISTINCT g.time_control_bucket) >= 2
   AND EXTRACT(MONTHS FROM MAX(g.played_at) - MIN(g.played_at)) >= 12
ORDER BY total_games DESC
LIMIT 10;
```

**Recommended selection criteria:**

- **Short-history (Cohort A):** Pick a user with 50-300 games, span under 4 months, preferably
  only 1 TC. The report should be concise and NOT have Score-Gap-by-time data (quintile table
  absent or most rows suppressed by the n-gate).
- **Sparse-section (Cohort B):** Pick a user with 500-1500 games but only one TC and few
  endgame sequences in some buckets (pawn or queen endgame, for example, with < 30 sequences).
  The time-pressure section may be thin. The report should stay concise on sparse sections.
- **Full-history (Cohort C):** Pick a user with > 3000 games, 2+ TCs, > 12 months history.
  This user is most likely to trigger the D-08 extended overview (≥3 distinct signals). Look
  for users with non-typical zones in multiple sections.

**Dev DB fallback candidates (if running locally):**

| Cohort | Dev user_id | Email | Rationale |
|--------|-------------|-------|-----------|
| Short-history | 43 | wasterram@test.com | ~564 games, few endgame sequences (173 endgame games) |
| Sparse-section | 33 | Sakrophan@test.com | ~1767 games, limited to 3 TCs, thinner time-pressure data |
| Full-history | 7 | hikaru@test.com | ~65469 games, 4 TCs, rich coverage across all sections |

---

## Cohort Scenarios and Checklists

---

### Cohort A: Short-History User

**Selected user_id:** `_______` (fill in after running Query 1 above)
**Email/username:** `_______`
**Rationale:** `_______` (e.g. "312 games, 3-month span, blitz only")

**Pass criteria:**

#### A-1 — Percentile present, enriched, and cohort-framed (D-03, D-05)
- [ ] At least one metric line in the report mentions a percentile rank, and the report **leads**
  with the percentile (not the zone) where a pctl exists.
- [ ] The framing reads "vs ~{anchor}-rated {tc} players" (e.g. "vs ~1200-rated blitz players"),
  NOT "globally" or "among all users".
- [ ] The percentile rank cited matches (within rounding) the chip shown on the Endgames page
  for the same metric and time control. (Compare the chip value to the report text.)
- [ ] Percentiles appear for **more than just score_gap** — verify the report cites percentiles
  for at least a couple of distinct metric families (e.g. Conversion/Recovery and a time-pressure
  metric), reflecting the all-11-metric coverage.
- [ ] Where the LLM cites reliability, it reflects the `n_games` basis (small samples qualified).

#### A-2 — Percentile-primary gate fires (D-04, REVERSED v37)
- [ ] Identify the metric with the most extreme percentile (check the page chips). If its pctl is
  `<25` or `>75` with adequate/rich data, confirm the report **DOES** narrate it — **even if its
  zone is typical**. (This is the v37 reversal: extreme percentile in a typical zone is now a
  legitimate story, the opposite of the pre-reversal rule.)
- [ ] Narration that combines both signals reads naturally — e.g. "in the typical zone, but at the
  82nd percentile vs peers at your level" — leading with percentile, zone as context.
- [ ] No double-narration: for Conv/Parity/Recovery, the report does not narrate both the
  ΔES-gap percentile and the raw-rate percentile for the same metric in the same bullet.

#### A-3 — Time-pressure narration (D-06)
- [ ] If the user has any non-typical time-pressure zone (Clock Gap or Net Flag Rate in a
  colored zone on the page), confirm the report mentions that metric.
- [ ] If time-pressure data is thin (most quintile rows suppressed by the n-gate because the
  user has < 30 games per quintile), the Score-Gap-by-time chart block is either absent or
  contains only a few rows — confirm no fabricated quintile data appears.
- [ ] Net Flag Rate is either mentioned with a real numeric value, or is explicitly absent
  because the zone is typical. It must NOT appear as "N/A" or be silently omitted while being
  non-typical. (This is the regression test: pre-phase it was always empty/NaN.)

#### A-4 — Overview length (D-08)
- [ ] The Data Analysis (overview) card is concise: roughly 2-3 paragraphs, well under ~500 words.
- [ ] No padding: no paragraph that restates another paragraph with slightly different wording.
- [ ] No fabricated "however" paragraphs that acknowledge thin data and then speculate anyway.

#### A-5 — Vocabulary (D-10)
- [ ] The report uses "Entry Eval Score" (not "Achievable Score") for the entry position metric.
- [ ] The report uses "Eval Score Gap" (not "Achievable Score Gap") for the page-level gap metric.
- [ ] The report uses "Endgame Score Gap" (not "Endgame vs Non-Endgame Score Gap").
- [ ] The report uses "Entry Eval" (not "Endgame Entry Eval") for the entry evaluation in pawns.
- [ ] No contradiction with the concepts accordion: if a term is defined in the accordion, the
  report's usage is consistent (same sign convention, same directionality).

---

### Cohort B: Sparse-Section User

**Selected user_id:** `_______` (fill in after running Query 2 above)
**Email/username:** `_______`
**Rationale:** `_______` (e.g. "900 games, rapid only, thin queen/pawn endgame coverage")

**Pass criteria:**

#### B-1 — Percentile cohort framing (D-03, D-05)
- [ ] The report references at least one percentile rank with cohort framing.
- [ ] The framing uses the correct anchor for the section granularity (per-TC for time-pressure
  metrics, aggregated-across-TCs framing for page-level metrics).

#### B-2 — Quality floor holds on sparse sections (D-04 v37 — the surviving guard)
- [ ] The v37 percentile-primary gate requires **adequate/rich** quality. For a section where data
  is sparse (a per-type card with "thin" sample quality), confirm the report does NOT narrate that
  metric as a finding **even if its percentile is extreme** — the quality floor still gates it.
- [ ] Confirm no "although the sample is small, you appear to be at the Nth percentile" framing.
- [ ] For any section that IS adequate/rich with an extreme pctl, confirm it IS now narrated
  (the reversal applies once the quality floor is met).

#### B-3 — Time-pressure narration (D-06)
- [ ] If this user has a non-typical Clock Gap zone: the report narrates Clock Gap with a
  real value and mentions it in the context of endgame time management.
- [ ] If Net Flag Rate zone is non-typical: the report mentions "net flag rate" (or "net timeout
  rate") with a real numeric value (not "N/A"). This is the primary regression check for LLM-06.
- [ ] If both zones are typical: neither metric is narrated as a finding. The time-pressure
  section of the report may be brief or absent — that is correct behavior.
- [ ] Score-Gap-by-time quintile table: if the user has at least one TC with ≥3 populated quintile
  rows (n-gate met), the report references low-clock performance. If all rows are suppressed, the
  report does not fabricate quintile commentary.

#### B-4 — No padding on sparse sections (D-08)
- [ ] Sections with thin/empty data are either skipped or acknowledged briefly.
  The report must NOT pad with hedging paragraphs that say nothing substantive.
- [ ] Count the distinct non-typical signals present (each of: an overall-gap story, a
  time-pressure story, a type-weakness story counts as one signal). If fewer than 3, the report
  should be in the default ~250-300 word range, not approaching 500 words.
- [ ] Flag any paragraph that is redundant (says the same thing as another paragraph in different
  words) — this is the most common padding failure.

#### B-5 — Vocabulary (D-10)
(Same checks as A-5 above — apply to this user's report.)
- [ ] "Entry Eval Score" (not "Achievable Score") used correctly.
- [ ] "Eval Score Gap" (not "Achievable Score Gap") used correctly.
- [ ] "Endgame Score Gap" (not "Endgame vs Non-Endgame Score Gap") used correctly.
- [ ] "Entry Eval" (not "Endgame Entry Eval") used correctly.
- [ ] Sign conventions match the MetricStatTooltip: percent-gap metrics (baseline=0) are signed
  (+/-), score-vs-50% metrics are unsigned, eval-in-pawns metrics are signed.

---

### Cohort C: Full-History User

**Selected user_id:** `_______` (fill in after running Query 3 above)
**Email/username:** `_______`
**Rationale:** `_______` (e.g. "8400 games, blitz + rapid, 18 months, non-typical zones in 4 metrics")

**Pass criteria:**

#### C-1 — Percentile coherence with page chips (D-03, D-05)
- [ ] Open the Endgames page for this user. Note the percentile values shown in chips for
  Endgame Score Gap (blitz), Endgame Score Gap (rapid), Clock Gap, and Net Flag Rate.
- [ ] For each chip value that appears in the report, confirm it matches the chip (within ±2pp
  rounding is acceptable).
- [ ] Cohort framing is "vs ~{anchor}-rated {tc} players" — the anchor value in the report
  should be close to the anchor in the chip tooltip (hover the chip to see).

#### C-2 — Percentile-primary: typical-zone but extreme-pctl metric IS narrated (D-04, REVERSED v37)
- [ ] Pick the metric whose chip sits in a typical zone band (gray/neutral) but whose percentile
  is extreme (`<25` or `>75`) with adequate/rich data. If no such metric exists, note "no
  typical-zone-extreme-pctl metric found for this user".
- [ ] Confirm that metric **IS** now narrated (it earns a mention as a finding), led by its
  percentile framing — this is the v37 reversal in action.
- [ ] Cross-check: a typical-zone metric whose percentile is **not** extreme (25-75) is still NOT
  narrated as a finding (the gate only opens for extreme pctl OR non-typical zone).
- [ ] Confirm no double-narration of a metric's ΔES-gap and raw-rate percentiles in one bullet.

#### C-3 — Time-pressure narration with real Net Flag Rate (D-06)
- [ ] The report narrates Score Gap by Remaining Time (low-clock quintile performance) if the
  user has non-typical time-pressure zones. The narration references "low-clock" or "under
  time pressure" and mentions a quintile bucket (Q0 = max pressure, Q4 = min pressure).
- [ ] The report narrates Clock Gap (`avg_clock_diff_pct`) if its zone is non-typical.
  The value cited should be close to the metric shown on the page.
- [ ] Net Flag Rate is mentioned with a real value (e.g. "+2.3% net flag advantage") if its
  zone is non-typical. **This is the primary regression check for LLM-06.** Pre-phase, this
  metric was always NaN and invisible to the model. Post-phase it must appear when the zone
  opens it.
- [ ] If all three time-pressure zones are typical: confirm none of them is narrated.

#### C-4 — Extended overview fires only when warranted (D-08)
- [ ] Count the distinct non-typical signals in this user's report:
  1. Overall-gap story (Endgame Score Gap or Eval Score Gap in a non-typical zone)?
  2. Time-pressure story (any time-pressure metric in a non-typical zone)?
  3. Type-weakness story (any per-endgame-type card in a non-typical zone)?
  4. ELO timeline story (Endgame ELO trending noticeably up/down)?
  Record the count: `_______` distinct signals.
- [ ] If count ≥ 3: the report MAY be up to ~500 words / 5 paragraphs. Measure approximate
  word count of the Data Analysis card: `_______` words.
- [ ] If count < 3: the report should be in the default ~250-300 word range.
- [ ] Regardless of length: no redundant paragraphs. No paragraph that is purely hedging filler
  without a specific observation. No paragraph that repeats the preceding one.

#### C-5 — Vocabulary (D-10)
(Same core checks as A-5 above, plus extended for full-history coverage.)
- [ ] "Entry Eval Score" (not "Achievable Score") used correctly.
- [ ] "Eval Score Gap" (not "Achievable Score Gap") used correctly.
- [ ] "Endgame Score Gap" used correctly for page-level metric.
- [ ] "Entry Eval" (not "Endgame Entry Eval") used correctly for pawns metric.
- [ ] Sign conventions: percent-gap metrics signed, score-vs-50% unsigned, pawn metrics signed.
- [ ] Endgame type labels: "Rook", "Minor Piece", "Pawn", "Queen", "Mixed" — match the page.
- [ ] "Conversion" / "Parity" / "Recovery" used without qualifying suffixes inconsistent with the
  accordion (the accordion calls them Win, Score, Save sections).
- [ ] No contradiction between the report's narration and the tooltip help text (hover any info
  icon on the Endgames page and compare the popover definition with the report's treatment of
  the same metric).

---

## Results Table

Fill in after running all three cohorts. Use pass (P), fail (F), or skip (S — metric absent for
this user, test inapplicable) in each cell.

| Scenario | User ID | D-03 Pctl present | D-04 Zone gate holds | D-05 Cohort framing | D-06 Time-pressure | D-08 Length policy | D-10 Vocabulary | Overall | Notes |
|----------|---------|------------------|----------------------|--------------------|-------------------|-------------------|----------------|---------|-------|
| A: Short-history | | | | | | | | | |
| B: Sparse-section | | | | | | | | | |
| C: Full-history | | | | | | | | | |

**Legend:** P = pass, F = fail, S = skip (criterion not testable for this user)

### Failure notes

(Fill in any failures — which criterion, what the report said, what it should have said.)

---

### Follow-up

Any failure triggers a `/gsd-plan-phase 102 --gaps` closure pass. Do not mark the phase complete
with open failures. Report the failures per the resume signal below.

---

## Resume Signal

After completing the UAT above, reply with:

- **"approved"** if all applicable criteria pass (S entries are fine; F entries are not).
- **List specific failures** if any criterion is F: scenario name, criterion ID (e.g. "C-3
  Net Flag Rate"), what the report said, what it should have said. These failures become the
  input for the --gaps closure pass.
