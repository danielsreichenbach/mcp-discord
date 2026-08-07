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

        result = await handlers.edit_channel(mock_bot, str(mock_text_channel.id), name="new-name")

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

        result = await handlers.edit_channel(mock_bot, str(mock_text_channel.id), topic="New topic")

        assert "topic" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_channel_slowmode(self, mock_bot, mock_text_channel):
        """Test editing channel slowmode delay."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.edit = AsyncMock()

        result = await handlers.edit_channel(mock_bot, str(mock_text_channel.id), slowmode_delay=30)

        assert "slowmode_delay" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_channel_nsfw(self, mock_bot, mock_text_channel):
        """Test editing channel NSFW setting."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.edit = AsyncMock()

        result = await handlers.edit_channel(mock_bot, str(mock_text_channel.id), nsfw=True)

        assert "nsfw" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_channel_multiple_properties(self, mock_bot, mock_text_channel):
        """Test editing multiple channel properties at once."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.edit = AsyncMock()
        mock_text_channel.name = "new-name"
        mock_text_channel.topic = "New topic"

        result = await handlers.edit_channel(
            mock_bot, str(mock_text_channel.id), name="new-name", topic="New topic", slowmode_delay=60, nsfw=False
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
        mock_bot.fetch_channel = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Channel not found"))

        with pytest.raises(ValueError, match="Channel.*not found"):
            await handlers.edit_channel(mock_bot, "999999999999999999", name="test")

    @pytest.mark.asyncio
    async def test_edit_channel_forbidden(self, mock_bot, mock_text_channel):
        """Test editing when bot lacks permissions."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.edit = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Missing permissions"))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.edit_channel(mock_bot, str(mock_text_channel.id), name="test")


class TestCreateCategory:
    """Tests for create_category handler."""

    @pytest.mark.asyncio
    async def test_create_category_success(self, mock_bot, mock_guild, mock_category):
        """Test creating a category."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.create_category = AsyncMock(return_value=mock_category)

        result = await handlers.create_category(
            mock_bot, str(mock_guild.id), name="Test Category", position=0, reason="Test category creation"
        )

        mock_guild.create_category.assert_called_once()
        assert result["category_id"] == str(mock_category.id)
        assert result["category_name"] == mock_category.name

    @pytest.mark.asyncio
    async def test_create_category_default_position(self, mock_bot, mock_guild, mock_category):
        """Test creating category without specifying position."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.create_category = AsyncMock(return_value=mock_category)

        result = await handlers.create_category(mock_bot, str(mock_guild.id), name="Test Category")

        assert result["category_id"] == str(mock_category.id)


class TestCreateVoiceChannel:
    """Tests for create_voice_channel handler."""

    @pytest.mark.asyncio
    async def test_create_voice_channel_success(self, mock_bot, mock_guild, mock_voice_channel):
        """Test creating a voice channel."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.create_voice_channel = AsyncMock(return_value=mock_voice_channel)

        result = await handlers.create_voice_channel(
            mock_bot, str(mock_guild.id), name="Test Voice", bitrate=64000, user_limit=10
        )

        mock_guild.create_voice_channel.assert_called_once()
        assert result["channel_id"] == str(mock_voice_channel.id)
        assert result["channel_name"] == "Test Voice"
        assert result["type"] == "voice"

    @pytest.mark.asyncio
    async def test_create_voice_channel_with_category(self, mock_bot, mock_guild, mock_voice_channel, mock_category):
        """Test creating voice channel in a category."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_bot.fetch_channel = AsyncMock(return_value=mock_category)
        mock_guild.create_voice_channel = AsyncMock(return_value=mock_voice_channel)

        result = await handlers.create_voice_channel(
            mock_bot, str(mock_guild.id), name="Test Voice", category_id=str(mock_category.id)
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
                bitrate=1000,  # Too low
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
            [{"id": str(channel1.id), "position": 2}, {"id": str(channel2.id), "position": 1}],
        )

        assert result["reordered"] is True
        assert len(result["channels"]) == 2


