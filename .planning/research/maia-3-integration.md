# Maia-3 — License & Integration Feasibility Report

**Date:** 2026-07-04
**Question:** What license is Maia-3 under, and can we (technically + legally) integrate it into the FlawChess analysis board?
**Short answer:** Technically easy. Legally usable, but Maia-3 is **AGPL-3.0**, not permissive — so it must be integrated at arm's length (separate UCI process, unmodified), exactly like we already run GPL-licensed Stockfish. Do **not** `import` the `maia3` package in-process into the MIT-licensed backend.

---

## 1. What Maia-3 is

Maia-3 ("Chessformer") is a transformer-based **human move-prediction** engine from the University of Toronto CSSLab (Monroe et al., ICLR 2026). Unlike Stockfish, it predicts *what a human of a given rating would actually play*, not the objectively best move. It also has a **value head that outputs Win/Draw/Loss** for a position.

- Predicts human moves conditioned on skill level across the rating ladder.
- Includes a WDL value head (directly relevant to our existing WDL framing).
- Explicitly **not** tuned for maximum playing strength — the model card steers strength-seekers to the Chessformer-in-lc0 build. Our use case (human-realistic prediction + analysis) is exactly what it's designed for, and it aligns with our tagline "Engines are flawless, humans play FlawChess."

Three sizes, PyTorch checkpoints on Hugging Face:

| Model | Params | Notes |
|-------|--------|-------|
| `maia3-5m` | 5M | CPU-friendly, chess GUIs |
| `maia3-23m` | 23M | Better accuracy |
| `maia3-79m` | 79M | Best accuracy (GPU recommended) |

## 2. License findings (verified against source, not summaries)

| Component | License | Source |
|-----------|---------|--------|
| **Code** (`CSSLab/maia3`) | **AGPL-3.0** (GNU Affero GPL v3) | Repo `LICENSE` file, read directly |
| **Weights** (`UofTCSSLab/Maia3-*` on HF) | Points to the repo license → **AGPL-3.0** | HF model card: *"CC BY 4.0 (paper); see repo for code/weights license"* |
| **Paper** | CC BY 4.0 | HF model card |
| Citation | Requested (BibTeX for Chessformer, Monroe et al. 2026) | README — academic courtesy, not a license term |

> ⚠️ **Correction to circulating claims:** Several news write-ups (e.g. aibase, Hasty Briefs) state Maia-3 is "Apache 2.0 / free to commercialize." **That is wrong.** The actual `LICENSE` in the repo is AGPL-3.0. Do not rely on the secondary reporting. (The *older* Maia 1 was GPL; Maia-3 is AGPL — stricter, not looser.)

### Why AGPL-3.0 matters for us specifically

AGPL-3.0 is the strongest common copyleft. Beyond GPL it adds **§13 (network use)**: if you run a **modified** version and let users interact with it **over a network**, you must offer those users the complete corresponding source of the modified version. For a hosted SaaS like flawchess.com this is the clause that bites — normal GPL's "distribution" trigger would never fire for a web app, but AGPL's does.

**FlawChess is currently MIT-licensed** (`LICENSE`, © 2026 Adrian Imfeld). MIT and AGPL are not the same world: if AGPL code becomes part of the FlawChess "work," the combined work's copyleft obligations attach and effectively override the permissive MIT terms for that combined work.

## 3. Legal integration analysis

The question is entirely **"combined work" vs "mere aggregation."**

- **In-process import (AVOID):** `pip install maia3` and `import` it inside the FastAPI backend / worker → the backend links AGPL code in-process. That makes the served backend a derivative/combined work. Under AGPL §13, we'd owe the **entire backend's** corresponding source to every network user under AGPL terms — i.e. we'd be relicensing our backend to AGPL in practice. Not acceptable if we want to keep MIT.

- **Separate process at arm's length (RECOMMENDED):** Maia-3 **implements the UCI protocol.** Run it as a **separate subprocess** (or standalone inference microservice) and talk to it over UCI / stdin-stdout / a network API, **unmodified**. Under the FSF's own interpretation this is *mere aggregation*, and AGPL's copyleft does **not** reach into our MIT code. This is **exactly how we already use Stockfish (GPL-3.0)** via python-chess's engine protocol — so we already have the precedent, the pattern, and the remote-worker plumbing.

