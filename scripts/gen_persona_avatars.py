"""Generate bot-persona avatar portraits via Gemini image generation (D-16).

Reads `frontend/src/data/personaAvatarPrompts.md` — the single generation
source (D-15) — and, for every persona that has no existing
`frontend/src/assets/personas/{persona-id}.webp`, generates a portrait with
Google's Gemini image model (via pydantic-ai's `NativeTool(ImageGenerationTool)`
capability), downscales it to 512x512, and writes it as a webp. Deleting a
curated webp and rerunning is the curation loop: this script only targets
personas that are still missing a file.

Doc <-> parser contract: this script parses ONLY `personaAvatarPrompts.md`
(never `personaRegistry.ts`) — the doc's per-persona descriptor bullets
(`- \\`persona-id\\` — Name the Species — notes`) must stay in that exact
shape or generation silently drops personas. See the doc's own header note.

Operator script, not app/services — no Sentry capture, no DB, no async
orchestration beyond what pydantic-ai's Agent.run needs. scripts/ is outside
the CI `ty check` path (app/ tests/ only).

Usage:
    # Preview: parse the doc, list pending personas, print assembled prompts.
    # No API key required, no network call.
    uv run python scripts/gen_persona_avatars.py --dry-run

    # Generate every persona missing a webp (needs GOOGLE_API_KEY in .env):
    uv run python scripts/gen_persona_avatars.py

    # Generate at most 3 this run (useful for a smoke check / spot curation):
    uv run python scripts/gen_persona_avatars.py --limit 3

    # Also pass the FlawChess logo as a style-reference image:
    uv run python scripts/gen_persona_avatars.py --logo-ref

    # Curation loop: tune a persona's descriptor line in the doc, then:
    rm frontend/src/assets/personas/attacker-800.webp
    uv run python scripts/gen_persona_avatars.py --limit 1
"""

from __future__ import annotations

import argparse
import asyncio
import io
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROMPTS_DOC = _REPO_ROOT / "frontend" / "src" / "data" / "personaAvatarPrompts.md"
_ASSETS_DIR = _REPO_ROOT / "frontend" / "src" / "assets" / "personas"
_LOGO_REF_PATH = _REPO_ROOT / "frontend" / "public" / "icons" / "logo-256.png"

# The 4 style names the doc's demeanor bullets and persona ids both key off —
# mirrors personaRegistry.ts's STYLE_SECTION_ORDER (Attacker/Trickster/Grinder/Wall).
STYLES = ("Attacker", "Trickster", "Grinder", "Wall")

# Placeholder text (INCLUDING the trailing period, so the splice doesn't leave
# a double period behind — the demeanor notes below already end in one) in the
# master style prompt blockquote where the per-persona demeanor gets spliced in.
_DEMEANOR_PLACEHOLDER = "[insert per-persona demeanor/accessory\nnotes below]."

# Final avatar dimensions (square) — the model returns a 1:1 image at a larger
# size; this is a straight downscale, not a crop.
AVATAR_SIZE_PX = 512

# The image-generation model. Gemini's native image-generation tool.
IMAGE_GEN_MODEL = "google:gemini-3.1-flash-image"

# Every doc revision must carry exactly 4 styles x 6 rungs = 24 personas — a
# silent drop (regex/shape mismatch) must fail loudly, not generate a partial set.
EXPECTED_PERSONA_COUNT = 24

# Regex for a per-persona descriptor bullet's first line, e.g.:
#   - `attacker-800` — Ziggy the Wasp — small, buzzing energy, ...
# Captures the persona id and the rest of the notes (name/species + notes,
# kept together — the script only needs the whole tail as prompt text).
_PERSONA_BULLET_RE = re.compile(r"^- `(?P<persona_id>[a-z]+-\d+)` — (?P<rest>.*)$")

# Regex for a per-style demeanor bullet's first line, e.g.:
#   - **Attacker** — alert, forward-leaning posture, ...
_STYLE_BULLET_RE = re.compile(r"^- \*\*(?P<style>\w+)\*\* — (?P<rest>.*)$")


@dataclass(frozen=True)
class PersonaPrompt:
    """One persona's fully assembled generation prompt + identifying fields."""

    persona_id: str
    style: str
    prompt: str


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def _style_from_persona_id(persona_id: str) -> str:
    """Derives a persona's style from its id (`'attacker-1200' -> 'Attacker'`)."""
    prefix = persona_id.split("-", 1)[0]
    return prefix[:1].upper() + prefix[1:]


