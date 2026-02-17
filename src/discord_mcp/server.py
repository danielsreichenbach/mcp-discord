import asyncio
import logging
import os
import sys
from collections.abc import Callable, Coroutine
from datetime import timedelta
from functools import wraps
from typing import Any

import discord
from discord.ext import commands
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


def _configure_windows_stdout_encoding() -> None:
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


_configure_windows_stdout_encoding()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord-mcp-server")


class _ServerState:
    """Holds runtime state for the Discord MCP server.

    Created once in main() after validating the environment.
    """

    def __init__(self, token: str) -> None:
        self.token = token
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self.app = Server("discord-server")
        self.discord_client: commands.Bot | None = None
        self.ready_event = asyncio.Event()

        @self.bot.event
        async def on_ready() -> None:
            self.discord_client = self.bot
            if self.bot.user:
                logger.info(f"Logged in as {self.bot.user.name}")  # noqa: G004
            self.ready_event.set()


_state: _ServerState | None = None


def _parse_id(value: str, name: str) -> int:
    """Convert a string argument to int with a descriptive error."""
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {name}: {value!r} is not a valid ID")


def _require_text_channel(channel: object, channel_id: str) -> discord.TextChannel:
    """Validate that a fetched channel is a text channel."""
    if not isinstance(channel, discord.TextChannel):
        raise ValueError(f"Channel {channel_id} is not a text channel")
    return channel


def _require_guild_channel(channel: object, channel_id: str) -> discord.abc.GuildChannel:
    """Validate that a fetched channel is a guild channel."""
    if not isinstance(channel, discord.abc.GuildChannel):
        raise ValueError(f"Channel {channel_id} is not a guild channel")
    return channel


async def _fetch_role(guild: discord.Guild, role_id: int) -> discord.Role:
    """Fetch a role from the API by ID."""
    roles = await guild.fetch_roles()
    for role in roles:
        if role.id == role_id:
            return role
    raise ValueError(f"Role {role_id} not found in guild {guild.name}")


def require_discord_client[T](
    func: Callable[..., Coroutine[Any, Any, T]],
) -> Callable[..., Coroutine[Any, Any, T]]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        if _state is None or _state.discord_client is None:
            raise RuntimeError("Discord client not ready")
        return await func(*args, **kwargs)

    return wrapper


