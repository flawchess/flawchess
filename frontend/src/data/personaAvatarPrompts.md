# Persona Avatar Prompts

Committed prompts for generating the 24 bot-persona portraits (D-15/D-16/D-17,
AVAT-01/AVAT-02). This document is the single generation source: it carries
every persona's descriptor line AND bio, and nothing else — `scripts/gen_persona_avatars.py`
reads ONLY this doc (never `personaRegistry.ts`) to assemble each generation
prompt.

Real workflow: `scripts/gen_persona_avatars.py` parses this doc (master style
prompt + per-style demeanor notes + the 24 per-persona descriptor bullets
below), generates a webp for every persona that has no existing
`frontend/src/assets/personas/{persona-id}.webp`, downscales to 512×512, and
writes it there. `resolveAvatarSrc()` (`personaAvatars.ts`) globs
`assets/personas/*.webp` at build time, so a curated webp is picked up
automatically — no code change needed. Curation loop: tune a bad avatar by
editing its descriptor line below, delete the stale webp, rerun the script
(it only (re)generates missing files, so deleting is what triggers a redo).

## Master Style Prompt

Match `frontend/public/icons/logo-256.png` — FlawChess's cel-shaded cartoon
detective-horse logo — exactly in rendering style:

> A cel-shaded, friendly cartoon animal portrait in the exact visual style of
> the FlawChess logo: clean bold black outlines, warm flat cel-shading with
> soft gradient highlights, big expressive eyes, a slightly oversized head on
> a compact body, square face-and-shoulders composition (crop at the chest,
> not a full body), centered on a plain neutral or softly-lit background,
> approximately 256×256, no text or watermark. The animal's expression and
> any accessories (glasses, hats, ties, necklaces, bandanas) should signal
> its chess playstyle personality — [insert per-persona demeanor/accessory
> notes below]. Warm, approachable, a little playful; never sinister or
> photorealistic.

Per-style demeanor to layer on top of the master prompt:

- **Attacker** — alert, forward-leaning posture, a determined or fired-up
  expression; optional small accessory suggesting readiness (e.g. a
  bandana, a sporty item) rather than anything overtly aggressive.
- **Trickster** — a mischievous, crooked grin, one eyebrow slightly raised;
  optional accessory that reads as sly (e.g. a monocle, a sly side-glance,
  a tilted hat).
- **Grinder** — calm, focused, a patient or slightly stoic expression;
  optional practical accessory (e.g. simple glasses, a scarf) reinforcing a
  no-nonsense, steady character.
- **Wall** — composed, unbothered, a small confident smile; optional cozy
  accessory (e.g. a snug sweater, a pair of round glasses) reinforcing a
  sturdy, unshakeable character.

Size/age cue: within each style, the low-rung (800) persona should read as
visually smaller/younger and the top-rung (1800) persona larger/more
seasoned — matching the species progression below (D-10).

## Per-Persona Descriptors

Each line: `persona-id — Name the Species — demeanor/accessory notes`.

### Attacker (fiery, forward, aggressive/complicating)

- `attacker-800` — Ziggy the Wasp — small, buzzing energy, big eager eyes,
  perhaps tiny sunglasses; reads as scrappy and quick. Bio: Ziggy buzzes
  toward your king the moment the position opens, sting first, plan later.
  At this level the checks and captures come fast and reckless — watch for a
  hanging piece mid-swarm.
- `attacker-1000` — Duke the Terrier — a scrappy little dog with a
  determined snarl-grin, maybe a small bandana. Bio: Duke barks first and
  calculates second, snapping up any pawn within reach. He is getting better
  at picking his fights, but a loose piece still tempts him more than it
  should.
- `attacker-1200` — Talon the Falcon — sharp-eyed, alert posture, feathers
  slightly ruffled forward, a focused predator gaze (still friendly, not
  scary). Bio: Talon circles quietly before diving — checks and captures are
  chosen, not just thrown. Watch for a sudden pawn storm the moment your king
  looks exposed.
