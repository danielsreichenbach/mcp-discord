"""MCP server for Discord operations using FastMCP."""

import json
import logging

from mcp.server.fastmcp import Context, FastMCP

from . import handlers, resources
from .client import DiscordContext, configure_windows_stdout_encoding, discord_lifespan

configure_windows_stdout_encoding()

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("discord-mcp")
logger.setLevel(logging.INFO)

mcp = FastMCP("discord-server", lifespan=discord_lifespan)


def _get_bot(ctx: Context) -> "DiscordContext":
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
async def read_messages(channel_id: str, ctx: Context, limit: int = 10) -> str:
    messages = await resources.read_messages(_get_bot(ctx).bot, channel_id, limit)

    def format_reaction(r: dict) -> str:
        return f"{r['emoji']}({r['count']})"

    lines = []
    for m in messages:
        reactions = ", ".join(format_reaction(r) for r in m["reactions"]) if m["reactions"] else "No reactions"
        lines.append(f"[{m['id']}] {m['author']} ({m['timestamp']}): {m['content']}\nReactions: {reactions}")
    return f"Retrieved {len(messages)} messages:\n\n" + "\n".join(lines)


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
