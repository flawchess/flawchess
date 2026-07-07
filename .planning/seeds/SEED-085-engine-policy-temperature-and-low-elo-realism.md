---
id: SEED-085
status: dormant
planted: 2026-07-06
planted_during: FlawChess Engine explainer doc session (2026-07-06)
trigger_when: after the FlawChess Engine ships its MVP UI (post SEED-082 MVP1) and real Maia+Stockfish providers are live enough to observe low-ELO recommendation quality
scope: medium (one tunable + a UI slider; possibly a deeper root-findability change)
source: user observation on a live 600-ELO analysis (screenshot) during the engine-doc session
depends_on: SEED-082 (FlawChess Engine — this tunes its behavior)
---

# SEED-085: Policy temperature knob + low-ELO practical-move realism

## The observation that triggered this

On a live 600-ELO analysis, the FlawChess Engine's top practical move was **Nb5** — which
Maia says a 600 plays only **5% of the time** (labeled "Best" in the move list, but nearly
unfindable at that level). The most *likely* human move in the same position was Rxf2 (a
Mistake, 57%). The complaint: at low ELO the engine still **favors Stockfish-like moves the
player is very unlikely to find**, which undercuts the "best move *you can actually pull off*"
promise.

## Two distinct threads (keep them separate)

### Thread A — Policy temperature (the user's proposed knob) [PRIMARY]

Add a **temperature** parameter on the Maia policy distribution, exposed as a **UI slider
directly below the ELO slider**.

- **Temperature > 1** flattens the distribution → more probability mass on low-probability
  (weaker, noisier) moves → the engine models *more* human fallibility.
- **Temperature < 1** sharpens toward the top move → converges toward Stockfish-like play.
- **Temperature = 1** is today's behavior (raw Maia policy).

This is the true global "how much does Maia matter" dial that the engine currently lacks
(the ratings are the only indirect lever today; leaf values are pure Stockfish, and Maia
priors only *weight* the expectation — there is no scalar to trade the two off). Temperature
is also already the designed mechanism for **time-pressure modeling** in SEED-082 (low clock
= flatter, noisier distribution), so the same knob does double duty. Structurally cheap: the
search already queries Maia with side-specific parameters, so temperature is one more
parameter, not a redesign.

**How it helps the observed case:** higher temperature raises the modeled probability that
*you* botch the accurate follow-up a line needs (Nb5 needs Nh3+ Kh1 Qxa1 Nxc7...). That
drags down the practical score of lines requiring hard-to-find continuations, so simpler,
more-forgiving moves can overtake them. It penalizes *fragile* lines.

### Thread B — Should the recommendation itself respect first-move findability? [DEEPER — the real fork]

Temperature alone does **not** fix the complaint. The root is a `max` node, and a root
candidate's practical score is the *expectation below it* — it deliberately does **not**
include the probability that you find the root move *itself*. If Nb5 were a one-move shot with
a trivial follow-up, no temperature setting would stop it topping the list.

**The premise under question (user, 2026-07-06):** "I'm not sure giving lines that assume the
first move is found makes sense. Practical lines are the ones where the first move can be
found more likely — especially at lower ELO." This challenges the SEED-082 rationale ("the
root is the one move you choose deliberately, *with the engine's help*, so assume you play
what we show you"). At 600, a 5%-findable top move is barely a recommendation — it reads as
"Stockfish with extra steps," the exact failure the engine exists to avoid.

**Converged direction (user, 2026-07-06):** aim for **"best you'll likely find,"** NOT "best
if you can find it" — the latter is too Stockfish-like. The recommendation should respect the
findability of the *first* move, especially at low ELO.

**"Why can't the root just be treated like all subsequent moves?" (user question, answered).**
It can't be *literally* identical, for one unavoidable reason: interior nodes never rank or
present a move — they only fold each move's probability into a weighted average to produce a
single position value. The root is the only node that must *select and present* a move. Treat
it literally like an interior node (average over your own moves) and you get a scalar position
score `Σ P_you(X)·V(X)`, not a recommendation — the "top move" disappears. So the root is
different *in kind*: it's the sole select-and-present node, and selection needs a criterion
averaging never needs.