- `attacker-1400` — Fury the Wolverine — compact and tough-looking, a
  confident smirk, maybe a scar-like marking for character (not gore).
  Also reused emoji visually for `trickster-1600` (Sly the Coyote) —
  keep the two portraits visually distinct despite the shared 🐺 emoji
  placeholder. Bio: Fury does not wait for a clean opening; she tears into
  any weakness she can find. Her attacks carry real teeth now, but she can
  still overextend chasing one more sacrifice.
- `attacker-1600` — Butch the Ram — sturdy build with curled horns, a
  charging-forward stance, determined expression. Bio: Butch charges with
  real calculation behind the horns, softmax-picking the sharpest line on
  the board. He is comfortable trading material for initiative — and
  usually right to.
- `attacker-1800` — Diesel the Bull — the largest Attacker, powerful build,
  calm-but-intense expression (calculated aggression, not wild). Bio: Diesel
  calculates deep before he charges, and by the time you feel the pressure
  it is already too late to retreat cleanly. He accepts the odd wild
  sacrifice as the price of a relentless attack.

### Trickster (mischievous, sly, complicating/swindling)

- `trickster-800` — Miko the Magpie — small glossy black-and-white bird,
  head cocked, a shiny trinket nearby (a small nod to "collecting" traps).
  Bio: Miko loves a shiny trap — Bongclouds, Grobs, anything that looks
  silly but bites back. At this level the traps are simple, but they catch
  more players than you would expect.
- `trickster-1000` — Slinky the Ferret — slender, sneaky-cute pose, one paw
  raised as if about to swipe something. Bio: Slinky slips into an odd
  opening and waits to see if you notice. His traps are still fairly easy
  to spot if you are paying attention, but plenty of players are not.
- `trickster-1200` — Vix the Fox — classic sly fox grin, maybe a
  bow-tie or neckerchief for a touch of charm. Bio: Vix mixes real openings
  with the occasional trick line, keeping you guessing about which game you
  are actually in. She is patient enough to wait for the swindle to ripen.
- `trickster-1400` — Riko the Raccoon — a raccoon with a mischievous mask
  marking (natural to the species) and a knowing smirk, maybe holding a
  small shiny object. Bio: Riko digs through the position looking for
  something to steal — a fork, a pin, a moment of confusion. He plays a
  real game, but never quite gives up on the trap underneath it.
- `trickster-1600` — Sly the Coyote — lean, alert, a wide toothy grin,
  slightly wild-eyed (swindle-mode energy). Bio: Sly enters swindle mode
  here, favoring sharp, high-variance lines that are easy to misplay under
  pressure. She is not always objectively best, but she is very good at
  making you second-guess yourself.
- `trickster-1800` — Cackle the Hyena — the largest Trickster, mid-laugh
  expression, confident and a little chaotic — the "swindle master" vibe.
  Bio: Cackle hunts for chaos, steering into the sharpest, most unbalanced
  positions the book allows. By this level the swindles are backed by real
  calculation — underestimate her at your own risk.

### Grinder (steady, methodical, trade-happy)

- `grinder-800` — Pip the Ant — tiny, industrious, carrying something twice
  its size, a determined little expression. Bio: Pip trades pieces the
  moment she gets the chance, happiest when the board is empty and simple.
  She is not fighting for the initiative — she is fighting for the endgame.
- `grinder-1000` — Dig the Mole — round and earthy, small round glasses,
  a patient expression, paws ready to dig in. Bio: Dig burrows toward a
  simplified position, offering trades whenever the exchange is even. He
  rarely storms forward — he would rather grind you down one pawn at a time.
- `grinder-1200` — Otto the Otter — calm and content, maybe holding a small
  stone (a nod to its patient, methodical nature). Bio: Otto swims calmly
  toward the endgame, trading down whenever the position allows it. He
  never resigns early, choosing to paddle on even in a difficult position.
