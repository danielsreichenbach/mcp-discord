"""MCP server for Discord operations using FastMCP."""

from __future__ import annotations

import datetime as dt
import json
import logging

from mcp.server.fastmcp import Context, FastMCP

from . import handlers, resources
from .client import DiscordContext, configure_windows_stdout_encoding, discord_lifespan
from .handlers import _SENTINEL

configure_windows_stdout_encoding()

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("discord-mcp")
logger.setLevel(logging.INFO)

mcp = FastMCP("discord-server", lifespan=discord_lifespan)


def _get_bot(ctx: Context) -> DiscordContext:
    return ctx.request_context.lifespan_context


# Resources (read-only data)


@mcp.resource("discord://servers")
async def list_servers_resource() -> str:
    ctx = mcp.get_context()
    servers = await resources.list_servers(_get_bot(ctx).bot)
    return json.dumps(servers, indent=2)


@mcp.resource("discord://servers/{server_id}")
async def get_server_info_resource(server_id: str) -> str:
    ctx = mcp.get_context()
    info = await resources.get_server_info(_get_bot(ctx).bot, server_id)
    return json.dumps(info, indent=2)


@mcp.resource("discord://servers/{server_id}/channels")
async def get_channels_resource(server_id: str) -> str:
    ctx = mcp.get_context()
    channels = await resources.get_channels(_get_bot(ctx).bot, server_id)
    return json.dumps(channels, indent=2)


@mcp.resource("discord://servers/{server_id}/members")
async def list_members_resource(server_id: str) -> str:
    ctx = mcp.get_context()
    members = await resources.list_members(_get_bot(ctx).bot, server_id)
    return json.dumps(members, indent=2)


@mcp.resource("discord://servers/{server_id}/roles")
async def list_roles_resource(server_id: str) -> str:
    ctx = mcp.get_context()
    roles = await resources.list_roles(_get_bot(ctx).bot, server_id)
    return json.dumps(roles, indent=2)


@mcp.resource("discord://channels/{channel_id}/messages")
async def read_messages_resource(channel_id: str) -> str:
    ctx = mcp.get_context()
    messages = await resources.read_messages(_get_bot(ctx).bot, channel_id)
    return json.dumps(messages, indent=2)


# Tools (actions)


@mcp.tool()
async def send_message(channel_id: str, content: str, ctx: Context) -> str:
    result = await handlers.send_message(_get_bot(ctx).bot, channel_id, content)
    return f"Message sent successfully. Message ID: {result['message_id']}"


@mcp.tool()
async def add_role(server_id: str, user_id: str, role_id: str, ctx: Context) -> str:
    result = await handlers.add_role(_get_bot(ctx).bot, server_id, user_id, role_id)
    return f"Added role {result['role_name']} to user {result['user_name']}"


@mcp.tool()
async def remove_role(server_id: str, user_id: str, role_id: str, ctx: Context) -> str:
    result = await handlers.remove_role(_get_bot(ctx).bot, server_id, user_id, role_id)
    return f"Removed role {result['role_name']} from user {result['user_name']}"


@mcp.tool()
async def create_text_channel(
    server_id: str,
    name: str,
    ctx: Context,
    category_id: str | None = None,
    topic: str | None = None,
) -> str:
    result = await handlers.create_text_channel(_get_bot(ctx).bot, server_id, name, category_id, topic)
    return f"Created text channel #{result['channel_name']} (ID: {result['channel_id']})"


@mcp.tool()
async def delete_channel(channel_id: str, ctx: Context, reason: str | None = None) -> str:
    await handlers.delete_channel(_get_bot(ctx).bot, channel_id, reason)
    return "Deleted channel successfully"


@mcp.tool()
async def add_reaction(channel_id: str, message_id: str, emoji: str, ctx: Context) -> str:
    await handlers.add_reaction(_get_bot(ctx).bot, channel_id, message_id, emoji)
    return f"Added reaction {emoji} to message"


@mcp.tool()
async def add_multiple_reactions(channel_id: str, message_id: str, emojis: list[str], ctx: Context) -> str:
    await handlers.add_multiple_reactions(_get_bot(ctx).bot, channel_id, message_id, emojis)
    return f"Added reactions: {', '.join(emojis)} to message"