**BUT the instinct behind the question is right, and sharper than "average the root."** The
real anomaly: every interior node *uses* a move's own probability `P(X)` (it's the weight),
while the root ranking *throws `P_you(X)` away* and sorts purely by `V(X)` (quality of the
resulting position). That is exactly why a 5%-findable Nb5 tops the list — its find-probability
is nowhere in the sort. The fix is not to average the root but to **stop being the one place
that ignores your own move probability: bring `P_you(X)` back into the root ranking.**

**The boundary that must be respected.** Do NOT rank by raw `P_you(X)·V(X)` — that recommends
your *most likely* move, which here is Rxf2 (57%, a Mistake). "Best you'll likely find" must
not collapse into "what you'll most likely play," or it becomes the greedy modal-move engine
SEED-082 explicitly rejected. Three distinct targets:

```
   rank by V(X)      →  Nb5   (Best, 5%)      ← too Stockfish ("if you find it")   ✗ rejected
   rank by P·V(X)    →  Rxf2  (Mistake, 57%)  ← too Maia (your likely blunder)     ✗ rejected
   best FINDABLE V   →  Qxf2  (Good, 9%)      ← "best you'll likely find"          ✓ target
```

**Leading approach:** rank by `V(X)` but only over moves above a findability **floor** (take
the strongest move you'd *plausibly* find), or equivalently a soft `P_you(X)^β · V(X)` with
moderate β — with the floor/β **auto-scaled by ELO** (near-off at master level where
everything is findable, aggressive at 600). No extra user control required. Within the
findable set you still take the best move (not the most probable), which is what keeps it a
*recommendation* and not a *prediction*.

**Cheap by construction — ranking-layer only.** The per-move practical score `V(X)` is
unchanged (it correctly answers "if I play Qxf2, how does it go"). Findability only decides
which move gets the spotlight, so the value math is untouched. This also reframes the engine's
identity from **oracle** (hands you the ideal move) to **coach** (best move within your reach)
— a deliberate product decision, not just a tuning tweak.

**Weaker options kept only for the record** (all rated below the leading approach): annotate-
but-don't-demote (too passive); explicit two-track "findable vs ideal" arrows (the "ideal"
track is the Stockfish-like framing the user rejected — only revive if a distinct teaching
surface is wanted); root-as-pure-expectation scalar (erases the recommendation, named only as
the theoretical endpoint).

**Interaction with Thread A:** the findability weighting should read `P_you` from the
*temperature-adjusted* Maia distribution, so temperature and the findability floor compose
instead of fighting. Design the two together.

## Why this matters

The whole differentiation of the FlawChess Engine is practical realism at the user's actual
level. A low-ELO user being told to play moves their peers find 5% of the time reads as "this
is just Stockfish with extra steps" — the exact failure mode the engine exists to avoid.
Getting low-ELO recommendations to *feel* human-appropriate is close to a make-or-break UX
signal for the product.

## When to surface

After the engine has a working MVP UI and real providers, so recommendation quality can be
observed on real positions (like the screenshot). Not before — this is a *tuning/UX* seed,
and it needs the live engine to tune against. Bundle Thread A (temperature slider) as the
quick win; treat Thread B as a design discussion in its own right.

## Breadcrumbs

- SEED-082 (`.planning/seeds/SEED-082-*`) — the engine this tunes; root=max rationale, the
  designed-but-unbuilt temperature knob for time pressure, and the explicitly-rejected
  "predict the modal move" design that Thread B must not slide back into.
- `docs/flawchess-engine-explained-2026-07-06.md` — plain-language engine explainer written
  the same session; its §5 (truncation, exploration floor) and §8 (deliberate limits) are the
  context for where temperature would slot in.

## Notes

Captured 2026-07-06 from a user observation on a live 600-ELO analysis during the
engine-explainer doc session. User proposed the temperature slider (Thread A); the
root-findability gap (Thread B) was surfaced as the likely deeper cause during capture.
