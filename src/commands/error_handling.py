# Copyright (c) NiceBots
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING

import discord
from discord import ui

if TYPE_CHECKING:
    from pycord_rest import App


class ErrorHandling(ui.DesignerView):
    def __init__(self, error_message: str) -> None:
        container = ui.Container(color=discord.Color.red())
        container.add_text("## Oops... An error occurred")
        container.add_text(f"```\n{error_message}\n```")

        super().__init__(container, store=False)


class ErrorHandler(discord.Cog):
    def __init__(self, app: "App") -> None:
        self.app: App = app
        super().__init__()

    @discord.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, error: Exception) -> None:
        await ctx.respond(view=ErrorHandling(str(error)), ephemeral=True)


__all__ = ("ErrorHandler",)