def _collect_continuation(lines: list[str], start_idx: int) -> tuple[list[str], int]:
    """Collects the indented continuation lines following bullet `start_idx`.

    A continuation line is non-empty, does not start a new `- ` bullet, and
    does not start a new `#` heading. Returns the continuation lines
    (stripped) and the index of the next unconsumed line (either the next
    bullet/heading or end of file).
    """
    parts: list[str] = []
    idx = start_idx + 1
    while idx < len(lines):
        stripped = lines[idx].strip()
        if stripped == "" or stripped.startswith("- ") or stripped.startswith("#"):
            break
        parts.append(stripped)
        idx += 1
    return parts, idx


def parse_master_style_prompt(doc_text: str) -> str:
    """Extracts the `> `-blockquoted master style prompt (D-16 step 2)."""
    lines = doc_text.splitlines()
    quote_lines = [line[2:] for line in lines if line.startswith("> ")]
    if not quote_lines:
        raise ValueError(
            f"parse_master_style_prompt: no blockquote ('> ') lines found in {_PROMPTS_DOC}"
        )
    return " ".join(quote_lines)


def parse_style_demeanor_notes(doc_text: str) -> dict[str, str]:
    """Extracts the 4 per-style demeanor bullets, keyed by style name."""
    lines = doc_text.splitlines()
    notes: dict[str, str] = {}
    idx = 0
    while idx < len(lines):
        match = _STYLE_BULLET_RE.match(lines[idx].strip())
        if match is None:
            idx += 1
            continue
        continuation, next_idx = _collect_continuation(lines, idx)
        notes[match.group("style")] = " ".join([match.group("rest"), *continuation])
        idx = next_idx
    missing = [style for style in STYLES if style not in notes]
    if missing:
        raise ValueError(f"parse_style_demeanor_notes: missing demeanor bullets for {missing}")
    return notes


def parse_persona_descriptors(doc_text: str) -> dict[str, str]:
    """Extracts all 24 persona descriptor bullets, keyed by persona id.

    Each value is the full tail after `persona-id\\` — ` (Name the Species —
    notes, including the woven-in bio), joined across continuation lines.
    """
    lines = doc_text.splitlines()
    descriptors: dict[str, str] = {}
    idx = 0
    while idx < len(lines):
        match = _PERSONA_BULLET_RE.match(lines[idx].strip())
        if match is None:
            idx += 1
            continue
        continuation, next_idx = _collect_continuation(lines, idx)
        descriptors[match.group("persona_id")] = " ".join([match.group("rest"), *continuation])
        idx = next_idx
    return descriptors


def build_persona_prompts(doc_text: str) -> list[PersonaPrompt]:
    """Assembles the full generation prompt for every persona in the doc.

    prompt = master style prompt (demeanor placeholder replaced with the
    persona's own style's demeanor notes) + the persona's own descriptor
    notes (which already carries its bio, per D-15).
    """
    master_prompt = parse_master_style_prompt(doc_text)
    style_notes = parse_style_demeanor_notes(doc_text)
    descriptors = parse_persona_descriptors(doc_text)
    if len(descriptors) != EXPECTED_PERSONA_COUNT:
        raise ValueError(
            f"build_persona_prompts: parsed {len(descriptors)} persona descriptor bullets "
            f"from {_PROMPTS_DOC}, expected exactly {EXPECTED_PERSONA_COUNT}. The doc's "
            "descriptor-line shape may have drifted from the parser's regex."
        )

    prompts: list[PersonaPrompt] = []
    for persona_id in sorted(descriptors):
        style = _style_from_persona_id(persona_id)
        if style not in STYLES:
            raise ValueError(
                f"build_persona_prompts: persona id {persona_id!r} resolves to unknown style {style!r}"
            )
        demeanor = style_notes[style]
        base_prompt = master_prompt.replace(_DEMEANOR_PLACEHOLDER.replace("\n", " "), demeanor)
        full_prompt = f"{base_prompt}\n\nThis persona: {descriptors[persona_id]}"
        prompts.append(PersonaPrompt(persona_id=persona_id, style=style, prompt=full_prompt))
    return prompts


