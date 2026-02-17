"""Tool handler implementations for Discord operations.

These are pure async functions that can be tested independently of MCP.
All functions take the Discord client as the first argument.
"""

from datetime import timedelta
from typing import Any

import discord
from discord.ext import commands

from .client import fetch_role, parse_id, require_guild_channel, require_text_channel


async def send_message(client: commands.Bot, channel_id: str, content: str) -> dict[str, Any]:
    """Send a message to a specific channel."""
    channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))
    text_channel = require_text_channel(channel, channel_id)
    message = await text_channel.send(content)
    return {"message_id": str(message.id), "channel_id": channel_id}


async def add_role(client: commands.Bot, server_id: str, user_id: str, role_id: str) -> dict[str, Any]:
    """Add a role to a user."""
    guild = await client.fetch_guild(parse_id(server_id, "server_id"))
    member = await guild.fetch_member(parse_id(user_id, "user_id"))
    role = await fetch_role(guild, parse_id(role_id, "role_id"))
    await member.add_roles(role, reason="Role added via MCP")
    return {"role_name": role.name, "user_name": member.name}


async def remove_role(client: commands.Bot, server_id: str, user_id: str, role_id: str) -> dict[str, Any]:
    """Remove a role from a user."""
    guild = await client.fetch_guild(parse_id(server_id, "server_id"))
    member = await guild.fetch_member(parse_id(user_id, "user_id"))
    role = await fetch_role(guild, parse_id(role_id, "role_id"))
    await member.remove_roles(role, reason="Role removed via MCP")
    return {"role_name": role.name, "user_name": member.name}


async def create_text_channel(
    client: commands.Bot,
    server_id: str,
    name: str,
    category_id: str | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    """Create a new text channel."""
    guild = await client.fetch_guild(parse_id(server_id, "server_id"))
    category = None
    if category_id:
        cat_channel = await client.fetch_channel(parse_id(category_id, "category_id"))
        if not isinstance(cat_channel, discord.CategoryChannel):
            raise ValueError(f"Channel {category_id} is not a category channel")
        category = cat_channel

    kwargs: dict[str, Any] = {"name": name, "reason": "Channel created via MCP"}
    if topic:
        kwargs["topic"] = topic
    if category:
        kwargs["category"] = category
    channel = await guild.create_text_channel(**kwargs)
    return {"channel_name": channel.name, "channel_id": str(channel.id)}


async def delete_channel(client: commands.Bot, channel_id: str, reason: str | None = None) -> dict[str, Any]:
    """Delete a channel."""
    channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))
    guild_channel = require_guild_channel(channel, channel_id)
    await guild_channel.delete(reason=reason or "Channel deleted via MCP")
    return {"channel_id": channel_id}


async def add_reaction(client: commands.Bot, channel_id: str, message_id: str, emoji: str) -> dict[str, Any]:
    """Add a reaction to a message."""
    channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))
    text_channel = require_text_channel(channel, channel_id)
    message = await text_channel.fetch_message(parse_id(message_id, "message_id"))
    await message.add_reaction(emoji)
    return {"emoji": emoji, "message_id": message_id}


async def add_multiple_reactions(
    client: commands.Bot, channel_id: str, message_id: str, emojis: list[str]
) -> dict[str, Any]:
    """Add multiple reactions to a message."""
    channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))
    text_channel = require_text_channel(channel, channel_id)
    message = await text_channel.fetch_message(parse_id(message_id, "message_id"))
    for emoji in emojis:
        await message.add_reaction(emoji)
    return {"emojis": emojis, "message_id": message_id}


async def remove_reaction(client: commands.Bot, channel_id: str, message_id: str, emoji: str) -> dict[str, Any]:
    """Remove a reaction from a message."""
    channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))
    text_channel = require_text_channel(channel, channel_id)
    message = await text_channel.fetch_message(parse_id(message_id, "message_id"))
    if client.user is None:
        raise RuntimeError("Discord client user not available")
    await message.remove_reaction(emoji, client.user)
    return {"emoji": emoji, "message_id": message_id}


async def moderate_message(
    client: commands.Bot,
    channel_id: str,
    message_id: str,
    reason: str,
    timeout_minutes: int | None = None,
) -> dict[str, Any]:
    """Delete a message and optionally timeout the user."""
    channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))
    text_channel = require_text_channel(channel, channel_id)
    message = await text_channel.fetch_message(parse_id(message_id, "message_id"))

    timeout_applied = False
    timeout_duration = 0
    if timeout_minutes and timeout_minutes > 0:
        guild = text_channel.guild
        try:
            member = await guild.fetch_member(message.author.id)
            duration = discord.utils.utcnow() + timedelta(minutes=timeout_minutes)
            await member.timeout(duration, reason=reason)
            timeout_applied = True
            timeout_duration = timeout_minutes
        except discord.NotFound:
            raise ValueError(f"Cannot timeout user {message.author.id}: member not found in guild")

    await message.delete()
    return {
        "deleted": True,
        "timeout_applied": timeout_applied,
        "timeout_minutes": timeout_duration if timeout_applied else None,
    }
