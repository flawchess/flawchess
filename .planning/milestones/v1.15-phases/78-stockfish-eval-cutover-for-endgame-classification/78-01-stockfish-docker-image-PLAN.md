---
phase: 78
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - Dockerfile
  - .github/workflows/ci.yml
autonomous: false
requirements: [ENG-01]
tags: [docker, stockfish, infra, ci, supply-chain]

must_haves:
  truths:
    - "Backend Docker image ships pinned Stockfish binary at /usr/local/bin/stockfish."
    - "STOCKFISH_PATH=/usr/local/bin/stockfish env var is set in the runtime image so app code reads engine location from one source."
    - "Stockfish binary integrity is verified at build time via SHA-256 checksum (supply-chain mitigation)."
    - "AVX2 must be verified on prod Hetzner VM before Dockerfile is locked: `ssh flawchess 'grep -c avx2 /proc/cpuinfo'` should be ≥ 1. If 0, fall back to `stockfish-ubuntu-x86-64-modern` (popcnt) or `stockfish-ubuntu-x86-64`."
    - "CI runs Stockfish-dependent unit tests; `apt install stockfish` is added to `.github/workflows/ci.yml` so engine wrapper tests in Plan 78-02 do not silently skip."
  artifacts:
    - path: "Dockerfile"
      provides: "Pinned Stockfish install layer in runtime stage with SHA-256 verification + STOCKFISH_PATH env var"
      contains: "stockfish-ubuntu-x86-64-avx2"
    - path: ".github/workflows/ci.yml"
      provides: "stockfish present on CI runner so engine tests do not skip silently"
      contains: "stockfish"
  key_links:
    - from: "Dockerfile"
      to: "/usr/local/bin/stockfish"
      via: "tar extraction + chmod +x + sha256sum --check"
      pattern: "stockfish-ubuntu-x86-64-avx2"
    - from: "Dockerfile (runtime stage)"
      to: "ENV STOCKFISH_PATH"
      via: "ENV directive"
      pattern: "STOCKFISH_PATH=/usr/local/bin/stockfish"
---

<objective>
Bake a pinned official Stockfish binary into the backend Docker image (D-06) and add Stockfish to the CI runner so the engine wrapper tests (Plan 78-02) do not silently skip. The runtime image must expose `STOCKFISH_PATH=/usr/local/bin/stockfish` so the wrapper module reads engine location from a single env var.

Purpose: ENG-01 prerequisite. The wrapper in Plan 78-02 cannot start without a Stockfish binary in the image. Hardcoded `apt install stockfish` is too stale (likely sf_16); building from source is overkill. Pinned official release binary + SHA-256 verification gives reproducibility across deploys and a supply-chain mitigation.

Output: Modified `Dockerfile` (Stockfish install layer + ENV var), modified `.github/workflows/ci.yml` (apt install for tests), and an operator-verified AVX2 confirmation on the prod VM.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-SPEC.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-PATTERNS.md
@CLAUDE.md
@Dockerfile
@.github/workflows/ci.yml

