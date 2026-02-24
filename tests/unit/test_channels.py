"""Unit tests for channel management handlers.

Tests for edit_channel, create_category, create_voice_channel, and reorder_channels.
"""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from discord_mcp import handlers


class TestEditChannel:
    """Tests for edit_channel handler."""

    @pytest.mark.asyncio
    async def test_edit_channel_name(self, mock_bot, mock_text_channel):
        """Test editing channel name."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.edit = AsyncMock()
        mock_text_channel.name = "new-name"

        result = await handlers.edit_channel(
            mock_bot,
            str(mock_text_channel.id),
            name="new-name"
        )

        mock_text_channel.edit.assert_called_once()
        assert result["channel_id"] == str(mock_text_channel.id)
        assert result["channel_name"] == "new-name"
        assert "name" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_channel_topic(self, mock_bot, mock_text_channel):
        """Test editing channel topic."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.edit = AsyncMock()
        mock_text_channel.topic = "New topic"

        result = await handlers.edit_channel(
            mock_bot,
            str(mock_text_channel.id),
            topic="New topic"
        )

        assert "topic" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_channel_slowmode(self, mock_bot, mock_text_channel):
        """Test editing channel slowmode delay."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.edit = AsyncMock()

        result = await handlers.edit_channel(
            mock_bot,
            str(mock_text_channel.id),
            slowmode_delay=30
        )

        assert "slowmode_delay" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_channel_nsfw(self, mock_bot, mock_text_channel):
        """Test editing channel NSFW setting."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.edit = AsyncMock()

        result = await handlers.edit_channel(
            mock_bot,
            str(mock_text_channel.id),
            nsfw=True
        )

        assert "nsfw" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_channel_multiple_properties(self, mock_bot, mock_text_channel):
        """Test editing multiple channel properties at once."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.edit = AsyncMock()
        mock_text_channel.name = "new-name"
        mock_text_channel.topic = "New topic"

        result = await handlers.edit_channel(
            mock_bot,
            str(mock_text_channel.id),
            name="new-name",
            topic="New topic",
            slowmode_delay=60,
            nsfw=False
        )

        assert "name" in result["changes"]
        assert "topic" in result["changes"]
        assert "slowmode_delay" in result["changes"]
        assert "nsfw" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_channel_invalid_id(self, mock_bot):
        """Test editing with invalid channel ID."""
        with pytest.raises(ValueError, match="Invalid channel_id"):
            await handlers.edit_channel(mock_bot, "invalid", name="test")

    @pytest.mark.asyncio
    async def test_edit_channel_not_found(self, mock_bot):
        """Test editing a channel that doesn't exist."""
        mock_bot.fetch_channel = AsyncMock(side_effect=discord.NotFound(
            MagicMock(), "Channel not found"
        ))

        with pytest.raises(ValueError, match="Channel.*not found"):
            await handlers.edit_channel(mock_bot, "999999999999999999", name="test")

    @pytest.mark.asyncio
    async def test_edit_channel_forbidden(self, mock_bot, mock_text_channel):
        """Test editing when bot lacks permissions."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.edit = AsyncMock(side_effect=discord.Forbidden(
            MagicMock(), "Missing permissions"
        ))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.edit_channel(
                mock_bot, str(mock_text_channel.id), name="test"
            )


class TestCreateCategory:
    """Tests for create_category handler."""

    @pytest.mark.asyncio
    async def test_create_category_success(self, mock_bot, mock_guild, mock_category):
        """Test creating a category."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.create_category = AsyncMock(return_value=mock_category)

        result = await handlers.create_category(
            mock_bot,
            str(mock_guild.id),
            name="Test Category",
            position=0,
            reason="Test category creation"
        )

        mock_guild.create_category.assert_called_once()
        assert result["category_id"] == str(mock_category.id)
        assert result["category_name"] == mock_category.name

    @pytest.mark.asyncio
    async def test_create_category_default_position(self, mock_bot, mock_guild, mock_category):
        """Test creating category without specifying position."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.create_category = AsyncMock(return_value=mock_category)

        result = await handlers.create_category(
            mock_bot,
            str(mock_guild.id),
            name="Test Category"
        )

        assert result["category_id"] == str(mock_category.id)


class TestCreateVoiceChannel:
    """Tests for create_voice_channel handler."""

    @pytest.mark.asyncio
    async def test_create_voice_channel_success(self, mock_bot, mock_guild, mock_voice_channel):
        """Test creating a voice channel."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.create_voice_channel = AsyncMock(return_value=mock_voice_channel)

        result = await handlers.create_voice_channel(
            mock_bot,
            str(mock_guild.id),
            name="Test Voice",
            bitrate=64000,
            user_limit=10
        )

        mock_guild.create_voice_channel.assert_called_once()
        assert result["channel_id"] == str(mock_voice_channel.id)
        assert result["channel_name"] == "Test Voice"
        assert result["type"] == "voice"

    @pytest.mark.asyncio
    async def test_create_voice_channel_with_category(
        self, mock_bot, mock_guild, mock_voice_channel, mock_category
    ):
        """Test creating voice channel in a category."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_bot.fetch_channel = AsyncMock(return_value=mock_category)
        mock_guild.create_voice_channel = AsyncMock(return_value=mock_voice_channel)

        result = await handlers.create_voice_channel(
            mock_bot,
            str(mock_guild.id),
            name="Test Voice",
            category_id=str(mock_category.id)
        )

        assert result["channel_id"] == str(mock_voice_channel.id)

    @pytest.mark.asyncio
    async def test_create_voice_channel_invalid_bitrate(self, mock_bot, mock_guild):
        """Test creating voice channel with invalid bitrate."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

        with pytest.raises(ValueError, match="bitrate"):
            await handlers.create_voice_channel(
                mock_bot,
                str(mock_guild.id),
                name="Test Voice",
                bitrate=1000  # Too low
            )


class TestReorderChannels:
    """Tests for reorder_channels handler."""

    @pytest.mark.asyncio
    async def test_reorder_channels_success(self, mock_bot, mock_guild):
        """Test reordering channels."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

        channel1 = MagicMock(spec=discord.TextChannel)
        channel1.id = 111111111111111111
        channel1.name = "channel-1"
        channel1.position = 1
        channel1.edit = AsyncMock()

        channel2 = MagicMock(spec=discord.TextChannel)
        channel2.id = 222222222222222222
        channel2.name = "channel-2"
        channel2.position = 2
        channel2.edit = AsyncMock()

        mock_bot.fetch_channel = AsyncMock(side_effect=[channel1, channel2])

        result = await handlers.reorder_channels(
            mock_bot,
            str(mock_guild.id),
            [
                {"id": str(channel1.id), "position": 2},
                {"id": str(channel2.id), "position": 1}
            ]
        )

        assert result["reordered"] is True
        assert len(result["channels"]) == 2
