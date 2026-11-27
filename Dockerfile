# Visual Task Factory: generate, validate and test inside a fixed environment.
#   docker build -t vtf .
#   docker run --rm vtf                                   # runs the test suite
#   docker run --rm -v "$PWD/out:/data" vtf uv run --frozen vtf generate /data/ds --seed 7
#   docker run --rm -v "$PWD/out:/data" vtf uv run --frozen vtf validate /data/ds --seed 7
#   docker run --rm -v "$PWD/out:/data" vtf scripts/determinism.sh /data/det 7 10
# Base images are pinned by digest (python 3.12-slim-bookworm, uv 0.13.10, digests read 2026-11-26).
FROM ghcr.io/astral-sh/uv:0.13.10@sha256:a3ea1357342c1a4bf9a0c53a3deb1b55379aefa037338d8113d5771efa01774f AS uv

FROM python:3.12-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64
COPY --from=uv /uv /uvx /usr/local/bin/
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PYTHON=/usr/local/bin/python3 MPLBACKEND=Agg
WORKDIR /app
# dependencies first, so code edits do not reinstall them
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY src ./src
COPY tests ./tests
COPY scripts ./scripts
RUN uv sync --frozen
CMD ["uv", "run", "--frozen", "pytest", "-q"]
