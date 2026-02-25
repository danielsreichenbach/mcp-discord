"""Unit tests for client utility functions.

Tests for parse_id, require_text_channel, require_guild_channel, fetch_role,
and create_discord_bot.
"""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from discord_mcp.client import (
    create_discord_bot,
    fetch_role,
    parse_id,
    require_guild_channel,
    require_text_channel,
)


class TestParseId:
    """Tests for parse_id utility."""

    def test_valid_int_string(self):
        assert parse_id("12345", "test_id") == 12345

    def test_large_discord_id(self):
        assert parse_id("987654321098765432", "server_id") == 987654321098765432

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError, match="Invalid channel_id"):
            parse_id("not_a_number", "channel_id")

    def test_none_raises(self):
        with pytest.raises(ValueError, match="Invalid user_id"):
            parse_id(None, "user_id")  # type: ignore[arg-type]

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Invalid role_id"):
            parse_id("", "role_id")

    def test_float_string_raises(self):
        with pytest.raises(ValueError, match="Invalid server_id"):
            parse_id("123.456", "server_id")

    def test_error_includes_name_parameter(self):
        with pytest.raises(ValueError, match="my_custom_name"):
            parse_id("bad", "my_custom_name")


class TestRequireTextChannel:
    """Tests for require_text_channel validator."""

    def test_text_channel_passes(self):
        channel = MagicMock(spec=discord.TextChannel)
        result = require_text_channel(channel, "123")
        assert result is channel

    def test_voice_channel_raises(self):
        channel = MagicMock(spec=discord.VoiceChannel)
        with pytest.raises(ValueError, match="not a text channel"):
            require_text_channel(channel, "123")

    def test_category_channel_raises(self):
        channel = MagicMock(spec=discord.CategoryChannel)
        with pytest.raises(ValueError, match="not a text channel"):
            require_text_channel(channel, "456")

    def test_plain_object_raises(self):
        with pytest.raises(ValueError, match="not a text channel"):
            require_text_channel(object(), "789")


class TestRequireGuildChannel:
    """Tests for require_guild_channel validator."""

    def test_text_channel_passes(self):
        channel = MagicMock(spec=discord.TextChannel)
        result = require_guild_channel(channel, "123")
        assert result is channel

    def test_voice_channel_passes(self):
        channel = MagicMock(spec=discord.VoiceChannel)
        result = require_guild_channel(channel, "123")
        assert result is channel

    def test_category_channel_passes(self):
        channel = MagicMock(spec=discord.CategoryChannel)
        result = require_guild_channel(channel, "123")
        assert result is channel

    def test_dm_channel_raises(self):
        channel = MagicMock(spec=discord.DMChannel)
        with pytest.raises(ValueError, match="not a guild channel"):
            require_guild_channel(channel, "123")

    def test_plain_object_raises(self):
        with pytest.raises(ValueError, match="not a guild channel"):
            require_guild_channel(object(), "789")


class TestFetchRole:
    """Tests for fetch_role async utility."""

    @pytest.mark.asyncio
    async def test_role_found(self):
        guild = MagicMock(spec=discord.Guild)
        guild.name = "Test Guild"
        target_role = MagicMock(spec=discord.Role)
        target_role.id = 444
        other_role = MagicMock(spec=discord.Role)
        other_role.id = 555
        guild.fetch_roles = AsyncMock(return_value=[other_role, target_role])

        result = await fetch_role(guild, 444)
        assert result is target_role

    @pytest.mark.asyncio
    async def test_role_not_found_raises(self):
        guild = MagicMock(spec=discord.Guild)
        guild.name = "Test Guild"
        other_role = MagicMock(spec=discord.Role)
        other_role.id = 555
        guild.fetch_roles = AsyncMock(return_value=[other_role])

        with pytest.raises(ValueError, match="Role 999 not found"):
            await fetch_role(guild, 999)

    @pytest.mark.asyncio
    async def test_empty_roles_raises(self):
        guild = MagicMock(spec=discord.Guild)
        guild.name = "Test Guild"
        guild.fetch_roles = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="Role 123 not found"):
            await fetch_role(guild, 123)


class TestCreateDiscordBot:
    """Tests for create_discord_bot factory."""

    def test_returns_bot_instance(self):
        bot = create_discord_bot()
        assert isinstance(bot, commands.Bot)

    def test_intents_configured(self):
        bot = create_discord_bot()
        assert bot.intents.message_content is True
        assert bot.intents.members is True

    def test_command_prefix(self):
        bot = create_discord_bot()
        assert bot.command_prefix == "!"
