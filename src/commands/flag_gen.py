# Copyright (c) Paillat-dev
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING, Final

import discord
from discord import ui
from discord.ext.commands import BucketType, cooldown

from config import CONFIG
from renderer.flag import Flag

if TYPE_CHECKING:
    from pycord_rest import App

    from renderer.base import FlagRenderer
    from renderer.manager import RendererManager

COOLDOWN_ARGS: Final = {
    "rate": CONFIG.cooldown_rate,
    "per": CONFIG.cooldown_per,
    "type": BucketType.user,
}


class FlagDisplayView(ui.DesignerView):
    def __init__(self, image: discord.File) -> None:
        container = ui.Container()
        container.add_text("## Your Flag is Ready!")
        container.add_gallery(discord.MediaGalleryItem(f"attachment://{image.filename}"))  # ty:ignore[invalid-argument-type]
        super().__init__(container, store=False)


class FlaggerCommands(discord.Cog):
    def __init__(self, app: "App", manager: "RendererManager", renderer: "FlagRenderer") -> None:
        self.app: App = app
        self.manager: RendererManager = manager
        self.renderer: FlagRenderer = renderer
        super().__init__()

    async def handle_flag_command(self, ctx: discord.ApplicationContext, image_url: str) -> None:
        async with self.manager.render_context_manager(self.renderer.render, Flag(image_url)) as gif_path:  # ty: ignore[invalid-argument-type]
            file = discord.File(gif_path, filename=gif_path.name)
            await ctx.respond(view=FlagDisplayView(file), files=[file])

    @discord.user_command(name="Create a Flag")
    @cooldown(**COOLDOWN_ARGS)  # ty:ignore[invalid-argument-type]
    async def create_flag(self, ctx: discord.ApplicationContext, user: discord.User | discord.Member) -> None:
        if user.display_avatar.is_animated():
            asset = user.display_avatar.with_format("gif")
        else:
            asset = user.display_avatar.with_format("png")
        await ctx.defer()

        await self.handle_flag_command(ctx, asset.url)

    flag = discord.SlashCommandGroup("flag", "Commands related to flag rendering.")

    @flag.command(name="user", description="Render a user's flag.")
    @cooldown(**COOLDOWN_ARGS)  # ty:ignore[invalid-argument-type]
    async def user(self, ctx: discord.ApplicationContext, user: discord.Member | None = None) -> None:
        target = user or ctx.author
        if target.display_avatar.is_animated():
            asset = target.display_avatar.with_format("gif")
        else:
            asset = target.display_avatar.with_format("png")
        await ctx.defer()

        await self.handle_flag_command(ctx, asset.url)

    @flag.command(name="custom", description="Render a custom flag from an image attachment.")
    @cooldown(**COOLDOWN_ARGS)  # ty:ignore[invalid-argument-type]
    async def custom_flag(self, ctx: discord.ApplicationContext, attachment: discord.Attachment) -> None:
        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            await ctx.respond("Please provide a valid image attachment.", ephemeral=True)
            return

        if attachment.content_type not in {"image/gif", "image/png", "image/jpeg"}:
            await ctx.respond("Unsupported image format. Please provide a PNG, JPEG, or GIF image.", ephemeral=True)
            return

        await ctx.defer()
        await self.handle_flag_command(ctx, attachment.url)


__all__ = ("FlaggerCommands",)
