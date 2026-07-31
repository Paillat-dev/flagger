

ARG PYTHON_VERSION=3.13
ARG NODE_VERSION=20
FROM python:${PYTHON_VERSION}-slim-bookworm AS python-base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install uv

WORKDIR /app
COPY pyproject.toml uv.lock ./

ENV UV_NO_DEV=1
RUN uv export -o requirements.txt

FROM node:${NODE_VERSION}-slim AS node-base

WORKDIR /app

COPY src/flagwaver/package*.json ./
RUN npm ci

COPY src/flagwaver/ ./
RUN npm exec gulp build

FROM python:${PYTHON_VERSION}-bookworm AS app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app


RUN adduser -u 6392 --disabled-password --gecos "" appuser && chown -R appuser /app

COPY --from=python-base --chown=appuser /app/requirements.txt ./
COPY LICENSE ./
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.local-browsers
RUN pip install $(grep '^playwright==' requirements.txt | tr -d '\\') && playwright install chromium --with-deps
RUN pip install -r requirements.txt

COPY --from=node-base --chown=appuser /app/dist/ ./src/static/flagwaver
ENV FLAGWAVER_PATH=/app/src/static/flagwaver

COPY src/ ./src
USER appuser

CMD ["python", "src"]
