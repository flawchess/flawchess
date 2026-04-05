# Requirements: FlawChess v1.8 Advanced Analytics

**Defined:** 2026-04-05
**Core Value:** Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening

## v1.8 Requirements

Requirements for the v1.8 milestone. Each maps to a roadmap phase.

### Endgame ELO

- [ ] **ELO-01**: User sees Endgame ELO per (platform, time-control) combination, derived from actual rating adjusted by conversion/recovery performance against fixed baselines
- [ ] **ELO-02**: User sees actual ELO, Endgame ELO, and gap displayed side-by-side per combination in a breakdown table (strength/weakness visible at a glance)
- [ ] **ELO-03**: Combinations below minimum rated-game threshold are omitted; "Insufficient data" fallback shown when nothing qualifies
- [ ] **ELO-04**: User can read an info popover explaining Endgame ELO methodology, baseline assumptions, and caveats
- [ ] **ELO-05**: User sees Endgame ELO tracked over time per combination in a timeline chart with color-matched paired lines (bright = Endgame ELO, dark = Actual ELO) showing over/underperformance visually
- [ ] **ELO-06**: Existing sidebar filters (platform, time-control, rated, recency, color, opponent type) apply to both the breakdown table and timeline chart

### Opening Analytics

- [ ] **OPN-01**: User sees opening risk per position, measured as material imbalance variance at the opening→middlegame transition
- [ ] **OPN-02**: User sees opening drawishness per position (draw rate of games ending in opening phase), muted for low sample sizes, with info popover noting it's more relevant for higher-rated players

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Endgame Refinements

- **END-01**: Per-endgame-type Endgame ELO breakdown (rook, minor piece, pawn, queen, mixed)
- **END-02**: Refined conversion/recovery presentation (per-type rates in performance view)
- **END-03**: Rating-bucketed baselines calibrated from empirical data

### Opening Volatility

- **OVL-01**: Opening volatility from engine eval data (RMS of win-probability changes)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Cross-platform rating normalization (lichess→chess.com offset) | Empirical approximation only; per-platform display is cleaner and more honest |
| WDL entropy risk per move in explorer | Confusing to users — doesn't translate into actionable chess insight |
| ELO adjustment for opening statistics | Causal direction is murky; defer until endgame version validated |
| Server-side eval computation for unanalyzed games | Requires dedicated compute tier not feasible on current VPS |
| Per-game sharpness display | Only available for analyzed games — creates confusing two-tier experience |
| Raw `adjusted_endgame_skill` score (original 999.5 formula) | Replaced by Endgame ELO, which is more interpretable and actionable |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ELO-01 | TBD | Pending |
| ELO-02 | TBD | Pending |
| ELO-03 | TBD | Pending |
| ELO-04 | TBD | Pending |
| ELO-05 | TBD | Pending |
| ELO-06 | TBD | Pending |
| OPN-01 | TBD | Pending |
| OPN-02 | TBD | Pending |

**Coverage:**
- v1.8 requirements: 8 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 8 ⚠️

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-05 after initial definition*
