"""Integration test fixtures for Discord MCP server.

Tests require DISCORD_TOKEN environment variable and access to a Discord server.
Set TEST_SERVER_ID and TEST_CHANNEL_ID for tests that need specific targets.
"""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from discord.ext import commands

from discord_mcp.client import create_discord_bot


def get_test_server_id() -> str | None:
    """Get test server ID from environment."""
    return os.getenv("TEST_SERVER_ID")


def get_test_channel_id() -> str | None:
    """Get test channel ID from environment."""
    return os.getenv("TEST_CHANNEL_ID")


def get_test_user_id() -> str | None:
    """Get test user ID for role/membership tests."""
    return os.getenv("TEST_USER_ID")


def get_test_role_id() -> str | None:
    """Get test role ID for role tests."""
    return os.getenv("TEST_ROLE_ID")


def skip_if_no_token() -> None:
    """Skip test if DISCORD_TOKEN is not set."""
    if not os.getenv("DISCORD_TOKEN"):
        pytest.skip("DISCORD_TOKEN not set")


@pytest_asyncio.fixture
async def discord_bot() -> AsyncGenerator[commands.Bot, None]:
    """Create and start a Discord bot for testing.

    Yields a connected bot instance. Automatically closes on cleanup.
    Requires DISCORD_TOKEN environment variable.
    """
    import asyncio

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        pytest.skip("DISCORD_TOKEN not set")

    bot = create_discord_bot()
    ready_event = asyncio.Event()

    @bot.event
    async def on_ready() -> None:
        ready_event.set()

    bot_task = asyncio.create_task(bot.start(token))

    try:
        await asyncio.wait_for(ready_event.wait(), timeout=30.0)
        yield bot
    finally:
        if not bot.is_closed():
            await bot.close()
        if not bot_task.done():
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass


@pytest.fixture
def test_server_id() -> str:
    """Fixture for test server ID."""
    server_id = get_test_server_id()
    if not server_id:
        pytest.skip("TEST_SERVER_ID not set")
    return server_id


@pytest.fixture
def test_channel_id() -> str:
    """Fixture for test channel ID."""
    channel_id = get_test_channel_id()
    if not channel_id:
        pytest.skip("TEST_CHANNEL_ID not set")
    return channel_id


@pytest.fixture
def test_user_id() -> str:
    """Fixture for test user ID."""
    user_id = get_test_user_id()
    if not user_id:
        pytest.skip("TEST_USER_ID not set")
    return user_id


@pytest.fixture
def test_role_id() -> str:
    """Fixture for test role ID."""
    role_id = get_test_role_id()
    if not role_id:
        pytest.skip("TEST_ROLE_ID not set")
    return role_id
