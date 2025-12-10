# Flagger

A Discord HTTP bot for flag animation rendering.

<img src="/art/custom_flag.png" width="500" center alt="Custom Flag Example"/>

## Core Components

This project integrates [flagwaver](https://github.com/krikienoid/flagwaver) as a git submodule (`src/flagwaver`), which serves as the core rendering engine for flag animations. Credit to the flagwaver project for providing the visualization component.

## Technology Stack

- **py-cord** (v2.7.0rc2): Discord API wrapper
- **pycord-rest** ([Paillat-dev/pycord-rest](https://github.com/Paillat-dev/pycord-rest)): rest bot implementation for py-cord
- **Playwright**: Browser automation for rendering
- **MoviePy**: Video processing
- **Pydantic**: Configuration and data validation

## Requirements

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager

## Development Workflow

This project uses tooling from [Astral](https://astral.sh/):

- **uv**: Fast Python package manager
- **ruff**: Linter and formatter
- **ty**: Type checker

### Commands

Format code:
```bash
uv run ruff format .
```

Lint and auto-fix issues:
```bash
uv run ruff check --fix .
```

Type check:
```bash
uv run ty check .
```

### Code Standards

All code is strictly typed and must pass type checking. The project enforces comprehensive linting rules with select exceptions defined in `pyproject.toml`.

## Configuration

Set the following environment variables:

### Required

- `DISCORD_TOKEN`: Your Discord bot token
- `DISCORD_PUBLIC_KEY`: Your Discord application's public key

### Optional

- `FLAGGER_RENDERER_WORKERS`: Number of concurrent renderer workers (default: `2`)
- `FLAGWAVER_HTTP_PORT`: Port for the flagwaver HTTP server (default: `8910`)
- `UVICORN_HOST`: Host address for the Uvicorn server (default: `0.0.0.0`)
- `AUTO_SYNC_COMMANDS`: Whether to automatically sync slash commands with Discord (default: `true`)

## Installation

1. Clone the repository with submodules:
```bash
git clone --recursive <repository-url>
```

If already cloned, initialize submodules:
```bash
git submodule update --init --recursive
```

2. Install dependencies:
```bash
uv sync
```

3. Set up environment variables in a `.env` file or export them directly.

4. Run the bot:
```bash
uv run python -m src
```

## Docker Deployment

The project includes a `Dockerfile` for containerized deployment and `compose.yaml` for local development.

### Building and Running with Docker

Build the image:
```bash
docker build -t flagger .
```

Run the container:
```bash
docker run --env-file .env -p 8000:8000 flagger
```

### Local Development with Docker Compose

For local development with hot reload:
```bash
docker compose up --watch
```

The compose configuration includes:
- Automatic restart on source code changes in `src/`
- Image rebuild on Dockerfile changes
- Environment variable loading from `.env` file
- Port mapping for the HTTP server

## License

Copyright (c) Paillat-dev
SPDX-License-Identifier: MIT