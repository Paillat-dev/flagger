# Copyright (c) Paillat-dev
# SPDX-License-Identifier: MIT

import os
import sys

import discord

sys.path.append(os.path.dirname(__file__))

import asyncio
import logging

from discord import Intents
from pycord_rest import App

from commands.error_handling import ErrorHandler
from commands.flag_gen import FlaggerCommands
from config import CONFIG
from http_server import HttpServer
from renderer.base import FlagRenderer
from renderer.manager import RendererManager

logging.basicConfig(level=getattr(logging, CONFIG.log_level.upper()))

intents = Intents.default()
app = App(
    intents=intents,
    auto_sync_commands=CONFIG.auto_sync_commands,
    default_command_contexts={
        discord.InteractionContextType.guild,
        discord.InteractionContextType.bot_dm,
        discord.InteractionContextType.private_channel,
    },
    default_command_integration_types={discord.IntegrationType.guild_install, discord.IntegrationType.user_install},
)


async def main() -> None:
    async with (
        RendererManager(num_workers=CONFIG.num_workers) as manager,
        HttpServer(port=CONFIG.flagwaver_http_port, path=CONFIG.flagwaver_path),
    ):
        renderer = FlagRenderer(manager, f"http://localhost:{CONFIG.flagwaver_http_port}")
        app.add_cog(FlaggerCommands(app, manager, renderer))
        app.add_cog(ErrorHandler(app))
        await app.start(token=CONFIG.token, public_key=CONFIG.public_key, uvicorn_options={"host": CONFIG.uvicorn_host})


if __name__ == "__main__":
    asyncio.run(main())
