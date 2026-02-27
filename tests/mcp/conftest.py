"""MCP integration test fixtures.

Provides a ClientSession connected to the production FastMCP server
with a mock Discord bot injected via lifespan patching.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import anyio
import discord
import pytest_asyncio
from discord.ext import commands
from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session

from discord_mcp.client import DiscordContext


def _make_mock_bot() -> MagicMock:
    """Create a mock bot with common attributes configured."""
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock()
    bot.user.id = 123456789012345678
    bot.user.name = "TestBot"
    bot.is_closed = MagicMock(return_value=False)

    # Default guild for tool calls
    guild = MagicMock(spec=discord.Guild)
    guild.id = 987654321098765432
    guild.name = "Test Server"
    guild.owner_id = 111111111111111111
    guild.approximate_member_count = 50
    guild.created_at = datetime(2023, 1, 1, tzinfo=UTC)
    guild.description = "A test server"
    guild.premium_tier = 0
    guild.explicit_content_filter = MagicMock()
    guild.explicit_content_filter.__str__ = lambda self: "disabled"
    guild.fetch_channels = AsyncMock(return_value=[])
    guild.fetch_roles = AsyncMock(return_value=[])
    guild.fetch_member = AsyncMock()
    guild.fetch_emojis = AsyncMock(return_value=[])
    guild.invites = AsyncMock(return_value=[])

    async def empty_gen(*args, **kwargs):  # noqa: ANN002, ANN003
        return
        yield

    guild.fetch_members = MagicMock(side_effect=empty_gen)
    guild.bans = MagicMock(side_effect=empty_gen)
    guild.audit_logs = MagicMock(side_effect=empty_gen)

    bot.fetch_guild = AsyncMock(return_value=guild)
    bot.guilds = [guild]

    # Default text channel
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 555555555555555555
    channel.name = "test-channel"
    channel.type = discord.ChannelType.text
    channel.guild = guild
    channel.send = AsyncMock()
    channel.fetch_message = AsyncMock()
    channel.edit = AsyncMock()
    channel.delete = AsyncMock()

    async def empty_history(**kwargs):  # noqa: ANN003
        return
        yield

    channel.history = MagicMock(side_effect=empty_history)
    bot.fetch_channel = AsyncMock(return_value=channel)

    # Default user
    user = MagicMock()
    user.id = 222222222222222222
    user.name = "TestUser"
    user.discriminator = "1234"
    user.bot = False
    user.created_at = datetime(2023, 6, 1, tzinfo=UTC)
    bot.fetch_user = AsyncMock(return_value=user)

    return bot


@pytest_asyncio.fixture
async def mcp_session() -> AsyncGenerator[tuple[ClientSession, MagicMock], None]:
    """Yield (ClientSession, mock_bot) connected to the production MCP server.

    The create_connected_server_and_client_session helper uses anyio task groups
    internally. Teardown can raise RuntimeError when pytest-asyncio runs the
    generator finalizer in a different task than the one that entered the cancel
    scope. We suppress that specific error during cleanup since the session has
    already been used successfully by that point.
    """
    mock_bot = _make_mock_bot()

    @asynccontextmanager
    async def mock_lifespan(server):  # noqa: ANN001
        yield DiscordContext(bot=mock_bot)

    from discord_mcp.server import mcp as production_mcp

    original_lifespan = production_mcp._mcp_server.lifespan
    production_mcp._mcp_server.lifespan = mock_lifespan
    try:
        async with create_connected_server_and_client_session(
            server=production_mcp,
            raise_exceptions=True,
        ) as session:
            await session.initialize()
            yield session, mock_bot
    except (RuntimeError, anyio.get_cancelled_exc_class(), ExceptionGroup):
        # Suppress teardown errors from anyio cancel scope / task group mismatch.
        # This occurs because pytest-asyncio runs fixture teardown in a different
        # task than setup, which conflicts with anyio's cancel scope tracking.
        pass
    finally:
        production_mcp._mcp_server.lifespan = original_lifespan
