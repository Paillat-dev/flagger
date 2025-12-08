# Copyright (c) Paillat-dev
# SPDX-License-Identifier: MIT

import os
import sys

sys.path.append(os.path.dirname(__file__))

import asyncio
import logging
from pathlib import Path

from discord import Intents
from pycord_rest import App

from commands.error_handling import ErrorHandler
from commands.flag_gen import FlaggerCommands
from config import CONFIG
from http_server import HttpServer
from renderer.base import FlagRenderer
from renderer.manager import RendererManager

logging.basicConfig(level=logging.DEBUG)

intents = Intents.default()
app = App(intents=intents, auto_sync_commands=False)

FLAGWAVER_PATH = Path(__file__).parent / "flagwaver" / "dist"


async def main() -> None:
    async with (
        RendererManager(num_workers=CONFIG.num_workers) as manager,
        HttpServer(port=CONFIG.flagwaver_http_port, path=FLAGWAVER_PATH),
    ):
        renderer = FlagRenderer(manager, f"http://localhost:{CONFIG.flagwaver_http_port}")
        app.add_cog(FlaggerCommands(app, manager, renderer))
        app.add_cog(ErrorHandler(app))
        await app.start(token=CONFIG.token, public_key=CONFIG.public_key, uvicorn_options={"host": CONFIG.uvicorn_host})


if __name__ == "__main__":
    asyncio.run(main())