<interfaces>
<!-- Stockfish release artifacts (pinned to sf_17). Executor must verify the SHA-256 from the official sha256sum.txt published alongside the release. -->
<!-- Source URL pattern: https://github.com/official-stockfish/Stockfish/releases/download/sf_17/<asset> -->
<!-- Asset names per CONTEXT.md D-06: stockfish-ubuntu-x86-64-avx2.tar (primary), stockfish-ubuntu-x86-64-modern.tar / stockfish-ubuntu-x86-64.tar (fallbacks). -->
<!-- Inside the .tar: directory `stockfish/` containing the binary `stockfish-ubuntu-x86-64-avx2` (rename to `stockfish` on install). -->
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Operator confirms AVX2 on prod Hetzner VM</name>
  <files>N/A — pre-implementation operator check; sets the binary asset choice for Task 2.</files>
  <action>Run the verification commands listed in `<how-to-verify>` and report back via `<resume-signal>`. The executor blocks on this signal before starting Task 2 so the Dockerfile asset choice (avx2 vs modern) matches the prod VM CPU capability.</action>
  <what-built>Pre-implementation gate. Before locking the Dockerfile to the AVX2 binary, operator confirms the prod VM CPU supports AVX2. If the prod VM lacks AVX2, the binary will segfault on first eval and the entire phase deploy breaks.</what-built>
  <how-to-verify>
    Run on operator's local machine:
    ```bash
    ssh flawchess 'grep -c avx2 /proc/cpuinfo'
    ```
    Expected: a positive integer (≥ 1).
    If `0`: report back so the executor uses `stockfish-ubuntu-x86-64-modern.tar` (popcnt baseline) instead of the AVX2 build.
    Also run on the operator's local dev box (used for the backfill in Plan 78-06):
    ```bash
    grep -c avx2 /proc/cpuinfo
    ```
    Operator should also note the local Stockfish version they intend to use for the backfill rounds (e.g. `stockfish --help | head -1`); local + Docker version drift is acceptable per CONTEXT.md specifics, but a record helps interpret VAL-01 results.
  </how-to-verify>
  <verify>
    <automated>echo "Operator-only check; resume-signal is the verification."</automated>
  </verify>
  <done>Operator has reported one of `avx2-confirmed`, `avx2-missing`, or `ssh-failed`. Task 2 can proceed with the chosen asset.</done>
  <resume-signal>Reply with one of: `avx2-confirmed` (use avx2 binary), `avx2-missing` (use modern/popcnt fallback), or `ssh-failed` (block until tunnel works).</resume-signal>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Pin Stockfish in backend Dockerfile</name>
  <files>Dockerfile</files>
  <read_first>
    - Dockerfile (current state — two-stage builder + runtime, python:3.13-slim)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md (D-06 — pinned official binary, env var, install path)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md "Stockfish Docker Install" section
    - CLAUDE.md "Production Server" section (BuildKit cache cap, Hetzner CX32 specs)
  </read_first>
  <action>
    Append a Stockfish install layer to the **runtime stage** of `Dockerfile` (after `COPY --from=builder /app /app`, before `COPY deploy/entrypoint.sh`). Layer specifics:

    1. Pinned release tag: `sf_17` (per D-06).
    2. Asset selection from Task 1's checkpoint:
       - If `avx2-confirmed`: `stockfish-ubuntu-x86-64-avx2.tar`, binary `stockfish-ubuntu-x86-64-avx2`.
       - If `avx2-missing`: `stockfish-ubuntu-x86-64-modern.tar`, binary `stockfish-ubuntu-x86-64-modern`.
    3. Verify integrity with `sha256sum --check`. Fetch the official `sha256sum.txt` from the release page (`https://github.com/official-stockfish/Stockfish/releases/download/sf_17/sha256sum.txt`) and pin the line for the chosen asset directly into the Dockerfile (do NOT download the sha256sum.txt at build time — pin the literal hash, otherwise the integrity gate is meaningless).
    4. Install path: `/usr/local/bin/stockfish` (rename from arch-suffixed name).
    5. Set `ENV STOCKFISH_PATH=/usr/local/bin/stockfish` so the wrapper (Plan 78-02) reads from one source.
    6. Cleanup: purge `wget` and `apt` cache after install to keep the layer small.

    Concrete Dockerfile additions (paste between `ENV PATH="/app/.venv/bin:$PATH"` and `COPY deploy/entrypoint.sh /entrypoint.sh`):

    ```dockerfile
    # Stockfish (pinned official release sf_17) — supply-chain integrity via SHA-256
    # See .planning/milestones/v1.15-phases/78-.../78-CONTEXT.md D-06
    # AVX2 binary verified on prod Hetzner VM (Phase 78 Plan 01 Task 1 checkpoint)
    ARG STOCKFISH_TAG=sf_17
    ARG STOCKFISH_ASSET=stockfish-ubuntu-x86-64-avx2
    # SHA-256 from https://github.com/official-stockfish/Stockfish/releases/download/sf_17/sha256sum.txt
    # MUST be the line matching ${STOCKFISH_ASSET}.tar — pin literally so build is reproducible.
    ARG STOCKFISH_SHA256=<paste-real-sha256-here>
    RUN apt-get update \
        && apt-get install -y --no-install-recommends wget ca-certificates \
        && wget -q "https://github.com/official-stockfish/Stockfish/releases/download/${STOCKFISH_TAG}/${STOCKFISH_ASSET}.tar" -O /tmp/stockfish.tar \
        && echo "${STOCKFISH_SHA256}  /tmp/stockfish.tar" | sha256sum -c - \
        && tar -xf /tmp/stockfish.tar -C /tmp \
        && mv "/tmp/stockfish/${STOCKFISH_ASSET}" /usr/local/bin/stockfish \
        && chmod +x /usr/local/bin/stockfish \
        && rm -rf /tmp/stockfish.tar /tmp/stockfish \
        && apt-get purge -y wget \
        && apt-get autoremove -y \
        && rm -rf /var/lib/apt/lists/*
    ENV STOCKFISH_PATH=/usr/local/bin/stockfish
    ```

    The executor MUST replace `<paste-real-sha256-here>` with the actual SHA-256 from the GitHub release `sha256sum.txt`. If the executor cannot reach the GitHub release page during build, fetch via:
    ```bash
    curl -sSL https://github.com/official-stockfish/Stockfish/releases/download/sf_17/sha256sum.txt | grep "${ASSET}.tar"
    ```
    and paste the literal hash into `STOCKFISH_SHA256`.

    **NO** behavior change to existing builder stage. **NO** `LATEST` tag. **NO** unverified download.
  </action>
  <verify>
    <automated>
      grep -n "STOCKFISH_TAG=sf_17" Dockerfile
      grep -n "ENV STOCKFISH_PATH=/usr/local/bin/stockfish" Dockerfile
      grep -n "sha256sum -c" Dockerfile
      docker build --target runtime -t flawchess-test:sf17 .
      docker run --rm flawchess-test:sf17 stockfish --help | head -3
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "STOCKFISH_TAG=sf_17" Dockerfile` returns a match.
    - `grep -n "ENV STOCKFISH_PATH=/usr/local/bin/stockfish" Dockerfile` returns a match.
    - `grep -n "sha256sum -c" Dockerfile` returns a match (literal `sha256sum -c -`).
    - `grep -n "<paste-real-sha256-here>" Dockerfile` returns ZERO matches (placeholder must be replaced with a real 64-char hex hash).
    - `docker build --target runtime -t flawchess-test:sf17 .` exits 0; the SHA-256 verification step does not fail.
    - `docker run --rm flawchess-test:sf17 stockfish --help` prints version info matching the pinned tag.
    - `docker run --rm flawchess-test:sf17 stat -c '%s' /usr/local/bin/stockfish` returns a positive integer (binary present, executable).
  </acceptance_criteria>
  <done>Stockfish binary present in runtime image at `/usr/local/bin/stockfish`, version printed matches `sf_17`, env var `STOCKFISH_PATH` set, image build succeeds with checksum verification.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Add Stockfish install to GitHub Actions CI</name>
  <files>.github/workflows/ci.yml</files>
  <read_first>
    - .github/workflows/ci.yml (current state — Ubuntu runner, uv, ruff, ty, pytest)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md "CI Considerations" section (lines 866-870)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-VALIDATION.md "Wave 0 Requirements" — `apt install stockfish` is required so engine tests run, not skip
  </read_first>
  <action>
    Add a step to install Stockfish on the Ubuntu CI runner so `tests/services/test_engine.py` (Plan 78-02 Wave 0) does NOT silently skip via `@skip_if_no_stockfish`. The step belongs in the same job that runs pytest, before the pytest invocation.

    Concrete edit — find the pytest job (likely named `test` or `backend`) and add this step immediately before the `Run pytest` (or equivalent) step:

    ```yaml
          - name: Install Stockfish (for engine wrapper tests)
            run: |
              sudo apt-get update
              sudo apt-get install -y --no-install-recommends stockfish
              stockfish --help | head -3
    ```

    Notes:
    - This installs whatever Stockfish version is in the Ubuntu apt repo (likely sf_16). That is acceptable — engine wrapper tests assert API contract (sign convention, mate detection, cp threshold), not exact eval values. Per RESEARCH.md "minor version differences are acceptable".
    - `stockfish --help` is run as a sanity check so failures are obvious in CI logs.
    - Do NOT use the pinned binary from the Dockerfile in CI — Docker layer caching is separate from CI runner setup, and adding a wget+sha256 dance to CI duplicates Dockerfile complexity for marginal benefit.
    - Do NOT replace `apt install` with the pinned binary download even if it would be more reproducible; the project's existing CI patterns (uv, ruff, ty) all use apt-style installs.
  </action>
  <verify>
    <automated>
      grep -n "stockfish" .github/workflows/ci.yml
      yamllint .github/workflows/ci.yml || true
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "Install Stockfish" .github/workflows/ci.yml` returns a match.
    - `grep -n "apt-get install -y --no-install-recommends stockfish" .github/workflows/ci.yml` returns a match.
    - The new step appears BEFORE the pytest invocation step in the job (manual review of step order; pytest step typically named "Run tests" / "pytest").
    - `yamllint .github/workflows/ci.yml` reports no errors (warnings acceptable).
  </acceptance_criteria>
  <done>CI workflow installs Stockfish on the Ubuntu runner before pytest; engine wrapper tests run (not skip) on PRs in Wave 1+.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Internet → build host | Stockfish tarball downloaded from GitHub releases during `docker build` |
