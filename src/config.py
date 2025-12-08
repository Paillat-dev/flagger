# Copyright (c) Paillat-dev
# SPDX-License-Identifier: MIT

import os
from pathlib import Path

from pydantic import BaseModel

try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv()


class Config(BaseModel):
    token: str
    public_key: str
    num_workers: int = 1
    flagwaver_http_port: int = 8910
    uvicorn_host: str = "0.0.0.0"  # noqa: S104
    auto_sync_commands: bool = True
    flagwaver_path: Path


CONFIG = Config(
    token=os.environ["DISCORD_TOKEN"],
    public_key=os.environ["DISCORD_PUBLIC_KEY"],
    num_workers=int(os.getenv("FLAGGER_RENDERER_WORKERS", "2")),
    flagwaver_http_port=int(os.getenv("FLAGWAVER_HTTP_PORT", "8910")),
    uvicorn_host=os.getenv("UVICORN_HOST", "0.0.0.0"),  # noqa: S104
    auto_sync_commands=os.getenv("AUTO_SYNC_COMMANDS", "true") == "true",
    flagwaver_path=Path(os.getenv("FLAGWAVER_PATH", Path(__file__).parent / "flagwaver" / "dist")),
)

__all__ = ["CONFIG"]
