# Persona Avatar Prompts

Committed prompts for generating the 24 bot-persona portraits (Phase 183,
D-15/AVAT-01). This phase ships **placeholder avatars only** — species emoji
on a per-style background tint (D-18, `personaAvatars.ts`). These prompts are
for the future real-art PR (D-16/D-17): run each descriptor below through an
image-generation tool of your choice, curate the results, and drop the
curated `.webp` files into `frontend/src/assets/personas/{persona-id}.webp`
(square, face-and-shoulders, ~256×256 — see D-17). Keeping the prompts here
(not just in a chat transcript) makes regeneration and the future >2000-ELO
extension (SEED-114) repeatable.

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
  perhaps tiny sunglasses; reads as scrappy and quick.
- `attacker-1000` — Duke the Terrier — a scrappy little dog with a
  determined snarl-grin, maybe a small bandana.
- `attacker-1200` — Talon the Falcon — sharp-eyed, alert posture, feathers
  slightly ruffled forward, a focused predator gaze (still friendly, not
  scary).
- `attacker-1400` — Fury the Wolverine — compact and tough-looking, a
  confident smirk, maybe a scar-like marking for character (not gore).
  Also reused emoji visually for `trickster-1600` (Sly the Coyote) —
  keep the two portraits visually distinct despite the shared 🐺 emoji
  placeholder.
- `attacker-1600` — Butch the Ram — sturdy build with curled horns, a
  charging-forward stance, determined expression.
- `attacker-1800` — Diesel the Bull — the largest Attacker, powerful build,
  calm-but-intense expression (calculated aggression, not wild).

### Trickster (mischievous, sly, complicating/swindling)

- `trickster-800` — Miko the Magpie — small glossy black-and-white bird,
  head cocked, a shiny trinket nearby (a small nod to "collecting" traps).
- `trickster-1000` — Slinky the Ferret — slender, sneaky-cute pose, one paw
  raised as if about to swipe something.
- `trickster-1200` — Vix the Fox — classic sly fox grin, maybe a
  bow-tie or neckerchief for a touch of charm.
- `trickster-1400` — Riko the Raccoon — a raccoon with a mischievous mask
  marking (natural to the species) and a knowing smirk, maybe holding a
  small shiny object.
- `trickster-1600` — Sly the Coyote — lean, alert, a wide toothy grin,
  slightly wild-eyed (swindle-mode energy).
- `trickster-1800` — Cackle the Hyena — the largest Trickster, mid-laugh
  expression, confident and a little chaotic — the "swindle master" vibe.

### Grinder (steady, methodical, trade-happy)

- `grinder-800` — Pip the Ant — tiny, industrious, carrying something twice
  its size, a determined little expression.
- `grinder-1000` — Dig the Mole — round and earthy, small round glasses,
  a patient expression, paws ready to dig in.
- `grinder-1200` — Otto the Otter — calm and content, maybe holding a small
  stone (a nod to its patient, methodical nature).
- `grinder-1400` — Tank the Ox — sturdy and grounded, a calm stoic
  expression, maybe a simple collar or bandana.
- `grinder-1600` — Bo the Buffalo — broad and solid, a calm confident
  stance, unshaken expression.
- `grinder-1800` — Yara the Yak — the largest Grinder, shaggy and imposing
  but gentle-eyed, a wise, unhurried expression.

### Wall (composed, defensive, simplifying)

- `wall-800` — Sheldon the Snail — small, tucked partly into its shell, a
  content sleepy-eyed expression.
- `wall-1000` — Spike the Hedgehog — round and prickly, curled slightly
  defensive, a small content smile.
- `wall-1200` — Shelly the Turtle — calm, steady, round glasses perhaps,
  unbothered expression.
- `wall-1400` — Bruno the Badger — sturdy, a bit stubborn-looking, maybe a
  scarf, a settled/planted stance.
- `wall-1600` — Dana the Beaver — practical and industrious-looking, maybe
  holding a small stick/log, a calm focused expression.
- `wall-1800` — Rocco the Armadillo — the largest Wall, armored and solid,
  a composed, immovable expression — "genuinely difficult to crack."

## Notes for the Future Real-Art PR

- Generate at a higher resolution than the final 256×256 and downscale
  before committing (D-17) — keeps line art crisp after compression.
- Curate for consistency: run several seeds/variations per persona and pick
  the ones that best match the master style prompt's line weight and
  shading (avoid a "different artist per image" look).
- File naming: `frontend/src/assets/personas/{persona-id}.webp`, matching
  `PersonaId` exactly (e.g. `attacker-800.webp`).
- This phase intentionally ships zero Vite asset-import machinery
  (RESEARCH.md Pitfall 6) — building the `import.meta.glob`/named-import
  seam is part of the future PR, not this document.