def _register_handlers(app: Server) -> None:
    """Register MCP tool handlers on the given Server instance."""

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        """List available Discord tools."""
        return [
            # Server Information Tools
            Tool(
                name="get_server_info",
                description="Get information about a Discord server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Discord server (guild) ID",
                        }
                    },
                    "required": ["server_id"],
                },
            ),
            Tool(
                name="get_channels",
                description="Get a list of all channels in a Discord server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Discord server (guild) ID",
                        }
                    },
                    "required": ["server_id"],
                },
            ),
            Tool(
                name="list_members",
                description="Get a list of members in a server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Discord server (guild) ID",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of members to fetch",
                            "minimum": 1,
                            "maximum": 1000,
                        },
                    },
                    "required": ["server_id"],
                },
            ),
            # Role Management Tools
            Tool(
                name="add_role",
                description="Add a role to a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Discord server ID",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User to add role to",
                        },
                        "role_id": {
                            "type": "string",
                            "description": "Role ID to add",
                        },
                    },
                    "required": ["server_id", "user_id", "role_id"],
                },
            ),
            Tool(
                name="remove_role",
                description="Remove a role from a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Discord server ID",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User to remove role from",
                        },
                        "role_id": {
                            "type": "string",
                            "description": "Role ID to remove",
                        },
                    },
                    "required": ["server_id", "user_id", "role_id"],
                },
            ),
            # Channel Management Tools
            Tool(
                name="create_text_channel",
                description="Create a new text channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Discord server ID",
                        },
                        "name": {
                            "type": "string",
                            "description": "Channel name",
                        },
                        "category_id": {
                            "type": "string",
                            "description": "Optional category ID to place channel in",
                        },
                        "topic": {
                            "type": "string",
                            "description": "Optional channel topic",
                        },
                    },
                    "required": ["server_id", "name"],
                },
            ),
            Tool(
                name="delete_channel",
                description="Delete a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "ID of channel to delete",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for deletion",
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            # Message Reaction Tools
            Tool(
                name="add_reaction",
                description="Add a reaction to a message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Channel containing the message",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "Message to react to",
                        },
                        "emoji": {
                            "type": "string",
                            "description": "Emoji to react with (Unicode or custom emoji ID)",
                        },
                    },
                    "required": ["channel_id", "message_id", "emoji"],
                },
            ),
            Tool(
                name="add_multiple_reactions",
                description="Add multiple reactions to a message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Channel containing the message",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "Message to react to",
                        },
                        "emojis": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "description": "Emoji to react with (Unicode or custom emoji ID)",
                            },
                            "description": "List of emojis to add as reactions",
                        },
                    },
                    "required": ["channel_id", "message_id", "emojis"],
                },
            ),
            Tool(
                name="remove_reaction",
                description="Remove a reaction from a message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Channel containing the message",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "Message to remove reaction from",
                        },
                        "emoji": {
                            "type": "string",
                            "description": "Emoji to remove (Unicode or custom emoji ID)",
                        },
                    },
                    "required": ["channel_id", "message_id", "emoji"],
                },
            ),
            Tool(
                name="send_message",
                description="Send a message to a specific channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Discord channel ID",
                        },
                        "content": {
                            "type": "string",
                            "description": "Message content",
                        },
                    },
                    "required": ["channel_id", "content"],
                },
            ),
            Tool(
                name="read_messages",
                description="Read recent messages from a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Discord channel ID",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of messages to fetch (max 100)",
                            "minimum": 1,
                            "maximum": 100,
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            Tool(
                name="get_user_info",
                description="Get information about a Discord user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "Discord user ID",
                        }
                    },
                    "required": ["user_id"],
                },
            ),
            Tool(
                name="moderate_message",
                description="Delete a message and optionally timeout the user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Channel ID containing the message",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "ID of message to moderate",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for moderation",
                        },
                        "timeout_minutes": {
                            "type": "integer",
                            "description": "Optional timeout duration in minutes",
                            "minimum": 0,
                            "maximum": 40320,
                        },
                    },
                    "required": ["channel_id", "message_id", "reason"],
                },
            ),
            Tool(
                name="list_servers",
                description=(
                    "Get a list of all Discord servers the bot has access to"
                    " with their details such as name, id, member count, and creation date."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="list_roles",
                description="Get a list of all roles in a Discord server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "server_id": {
                            "type": "string",
                            "description": "Discord server (guild) ID",
                        }
                    },
                    "required": ["server_id"],
                },
            ),
        ]

    @app.call_tool()
    @require_discord_client
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle Discord tool calls."""
        assert _state is not None and _state.discord_client is not None
        discord_client = _state.discord_client

        if name == "send_message":
            channel = await discord_client.fetch_channel(_parse_id(arguments["channel_id"], "channel_id"))
            text_channel = _require_text_channel(channel, arguments["channel_id"])
            message = await text_channel.send(arguments["content"])
            return [TextContent(type="text", text=f"Message sent successfully. Message ID: {message.id}")]

        elif name == "read_messages":
            channel = await discord_client.fetch_channel(_parse_id(arguments["channel_id"], "channel_id"))
            text_channel = _require_text_channel(channel, arguments["channel_id"])
            limit = min(int(arguments.get("limit", 10)), 100)
            messages = []
            async for message in text_channel.history(limit=limit):
                reaction_data = []
                for reaction in message.reactions:
                    emoji = reaction.emoji
                    if isinstance(emoji, str):
                        emoji_str = emoji
                    elif hasattr(emoji, "name") and emoji.name:
                        emoji_str = emoji.name
                    else:
                        emoji_str = str(emoji.id)
                    reaction_info = {"emoji": emoji_str, "count": reaction.count}
                    logger.debug(f"Emoji: {emoji_str}")  # noqa: G004
                    reaction_data.append(reaction_info)
                messages.append(
                    {
                        "id": str(message.id),
                        "author": str(message.author),
                        "content": message.content,
                        "timestamp": message.created_at.isoformat(),
                        "reactions": reaction_data,
                    }
                )

            def format_reaction(r: dict[str, Any]) -> str:
                return f"{r['emoji']}({r['count']})"

            return [
                TextContent(
                    type="text",
                    text=f"Retrieved {len(messages)} messages:\n\n"
                    + "\n".join(
                        [
                            f"[{m['id']}] {m['author']} ({m['timestamp']}): {m['content']}\n"
                            + "Reactions: "
                            + (
                                ", ".join(format_reaction(r) for r in m["reactions"])
                                if m["reactions"]
                                else "No reactions"
                            )
                            for m in messages
                        ]
                    ),
                )
            ]

        elif name == "get_user_info":
            user = await discord_client.fetch_user(_parse_id(arguments["user_id"], "user_id"))
            user_info = {
                "id": str(user.id),
                "name": user.name,
                "discriminator": user.discriminator,
                "bot": user.bot,
                "created_at": user.created_at.isoformat(),
            }
            return [
                TextContent(
                    type="text",
                    text="User information:\n"
                    + f"Name: {user_info['name']}#{user_info['discriminator']}\n"
                    + f"ID: {user_info['id']}\n"
                    + f"Bot: {user_info['bot']}\n"
                    + f"Created: {user_info['created_at']}",
                )
            ]

        elif name == "moderate_message":
            channel = await discord_client.fetch_channel(_parse_id(arguments["channel_id"], "channel_id"))
            text_channel = _require_text_channel(channel, arguments["channel_id"])
            message = await text_channel.fetch_message(_parse_id(arguments["message_id"], "message_id"))

            # Apply timeout before deleting the message so we can resolve the author
            timeout_applied = False
            if "timeout_minutes" in arguments and arguments["timeout_minutes"] > 0:
                guild = text_channel.guild
                try:
                    member = await guild.fetch_member(message.author.id)
                    duration = discord.utils.utcnow() + timedelta(minutes=arguments["timeout_minutes"])
                    await member.timeout(duration, reason=arguments["reason"])
                    timeout_applied = True
                except discord.NotFound:
                    raise ValueError(
                        f"Cannot timeout user {message.author.id}: member not found in guild"
                    )

            await message.delete()

            if timeout_applied:
                return [
                    TextContent(
                        type="text",
                        text=f"Message deleted and user timed out for {arguments['timeout_minutes']} minutes.",
                    )
                ]
            return [TextContent(type="text", text="Message deleted successfully.")]

        # Server Information Tools
        elif name == "get_server_info":
            guild = await discord_client.fetch_guild(
                _parse_id(arguments["server_id"], "server_id"), with_counts=True
            )
            info = {
                "name": guild.name,
                "id": str(guild.id),
                "owner_id": str(guild.owner_id),
                "member_count": guild.approximate_member_count,
                "created_at": guild.created_at.isoformat(),
                "description": guild.description,
                "premium_tier": guild.premium_tier,
                "explicit_content_filter": str(guild.explicit_content_filter),
            }
            return [
                TextContent(
                    type="text",
                    text="Server Information:\n" + "\n".join(f"{k}: {v}" for k, v in info.items()),
                )
            ]

        elif name == "get_channels":
            guild = await discord_client.fetch_guild(_parse_id(arguments["server_id"], "server_id"))
            channels = await guild.fetch_channels()
            channel_list = []
            for ch in channels:
                channel_list.append(f"#{ch.name} (ID: {ch.id}) - {ch.type}")

            return [
                TextContent(
                    type="text",
                    text=f"Channels in {guild.name}:\n" + "\n".join(channel_list),
                )
            ]

        elif name == "list_members":
            guild = await discord_client.fetch_guild(_parse_id(arguments["server_id"], "server_id"))
            limit = min(int(arguments.get("limit", 100)), 1000)

            members = []
            async for member in guild.fetch_members(limit=limit):
                members.append(
                    {
                        "id": str(member.id),
                        "name": member.name,
                        "nick": member.nick,
                        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                        "roles": [str(role.id) for role in member.roles[1:]],  # Skip @everyone
                    }
                )

            return [
                TextContent(
                    type="text",
                    text=f"Server Members ({len(members)}):\n"
                    + "\n".join(
                        f"{m['name']} (ID: {m['id']}, Roles: {', '.join(m['roles'])})" for m in members
                    ),
                )
            ]

        # Role Management Tools
        elif name == "add_role":
            guild = await discord_client.fetch_guild(_parse_id(arguments["server_id"], "server_id"))
            member = await guild.fetch_member(_parse_id(arguments["user_id"], "user_id"))
            role = await _fetch_role(guild, _parse_id(arguments["role_id"], "role_id"))

            await member.add_roles(role, reason="Role added via MCP")
            return [TextContent(type="text", text=f"Added role {role.name} to user {member.name}")]

        elif name == "remove_role":
            guild = await discord_client.fetch_guild(_parse_id(arguments["server_id"], "server_id"))
            member = await guild.fetch_member(_parse_id(arguments["user_id"], "user_id"))
            role = await _fetch_role(guild, _parse_id(arguments["role_id"], "role_id"))

            await member.remove_roles(role, reason="Role removed via MCP")
            return [TextContent(type="text", text=f"Removed role {role.name} from user {member.name}")]

        # Channel Management Tools
        elif name == "create_text_channel":
            guild = await discord_client.fetch_guild(_parse_id(arguments["server_id"], "server_id"))
            category = None
            if "category_id" in arguments:
                cat_channel = await discord_client.fetch_channel(
                    _parse_id(arguments["category_id"], "category_id")
                )
                if not isinstance(cat_channel, discord.CategoryChannel):
                    raise ValueError(f"Channel {arguments['category_id']} is not a category channel")
                category = cat_channel

            kwargs: dict[str, Any] = {"name": arguments["name"], "reason": "Channel created via MCP"}
            if "topic" in arguments:
                kwargs["topic"] = arguments["topic"]
            if category:
                kwargs["category"] = category
            channel = await guild.create_text_channel(**kwargs)

            return [TextContent(type="text", text=f"Created text channel #{channel.name} (ID: {channel.id})")]

        elif name == "delete_channel":
            channel = await discord_client.fetch_channel(_parse_id(arguments["channel_id"], "channel_id"))
            guild_channel = _require_guild_channel(channel, arguments["channel_id"])
            await guild_channel.delete(reason=arguments.get("reason", "Channel deleted via MCP"))
            return [TextContent(type="text", text="Deleted channel successfully")]

        # Message Reaction Tools
        elif name == "add_reaction":
            channel = await discord_client.fetch_channel(_parse_id(arguments["channel_id"], "channel_id"))
            text_channel = _require_text_channel(channel, arguments["channel_id"])
            message = await text_channel.fetch_message(_parse_id(arguments["message_id"], "message_id"))
            await message.add_reaction(arguments["emoji"])
            return [TextContent(type="text", text=f"Added reaction {arguments['emoji']} to message")]

        elif name == "add_multiple_reactions":
            channel = await discord_client.fetch_channel(_parse_id(arguments["channel_id"], "channel_id"))
            text_channel = _require_text_channel(channel, arguments["channel_id"])
            message = await text_channel.fetch_message(_parse_id(arguments["message_id"], "message_id"))
            for emoji in arguments["emojis"]:
                await message.add_reaction(emoji)
            return [TextContent(type="text", text=f"Added reactions: {', '.join(arguments['emojis'])} to message")]

        elif name == "remove_reaction":
            channel = await discord_client.fetch_channel(_parse_id(arguments["channel_id"], "channel_id"))
            text_channel = _require_text_channel(channel, arguments["channel_id"])
            message = await text_channel.fetch_message(_parse_id(arguments["message_id"], "message_id"))
            if discord_client.user is None:
                raise RuntimeError("Discord client user not available")
            await message.remove_reaction(arguments["emoji"], discord_client.user)
            return [TextContent(type="text", text=f"Removed reaction {arguments['emoji']} from message")]

        elif name == "list_servers":
            servers = []
            for guild in discord_client.guilds:
                servers.append(
                    {
                        "id": str(guild.id),
                        "name": guild.name,
                        "member_count": guild.member_count,
                        "created_at": guild.created_at.isoformat(),
                    }
                )

            return [
                TextContent(
                    type="text",
                    text=f"Available Servers ({len(servers)}):\n"
                    + "\n".join(
                        f"{s['name']} (ID: {s['id']}, Members: {s['member_count']})" for s in servers
                    ),
                )
            ]

        elif name == "list_roles":
            guild = await discord_client.fetch_guild(_parse_id(arguments["server_id"], "server_id"))
            roles = await guild.fetch_roles()
            role_list = []
            for role in sorted(roles, key=lambda r: r.position, reverse=True):
                role_list.append(
                    {
                        "id": str(role.id),
                        "name": role.name,
                        "color": str(role.color),
                        "position": role.position,
                        "mentionable": role.mentionable,
                        "member_count": len(role.members) if role.members else None,
                    }
                )

            return [
                TextContent(
                    type="text",
                    text=f"Roles in server ({len(role_list)}):\n"
                    + "\n".join(
                        f"{r['name']} (ID: {r['id']}, Position: {r['position']}, Color: {r['color']})"
                        for r in role_list
                    ),
                )
            ]

        raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    global _state

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable is required")

    _state = _ServerState(token)
    _register_handlers(_state.app)

    # Start Discord bot in the background
    bot_task = asyncio.create_task(_state.bot.start(_state.token))

    try:
        # Wait for the bot to connect before accepting MCP requests
        try:
            await asyncio.wait_for(_state.ready_event.wait(), timeout=30.0)
        except TimeoutError:
            # Check if the bot task failed (e.g. bad token)
            if bot_task.done():
                bot_task.result()  # raises the stored exception
            raise RuntimeError("Discord bot did not become ready within 30 seconds")

        # If the bot task already failed, surface the error
        if bot_task.done():
            bot_task.result()

        # Run MCP server
        async with stdio_server() as (read_stream, write_stream):
            await _state.app.run(read_stream, write_stream, _state.app.create_initialization_options())
    finally:
        if not _state.bot.is_closed():
            await _state.bot.close()
        if not bot_task.done():
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    asyncio.run(main())