@mcp.tool()
async def remove_reaction(channel_id: str, message_id: str, emoji: str, ctx: Context) -> str:
    await handlers.remove_reaction(_get_bot(ctx).bot, channel_id, message_id, emoji)
    return f"Removed reaction {emoji} from message"


@mcp.tool()
async def moderate_message(
    channel_id: str,
    message_id: str,
    reason: str,
    ctx: Context,
    timeout_minutes: int | None = None,
) -> str:
    result = await handlers.moderate_message(_get_bot(ctx).bot, channel_id, message_id, reason, timeout_minutes)
    if result["timeout_applied"]:
        return f"Message deleted and user timed out for {result['timeout_minutes']} minutes."
    return "Message deleted successfully."


# ============================================================================
# Member Moderation Tools (Phase 1A)
# ============================================================================


@mcp.tool()
async def kick_member(
    server_id: str,
    user_id: str,
    ctx: Context,
    reason: str | None = None,
) -> str:
    """Kick a member from the server."""
    result = await handlers.kick_member(_get_bot(ctx).bot, server_id, user_id, reason)
    return f"Kicked user {result['user_name']} (ID: {result['user_id']}). Reason: {result.get('reason', 'None')}"


@mcp.tool()
async def ban_member(
    server_id: str,
    user_id: str,
    ctx: Context,
    reason: str | None = None,
    delete_message_days: int = 0,
) -> str:
    """Ban a user from the server. Optionally delete their recent messages."""
    result = await handlers.ban_member(
        _get_bot(ctx).bot, server_id, user_id, reason, delete_message_days,
    )
    days = result['messages_deleted_days']
    return f"Banned user {result['user_name']} (ID: {result['user_id']}). Deleted {days} days of messages."


@mcp.tool()
async def unban_member(
    server_id: str,
    user_id: str,
    ctx: Context,
    reason: str | None = None,
) -> str:
    """Remove a ban for a user."""
    result = await handlers.unban_member(_get_bot(ctx).bot, server_id, user_id, reason)
    return f"Unbanned user ID: {result['user_id']}. Reason: {result.get('reason', 'None')}"


@mcp.tool()
async def list_bans(server_id: str, ctx: Context) -> str:
    """List all banned users in a server."""
    result = await handlers.list_bans(_get_bot(ctx).bot, server_id)
    if not result:
        return "No bans in this server."
    lines = [f"- {b['user_name']} (ID: {b['user_id']}): {b.get('reason', 'No reason')}" for b in result]
    return f"Banned users ({len(result)}):\n" + "\n".join(lines)


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
) -> str:
    """Modify member properties: nickname, timeout, voice mute/deafen."""
    timeout_until: str | None | object = _SENTINEL
    if timeout_minutes is not None:
        timeout_until = (
            dt.datetime.now(dt.UTC) + dt.timedelta(minutes=timeout_minutes)
        ).isoformat()

    result = await handlers.edit_member(
        _get_bot(ctx).bot, server_id, user_id,
        nick=nick if nick is not None else _SENTINEL,
        timeout_until=timeout_until,
        mute=mute,
        deafen=deafen,
        reason=reason,
    )
    return f"Updated member {result['user_name']}. Changes: {', '.join(result['changes'])}"


@mcp.tool()
async def remove_timeout(
    server_id: str,
    user_id: str,
    ctx: Context,
    reason: str | None = None,
) -> str:
    """Remove a timeout from a member."""
    result = await handlers.remove_timeout(_get_bot(ctx).bot, server_id, user_id, reason)
    return f"Removed timeout from user {result['user_name']} (ID: {result['user_id']})"


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
) -> str:
    """Create a new role in the server."""
    result = await handlers.create_role(
        _get_bot(ctx).bot, server_id, name, permissions, color, hoist, mentionable, reason,
    )
    return f"Created role '{result['role_name']}' (ID: {result['role_id']}) at position {result['position']}"


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
) -> str:
    """Modify an existing role."""
    result = await handlers.edit_role(
        _get_bot(ctx).bot, server_id, role_id, name, permissions, color, hoist, mentionable, reason,
    )
    return f"Updated role '{result['role_name']}'. Changes: {', '.join(result['changes'])}"


@mcp.tool()
async def delete_role(
    server_id: str,
    role_id: str,
    ctx: Context,
    reason: str | None = None,
) -> str:
    """Delete a role from the server."""
    result = await handlers.delete_role(_get_bot(ctx).bot, server_id, role_id, reason)
    return f"Deleted role '{result['role_name']}' (ID: {result['role_id']})"


