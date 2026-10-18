# Phase 242: Openings Stats + Insights Rework (SEED-204) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-17
**Phase:** 242-openings-stats-insights-rework
**Areas discussed:** Current/past cutoff rule, Most-played row count, Findings density

Pre-discussion prod check (1,276 user×colour pairs): last-200-games window per colour is ~61–68 days median
for 1000+ game users, p10 ~15–17 days; users under 200 games per colour see everything as current.

---

## Current/past cutoff rule

| Option | Description | Selected |
|--------|-------------|----------|
| 200 games OR 60 days | Current if within last 200 games of that colour or last 60 days, whichever is wider | ✓ |
| 200 games OR 30 days | Same hybrid, tighter floor | |
| Pure 200 games | As sketched; heavy players see 3-week-old openings as past | |

**User's choice:** 200 games OR 60 days

| Option | Description | Selected |
|--------|-------------|----------|
| Active filters | Cutoff under current sidebar filters, per colour | ✓ |
| All games, ignore filters | One stable definition per user | |

**User's choice:** Active filters

---

## Most-played row count

| Option | Description | Selected |
|--------|-------------|----------|
| Up to 10 current + up to 10 past | Fetch more before dedupe/split, cap each group at 10 | ✓ |
| Flat 20, split afterwards | Simpler; past can still crowd out current | |
| Keep 10 total | No change | |

**User's choice:** Up to 10 current + up to 10 past

| Option | Description | Selected |
|--------|-------------|----------|
| Keep current minimum | `MIN_GAMES_FOR_OPENING = 1`; fading carries low-sample signal | ✓ |
| Require 20 games for past rows | Drop small past openings | |

**User's choice:** Keep current minimum

---

## Findings density

| Option | Description | Selected |
|--------|-------------|----------|
| 2, then "Show more" | Phone shows 2 per section, expands to 5 | ✓ |
| Same 5 as desktop | One rule everywhere | |
| 1, then "Show more" | Table first | |

| Option | Description | Selected |
|--------|-------------|----------|
| Cap at 10, strongest p first | Current before older games | ✓ |
| No cap, strongest p first | Can grow to dozens | |
| Cap at 5 | Matches the cards | |

| Option | Description | Selected |
|--------|-------------|----------|
| Only p < 0.05 (medium) | The "leaning" candidates the empty state refers to | ✓ |
| Everything below 99% | Includes low-confidence noise | |

---

## Claude's Discretion

Defaults confirmed by owner: backend wave first; Moves tab eval centring in this phase; retire ScoreChart
multi-bookmark mode (StatsTab only caller); `/openings/insights` redirects to `/openings/stats`; 60-day floor
anchors on `dev_now_utc`.

## Deferred Ideas

None.