- `grinder-1400` — Tank the Ox — sturdy and grounded, a calm stoic
  expression, maybe a simple collar or bandana. Bio: Tank plows through
  complications by simplifying them away, trading pieces until only the
  essentials remain. He is stubborn in a lost position, playing on long
  past the point most bots would resign.
- `grinder-1600` — Bo the Buffalo — broad and solid, a calm confident
  stance, unshaken expression. Bio: Bo calculates its way into favorable
  trades, steering the game toward the flat, grounded endgames it measures
  best in. It genuinely enjoys a long fight and will not give up a
  difficult position without one.
- `grinder-1800` — Yara the Yak — the largest Grinder, shaggy and imposing
  but gentle-eyed, a wise, unhurried expression. Bio: Yara calculates deep
  into the endgame before she ever agrees to trade, and by the time the
  dust settles she usually has the better structure. She almost never
  resigns, grinding on long after the position looks lost.

### Wall (composed, defensive, simplifying)

- `wall-800` — Sheldon the Snail — small, tucked partly into its shell, a
  content sleepy-eyed expression. Bio: Sheldon retreats into his shell at
  the first sign of trouble, preferring a slow, solid setup over any early
  adventure. He is happy to trade down toward a draw well before things get
  complicated.
- `wall-1000` — Spike the Hedgehog — round and prickly, curled slightly
  defensive, a small content smile. Bio: Spike curls into a tight, prickly
  system and dares you to break through it. He welcomes an early draw more
  readily than most, content to hold rather than fight.
- `wall-1200` — Shelly the Turtle — calm, steady, round glasses perhaps,
  unbothered expression. Bio: Shelly plays the same fixed system regardless
  of what you throw at her, trading pieces whenever the position allows it.
  She never storms forward — patience is the whole plan.
- `wall-1400` — Bruno the Badger — sturdy, a bit stubborn-looking, maybe a
  scarf, a settled/planted stance. Bio: Bruno digs into his favorite system
  openings and holds his ground, trading down at every opportunity. He is a
  touch too eager to offer a draw, even from a perfectly fine position.
- `wall-1600` — Dana the Beaver — practical and industrious-looking, maybe
  holding a small stick/log, a calm focused expression. Bio: Dana calculates
  carefully to keep the position as flat and quiet as possible, damming up
  any complications before they start. She is genuinely comfortable
  steering toward a solid, simplified draw.
- `wall-1800` — Rocco the Armadillo — the largest Wall, armored and solid,
  a composed, immovable expression — "genuinely difficult to crack." Bio:
  Rocco calculates deep to keep everything under control, curling into the
  least chaotic line available whenever the position allows it. By this
  level his system openings and simplifying trades add up to a genuinely
  difficult wall to crack.

## Generating and Curating Avatars

- Run `uv run python scripts/gen_persona_avatars.py` (needs `GOOGLE_API_KEY`
  in `.env`) — it parses this doc, generates a 512×512 webp for every persona
  missing one under `frontend/src/assets/personas/`, and writes it there.
  `--dry-run` lists the pending personas and prints their assembled prompts
  with no API key required; `--limit N` caps the run; `--logo-ref` also
  passes the FlawChess logo as a style-reference image.
- Curate for consistency: delete a bad avatar's `.webp` and rerun the script
  — it only (re)generates missing files, so deleting is what triggers a
  redo. Tune the result by editing that persona's descriptor line above
  first (accessory, expression, size cue), then delete-and-rerun.
- File naming: `frontend/src/assets/personas/{persona-id}.webp`, matching
  `PersonaId` exactly (e.g. `attacker-800.webp`).
- `resolveAvatarSrc()` (`personaAvatars.ts`) globs `assets/personas/*.webp`
  at build time, keyed by the filename stem — a curated webp appears on the
  Bots page automatically, no code change needed. Until a persona's webp
  exists, its card falls back to the D-18 emoji placeholder.