| Build artifact → runtime | Pinned binary copied into the image; trusted thereafter |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-78-01 | Tampering | Stockfish binary download (build-time) | mitigate | SHA-256 pin in Dockerfile; build fails if hash mismatch (`sha256sum -c -`). Hash sourced from official `sha256sum.txt` at the pinned tag. |
| T-78-02 | Tampering | Floating binary (`latest` tag) | mitigate | Pin to specific GitHub release tag `sf_17` (D-06); no `latest` reference anywhere in Dockerfile. |
| T-78-03 | DoS | Wrong-arch binary on prod VM (segfault on first eval) | mitigate | Pre-implementation operator checkpoint (Task 1) confirms AVX2 on prod VM before Dockerfile lock. Fallback to `modern` binary if AVX2 absent. |
| T-78-04 | Information disclosure | CI runner caches GitHub release URL with checksum | accept | Public binary, public checksum; no secrets in this layer. |
| T-78-05 | Elevation of privilege | Stockfish binary runs as backend container user | accept | Runs as the same `python:3.13-slim` user as the rest of the app; no privilege escalation. Backend container is already an execution boundary; UCI process inherits its sandbox. |
</threat_model>

<verification>
- `docker build --target runtime` succeeds with the SHA-256 verification step.
- The built image runs `stockfish --help` and prints a version string matching `sf_17`.
- AVX2 confirmed on prod VM (Task 1 checkpoint).
- CI workflow shows a Stockfish install step before pytest.
</verification>

<success_criteria>
- Dockerfile pins Stockfish to `sf_17` with SHA-256 verification.
- `STOCKFISH_PATH=/usr/local/bin/stockfish` is set in the runtime image.
- AVX2 confirmed on prod VM, or fallback binary chosen.
- CI installs Stockfish so Plan 78-02 wrapper tests run, not skip.
</success_criteria>

<output>
After completion, create `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-01-SUMMARY.md` recording: chosen binary asset (avx2 vs modern), pinned SHA-256, prod VM AVX2 check result, CI Stockfish version observed.
</output>
