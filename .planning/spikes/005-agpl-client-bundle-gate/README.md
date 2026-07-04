---
spike: 005
name: agpl-client-bundle-gate
type: standard
validates: "Given Maia-3 is AGPL-3.0 and the FlawChess frontend is MIT, when the Maia model ships client-side, then determine whether that forces the frontend into AGPL (kill for client-side) or is acceptable under stated conditions"
verdict: PARTIAL
related: [004]
tags: [maia, license, agpl, seed-081]
---

# Spike 005: AGPL-in-MIT-frontend license gate

## What This Validates

Given Maia-3 (code + weights) is **AGPL-3.0** and the FlawChess frontend is **MIT**, when we
ship Maia client-side (spike 004's architecture), does the AGPL copyleft attach to our frontend
(a kill for client-side), or is it acceptable? This is a legal-analysis spike, not code.

## Research

Grounded in `.planning/research/maia-3-integration.md` (verified: `CSSLab/maia3` `LICENSE` =
AGPL-3.0; weights point to repo license; the "Apache 2.0" press claim is wrong) plus AGPL-3.0
§0/§5/§13 and standard FSF "mere aggregation vs combined work" doctrine.

### The two obligations client-side shipping creates

1. **Conveying the model to users.** The browser downloads the `.onnx`, which is an AGPL work.
   That's "conveying" → we must offer recipients the corresponding source. Because the model is
   **unmodified and publicly available** (CSSLab / maiachess.com), this is satisfied trivially
   by an offer-source notice (link to the CSSLab repo + AGPL text + the model). **Cheap.**

2. **Does bundling it make the MIT frontend a "combined work" → AGPL?** This is the crux, and
   the answer hinges entirely on *what we bundle*:

   - **onnxruntime-web is MIT** (Microsoft) — permissive, no issue.
   - **The Maia `.onnx` is loaded as a runtime data asset** by a generic permissive runtime.
     Feeding a model *file* to an interpreter is much closer to **mere aggregation / data**
     than to *linking AGPL program code* into our program. Our frontend source incorporates
     none of Maia's code. Under a reasonable reading, our MIT code stays MIT.
   - **The kill scenario:** copying/bundling **CSSLab's own AGPL JS** (their `MaiaEngineContext`,
     board→tensor encoding, decoding glue from `maia3` / `maia-platform-frontend`) into our
     bundle. *That* combines AGPL **source** into the MIT frontend → combined work → AGPL
     attaches to the frontend. Avoidable.

### Why §13 (the AGPL network clause) is largely inert here

§13 obliges offering source to users who interact with a **modified** version **over a network**.
Client-side, the user runs the model **locally** and we ship it **unmodified** — we are not
operating a network server running a modified Maia. So the scary AGPL-specific clause mostly
doesn't fire; we're left with the ordinary GPL "conveying → offer source" duty (already cheap).
Ironically, client-side is a *cleaner* §13 story than a server-side hosted deployment of a
modified model would be.

### The genuinely untested bit

Whether ML **weights** are copyrightable at all, and whether "load model as data" defeats the
combined-work theory, are **not settled law**. The analysis above is a reasonable interpretation,
not a certainty. The offer-source compliance (obligation 1) is airtight; the "frontend stays
MIT" conclusion (obligation 2) rests on the data-vs-linking reading.

## Conditions for client-side to be safe

1. Load the **unmodified** AGPL `.onnx` as a **runtime data asset** via **MIT onnxruntime-web**.
2. Write **our own MIT glue** (board encoding, ELO input, legal-move masking, softmax, chart).
   **Do NOT copy or bundle CSSLab's AGPL inference/encoding JS.**
3. Ship an **attribution + offer-source notice** (link CSSLab repo + AGPL-3.0 text + the model)
   and **cite the Chessformer paper**.
4. Keep the model **unmodified**. Any fine-tune → §13 + publish-source obligations (treat a
   fork as its own AGPL project).

## Results

**VERDICT: PARTIAL** — client-side is **legally viable under the four conditions above**, and is
**not** an automatic kill. It is *not* a clean VALIDATED because obligation-2 rests on the
untested "model-as-data ≠ linking" interpretation. **Recommendation: get a one-paragraph
confirmation from someone comfortable with AGPL before shipping** (the seed already flags this).

**Fallback if counsel is uncomfortable:** the **server-side** path (spike 004's fallback) is the
conservative alternative — run Maia in a **separate, unmodified process** (arm's-length, exactly
like our current GPL Stockfish usage; never `import maia3` in-process into the MIT backend). That
avoids conveying weights to users entirely and has clean precedent in this codebase.

**Bottom line:** license does **not** block the plan. Client-side is shippable with cheap
notices + a "write our own glue" discipline + a legal nod; server-side arm's-length is the
safe harbor either way.