@mcp.tool()
async def reorder_roles(
    server_id: str,
    role_positions: list[dict[str, int]],
    ctx: Context,
    reason: str | None = None,
) -> str:
    """Change the position/order of roles. Provide list of {id: role_id, position: new_position}."""
    result = await handlers.reorder_roles(_get_bot(ctx).bot, server_id, role_positions, reason)
    lines = [f"- {r['name']}: position {r['position']}" for r in result['roles']]
    return "Reordered roles:\n" + "\n".join(lines)


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
    reason: str | None = None,
) -> str:
    """Modify channel properties: name, topic, NSFW, slowmode."""
    result = await handlers.edit_channel(
        _get_bot(ctx).bot, channel_id, name, topic, nsfw, slowmode_delay, reason=reason,
    )
    return f"Updated channel #{result['channel_name']}. Changes: {', '.join(result['changes'])}"


@mcp.tool()
async def create_category(
    server_id: str,
    name: str,
    ctx: Context,
    position: int | None = None,
    reason: str | None = None,
) -> str:
    """Create a new channel category."""
    result = await handlers.create_category(_get_bot(ctx).bot, server_id, name, position, reason)
    return (
        f"Created category '{result['category_name']}'"
        f" (ID: {result['category_id']}) at position {result['position']}"
    )


@mcp.tool()
async def create_voice_channel(
    server_id: str,
    name: str,
    ctx: Context,
    category_id: str | None = None,
    bitrate: int | None = None,
    user_limit: int | None = None,
    reason: str | None = None,
) -> str:
    """Create a new voice channel."""
    result = await handlers.create_voice_channel(
        _get_bot(ctx).bot, server_id, name, category_id, bitrate, user_limit, reason,
    )
    return (
        f"Created voice channel '{result['channel_name']}'"
        f" (ID: {result['channel_id']}, bitrate: {result['bitrate']})"
    )


@mcp.tool()
async def reorder_channels(
    server_id: str,
    channel_positions: list[dict[str, int | str | None]],
    ctx: Context,
    reason: str | None = None,
) -> str:
    """Change channel positions. Provide list of {id, position, parent_id}."""
    result = await handlers.reorder_channels(_get_bot(ctx).bot, server_id, channel_positions, reason)
    return f"Reordered {len(result['channels'])} channels"


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
) -> str:
    """Create a channel invite. max_age in seconds (0=never), max_uses (0=unlimited)."""
    result = await handlers.create_invite(_get_bot(ctx).bot, channel_id, max_age, max_uses, temporary, unique, reason)
    return f"Created invite: {result['url']} (max uses: {result['max_uses']}, expires in: {result['max_age']}s)"


@mcp.tool()
async def list_server_invites(server_id: str, ctx: Context) -> str:
    """List all invites for a server."""
    result = await handlers.list_server_invites(_get_bot(ctx).bot, server_id)
    if not result:
        return "No active invites in this server."
    lines = [
        f"- {inv['url']} (channel: {inv['channel_name']}, uses: {inv['uses']}/{inv['max_uses'] or '∞'})"
        for inv in result
    ]
    return f"Server invites ({len(result)}):\n" + "\n".join(lines)


@mcp.tool()
async def list_channel_invites(channel_id: str, ctx: Context) -> str:
    """List all invites for a specific channel."""
    result = await handlers.list_channel_invites(_get_bot(ctx).bot, channel_id)
    if not result:
        return "No active invites for this channel."
    lines = [f"- {inv['url']} (uses: {inv['uses']}/{inv['max_uses'] or '∞'})" for inv in result]
    return f"Channel invites ({len(result)}):\n" + "\n".join(lines)


@mcp.tool()
async def delete_invite(invite_code: str, ctx: Context, reason: str | None = None) -> str:
    """Delete/revoke an invite by its code."""
    result = await handlers.delete_invite(_get_bot(ctx).bot, invite_code, reason)
    return f"Deleted invite: {result['code']}"


# ============================================================================
# Message Management Tools (Phase 1D continued)
# ============================================================================


@mcp.tool()
async def edit_message(
    channel_id: str,
    message_id: str,
    content: str,
    ctx: Context,
) -> str:
    """Edit a message sent by the bot."""
    result = await handlers.edit_message(_get_bot(ctx).bot, channel_id, message_id, content)
    return f"Edited message {result['message_id']}"