def pending_personas(prompts: list[PersonaPrompt]) -> list[PersonaPrompt]:
    """Filters to personas with no existing webp (the delete-and-rerun loop)."""
    return [p for p in prompts if not (_ASSETS_DIR / f"{p.persona_id}.webp").exists()]


def _downscale_and_save_webp(image_bytes: bytes, persona_id: str) -> Path:
    """Opens `image_bytes`, resizes to `AVATAR_SIZE_PX` square, saves as webp."""
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(image_bytes)) as img:
        resized = img.convert("RGB").resize((AVATAR_SIZE_PX, AVATAR_SIZE_PX))
        output_path = _ASSETS_DIR / f"{persona_id}.webp"
        resized.save(output_path, format="WEBP")
    return output_path


async def _generate_one(persona: PersonaPrompt, *, logo_ref: bool) -> Path:
    """Runs the image-generation agent for one persona and writes its webp."""
    # Imported lazily so `--dry-run` and `--help` never require GOOGLE_API_KEY
    # to resolve (constructing the Agent's GoogleProvider raises immediately
    # if the env var is unset — see the missing-key guard in main()).
    from pydantic_ai import Agent, BinaryContent, BinaryImage
    from pydantic_ai.capabilities import NativeTool
    from pydantic_ai.native_tools import ImageGenerationTool

    agent = Agent(
        IMAGE_GEN_MODEL,
        output_type=BinaryImage,
        capabilities=[NativeTool(ImageGenerationTool(aspect_ratio="1:1", size="1K"))],
    )

    if logo_ref:
        logo_bytes = _LOGO_REF_PATH.read_bytes()
        user_content = [
            persona.prompt,
            BinaryContent(data=logo_bytes, media_type="image/png"),
        ]
        result = await agent.run(user_content)
    else:
        result = await agent.run(persona.prompt)

    # Suppressed below: ty infers `result.output` as `str` here (a known
    # pydantic-ai generic-inference limitation with the `output_type=BinaryImage`
    # kwarg form); confirmed correct at runtime (verified via manual construction
    # against the installed 1.104.0 package — result.output is a BinaryImage
    # with a `.data` bytes field).
    return _downscale_and_save_webp(result.output.data, persona.persona_id)  # ty: ignore[unresolved-attribute]


async def run_generation(
    prompts: list[PersonaPrompt], *, limit: int | None, logo_ref: bool
) -> None:
    """Generates webps for `prompts` (already filtered to pending), up to `limit`."""
    targets = prompts if limit is None else prompts[:limit]
    _log(f"{len(prompts)} pending personas; generating {len(targets)} this run.")
    for i, persona in enumerate(targets, start=1):
        _log(f"  [{i}/{len(targets)}] generating {persona.persona_id}...")
        output_path = await _generate_one(persona, logo_ref=logo_ref)
        _log(f"    wrote {output_path.relative_to(_REPO_ROOT)}")
    _log("Done." if targets else "Nothing to generate (no pending personas).")


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate bot-persona avatar portraits from personaAvatarPrompts.md via "
            "Gemini image generation (D-16)."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Cap the number of avatars generated this run. Default: no limit.",
    )
    parser.add_argument(
        "--logo-ref",
        action="store_true",
        dest="logo_ref",
        help="Pass frontend/public/icons/logo-256.png as a style-reference image.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help=(
            "Parse the doc, list pending personas, and print each assembled prompt. "
            "Makes no API call and does not require GOOGLE_API_KEY."
        ),
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    doc_text = _PROMPTS_DOC.read_text(encoding="utf-8")
    all_prompts = build_persona_prompts(doc_text)
    pending = pending_personas(all_prompts)

    if args.dry_run:
        _log(f"{len(pending)} pending personas (of {len(all_prompts)} total).")
        for persona in pending:
            print(f"\n--- {persona.persona_id} ({persona.style}) ---")
            print(persona.prompt)
        return

    if not pending:
        _log("No pending personas — every persona already has a webp. Nothing to do.")
        return

    if not os.environ.get("GOOGLE_API_KEY"):
        print(
            "ERROR: GOOGLE_API_KEY is not set. Add it to .env or export it before running "
            "(pydantic-ai's GoogleProvider reads it automatically). Use --dry-run to preview "
            "without a key.",
            file=sys.stderr,
        )
        sys.exit(1)

    asyncio.run(run_generation(pending, limit=args.limit, logo_ref=args.logo_ref))


if __name__ == "__main__":
    main()
