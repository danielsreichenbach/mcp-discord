"""Resource handler implementations for Discord read operations.

These are pure async functions that can be tested independently of MCP.
All functions take the Discord client as the first argument.
Returns dicts/lists for easy serialization.
"""

from typing import Any

from discord.ext import commands

from .client import parse_id, require_text_channel


async def list_servers(client: commands.Bot) -> list[dict[str, Any]]:
    """List all servers the bot has access to."""
    servers = []
    for guild in client.guilds:
        servers.append(
            {
                "id": str(guild.id),
                "name": guild.name,
                "member_count": guild.member_count,
                "created_at": guild.created_at.isoformat(),
            }
        )
    return servers


async def get_server_info(client: commands.Bot, server_id: str) -> dict[str, Any]:
    """Get information about a Discord server."""
    guild = await client.fetch_guild(parse_id(server_id, "server_id"), with_counts=True)
    return {
        "name": guild.name,
        "id": str(guild.id),
        "owner_id": str(guild.owner_id),
        "member_count": guild.approximate_member_count,
        "created_at": guild.created_at.isoformat(),
        "description": guild.description,
        "premium_tier": guild.premium_tier,
        "explicit_content_filter": str(guild.explicit_content_filter),
    }


async def get_channels(client: commands.Bot, server_id: str) -> list[dict[str, Any]]:
    """Get a list of all channels in a Discord server."""
    guild = await client.fetch_guild(parse_id(server_id, "server_id"))
    channels = await guild.fetch_channels()
    return [
        {
            "id": str(ch.id),
            "name": ch.name,
            "type": str(ch.type),
        }
        for ch in channels
    ]


async def list_members(client: commands.Bot, server_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Get a list of members in a server."""
    guild = await client.fetch_guild(parse_id(server_id, "server_id"))
    actual_limit = min(limit, 1000)
    members = []
    async for member in guild.fetch_members(limit=actual_limit):
        members.append(
            {
                "id": str(member.id),
                "name": member.name,
                "nick": member.nick,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "roles": [str(role.id) for role in member.roles[1:]],
            }
        )
    return members


async def list_roles(client: commands.Bot, server_id: str) -> list[dict[str, Any]]:
    """Get a list of all roles in a Discord server."""
    guild = await client.fetch_guild(parse_id(server_id, "server_id"))
    roles = await guild.fetch_roles()
    return [
        {
            "id": str(role.id),
            "name": role.name,
            "color": str(role.color),
            "position": role.position,
            "mentionable": role.mentionable,
            "member_count": len(role.members) if role.members else None,
        }
        for role in sorted(roles, key=lambda r: r.position, reverse=True)
    ]


async def read_messages(client: commands.Bot, channel_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Read recent messages from a channel."""
    channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))
    text_channel = require_text_channel(channel, channel_id)
    actual_limit = min(limit, 100)
    messages = []
    async for message in text_channel.history(limit=actual_limit):
        reaction_data = []
        for reaction in message.reactions:
            emoji = reaction.emoji
            if isinstance(emoji, str):
                emoji_str = emoji
            elif hasattr(emoji, "name") and emoji.name:
                emoji_str = emoji.name
            else:
                emoji_str = str(emoji.id)
            reaction_data.append({"emoji": emoji_str, "count": reaction.count})
        messages.append(
            {
                "id": str(message.id),
                "author": str(message.author),
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
                "reactions": reaction_data,
            }
        )
    return messages


async def get_user_info(client: commands.Bot, user_id: str) -> dict[str, Any]:
    """Get information about a Discord user."""
    user = await client.fetch_user(parse_id(user_id, "user_id"))
    return {
        "id": str(user.id),
        "name": user.name,
        "discriminator": user.discriminator,
        "bot": user.bot,
        "created_at": user.created_at.isoformat(),
    }
