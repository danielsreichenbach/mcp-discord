"""MCP server for Discord operations using FastMCP."""

from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Any, cast

from mcp.server.mcpserver import Context, MCPServer

from . import __version__, handlers, resources
from .client import DiscordContext, configure_windows_stdout_encoding, discord_lifespan
from .handlers import _SENTINEL, ChannelPosition, RolePosition

configure_windows_stdout_encoding()

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("discord-mcp")
logger.setLevel(logging.INFO)

mcp = MCPServer[DiscordContext]("discord-server", lifespan=discord_lifespan, version=__version__)


def _get_bot(ctx: Context) -> DiscordContext:
    # The SDK's Context TypeVar defaults LifespanContextT to dict[str, Any];
    # this server's lifespan yields DiscordContext.
    return cast(DiscordContext, ctx.request_context.lifespan_context)


# Resources (read-only data)


@mcp.resource("discord://servers/{server_id}")
async def get_server_info_resource(server_id: str, ctx: Context) -> str:
    info = await resources.get_server_info(_get_bot(ctx).bot, server_id)
    return json.dumps(info)


@mcp.resource("discord://servers/{server_id}/channels")
async def get_channels_resource(server_id: str, ctx: Context) -> str:
    channels = await resources.get_channels(_get_bot(ctx).bot, server_id)
    return json.dumps(channels)


@mcp.resource("discord://servers/{server_id}/members")
async def list_members_resource(server_id: str, ctx: Context) -> str:
    members = await resources.list_members(_get_bot(ctx).bot, server_id)
    return json.dumps(members)


@mcp.resource("discord://servers/{server_id}/roles")
async def list_roles_resource(server_id: str, ctx: Context) -> str:
    roles = await resources.list_roles(_get_bot(ctx).bot, server_id)
    return json.dumps(roles)


@mcp.resource("discord://channels/{channel_id}/messages")
async def read_messages_resource(channel_id: str, ctx: Context) -> str:
    messages = await resources.read_messages(_get_bot(ctx).bot, channel_id)
    return json.dumps(messages)


# Tools (actions)


@mcp.tool()
async def send_message(channel_id: str, content: str, ctx: Context) -> dict[str, Any]:
    """Send a message to a specific channel."""
    return await handlers.send_message(_get_bot(ctx).bot, channel_id, content)


@mcp.tool()
async def add_role(server_id: str, user_id: str, role_id: str, ctx: Context) -> dict[str, Any]:
    """Add a role to a user in a server."""
    return await handlers.add_role(_get_bot(ctx).bot, server_id, user_id, role_id)


@mcp.tool()
async def remove_role(server_id: str, user_id: str, role_id: str, ctx: Context) -> dict[str, Any]:
    """Remove a role from a user in a server."""
    return await handlers.remove_role(_get_bot(ctx).bot, server_id, user_id, role_id)