@mcp.tool()
async def delete_message(
    channel_id: str,
    message_id: str,
    ctx: Context,
) -> str:
    """Delete a single message."""
    result = await handlers.delete_message(_get_bot(ctx).bot, channel_id, message_id)
    return f"Deleted message {result['message_id']}"


@mcp.tool()
async def bulk_delete_messages(
    channel_id: str,
    message_ids: list[str],
    ctx: Context,
    reason: str | None = None,
) -> str:
    """Delete multiple messages at once (2-100 messages, must be less than 14 days old)."""
    result = await handlers.bulk_delete_messages(_get_bot(ctx).bot, channel_id, message_ids, reason)
    return f"Deleted {result['deleted_count']} messages"


@mcp.tool()
async def pin_message(
    channel_id: str,
    message_id: str,
    ctx: Context,
    reason: str | None = None,
) -> str:
    """Pin a message to the channel."""
    result = await handlers.pin_message(_get_bot(ctx).bot, channel_id, message_id, reason)
    return f"Pinned message {result['message_id']}"


@mcp.tool()
async def unpin_message(
    channel_id: str,
    message_id: str,
    ctx: Context,
    reason: str | None = None,
) -> str:
    """Unpin a message from the channel."""
    result = await handlers.unpin_message(_get_bot(ctx).bot, channel_id, message_id, reason)
    return f"Unpinned message {result['message_id']}"


@mcp.tool()
async def list_pinned_messages(channel_id: str, ctx: Context) -> str:
    """List all pinned messages in a channel."""
    result = await handlers.list_pinned_messages(_get_bot(ctx).bot, channel_id)
    if not result:
        return "No pinned messages in this channel."
    lines = [f"- [{msg['message_id']}] {msg['author_name']}: {msg['content'][:50]}..." for msg in result]
    return f"Pinned messages ({len(result)}):\n" + "\n".join(lines)


# ============================================================================
# Audit Log Tools (Phase 1G)
# ============================================================================


@mcp.tool()
async def get_audit_log(
    server_id: str,
    ctx: Context,
    user_id: str | None = None,
    action_type: int | None = None,
    limit: int = 50,
) -> str:
    """Retrieve server audit logs. Filter by user_id or action_type (see Discord docs for action types)."""
    result = await handlers.get_audit_log(_get_bot(ctx).bot, server_id, user_id, action_type, limit=limit)
    if not result['entries']:
        return "No audit log entries found."
    lines = []
    for entry in result['entries'][:20]:  # Limit display to 20
        lines.append(f"- [{entry['action_type_name']}] by {entry['user_name']}: {entry.get('reason', 'No reason')}")
    more = f" (+ {len(result['entries']) - 20} more)" if len(result['entries']) > 20 else ""
    return f"Audit Log ({len(result['entries'])} entries{more}):\n" + "\n".join(lines)


# ============================================================================
# Emoji Management Tools (Phase 1H)
# ============================================================================


@mcp.tool()
async def list_emojis(server_id: str, ctx: Context) -> str:
    """List all custom emojis in the server."""
    result = await handlers.list_emojis(_get_bot(ctx).bot, server_id)
    if not result:
        return "No custom emojis in this server."
    lines = [f"- :{e['name']}: (ID: {e['id']}, animated: {e['animated']})" for e in result]
    return f"Custom emojis ({len(result)}):\n" + "\n".join(lines)


@mcp.tool()
async def create_emoji(
    server_id: str,
    name: str,
    image: str,
    ctx: Context,
    roles: list[str] | None = None,
    reason: str | None = None,
) -> str:
    """Upload a custom emoji. Image must be base64 data URI (data:image/png;base64,...)."""
    result = await handlers.create_emoji(_get_bot(ctx).bot, server_id, name, image, roles, reason)
    return f"Created emoji :{result['name']}: (ID: {result['emoji_id']})"


@mcp.tool()
async def delete_emoji(
    server_id: str,
    emoji_id: str,
    ctx: Context,
    reason: str | None = None,
) -> str:
    """Delete a custom emoji."""
    result = await handlers.delete_emoji(_get_bot(ctx).bot, server_id, emoji_id, reason)
    return f"Deleted emoji :{result['emoji_name']}: (ID: {result['emoji_id']})"


# ============================================================================
# Thread Discovery Tools
# ============================================================================


