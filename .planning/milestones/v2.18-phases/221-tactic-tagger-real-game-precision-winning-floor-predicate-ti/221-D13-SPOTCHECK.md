# D-13 operator spot-check — verdicts (2026-09-13)

Operator review of the four `sacrifice` rows that carry `label: real` in
`fixtures/tagger/realgame_tags.csv` AND are dropped by D-05's persistence rule.
These four are the rows where the frozen label and the post-fix detector disagree, so
they are the only rows whose verdict can move the `sacrifice` floor.

Reviewed on a lichess board built from `pre_flaw_fen` (`board_url`), because the app's
own surface hides a stored tag whose pre-move position was already decisively lost or
whose confidence is under 70 (`library_repository.py`, `_TACTIC_CHIP_CONFIDENCE_MIN`
and the decided-lost suppression) — "no chip in the UI" does not mean "not tagged".

Material trajectories below are pov-relative (pov = the tagging side), measured from
line entry, via a standalone script over the frozen fixture.

## Verdicts

| Row | Operator verdict | Detector (post-fix) | Who is wrong |
|---|---|---|---|
| 0064 | Real sacrifice | dropped | **the rule** |
| 0128 | Could not follow — local Stockfish gives different best moves | dropped | unverifiable |
| 0133 | Real sacrifice | dropped | **the rule** |
| 0134 | No sacrifice occurs in this line | dropped | **the label** |

## 0064 and 0133 — the same failure shape

```
0064  k=2 cxb5   -3  <== fires     0133  k=2 Bxd3    -6  <== fires
      k=3 Nxb5   -2                      k=3 fxg7    -3
      k=5 Nxd6   +1  material back       k=5 gxf8=Q+ +10  material back
```

D-05 requires the deficit to still hold on `boards[k + 3]`. In both lines it does not —
and in both lines **the recovery IS the point of the sacrifice**: `Nxd6` and `gxf8=Q+`
are precisely the follow-ups the material was invested in. The rule cannot distinguish
"material returned because the sacrifice worked" from "material returned because it was
a plain recapture", which is the discrimination D-05 exists to make.

This is a defect in the rule, not in the labels. It is the direct cause of `sacrifice`'s
post-fix real-share of 0.222 and therefore of the 0.32 -> 0.17 floor re-seed: that floor
was derived by treating these drops as correct.

## 0134 — a mislabelled row

```
k=1 Qxb1  +4   (White wins a knight)
k=2 Qxe5+ +3
k=4 Bxf1  -2  <== fires  (Black wins a rook)
```

White never offers material; Black captures it. The stored `rationale` ("the trade
sequence nets the mover a material/initiative edge") does not describe a sacrifice at
all. Correct label is `wrong`, not `real`. The detector dropping it is the right outcome.

## 0128 — not usable as evidence

White is +12 at entry and +10 at the firing node: the "sacrifice" is `Rxe5` returning two
points while already completely winning, to force mate in 7. The stored PV is the line
from analysis time under a bounded engine budget, so a fresh deeper local search
legitimately disagrees with it. Do not spend more review time on this row.

## Consequence

Scope and limits: n=4, and these four were selected *because* they are contested, so this
is not a random sample. But two clean false drops that fail in the identical way is a
signal, not noise.

Decision taken by the operator on 2026-09-13: **fix D-05 in a gap-closure plan (221-08)
before the release and the prod retag**, rather than retagging 3.18M prod rows with a
rule that demonstrably drops genuine sacrifices, and rather than lowering the floor to
accommodate it. Plan 221-07 (release + prod retag) is deferred behind that work.
