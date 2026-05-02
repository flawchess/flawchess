FROM python:3.13-slim@sha256:d168b8d9eb761f4d3fe305ebd04aeb7e7f2de0297cec5fb2f8f6403244621664 AS builder
COPY --from=ghcr.io/astral-sh/uv:0.10.9@sha256:10902f58a1606787602f303954cea099626a4adb02acbac4c69920fe9d278f82 /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (cacheable layer — copied before source code)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

# Copy source and install project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:3.13-slim@sha256:d168b8d9eb761f4d3fe305ebd04aeb7e7f2de0297cec5fb2f8f6403244621664 AS runtime
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"

# Stockfish (pinned official release sf_17) — supply-chain integrity via SHA-256
# See .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md D-06
# AVX2 binary verified on prod Hetzner VM (Phase 78 Plan 01 Task 1: ssh flawchess 'grep -c avx2 /proc/cpuinfo' → 4)
ARG STOCKFISH_TAG=sf_17
ARG STOCKFISH_ASSET=stockfish-ubuntu-x86-64-avx2
# SHA-256 from https://github.com/official-stockfish/Stockfish/releases/download/sf_17/stockfish-ubuntu-x86-64-avx2.tar
# Computed at plan time: sha256sum on the downloaded .tar — build fails if hash mismatches (T-78-01 mitigation).
ARG STOCKFISH_SHA256=6c9aaaf4c7db0f6934a5f7c29a06172f9d22c1e6db68dfdf22f69ae60341cdde
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

COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