@mcp.tool()
async def list_threads(
    server_id: str,
    ctx: Context,
    channel_id: str | None = None,
    include_archived: bool = False,
) -> str:
    """List active (and optionally archived) threads in a server or channel."""
    result = await handlers.list_threads(
        _get_bot(ctx).bot, server_id, channel_id=channel_id, include_archived=include_archived
    )
    if not result["threads"]:
        return "No threads found."
    lines = []
    for t in result["threads"]:
        status = "archived" if t["archived"] else "active"
        lines.append(
            f"- {t['name']} (ID: {t['id']}, parent: #{t['parent_name']}, "
            f"{status}, messages: {t['message_count']}, members: {t['member_count']})"
        )
    return f"Threads ({result['count']}):\n" + "\n".join(lines)


# Read tools (wrappers around resources for tool access)


@mcp.tool()
async def list_servers(ctx: Context) -> str:
    servers = await resources.list_servers(_get_bot(ctx).bot)
    lines = [f"{s['name']} (ID: {s['id']}, Members: {s['member_count']})" for s in servers]
    return f"Available Servers ({len(servers)}):\n" + "\n".join(lines)


@mcp.tool()
async def get_server_info(server_id: str, ctx: Context) -> str:
    info = await resources.get_server_info(_get_bot(ctx).bot, server_id)
    return "Server Information:\n" + "\n".join(f"{k}: {v}" for k, v in info.items())


@mcp.tool()
async def get_channels(server_id: str, ctx: Context) -> str:
    channels = await resources.get_channels(_get_bot(ctx).bot, server_id)
    lines = [f"#{ch['name']} (ID: {ch['id']}) - {ch['type']}" for ch in channels]
    return "Channels:\n" + "\n".join(lines)


@mcp.tool()
async def list_members(server_id: str, ctx: Context, limit: int = 100) -> str:
    members = await resources.list_members(_get_bot(ctx).bot, server_id, limit)
    lines = [f"{m['name']} (ID: {m['id']}, Roles: {', '.join(m['roles'])})" for m in members]
    return f"Server Members ({len(members)}):\n" + "\n".join(lines)


@mcp.tool()
async def list_roles(server_id: str, ctx: Context) -> str:
    roles = await resources.list_roles(_get_bot(ctx).bot, server_id)
    lines = [f"{r['name']} (ID: {r['id']}, Position: {r['position']}, Color: {r['color']})" for r in roles]
    return f"Roles in server ({len(roles)}):\n" + "\n".join(lines)


@mcp.tool()
async def read_messages(
    channel_id: str,
    ctx: Context,
    limit: int = 50,
    before: str | None = None,
    after: str | None = None,
    oldest_first: bool = False,
) -> str:
    """Read messages from a channel or thread. Supports pagination via before/after message IDs."""
    messages = await resources.read_messages(
        _get_bot(ctx).bot, channel_id, limit, before=before, after=after, oldest_first=oldest_first
    )

    def format_reaction(r: dict) -> str:
        return f"{r['emoji']}({r['count']})"

    lines = []
    for m in messages:
        reactions = ", ".join(format_reaction(r) for r in m["reactions"]) if m["reactions"] else "No reactions"
        parts = [f"[{m['id']}] {m['author']} ({m['timestamp']}): {m['content']}", f"Reactions: {reactions}"]

        if m.get("attachments"):
            att_strs = [f"{a['filename']} ({a['content_type'] or 'unknown'})" for a in m["attachments"]]
            parts.append(f"Attachments: {', '.join(att_strs)}")

        if m.get("embeds"):
            emb_strs = [e.get("title") or e.get("url") or "embed" for e in m["embeds"]]
            parts.append(f"Embeds: {', '.join(emb_strs)}")

        lines.append("\n".join(parts))
    return f"Retrieved {len(messages)} messages:\n\n" + "\n\n".join(lines)


@mcp.tool()
async def get_user_info(user_id: str, ctx: Context) -> str:
    info = await resources.get_user_info(_get_bot(ctx).bot, user_id)
    return (
        f"User information:\n"
        f"Name: {info['name']}#{info['discriminator']}\n"
        f"ID: {info['id']}\n"
        f"Bot: {info['bot']}\n"
        f"Created: {info['created_at']}"
    )


def main() -> None:
    """Run the MCP server."""
    mcp.run()
