"""Discord client setup and utility functions."""

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import discord
from discord.ext import commands
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("discord-mcp")


def configure_windows_stdout_encoding() -> None:
    """Configure stdout/stderr for UTF-8 on Windows."""
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def create_discord_bot() -> commands.Bot:
    """Create and configure the Discord bot with required intents."""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    return commands.Bot(command_prefix="!", intents=intents)


def parse_id(value: str, name: str) -> int:
    """Convert a string argument to int with a descriptive error."""
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {name}: {value!r} is not a valid ID")


def require_text_channel(channel: object, channel_id: str) -> discord.TextChannel:
    """Validate that a fetched channel is a text channel."""
    if not isinstance(channel, discord.TextChannel):
        raise ValueError(f"Channel {channel_id} is not a text channel")
    return channel


def require_messageable_channel(
    channel: object, channel_id: str
) -> discord.TextChannel | discord.Thread:
    """Validate that a fetched channel is a text channel or thread.

    Both types support .history() for reading messages.
    """
    if isinstance(channel, (discord.TextChannel, discord.Thread)):
        return channel
    raise ValueError(f"Channel {channel_id} is not a text channel or thread")


def require_guild_channel(channel: object, channel_id: str) -> discord.abc.GuildChannel:
    """Validate that a fetched channel is a guild channel."""
    if not isinstance(channel, discord.abc.GuildChannel):
        raise ValueError(f"Channel {channel_id} is not a guild channel")
    return channel


async def fetch_role(guild: discord.Guild, role_id: int) -> discord.Role:
    """Fetch a role from the API by ID."""
    roles = await guild.fetch_roles()
    for role in roles:
        if role.id == role_id:
            return role
    raise ValueError(f"Role {role_id} not found in guild {guild.name}")


@dataclass
class DiscordContext:
    """Context holding the connected Discord bot client."""

    bot: commands.Bot


@asynccontextmanager
async def discord_lifespan(mcp: FastMCP) -> AsyncIterator[DiscordContext]:
    """Lifespan context manager for Discord bot lifecycle."""
    import asyncio
    import os

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable is required")

    bot = create_discord_bot()
    ready_event = asyncio.Event()

    @bot.event
    async def on_ready() -> None:
        if bot.user:
            logger.info(f"Logged in as {bot.user.name}")
        ready_event.set()

    bot_task = asyncio.create_task(bot.start(token))

    try:
        try:
            await asyncio.wait_for(ready_event.wait(), timeout=30.0)
        except TimeoutError:
            if bot_task.done():
                bot_task.result()
            raise RuntimeError("Discord bot did not become ready within 30 seconds")

        if bot_task.done():
            bot_task.result()

        yield DiscordContext(bot=bot)
    finally:
        logger.info("Shutting down Discord bot...")
        if not bot.is_closed():
            try:
                await asyncio.wait_for(bot.close(), timeout=5.0)
            except TimeoutError:
                logger.warning("Bot close timed out, forcing shutdown")
                await bot.close()
        if not bot_task.done():
            bot_task.cancel()
            try:
                await asyncio.wait_for(bot_task, timeout=2.0)
            except (asyncio.CancelledError, TimeoutError):
                pass
        logger.info("Discord bot shut down complete")
