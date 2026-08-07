"""Tool handler implementations for Discord operations.

These are pure async functions that can be tested independently of MCP.
All functions take the Discord client as the first argument.
"""

from __future__ import annotations

import base64
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any, NotRequired, TypedDict

import discord
from discord.ext import commands

from .client import fetch_role, parse_id, require_guild_channel, require_text_channel

_SENTINEL = object()
"""Sentinel value used to distinguish 'not provided' from None."""


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


# ============================================================================
# Member Moderation Tools (Phase 1A)
# ============================================================================


async def kick_member(
    client: commands.Bot,
    server_id: str,
    user_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Kick a member from the server.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        user_id: User ID to kick
        reason: Optional reason for the kick (shown in audit log)

    Returns:
        Dict with kick status and user info

    Raises:
        ValueError: If server or member not found
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        member = await guild.fetch_member(parse_id(user_id, "user_id"))

        await member.kick(reason=reason)

        return {
            "kicked": True,
            "user_id": str(member.id),
            "user_name": member.name,
            "reason": reason,
        }

    except discord.NotFound as e:
        if "guild" in str(e).lower() or "server" in str(e).lower():
            raise ValueError(f"Server {server_id} not found") from e
        raise ValueError(f"Member {user_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to kick member: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def ban_member(
    client: commands.Bot,
    server_id: str,
    user_id: str,
    reason: str | None = None,
    delete_message_days: int = 0,
) -> dict[str, Any]:
    """Ban a user from the server.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        user_id: User ID to ban
        reason: Optional reason for the ban (shown in audit log)
        delete_message_days: Days of messages to delete (0-7)

    Returns:
        Dict with ban status and user info

    Raises:
        ValueError: If server not found or invalid delete_message_days
        PermissionError: If bot lacks permissions
    """
    if delete_message_days < 0 or delete_message_days > 7:
        raise ValueError("delete_message_days must be between 0 and 7")

    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        try:
            user = await guild.fetch_member(parse_id(user_id, "user_id"))
        except discord.NotFound:
            # User not in guild, fetch user object instead
            user = await client.fetch_user(parse_id(user_id, "user_id"))

        await guild.ban(user, reason=reason, delete_message_days=delete_message_days)

        return {
            "banned": True,
            "user_id": str(user.id),
            "user_name": user.name,
            "reason": reason,
            "messages_deleted_days": delete_message_days,
        }

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to ban user: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def unban_member(
    client: commands.Bot,
    server_id: str,
    user_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Remove a ban for a user.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        user_id: User ID to unban
        reason: Optional reason for the unban (shown in audit log)

    Returns:
        Dict with unban status

    Raises:
        ValueError: If server not found or user not banned
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        user = await client.fetch_user(parse_id(user_id, "user_id"))

        await guild.unban(user, reason=reason)

        return {
            "unbanned": True,
            "user_id": str(user.id),
            "reason": reason,
        }

    except discord.NotFound as e:
        raise ValueError(f"User {user_id} is not banned or not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to unban user: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def list_bans(
    client: commands.Bot,
    server_id: str,
) -> list[dict[str, Any]]:
    """List all banned users in a server.

    Args:
        client: Discord bot client
        server_id: Guild/server ID

    Returns:
        List of dicts with ban info (user_id, user_name, reason)

    Raises:
        ValueError: If server not found
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        bans = []
        async for ban in guild.bans():
            bans.append(
                {
                    "user_id": str(ban.user.id),
                    "user_name": ban.user.name,
                    "reason": ban.reason,
                }
            )

        return bans

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to view bans: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def edit_member(
    client: commands.Bot,
    server_id: str,
    user_id: str,
    nick: str | None | object = _SENTINEL,
    timeout_until: str | None | object = _SENTINEL,
    mute: bool | None = None,
    deafen: bool | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Modify member properties (nickname, timeout, voice mute/deafen).

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        user_id: User ID to modify
        nick: New nickname (None to clear, _SENTINEL to not change)
        timeout_until: ISO datetime for timeout end (None to remove, _SENTINEL to not change)
        mute: Voice mute state (None to not change)
        deafen: Voice deafen state (None to not change)
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with user info and list of changed fields

    Raises:
        ValueError: If server/member not found or invalid datetime
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        member = await guild.fetch_member(parse_id(user_id, "user_id"))

        changes: list[str] = []
        edit_kwargs: dict[str, Any] = {"reason": reason}

        # Handle nickname changes
        if nick is not _SENTINEL:
            edit_kwargs["nick"] = nick
            changes.append("nick")

        # Handle timeout changes
        if timeout_until is not _SENTINEL:
            if timeout_until is None:
                edit_kwargs["timeout"] = None
            else:
                assert isinstance(timeout_until, str)
                try:
                    timeout_dt = datetime.fromisoformat(timeout_until.replace("Z", "+00:00"))
                    if timeout_dt.tzinfo is None:
                        timeout_dt = timeout_dt.replace(tzinfo=UTC)
                    edit_kwargs["timeout"] = timeout_dt
                except ValueError as e:
                    raise ValueError(f"Invalid timeout_until format: {e}") from e
            changes.append("timeout_until")

        # Handle voice mute
        if mute is not None:
            edit_kwargs["mute"] = mute
            changes.append("mute")

        # Handle voice deafen
        if deafen is not None:
            edit_kwargs["deafen"] = deafen
            changes.append("deafen")

        await member.edit(**edit_kwargs)

        return {
            "user_id": str(member.id),
            "user_name": member.name,
            "nick": member.nick,
            "timeout_until": (member.timed_out_until.isoformat() if member.timed_out_until else None),
            "changes": changes,
        }

    except discord.NotFound as e:
        if "guild" in str(e).lower() or "server" in str(e).lower():
            raise ValueError(f"Server {server_id} not found") from e
        raise ValueError(f"Member {user_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to edit member: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def remove_timeout(
    client: commands.Bot,
    server_id: str,
    user_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Remove a timeout from a member.

    Convenience wrapper for edit_member.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        user_id: User ID to remove timeout from
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with timeout removal status

    Raises:
        ValueError: If server/member not found
        PermissionError: If bot lacks permissions
    """
    result = await edit_member(
        client=client,
        server_id=server_id,
        user_id=user_id,
        timeout_until=None,
        reason=reason,
    )

    return {
        "timeout_removed": True,
        "user_id": result["user_id"],
        "user_name": result["user_name"],
        "reason": reason,
    }


# ============================================================================
# Role Management Tools (Phase 1B)
# ============================================================================


async def create_role(
    client: commands.Bot,
    server_id: str,
    name: str,
    permissions: int | None = None,
    color: int | None = None,
    hoist: bool = False,
    mentionable: bool = False,
    reason: str | None = None,
) -> dict[str, Any]:
    """Create a new role in the server.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        name: Role name
        permissions: Permission bitwise value (optional)
        color: RGB color value (optional)
        hoist: Show role separately in member list
        mentionable: Allow @mention for the role
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with created role info

    Raises:
        ValueError: If server not found
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        kwargs: dict[str, Any] = {
            "name": name,
            "hoist": hoist,
            "mentionable": mentionable,
        }

        if permissions is not None:
            kwargs["permissions"] = discord.Permissions(permissions)

        if color is not None:
            kwargs["colour"] = discord.Colour(color)

        role = await guild.create_role(**kwargs, reason=reason)

        return {
            "role_id": str(role.id),
            "role_name": role.name,
            "color": role.color.value,
            "position": role.position,
            "permissions": role.permissions.value,
            "hoist": role.hoist,
            "mentionable": role.mentionable,
        }

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to create role: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def edit_role(
    client: commands.Bot,
    server_id: str,
    role_id: str,
    name: str | None = None,
    permissions: int | None = None,
    color: int | None = None,
    hoist: bool | None = None,
    mentionable: bool | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Modify an existing role.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        role_id: Role ID to edit
        name: New role name (optional)
        permissions: New permission bitwise value (optional)
        color: New RGB color value (optional)
        hoist: New hoist setting (optional)
        mentionable: New mentionable setting (optional)
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with updated role info and list of changes

    Raises:
        ValueError: If server or role not found
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        role = await fetch_role(guild, parse_id(role_id, "role_id"))

        edit_kwargs: dict[str, Any] = {"reason": reason}
        changes: list[str] = []

        if name is not None:
            edit_kwargs["name"] = name
            changes.append("name")

        if permissions is not None:
            edit_kwargs["permissions"] = discord.Permissions(permissions)
            changes.append("permissions")

        if color is not None:
            edit_kwargs["colour"] = discord.Colour(color)
            changes.append("color")

        if hoist is not None:
            edit_kwargs["hoist"] = hoist
            changes.append("hoist")

        if mentionable is not None:
            edit_kwargs["mentionable"] = mentionable
            changes.append("mentionable")

        await role.edit(**edit_kwargs)

        return {
            "role_id": str(role.id),
            "role_name": role.name,
            "color": role.color.value,
            "position": role.position,
            "permissions": role.permissions.value,
            "hoist": role.hoist,
            "mentionable": role.mentionable,
            "changes": changes,
        }

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to edit role: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def delete_role(
    client: commands.Bot,
    server_id: str,
    role_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Delete a role from the server.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        role_id: Role ID to delete
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with deletion status

    Raises:
        ValueError: If server or role not found
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        role = await fetch_role(guild, parse_id(role_id, "role_id"))
        role_name = role.name
        role_id_str = str(role.id)

        await role.delete(reason=reason)

        return {
            "deleted": True,
            "role_name": role_name,
            "role_id": role_id_str,
        }

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to delete role: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


class RolePosition(TypedDict):
    """Role id and new position for reorder_roles."""

    id: str
    position: int


async def reorder_roles(
    client: commands.Bot,
    server_id: str,
    role_positions: list[RolePosition],
    reason: str | None = None,
) -> dict[str, Any]:
    """Change the position/order of roles.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        role_positions: List of {"id": role_id, "position": new_position}
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with reorder status and updated roles

    Raises:
        ValueError: If server not found or invalid position data
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        # Convert to dict format expected by discord.py
        positions_dict: dict[discord.abc.Snowflake, int] = {}

        for item in role_positions:
            role_id = parse_id(str(item["id"]), "role_id")
            position = int(item["position"])

            role = await fetch_role(guild, role_id)
            positions_dict[role] = position

        # Perform reorder
        updated_roles = await guild.edit_role_positions(
            positions_dict,
            reason=reason,
        )

        return {
            "reordered": True,
            "roles": [
                {
                    "id": str(role.id),
                    "name": role.name,
                    "position": role.position,
                }
                for role in updated_roles
            ],
        }

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to reorder roles: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


# ============================================================================
# Channel Management Tools (Phase 1C)
# ============================================================================


async def edit_channel(
    client: commands.Bot,
    channel_id: str,
    name: str | None = None,
    topic: str | None = None,
    nsfw: bool | None = None,
    slowmode_delay: int | None = None,
    default_auto_archive_duration: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Modify channel properties.

    Args:
        client: Discord bot client
        channel_id: Channel ID to edit
        name: New channel name (optional)
        topic: New channel topic (optional, text channels only)
        nsfw: NSFW setting (optional)
        slowmode_delay: Slowmode delay in seconds, 0-21600 (optional)
        default_auto_archive_duration: Default thread archive duration in minutes
            (optional: 60, 1440, 4320, 10080)
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with updated channel info and list of changes

    Raises:
        ValueError: If channel not found or invalid parameters
        PermissionError: If bot lacks permissions
    """
    try:
        channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))

        if not isinstance(channel, discord.abc.GuildChannel):
            raise ValueError(f"Channel {channel_id} is not a guild channel")

        edit_kwargs: dict[str, Any] = {"reason": reason}
        changes: list[str] = []

        if name is not None:
            edit_kwargs["name"] = name
            changes.append("name")

        if topic is not None:
            if not isinstance(channel, discord.TextChannel):
                raise ValueError("topic can only be set for text channels")
            edit_kwargs["topic"] = topic
            changes.append("topic")

        if nsfw is not None:
            edit_kwargs["nsfw"] = nsfw
            changes.append("nsfw")

        if slowmode_delay is not None:
            if slowmode_delay < 0 or slowmode_delay > 21600:
                raise ValueError("slowmode_delay must be between 0 and 21600 seconds")
            edit_kwargs["slowmode_delay"] = slowmode_delay
            changes.append("slowmode_delay")

        if default_auto_archive_duration is not None:
            valid_durations = [60, 1440, 4320, 10080]
            if default_auto_archive_duration not in valid_durations:
                raise ValueError(f"default_auto_archive_duration must be one of {valid_durations}")
            edit_kwargs["default_auto_archive_duration"] = default_auto_archive_duration
            changes.append("default_auto_archive_duration")

        await channel.edit(**edit_kwargs)

        return {
            "channel_id": str(channel.id),
            "channel_name": channel.name,
            "topic": getattr(channel, "topic", None),
            "nsfw": getattr(channel, "nsfw", False),
            "slowmode_delay": getattr(channel, "slowmode_delay", 0),
            "changes": changes,
        }

    except discord.NotFound as e:
        raise ValueError(f"Channel {channel_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to edit channel: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def create_category(
    client: commands.Bot,
    server_id: str,
    name: str,
    position: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Create a new channel category.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        name: Category name
        position: Position in channel list (optional)
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with created category info

    Raises:
        ValueError: If server not found
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        kwargs: dict[str, Any] = {"name": name}
        if position is not None:
            kwargs["position"] = position

        category = await guild.create_category(**kwargs, reason=reason)

        return {
            "category_id": str(category.id),
            "category_name": category.name,
            "position": category.position,
        }

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to create category: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def create_voice_channel(
    client: commands.Bot,
    server_id: str,
    name: str,
    category_id: str | None = None,
    bitrate: int | None = None,
    user_limit: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Create a new voice channel.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        name: Voice channel name
        category_id: Parent category ID (optional)
        bitrate: Bitrate in bits per second (8000-96000, VIP: 128000)
        user_limit: Max users (0-99, 0 = unlimited)
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with created voice channel info

    Raises:
        ValueError: If server not found or invalid parameters
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        kwargs: dict[str, Any] = {"name": name}

        if category_id is not None:
            category = await client.fetch_channel(parse_id(category_id, "category_id"))
            if not isinstance(category, discord.CategoryChannel):
                raise ValueError(f"Channel {category_id} is not a category channel")
            kwargs["category"] = category

        if bitrate is not None:
            min_bitrate = 8000
            max_bitrate = 128000  # VIP servers can have higher
            if bitrate < min_bitrate or bitrate > max_bitrate:
                raise ValueError(f"bitrate must be between {min_bitrate} and {max_bitrate}")
            kwargs["bitrate"] = bitrate

        if user_limit is not None:
            if user_limit < 0 or user_limit > 99:
                raise ValueError("user_limit must be between 0 and 99")
            kwargs["user_limit"] = user_limit

        channel = await guild.create_voice_channel(**kwargs, reason=reason)

        return {
            "channel_id": str(channel.id),
            "channel_name": channel.name,
            "type": "voice",
            "bitrate": channel.bitrate,
            "user_limit": channel.user_limit,
        }

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to create voice channel: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


class ChannelPosition(TypedDict):
    """Channel id, new position, and optional parent category for reorder_channels."""

    id: str
    position: int
    parent_id: NotRequired[str | None]


async def reorder_channels(
    client: commands.Bot,
    server_id: str,
    channel_positions: list[ChannelPosition],
    reason: str | None = None,
) -> dict[str, Any]:
    """Change channel positions within/across categories.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        channel_positions: List of {"id": channel_id, "position": pos,
            "parent_id": category_id | None}
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with reorder status and updated channels

    Raises:
        ValueError: If server not found or invalid position data
        PermissionError: If bot lacks permissions
    """
    try:
        await client.fetch_guild(parse_id(server_id, "server_id"))  # validate server exists

        updated: list[dict[str, Any]] = []

        for item in channel_positions:
            chan_id = parse_id(str(item["id"]), "channel_id")
            position = int(item["position"])
            parent_id = item.get("parent_id")

            channel = await client.fetch_channel(chan_id)
            if not isinstance(channel, discord.abc.GuildChannel):
                raise ValueError(f"Channel {chan_id} is not a guild channel")

            edit_kwargs: dict[str, Any] = {"position": position, "reason": reason}
            if parent_id is not None:
                category = await client.fetch_channel(parse_id(str(parent_id), "parent_id"))
                if isinstance(category, discord.CategoryChannel):
                    edit_kwargs["category"] = category

            await channel.edit(**edit_kwargs)
            updated.append(
                {
                    "id": str(channel.id),
                    "name": channel.name,
                    "position": position,
                }
            )

        return {
            "reordered": True,
            "channels": updated,
        }

    except discord.NotFound as e:
        raise ValueError("Server or channel not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to reorder channels: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


# ============================================================================
# Invite Management Tools (Phase 1D)
# ============================================================================


async def create_invite(
    client: commands.Bot,
    channel_id: str,
    max_age: int = 86400,
    max_uses: int = 0,
    temporary: bool = False,
    unique: bool = False,
    reason: str | None = None,
) -> dict[str, Any]:
    """Create a channel invite.

    Args:
        client: Discord bot client
        channel_id: Channel ID to create invite for
        max_age: Duration in seconds before expiry (0 = never, default 86400)
        max_uses: Max uses (0 = unlimited, default 0)
        temporary: Grant temporary membership (default False)
        unique: Create unique invite even if similar exists (default False)
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with invite info including code and URL

    Raises:
        ValueError: If channel not found or not a guild channel
        PermissionError: If bot lacks permissions
    """
    try:
        channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))

        if not isinstance(channel, discord.abc.GuildChannel):
            raise ValueError(f"Channel {channel_id} is not a guild channel")

        invite = await channel.create_invite(
            max_age=max_age,
            max_uses=max_uses,
            temporary=temporary,
            unique=unique,
            reason=reason,
        )

        return {
            "code": invite.code,
            "url": "https://discord.gg/" + invite.code,
            "channel_id": str(channel.id),
            "channel_name": channel.name,
            "max_age": invite.max_age,
            "max_uses": invite.max_uses,
            "temporary": invite.temporary,
            "created_at": invite.created_at.isoformat() if invite.created_at else None,
        }

    except discord.NotFound as e:
        raise ValueError(f"Channel {channel_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to create invite: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def list_server_invites(
    client: commands.Bot,
    server_id: str,
) -> list[dict[str, Any]]:
    """List all invites for a server.

    Args:
        client: Discord bot client
        server_id: Guild/server ID

    Returns:
        List of dicts with invite info

    Raises:
        ValueError: If server not found
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        invites = await guild.invites()

        result = []
        for invite in invites:
            ch = invite.channel
            result.append(
                {
                    "code": invite.code,
                    "url": "https://discord.gg/" + invite.code,
                    "channel_id": str(ch.id) if ch else None,
                    "channel_name": getattr(ch, "name", None) if ch else None,
                    "inviter": {
                        "id": str(invite.inviter.id),
                        "name": invite.inviter.name,
                    }
                    if invite.inviter
                    else None,
                    "uses": invite.uses,
                    "max_uses": invite.max_uses,
                    "max_age": invite.max_age,
                    "temporary": invite.temporary,
                    "created_at": (invite.created_at.isoformat() if invite.created_at else None),
                    "expires_at": (
                        invite.expires_at.isoformat() if hasattr(invite, "expires_at") and invite.expires_at else None
                    ),
                }
            )
        return result

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to view invites: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def list_channel_invites(
    client: commands.Bot,
    channel_id: str,
) -> list[dict[str, Any]]:
    """List all invites for a specific channel.

    Args:
        client: Discord bot client
        channel_id: Channel ID

    Returns:
        List of dicts with invite info

    Raises:
        ValueError: If channel not found
        PermissionError: If bot lacks permissions
    """
    try:
        channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))

        if not isinstance(channel, discord.abc.GuildChannel):
            raise ValueError(f"Channel {channel_id} is not a guild channel")

        invites = await channel.invites()

        result = []
        for invite in invites:
            result.append(
                {
                    "code": invite.code,
                    "url": "https://discord.gg/" + invite.code,
                    "channel_id": str(channel.id),
                    "channel_name": channel.name,
                    "inviter": {
                        "id": str(invite.inviter.id),
                        "name": invite.inviter.name,
                    }
                    if invite.inviter
                    else None,
                    "uses": invite.uses,
                    "max_uses": invite.max_uses,
                    "max_age": invite.max_age,
                    "temporary": invite.temporary,
                    "created_at": invite.created_at.isoformat() if invite.created_at else None,
                }
            )
        return result

    except discord.NotFound as e:
        raise ValueError(f"Channel {channel_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to view invites: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def delete_invite(
    client: commands.Bot,
    invite_code: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Delete/revoke an invite.

    Args:
        client: Discord bot client
        invite_code: The invite code to delete
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with deletion status

    Raises:
        ValueError: If invite not found
        PermissionError: If bot lacks permissions
    """
    try:
        invite = await client.fetch_invite(invite_code)

        await invite.delete(reason=reason)

        return {
            "deleted": True,
            "code": invite_code,
        }

    except discord.NotFound as e:
        raise ValueError(f"Invite {invite_code} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to delete invite: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


# ============================================================================
# Message Management Tools (Phase 1D continued)
# ============================================================================


async def edit_message(
    client: commands.Bot,
    channel_id: str,
    message_id: str,
    content: str,
) -> dict[str, Any]:
    """Edit a message sent by the bot.

    Args:
        client: Discord bot client
        channel_id: Channel ID
        message_id: Message ID to edit
        content: New message content

    Returns:
        Dict with updated message info

    Raises:
        ValueError: If channel or message not found
        PermissionError: If bot lacks permissions (can only edit own messages)
    """
    try:
        channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))

        text_channel = require_text_channel(channel, channel_id)
        message = await text_channel.fetch_message(parse_id(message_id, "message_id"))

        await message.edit(content=content)

        return {
            "message_id": str(message.id),
            "channel_id": str(channel.id),
            "content": message.content,
        }

    except discord.NotFound as e:
        raise ValueError(f"Message {message_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to edit message: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def delete_message(
    client: commands.Bot,
    channel_id: str,
    message_id: str,
) -> dict[str, Any]:
    """Delete a single message.

    Args:
        client: Discord bot client
        channel_id: Channel ID
        message_id: Message ID to delete

    Returns:
        Dict with deletion status

    Raises:
        ValueError: If channel or message not found
        PermissionError: If bot lacks permissions
    """
    try:
        channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))

        text_channel = require_text_channel(channel, channel_id)
        message = await text_channel.fetch_message(parse_id(message_id, "message_id"))

        await message.delete()

        return {
            "deleted": True,
            "message_id": str(message.id),
            "channel_id": str(channel.id),
        }

    except discord.NotFound as e:
        raise ValueError(f"Message {message_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to delete message: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def bulk_delete_messages(
    client: commands.Bot,
    channel_id: str,
    message_ids: list[str],
    reason: str | None = None,
) -> dict[str, Any]:
    """Delete multiple messages at once (2-100 messages).

    Note: Messages must be less than 14 days old. For older messages,
    use individual delete_message calls.

    Args:
        client: Discord bot client
        channel_id: Channel ID
        message_ids: List of message IDs to delete (2-100)
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with deletion count

    Raises:
        ValueError: If channel not found or invalid message count
        PermissionError: If bot lacks permissions
    """
    if len(message_ids) < 2:
        raise ValueError("bulk_delete requires at least 2 messages")
    if len(message_ids) > 100:
        raise ValueError("bulk_delete can delete maximum 100 messages at once")

    try:
        channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))

        text_channel = require_text_channel(channel, channel_id)

        # Fetch each message individually
        messages: list[discord.Message] = []
        for mid in message_ids:
            msg = await text_channel.fetch_message(parse_id(mid, "message_id"))
            messages.append(msg)

        await text_channel.delete_messages(messages, reason=reason)

        return {
            "deleted_count": len(messages),
            "channel_id": str(channel.id),
        }

    except discord.NotFound as e:
        raise ValueError("Channel or message not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to delete messages: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def pin_message(
    client: commands.Bot,
    channel_id: str,
    message_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Pin a message to the channel.

    Args:
        client: Discord bot client
        channel_id: Channel ID
        message_id: Message ID to pin
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with pin status

    Raises:
        ValueError: If channel or message not found
        PermissionError: If bot lacks permissions
    """
    try:
        channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))

        text_channel = require_text_channel(channel, channel_id)
        message = await text_channel.fetch_message(parse_id(message_id, "message_id"))

        await message.pin(reason=reason)

        return {
            "pinned": True,
            "message_id": str(message.id),
            "channel_id": str(channel.id),
        }

    except discord.NotFound as e:
        raise ValueError(f"Message {message_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to pin message: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def unpin_message(
    client: commands.Bot,
    channel_id: str,
    message_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Unpin a message from the channel.

    Args:
        client: Discord bot client
        channel_id: Channel ID
        message_id: Message ID to unpin
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with unpin status

    Raises:
        ValueError: If channel or message not found
        PermissionError: If bot lacks permissions
    """
    try:
        channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))

        text_channel = require_text_channel(channel, channel_id)
        message = await text_channel.fetch_message(parse_id(message_id, "message_id"))

        await message.unpin(reason=reason)

        return {
            "unpinned": True,
            "message_id": str(message.id),
            "channel_id": str(channel.id),
        }

    except discord.NotFound as e:
        raise ValueError(f"Message {message_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to unpin message: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def list_pinned_messages(
    client: commands.Bot,
    channel_id: str,
) -> list[dict[str, Any]]:
    """List all pinned messages in a channel.

    Args:
        client: Discord bot client
        channel_id: Channel ID

    Returns:
        List of dicts with pinned message info

    Raises:
        ValueError: If channel not found
        PermissionError: If bot lacks permissions
    """
    try:
        channel = await client.fetch_channel(parse_id(channel_id, "channel_id"))

        text_channel = require_text_channel(channel, channel_id)
        pinned_messages = await text_channel.pins()

        return [
            {
                "message_id": str(msg.id),
                "content": msg.content,
                "author_id": str(msg.author.id),
                "author_name": msg.author.name,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "url": msg.jump_url,
            }
            for msg in pinned_messages
        ]

    except discord.NotFound as e:
        raise ValueError(f"Channel {channel_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to view pins: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


# ============================================================================
# Audit Log Tools (Phase 1G)
# ============================================================================


# Audit log action type names mapping
AUDIT_LOG_ACTION_NAMES = {
    1: "GUILD_UPDATE",
    10: "CHANNEL_CREATE",
    11: "CHANNEL_UPDATE",
    12: "CHANNEL_DELETE",
    13: "CHANNEL_OVERWRITE_CREATE",
    14: "CHANNEL_OVERWRITE_UPDATE",
    15: "CHANNEL_OVERWRITE_DELETE",
    20: "MEMBER_KICK",
    21: "MEMBER_PRUNE",
    22: "MEMBER_BAN_ADD",
    23: "MEMBER_BAN_REMOVE",
    24: "MEMBER_UPDATE",
    25: "MEMBER_ROLE_UPDATE",
    26: "MEMBER_MOVE",
    27: "MEMBER_DISCONNECT",
    28: "BOT_ADD",
    30: "ROLE_CREATE",
    31: "ROLE_UPDATE",
    32: "ROLE_DELETE",
    40: "INVITE_CREATE",
    41: "INVITE_UPDATE",
    42: "INVITE_DELETE",
    50: "WEBHOOK_CREATE",
    51: "WEBHOOK_UPDATE",
    52: "WEBHOOK_DELETE",
    60: "EMOJI_CREATE",
    61: "EMOJI_UPDATE",
    62: "EMOJI_DELETE",
    70: "MESSAGE_DELETE",
    71: "MESSAGE_BULK_DELETE",
    72: "MESSAGE_PIN",
    73: "MESSAGE_UNPIN",
    80: "INTEGRATION_CREATE",
    81: "INTEGRATION_UPDATE",
    82: "INTEGRATION_DELETE",
    83: "STAGE_INSTANCE_CREATE",
    84: "STAGE_INSTANCE_UPDATE",
    85: "STAGE_INSTANCE_DELETE",
    90: "STICKER_CREATE",
    91: "STICKER_UPDATE",
    92: "STICKER_DELETE",
    100: "GUILD_SCHEDULED_EVENT_CREATE",
    101: "GUILD_SCHEDULED_EVENT_UPDATE",
    102: "GUILD_SCHEDULED_EVENT_DELETE",
    110: "THREAD_CREATE",
    111: "THREAD_UPDATE",
    112: "THREAD_DELETE",
    140: "APPLICATION_COMMAND_PERMISSION_UPDATE",
}


async def get_audit_log(
    client: commands.Bot,
    server_id: str,
    user_id: str | None = None,
    action_type: int | None = None,
    before: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Retrieve server audit logs.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        user_id: Filter by user ID (optional)
        action_type: Filter by action type (optional)
        before: Get entries before this entry ID (optional)
        limit: Max entries to return (1-100, default 50)

    Returns:
        Dict with entries list and has_more flag

    Raises:
        ValueError: If server not found or invalid parameters
        PermissionError: If bot lacks VIEW_AUDIT_LOG permission
    """
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        # Fetch one extra entry to detect whether more pages exist.
        kwargs: dict[str, Any] = {"limit": limit + 1}

        if user_id is not None:
            kwargs["user"] = await client.fetch_user(parse_id(user_id, "user_id"))

        if action_type is not None:
            kwargs["action"] = discord.AuditLogAction(action_type)

        if before is not None:
            kwargs["before"] = discord.Object(parse_id(before, "before_id"))

        entries = []
        has_more = False

        async for entry in guild.audit_logs(**kwargs):
            if len(entries) >= limit:
                has_more = True
                break

            action_value = entry.action.value
            action_name = AUDIT_LOG_ACTION_NAMES.get(action_value, f"UNKNOWN_{action_value}")

            # Build changes from before/after diffs
            change_list: list[dict[str, str | None]] = []
            if entry.before and entry.after:
                for attr, old_val in entry.before:
                    new_val = getattr(entry.after, attr, None)
                    change_list.append(
                        {
                            "key": attr,
                            "old": str(old_val) if old_val is not None else None,
                            "new": str(new_val) if new_val is not None else None,
                        }
                    )

            target_id = None
            if entry.target is not None:
                target_id = str(entry.target.id)

            entries.append(
                {
                    "id": str(entry.id),
                    "action_type": action_value,
                    "action_type_name": action_name,
                    "user_id": str(entry.user.id) if entry.user else None,
                    "user_name": entry.user.name if entry.user else None,
                    "target_id": target_id,
                    "changes": change_list,
                    "reason": entry.reason,
                    "created_at": (entry.created_at.isoformat() if entry.created_at else None),
                }
            )

        return {
            "entries": entries,
            "has_more": has_more,
        }

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to view audit log: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


# ============================================================================
# Emoji Management Tools (Phase 1H)
# ============================================================================


async def _fetch_guild_emoji(guild: discord.Guild, emoji_id: int) -> discord.Emoji:
    """Fetch an emoji from guild by ID.

    Args:
        guild: Discord guild
        emoji_id: Emoji ID to find

    Returns:
        Discord Emoji object

    Raises:
        ValueError: If emoji not found
    """
    emojis = await guild.fetch_emojis()
    for emoji in emojis:
        if emoji.id == emoji_id:
            return emoji
    raise ValueError(f"Emoji {emoji_id} not found in guild")


async def list_emojis(
    client: commands.Bot,
    server_id: str,
) -> list[dict[str, Any]]:
    """List all custom emojis in the server.

    Args:
        client: Discord bot client
        server_id: Guild/server ID

    Returns:
        List of dicts with emoji info

    Raises:
        ValueError: If server not found
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        emojis = await guild.fetch_emojis()

        return [
            {
                "id": str(emoji.id),
                "name": emoji.name,
                "animated": emoji.animated,
                "available": emoji.available,
                "managed": emoji.managed,
                "require_colons": emoji.require_colons,
                "url": str(emoji.url),
            }
            for emoji in emojis
        ]

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to view emojis: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def create_emoji(
    client: commands.Bot,
    server_id: str,
    name: str,
    image: str,
    roles: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Upload a custom emoji.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        name: Emoji name (2-32 characters, alphanumeric + underscores)
        image: Base64-encoded image data (data URI)
        roles: Role IDs that can use this emoji (optional, None = all)
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with created emoji info

    Raises:
        ValueError: If server not found or invalid parameters
        PermissionError: If bot lacks permissions
    """
    # Validate name
    if len(name) < 2 or len(name) > 32:
        raise ValueError("Emoji name must be between 2 and 32 characters")

    if not re.match(r"^[a-zA-Z0-9_]+$", name):
        raise ValueError("Emoji name must only contain alphanumeric characters and underscores")

    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        # Parse role IDs if provided
        role_objects = []
        if roles:
            guild_roles = await guild.fetch_roles()
            for role_id in roles:
                role = discord.utils.get(guild_roles, id=parse_id(role_id, "role_id"))
                if role:
                    role_objects.append(role)

        # Convert base64 data URI to bytes
        image_bytes: bytes
        if image.startswith("data:"):
            # Strip data URI prefix (e.g. "data:image/png;base64,...")
            _, encoded = image.split(",", 1)
            image_bytes = base64.b64decode(encoded)
        else:
            image_bytes = base64.b64decode(image)

        emoji = await guild.create_custom_emoji(
            name=name,
            image=image_bytes,
            roles=role_objects,
            reason=reason,
        )

        return {
            "emoji_id": str(emoji.id),
            "name": emoji.name,
            "animated": emoji.animated,
            "available": emoji.available,
            "url": str(emoji.url),
        }

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to create emoji: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def delete_emoji(
    client: commands.Bot,
    server_id: str,
    emoji_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Delete a custom emoji.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        emoji_id: Emoji ID to delete
        reason: Optional reason (shown in audit log)

    Returns:
        Dict with deletion status

    Raises:
        ValueError: If server or emoji not found
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        emoji = await _fetch_guild_emoji(guild, parse_id(emoji_id, "emoji_id"))
        emoji_name = emoji.name
        emoji_id_str = str(emoji.id)

        await emoji.delete(reason=reason)

        return {
            "deleted": True,
            "emoji_name": emoji_name,
            "emoji_id": emoji_id_str,
        }

    except discord.NotFound as e:
        raise ValueError(f"Server {server_id} not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to delete emoji: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


async def list_threads(
    client: commands.Bot,
    server_id: str,
    channel_id: str | None = None,
    include_archived: bool = False,
) -> dict[str, Any]:
    """List active (and optionally archived) threads in a server or channel.

    Args:
        client: Discord bot client
        server_id: Guild/server ID
        channel_id: Optional channel ID to restrict to a single channel
        include_archived: Whether to also fetch archived threads

    Returns:
        Dict with a list of thread metadata and count

    Raises:
        ValueError: If server or channel not found
        PermissionError: If bot lacks permissions
    """
    try:
        guild = await client.fetch_guild(parse_id(server_id, "server_id"))

        channels_to_scan: list[discord.TextChannel] = []

        if channel_id is not None:
            ch = await client.fetch_channel(parse_id(channel_id, "channel_id"))
            if not isinstance(ch, discord.TextChannel):
                raise ValueError(f"Channel {channel_id} is not a text channel")
            channels_to_scan.append(ch)
        else:
            fetched = await guild.fetch_channels()
            channels_to_scan = [c for c in fetched if isinstance(c, discord.TextChannel)]

        threads: list[dict[str, Any]] = []

        for ch in channels_to_scan:
            # Active threads are available on the channel object
            for thread in ch.threads:
                threads.append(_thread_to_dict(thread, ch))

            if include_archived:
                async for thread in ch.archived_threads():
                    threads.append(_thread_to_dict(thread, ch))

        return {"threads": threads, "count": len(threads)}

    except discord.NotFound as e:
        raise ValueError("Server or channel not found") from e
    except discord.Forbidden as e:
        raise PermissionError(f"Missing permissions to list threads: {e}") from e
    except discord.HTTPException as e:
        raise RuntimeError(f"Discord API error: {e}") from e


def _thread_to_dict(thread: discord.Thread, parent: discord.TextChannel) -> dict[str, Any]:
    """Convert a Thread object to a serializable dict."""
    return {
        "id": str(thread.id),
        "name": thread.name,
        "parent_id": str(parent.id),
        "parent_name": parent.name,
        "archived": thread.archived,
        "message_count": thread.message_count,
        "member_count": thread.member_count,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
    }


# ============================================================================
# Bot Invite & Permission Utilities
# ============================================================================

_PERMISSION_FLAGS: list[tuple[int, str]] = [
    (0x00000001, "Create Instant Invite"),
    (0x00000002, "Kick Members"),
    (0x00000004, "Ban Members"),
    (0x00000008, "Administrator"),
    (0x00000010, "Manage Channels"),
    (0x00000020, "Manage Server"),
    (0x00000040, "Add Reactions"),
    (0x00000080, "View Audit Log"),
    (0x00000400, "View Channels"),
    (0x00000800, "Send Messages"),
    (0x00002000, "Manage Messages"),
    (0x00004000, "Embed Links"),
    (0x00008000, "Attach Files"),
    (0x00010000, "Read Message History"),
    (0x00020000, "Mention Everyone"),
    (0x00040000, "Use External Emojis"),
    (0x00100000, "Connect"),
    (0x00200000, "Speak"),
    (0x00400000, "Mute Members"),
    (0x00800000, "Deafen Members"),
    (0x01000000, "Move Members"),
    (0x04000000, "Manage Nicknames"),
    (0x08000000, "Manage Roles"),
    (0x10000000, "Manage Webhooks"),
    (0x40000000, "Manage Expressions"),
    (0x0000100000000000, "Moderate Members"),
]

PERMISSION_PRESETS: dict[str, int] = {
    "read_only": 0x00000400 | 0x00010000,  # View Channels + Read Message History = 66560
    "moderate": (
        0x00000400  # View Channels
        | 0x00010000  # Read Message History
        | 0x00002000  # Manage Messages
        | 0x00000002  # Kick Members
        | 0x00000004  # Ban Members
    ),
    "full": (
        0x00000400  # View Channels
        | 0x00010000  # Read Message History
        | 0x00000800  # Send Messages
        | 0x00002000  # Manage Messages
        | 0x00000040  # Add Reactions
        | 0x00000080  # View Audit Log
        | 0x00000020  # Manage Server
        | 0x08000000  # Manage Roles
        | 0x00000010  # Manage Channels
        | 0x00000002  # Kick Members
        | 0x00000004  # Ban Members
        | 0x00000001  # Create Instant Invite
        | 0x04000000  # Manage Nicknames
        | 0x40000000  # Manage Expressions
        | 0x0000100000000000  # Moderate Members
        | 0x00004000  # Embed Links
        | 0x00008000  # Attach Files
    ),
}


def _describe_permissions(value: int) -> list[str]:
    """Return human-readable names for each set permission bit."""
    names: list[str] = []
    for bit, name in _PERMISSION_FLAGS:
        if value & bit:
            names.append(name)
    return names


async def generate_invite_url(
    client: commands.Bot,
    preset: str | None = None,
    permissions: int | None = None,
) -> dict[str, Any]:
    """Generate an OAuth2 bot invite URL.

    Uses *preset* to look up a predefined permission value, or accepts
    a raw *permissions* integer.  Falls back to ``read_only`` when neither
    is provided.
    """
    # Resolve application / client ID
    app_id: str | None = None
    if client.user is not None:
        app_id = str(client.user.id)
    if app_id is None:
        app_id = os.environ.get("DISCORD_CLIENT_ID")
    if app_id is None:
        raise ValueError("Cannot determine application ID. Ensure the bot is logged in or set DISCORD_CLIENT_ID.")

    # Resolve permission value
    if permissions is not None:
        perm_value = permissions
        preset_used = None
    elif preset is not None:
        if preset not in PERMISSION_PRESETS:
            raise ValueError(f"Unknown preset {preset!r}. Available: {', '.join(sorted(PERMISSION_PRESETS))}")
        perm_value = PERMISSION_PRESETS[preset]
        preset_used = preset
    else:
        perm_value = PERMISSION_PRESETS["read_only"]
        preset_used = "read_only"

    url = f"https://discord.com/oauth2/authorize?client_id={app_id}&scope=bot&permissions={perm_value}"

    return {
        "url": url,
        "permissions_value": perm_value,
        "permissions": _describe_permissions(perm_value),
        "preset": preset_used,
    }