class TestListThreads:
    """Tests for list_threads handler."""

    def _make_thread(self, thread_id, name, archived=False, message_count=10, member_count=3):
        thread = MagicMock(spec=discord.Thread)
        thread.id = thread_id
        thread.name = name
        thread.archived = archived
        thread.message_count = message_count
        thread.member_count = member_count
        thread.created_at = MagicMock()
        thread.created_at.isoformat = MagicMock(return_value="2024-01-01T00:00:00+00:00")
        return thread

    @pytest.mark.asyncio
    async def test_list_active_threads_in_channel(self, mock_bot, mock_guild, mock_text_channel):
        """Test listing active threads in a specific channel."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)

        thread1 = self._make_thread(1001, "help-thread")
        thread2 = self._make_thread(1002, "discussion-thread")
        mock_text_channel.threads = [thread1, thread2]

        result = await handlers.list_threads(mock_bot, str(mock_guild.id), channel_id=str(mock_text_channel.id))

        assert result["count"] == 2
        assert result["threads"][0]["name"] == "help-thread"
        assert result["threads"][0]["id"] == "1001"
        assert result["threads"][0]["parent_id"] == str(mock_text_channel.id)
        assert result["threads"][0]["parent_name"] == mock_text_channel.name
        assert result["threads"][0]["archived"] is False

    @pytest.mark.asyncio
    async def test_list_threads_includes_archived(self, mock_bot, mock_guild, mock_text_channel):
        """Test listing threads with include_archived=True."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)

        active_thread = self._make_thread(1001, "active-thread")
        archived_thread = self._make_thread(1002, "old-thread", archived=True)
        mock_text_channel.threads = [active_thread]

        async def mock_archived_threads():
            yield archived_thread

        mock_text_channel.archived_threads = MagicMock(side_effect=mock_archived_threads)

        result = await handlers.list_threads(
            mock_bot,
            str(mock_guild.id),
            channel_id=str(mock_text_channel.id),
            include_archived=True,
        )

        assert result["count"] == 2
        names = [t["name"] for t in result["threads"]]
        assert "active-thread" in names
        assert "old-thread" in names

    @pytest.mark.asyncio
    async def test_list_threads_server_wide(self, mock_bot, mock_guild):
        """Test listing threads across all channels in the server."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

        ch1 = MagicMock(spec=discord.TextChannel)
        ch1.id = 100
        ch1.name = "general"
        ch1.threads = [self._make_thread(1001, "gen-thread")]

        ch2 = MagicMock(spec=discord.TextChannel)
        ch2.id = 200
        ch2.name = "modding"
        ch2.threads = [self._make_thread(1002, "mod-thread")]

        # Include a non-text channel that should be skipped
        voice = MagicMock(spec=discord.VoiceChannel)
        voice.id = 300
        voice.name = "voice"

        mock_guild.fetch_channels = AsyncMock(return_value=[ch1, ch2, voice])

        result = await handlers.list_threads(mock_bot, str(mock_guild.id))

        assert result["count"] == 2
        parent_names = {t["parent_name"] for t in result["threads"]}
        assert parent_names == {"general", "modding"}

    @pytest.mark.asyncio
    async def test_list_threads_empty(self, mock_bot, mock_guild, mock_text_channel):
        """Test listing threads when none exist."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.threads = []

        result = await handlers.list_threads(mock_bot, str(mock_guild.id), channel_id=str(mock_text_channel.id))

        assert result["count"] == 0
        assert result["threads"] == []

    @pytest.mark.asyncio
    async def test_list_threads_non_text_channel_raises(self, mock_bot, mock_guild, mock_voice_channel):
        """Test that passing a voice channel raises ValueError."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_bot.fetch_channel = AsyncMock(return_value=mock_voice_channel)

        with pytest.raises(ValueError, match="not a text channel"):
            await handlers.list_threads(mock_bot, str(mock_guild.id), channel_id=str(mock_voice_channel.id))

    @pytest.mark.asyncio
    async def test_list_threads_invalid_server_id(self, mock_bot):
        """Test that invalid server ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid server_id"):
            await handlers.list_threads(mock_bot, "invalid")

    @pytest.mark.asyncio
    async def test_list_threads_forbidden(self, mock_bot, mock_guild):
        """Test that missing permissions raises PermissionError."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_channels = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Missing permissions"))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.list_threads(mock_bot, str(mock_guild.id))
