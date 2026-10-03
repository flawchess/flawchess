# Phase 226 review disposition

Source: `226-REVIEW.md` (standard depth, 17 tooling files, 0 critical / 7 warning / 4 info).
After the 226-13 reverts the branch carries only measurement tooling, so every finding concerns
developer and operator scripts, not production paths.

**Data check (orchestrator, 2026-10-01).** The committed gate data was checked directly against
the conditions the warnings say the tool does not validate:

- Every stop TSV for a2, a21 and a21s has `stop_rule == on` (16/16).
- Every MQ TSV carries the arm label matching its directory and the `stop_rule` matching its
  mode (60/60 each).
- MQ and throughput `root_split_calls` are 0 at a2/a21 and > 0 at a21s.
- `pool_size` matches the config: 4 for p4 and the MQ/stop runs, 2 for p2.
- Content rows' `hash_mode` matches their directory (76 clear, 76 warm).
- No arm's data is absent.

No finding changes the committed verdict.

| Finding | Disposition | Note |
|---|---|---|
| WR-01 reruns without is_dir guard | open (deferred) | Tooling hardening; the reruns ran to NO RERUNS REQUIRED on complete data |
| WR-02 S2 does not assert stop_rule on | open (deferred) | Data check: all stop rows are `on` |
| WR-03 mislabel validation narrow | open (deferred) | Data check: arm/stop_rule/root_split/pool_size/hash_mode all consistent |
| WR-04 absent arms not reported missing | open (deferred) | Data check: no arm absent |
| WR-05 NaN se/shift not flagged | open (deferred) | Committed verdict JSONs carry finite shifts and se |
| WR-06 fixture header hard-codes depth/quota | open (deferred) | The committed fixture was built with the defaults it labels; risk is a future overwrite |
| WR-07 trace edges keyed by child FEN | open (deferred) | Consistent with the D-13 override's finding that the duplicate-leaf anomalies sit on repetition-heavy control positions and appear identically at A0, i.e. they look like transposition artifacts. Supports that override |
| IN-01 floor rounding | open (deferred) | Committed 0.97 unaffected |
| IN-02 delta_bot rounding | open (deferred) | No boundary row in committed MQ data was reported |
| IN-03 identity key omits elo/blend | open (deferred) | Comparison is per cell, so no cross-cell collision |
| IN-04 fixture depth mixing, NaN gap | open (deferred) | Fixture quality; affects all arms equally |

All items are deferred to whichever phase next reuses this tooling (Phase 227 reuses the harness
and pool). Fixing them here would be unscoped work on a branch that ships no engine change.