@mcp.tool()
async def create_text_channel(
    server_id: str,
    name: str,
    ctx: Context,
    category_id: str | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    """Create a new text channel in a server."""
    return await handlers.create_text_channel(_get_bot(ctx).bot, server_id, name, category_id, topic)


@mcp.tool()
async def delete_channel(channel_id: str, ctx: Context, reason: str | None = None) -> dict[str, Any]:
    """Delete a channel."""
    return await handlers.delete_channel(_get_bot(ctx).bot, channel_id, reason)


@mcp.tool()
async def add_reaction(channel_id: str, message_id: str, emoji: str, ctx: Context) -> dict[str, Any]:
    """Add a reaction to a message."""
    return await handlers.add_reaction(_get_bot(ctx).bot, channel_id, message_id, emoji)


@mcp.tool()
async def add_multiple_reactions(channel_id: str, message_id: str, emojis: list[str], ctx: Context) -> dict[str, Any]:
    """Add multiple reactions to a message."""
    return await handlers.add_multiple_reactions(_get_bot(ctx).bot, channel_id, message_id, emojis)


@mcp.tool()
async def remove_reaction(channel_id: str, message_id: str, emoji: str, ctx: Context) -> dict[str, Any]:
    """Remove the bot's reaction from a message."""
    return await handlers.remove_reaction(_get_bot(ctx).bot, channel_id, message_id, emoji)


@mcp.tool()
async def moderate_message(
    channel_id: str,
    message_id: str,
    reason: str,
    ctx: Context,
    timeout_minutes: int | None = None,
) -> dict[str, Any]:
    """Delete a message and optionally timeout the author."""
    return await handlers.moderate_message(_get_bot(ctx).bot, channel_id, message_id, reason, timeout_minutes)


# ============================================================================
# Member Moderation Tools (Phase 1A)
# ============================================================================


@mcp.tool()
async def kick_member(
    server_id: str,
    user_id: str,
    ctx: Context,
    reason: str | None = None,
) -> dict[str, Any]:
    """Kick a member from the server."""
    return await handlers.kick_member(_get_bot(ctx).bot, server_id, user_id, reason)


@mcp.tool()
async def ban_member(
    server_id: str,
    user_id: str,
    ctx: Context,
    reason: str | None = None,
    delete_message_days: int = 0,
) -> dict[str, Any]:
    """Ban a user from the server. Optionally delete their recent messages."""
    return await handlers.ban_member(
        _get_bot(ctx).bot,
        server_id,
        user_id,
        reason,
        delete_message_days,
    )


@mcp.tool()
async def unban_member(
    server_id: str,
    user_id: str,
    ctx: Context,
    reason: str | None = None,
) -> dict[str, Any]:
    """Remove a ban for a user."""
    return await handlers.unban_member(_get_bot(ctx).bot, server_id, user_id, reason)


@mcp.tool()
async def list_bans(server_id: str, ctx: Context) -> list[dict[str, Any]]:
    """List all banned users in a server."""
    return await handlers.list_bans(_get_bot(ctx).bot, server_id)


@mcp.tool()
async def edit_member(
    server_id: str,
    user_id: str,
    ctx: Context,
    nick: str | None = None,
    timeout_minutes: int | None = None,
    mute: bool | None = None,
    deafen: bool | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Modify member properties: nickname, timeout, voice mute/deafen.

    Omit a field (or pass null) to leave it unchanged. Pass an empty string
    for nick to clear the nickname; use remove_timeout to clear a timeout."""
    timeout_until: str | None | object = _SENTINEL
    if timeout_minutes is not None:
        timeout_until = (dt.datetime.now(dt.UTC) + dt.timedelta(minutes=timeout_minutes)).isoformat()

    return await handlers.edit_member(
        _get_bot(ctx).bot,
        server_id,
        user_id,
        nick=nick if nick is not None else _SENTINEL,
        timeout_until=timeout_until,
        mute=mute,
        deafen=deafen,
        reason=reason,
    )


@mcp.tool()
async def remove_timeout(
    server_id: str,
    user_id: str,
    ctx: Context,
    reason: str | None = None,
) -> dict[str, Any]:
    """Remove a timeout from a member."""
    return await handlers.remove_timeout(_get_bot(ctx).bot, server_id, user_id, reason)


# ============================================================================
# Role Management Tools (Phase 1B)
# ============================================================================


@mcp.tool()
async def create_role(
    server_id: str,
    name: str,
    ctx: Context,
    permissions: int | None = None,
    color: int | None = None,
    hoist: bool = False,
    mentionable: bool = False,
    reason: str | None = None,
) -> dict[str, Any]:
    """Create a new role in the server.

    permissions: bitwise permission value (see discord.Permissions); color: RGB
    integer value (0xRRGGBB)."""
    return await handlers.create_role(
        _get_bot(ctx).bot,
        server_id,
        name,
        permissions,
        color,
        hoist,
        mentionable,
        reason,
    )


@mcp.tool()
async def edit_role(
    server_id: str,
    role_id: str,
    ctx: Context,
    name: str | None = None,
    permissions: int | None = None,
    color: int | None = None,
    hoist: bool | None = None,
    mentionable: bool | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Modify an existing role."""
    return await handlers.edit_role(
        _get_bot(ctx).bot,
        server_id,
        role_id,
        name,
        permissions,
        color,
        hoist,
        mentionable,
        reason,
    )


@mcp.tool()
async def delete_role(
    server_id: str,
    role_id: str,
    ctx: Context,
    reason: str | None = None,
) -> dict[str, Any]:
    """Delete a role from the server."""
    return await handlers.delete_role(_get_bot(ctx).bot, server_id, role_id, reason)


@mcp.tool()
async def reorder_roles(
    server_id: str,
    role_positions: list[RolePosition],
    ctx: Context,
    reason: str | None = None,
) -> dict[str, Any]:
    """Change the position/order of roles. Each item: {id: role_id, position: new_position}."""
    return await handlers.reorder_roles(_get_bot(ctx).bot, server_id, role_positions, reason)


# ============================================================================
# Channel Management Tools (Phase 1C)
# ============================================================================


@mcp.tool()
async def edit_channel(
    channel_id: str,
    ctx: Context,
    name: str | None = None,
    topic: str | None = None,
    nsfw: bool | None = None,
    slowmode_delay: int | None = None,
    default_auto_archive_duration: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Modify channel properties: name, topic, NSFW, slowmode.

    default_auto_archive_duration: thread auto-archive minutes, one of
    60, 1440, 4320, 10080."""
    return await handlers.edit_channel(
        _get_bot(ctx).bot,
        channel_id,
        name,
        topic,
        nsfw,
        slowmode_delay,
        default_auto_archive_duration,
        reason=reason,
    )


@mcp.tool()
async def create_category(
    server_id: str,
    name: str,
    ctx: Context,
    position: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Create a new channel category."""
    return await handlers.create_category(_get_bot(ctx).bot, server_id, name, position, reason)


@mcp.tool()
async def create_voice_channel(
    server_id: str,
    name: str,
    ctx: Context,
    category_id: str | None = None,
    bitrate: int | None = None,
    user_limit: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Create a new voice channel.

    bitrate: bits per second (8000-128000); user_limit: max users (0-99, 0 = unlimited)."""
    return await handlers.create_voice_channel(
        _get_bot(ctx).bot,
        server_id,
        name,
        category_id,
        bitrate,
        user_limit,
        reason,
    )


@mcp.tool()
async def reorder_channels(
    server_id: str,
    channel_positions: list[ChannelPosition],
    ctx: Context,
    reason: str | None = None,
) -> dict[str, Any]:
    """Change channel positions. Each item: {id: channel_id, position: new_position, parent_id: category_id}."""
    return await handlers.reorder_channels(_get_bot(ctx).bot, server_id, channel_positions, reason)


# ============================================================================
# Invite Management Tools (Phase 1D)
# ============================================================================


@mcp.tool()
async def create_invite(
    channel_id: str,
    ctx: Context,
    max_age: int = 86400,
    max_uses: int = 0,
    temporary: bool = False,
    unique: bool = False,
    reason: str | None = None,
) -> dict[str, Any]:
    """Create a channel invite. max_age in seconds (0=never), max_uses (0=unlimited)."""
    return await handlers.create_invite(_get_bot(ctx).bot, channel_id, max_age, max_uses, temporary, unique, reason)


@mcp.tool()
async def list_server_invites(server_id: str, ctx: Context) -> list[dict[str, Any]]:
    """List all invites for a server."""
    return await handlers.list_server_invites(_get_bot(ctx).bot, server_id)


@mcp.tool()
async def list_channel_invites(channel_id: str, ctx: Context) -> list[dict[str, Any]]:
    """List all invites for a specific channel."""
    return await handlers.list_channel_invites(_get_bot(ctx).bot, channel_id)


@mcp.tool()
async def delete_invite(invite_code: str, ctx: Context, reason: str | None = None) -> dict[str, Any]:
    """Delete/revoke an invite by its code."""
    return await handlers.delete_invite(_get_bot(ctx).bot, invite_code, reason)


# ============================================================================
# Message Management Tools (Phase 1D continued)
# ============================================================================


@mcp.tool()
async def edit_message(
    channel_id: str,
    message_id: str,
    content: str,
    ctx: Context,
) -> dict[str, Any]:
    """Edit a message sent by the bot."""
    return await handlers.edit_message(_get_bot(ctx).bot, channel_id, message_id, content)


@mcp.tool()
async def delete_message(
    channel_id: str,
    message_id: str,
    ctx: Context,
) -> dict[str, Any]:
    """Delete a single message."""
    return await handlers.delete_message(_get_bot(ctx).bot, channel_id, message_id)


@mcp.tool()
async def bulk_delete_messages(
    channel_id: str,
    message_ids: list[str],
    ctx: Context,
    reason: str | None = None,
) -> dict[str, Any]:
    """Delete multiple messages at once (2-100 messages, must be less than 14 days old)."""
    return await handlers.bulk_delete_messages(_get_bot(ctx).bot, channel_id, message_ids, reason)


@mcp.tool()
async def pin_message(
    channel_id: str,
    message_id: str,
    ctx: Context,
    reason: str | None = None,
) -> dict[str, Any]:
    """Pin a message to the channel."""
    return await handlers.pin_message(_get_bot(ctx).bot, channel_id, message_id, reason)


@mcp.tool()
async def unpin_message(
    channel_id: str,
    message_id: str,
    ctx: Context,
    reason: str | None = None,
) -> dict[str, Any]:
    """Unpin a message from the channel."""
    return await handlers.unpin_message(_get_bot(ctx).bot, channel_id, message_id, reason)


@mcp.tool()
async def list_pinned_messages(channel_id: str, ctx: Context) -> list[dict[str, Any]]:
    """List all pinned messages in a channel."""
    return await handlers.list_pinned_messages(_get_bot(ctx).bot, channel_id)


# ============================================================================
# Audit Log Tools (Phase 1G)
# ============================================================================


@mcp.tool()
async def get_audit_log(
    server_id: str,
    ctx: Context,
    user_id: str | None = None,
    action_type: int | None = None,
    before: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Retrieve server audit logs.

    Filter by user_id (moderator) or action_type (audit log event int, e.g.
    20 kick, 22 ban, 30 role create; full list at
    discord.com/developers/docs/resources/audit-log). Pass the last entry's
    id as before to page further."""
    return await handlers.get_audit_log(_get_bot(ctx).bot, server_id, user_id, action_type, before, limit=limit)


# ============================================================================
# Emoji Management Tools (Phase 1H)
# ============================================================================


@mcp.tool()
async def list_emojis(server_id: str, ctx: Context) -> list[dict[str, Any]]:
    """List all custom emojis in the server."""
    return await handlers.list_emojis(_get_bot(ctx).bot, server_id)


@mcp.tool()
async def create_emoji(
    server_id: str,
    name: str,
    image: str,
    ctx: Context,
    roles: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Upload a custom emoji. Image must be base64 data URI (data:image/png;base64,...)."""
    return await handlers.create_emoji(_get_bot(ctx).bot, server_id, name, image, roles, reason)


@mcp.tool()
async def delete_emoji(
    server_id: str,
    emoji_id: str,
    ctx: Context,
    reason: str | None = None,
) -> dict[str, Any]:
    """Delete a custom emoji."""
    return await handlers.delete_emoji(_get_bot(ctx).bot, server_id, emoji_id, reason)


# ============================================================================
# Thread Discovery Tools
# ============================================================================


@mcp.tool()
async def list_threads(
    server_id: str,
    ctx: Context,
    channel_id: str | None = None,
    include_archived: bool = False,
) -> dict[str, Any]:
    """List active (and optionally archived) threads in a server or channel."""
    return await handlers.list_threads(
        _get_bot(ctx).bot, server_id, channel_id=channel_id, include_archived=include_archived
    )


# ============================================================================
# Bot Invite & Permission Tools
# ============================================================================


@mcp.tool()
async def generate_invite_url(
    ctx: Context,
    preset: str | None = None,
    permissions: int | None = None,
) -> dict[str, Any]:
    """Generate an OAuth2 bot invite URL.

    preset: read_only, moderate, or full; or pass a raw permissions bitwise
    value. Defaults to read_only."""
    return await handlers.generate_invite_url(_get_bot(ctx).bot, preset=preset, permissions=permissions)


@mcp.tool()
async def list_bot_guilds(ctx: Context) -> list[dict[str, Any]]:
    """List all guilds the bot is in with read-access status."""
    return await resources.list_bot_guilds(_get_bot(ctx).bot)


@mcp.tool()
async def audit_bot_permissions(server_id: str, ctx: Context) -> dict[str, Any]:
    """Audit bot permissions in a guild against permission presets."""
    return await resources.audit_bot_permissions(_get_bot(ctx).bot, server_id)


# Read tools (wrappers around resources for tool access)


@mcp.tool()
async def list_servers(ctx: Context) -> list[dict[str, Any]]:
    """List all servers the bot has access to."""
    return await resources.list_servers(_get_bot(ctx).bot)


@mcp.tool()
async def get_server_info(server_id: str, ctx: Context) -> dict[str, Any]:
    """Get information about a server."""
    return await resources.get_server_info(_get_bot(ctx).bot, server_id)


@mcp.tool()
async def get_channels(server_id: str, ctx: Context) -> list[dict[str, Any]]:
    """List all channels in a server."""
    return await resources.get_channels(_get_bot(ctx).bot, server_id)


@mcp.tool()
async def list_members(server_id: str, ctx: Context, limit: int = 100) -> list[dict[str, Any]]:
    """List members in a server."""
    return await resources.list_members(_get_bot(ctx).bot, server_id, limit)


@mcp.tool()
async def list_roles(server_id: str, ctx: Context) -> list[dict[str, Any]]:
    """List all roles in a server."""
    return await resources.list_roles(_get_bot(ctx).bot, server_id)


@mcp.tool()
async def read_messages(
    channel_id: str,
    ctx: Context,
    limit: int = 50,
    before: str | None = None,
    after: str | None = None,
    oldest_first: bool = False,
) -> list[dict[str, Any]]:
    """Read messages from a channel or thread. Supports pagination via before/after message IDs."""
    return await resources.read_messages(
        _get_bot(ctx).bot, channel_id, limit, before=before, after=after, oldest_first=oldest_first
    )


@mcp.tool()
async def get_user_info(user_id: str, ctx: Context) -> dict[str, Any]:
    """Get information about a Discord user."""
    return await resources.get_user_info(_get_bot(ctx).bot, user_id)


def main() -> None:
    """Run the MCP server."""
    mcp.run()