- **AGPL §13 in the arm's-length case:** §13 only triggers on a **modified** version. If we ship Maia-3 **unmodified**, we incur no extra network-source obligation beyond it already being public on GitHub/HF. If we ever fine-tune or patch the model/code, §13 kicks in and we must publish those modifications and offer them to users. Recommendation: **keep it unmodified**; if we fine-tune, treat that fork as a separate AGPL project with its own public repo.

- **Weights-as-AGPL caveat:** Applying AGPL to ML weights is legally novel and largely untested (it's unclear weights are even copyrightable the way code is). Treat conservatively — assume AGPL applies to the weights and follow the arm's-length + unmodified path, rather than betting on an untested "weights aren't software" argument.

- **Attribution / notice hygiene:** Add a visible attribution + link to the Maia-3 source (GitHub/HF) and cite the Chessformer paper. Cheap, satisfies AGPL notice expectations and the academic ask.

### Legal bottom line
✅ **Usable** for FlawChess (including our hosted, ad-free/free product) **if** integrated as a separate, unmodified UCI process/service and clearly attributed — mirroring our existing Stockfish setup. ❌ **Not** usable as an in-process library import without relicensing the backend to AGPL. Given the money/relicensing stakes, get a one-paragraph confirmation from someone comfortable with AGPL before shipping if any doubt remains.

## 4. Technical integration feasibility

Clean fit with our stack.

- **Runtime:** Python 3 + PyTorch. Runs on **CPU** (`--device cpu --no-use-amp`); GPU optional and only really wanted for the 79M model. Our backend is Python; our remote-worker infra already runs a chess engine pool.
- **No lc0 dependency:** unlike Maia 1/2 (which needed lc0 + weights), Maia-3 is self-contained PyTorch. Fewer moving parts.
- **Interface:** ships a **UCI** engine (`maia3-5m/23m/79m` executables) → drop-in with `python-chess`'s `SimpleEngine`/UCI layer, same as Stockfish. Also usable as a raw PyTorch module if we went the (discouraged) in-process route.
- **Inference:** no tree search — single forward pass, `nodes=1`-style. Move policy (probabilistic, temperature/nucleus sampling) **+ WDL value head**. Cheap per-position vs a Stockfish depth search.
- **Weights:** `.pt` state-dicts auto-downloaded from Hugging Face and cached on first run (need to pre-bake/cache in worker images so prod isn't fetching from HF at runtime; also pin a version).
- **Product surface:** on the analysis board we could show, per position, "what a 1200 / 1600 / 2000 player would likely play here" and a human-model WDL — complementary to Stockfish's objective eval, and directly on-theme.

### Effort / risks
- **Low integration effort** — treat it as a second engine in the existing worker/UCI framework. Serve as a separate process/service for license safety.
- **Resource cost:** 5M/23M are light on CPU; profile before enabling 79M on prod workers (RAM/CPU already contended — see prod OOM history). Start with 5M or 23M.
- **Ops:** pin the model version and pre-cache weights in the image (no runtime HF dependency, reproducible).

## 5. Recommendation

1. **Feasible and on-brand** — pursue as a candidate feature (human-move prediction + human WDL on the analysis board), but as a **new GSD phase/seed**, not ad hoc.
2. **License-safe pattern:** run Maia-3 as a **separate, unmodified UCI process/microservice**, attributed and paper-cited — identical governance to our current Stockfish (GPL) usage. Never `import` it in-process into the MIT backend.
3. **Keep it unmodified.** Any fine-tune/patch = AGPL §13 obligations (publish the fork, offer source to network users). Decide that deliberately if we ever go there.
4. Start with the **5M or 23M** model on CPU workers; gate 79M behind a resource soak given prod memory pressure.
5. Get a quick AGPL sanity-check sign-off before shipping, given the MIT-vs-AGPL stakes.

---

### Sources
- Maia-3 code repo (LICENSE = AGPL-3.0): https://github.com/CSSLab/maia3
- Maia-3 README: https://github.com/CSSLab/maia3/blob/main/README.md
- Weights + license note (CC BY 4.0 paper; repo for code/weights): https://huggingface.co/UofTCSSLab/Maia3-23M , https://huggingface.co/UofTCSSLab/Maia3-79M
- Project site: https://www.maiachess.com/
- Original Maia (GPL, lc0-based, for contrast): https://github.com/CSSLab/maia-chess
- FlawChess license: `./LICENSE` (MIT)
