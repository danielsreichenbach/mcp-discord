"""Unit tests for message management handlers.

Tests for edit_message, delete_message, bulk_delete_messages, pin_message,
unpin_message, and list_pinned_messages.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from discord_mcp import handlers


class TestEditMessage:
    """Tests for edit_message handler."""

    @pytest.mark.asyncio
    async def test_edit_message_success(self, mock_bot, mock_text_channel, mock_message):
        """Test editing a message sent by the bot."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)
        mock_message.edit = AsyncMock()
        mock_message.content = "Edited content"

        result = await handlers.edit_message(
            mock_bot,
            str(mock_text_channel.id),
            str(mock_message.id),
            content="Edited content"
        )

        mock_message.edit.assert_called_once()
        assert result["message_id"] == str(mock_message.id)
        assert result["content"] == "Edited content"

    @pytest.mark.asyncio
    async def test_edit_message_not_found(self, mock_bot, mock_text_channel):
        """Test editing a message that doesn't exist."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(side_effect=discord.NotFound(
            MagicMock(), "Message not found"
        ))

        with pytest.raises(ValueError, match="Message.*not found"):
            await handlers.edit_message(
                mock_bot, str(mock_text_channel.id), "999999999999999999", "content"
            )

    @pytest.mark.asyncio
    async def test_edit_message_forbidden(self, mock_bot, mock_text_channel, mock_message):
        """Test editing a message when bot lacks permissions."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)
        mock_message.edit = AsyncMock(side_effect=discord.Forbidden(
            MagicMock(), "Cannot edit other user's message"
        ))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.edit_message(
                mock_bot, str(mock_text_channel.id), str(mock_message.id), "content"
            )


class TestDeleteMessage:
    """Tests for delete_message handler."""

    @pytest.mark.asyncio
    async def test_delete_message_success(self, mock_bot, mock_text_channel, mock_message):
        """Test deleting a message."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)
        mock_message.delete = AsyncMock()

        result = await handlers.delete_message(
            mock_bot,
            str(mock_text_channel.id),
            str(mock_message.id),
        )

        mock_message.delete.assert_called_once()
        assert result["deleted"] is True
        assert result["message_id"] == str(mock_message.id)

    @pytest.mark.asyncio
    async def test_delete_message_not_found(self, mock_bot, mock_text_channel):
        """Test deleting a message that doesn't exist."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(side_effect=discord.NotFound(
            MagicMock(), "Message not found"
        ))

        with pytest.raises(ValueError, match="Message.*not found"):
            await handlers.delete_message(
                mock_bot, str(mock_text_channel.id), "999999999999999999"
            )


class TestBulkDeleteMessages:
    """Tests for bulk_delete_messages handler."""

    @pytest.mark.asyncio
    async def test_bulk_delete_messages_success(self, mock_bot, mock_text_channel):
        """Test bulk deleting messages."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)

        messages = []
        for i in range(5):
            msg = MagicMock(spec=discord.Message)
            msg.id = 1000 + i
            messages.append(msg)

        # Each individual fetch returns the corresponding message
        mock_text_channel.fetch_message = AsyncMock(side_effect=messages)
        mock_text_channel.delete_messages = AsyncMock()

        result = await handlers.bulk_delete_messages(
            mock_bot,
            str(mock_text_channel.id),
            [str(msg.id) for msg in messages],
            reason="Bulk delete test"
        )

        assert result["deleted_count"] == 5
        assert result["channel_id"] == str(mock_text_channel.id)

    @pytest.mark.asyncio
    async def test_bulk_delete_messages_too_few(self, mock_bot, mock_text_channel):
        """Test bulk delete with too few messages."""
        with pytest.raises(ValueError, match="at least 2 messages"):
            await handlers.bulk_delete_messages(
                mock_bot,
                str(mock_text_channel.id),
                ["123"]
            )

    @pytest.mark.asyncio
    async def test_bulk_delete_messages_too_many(self, mock_bot, mock_text_channel):
        """Test bulk delete with too many messages."""
        message_ids = [str(i) for i in range(101)]

        with pytest.raises(ValueError, match="maximum 100 messages"):
            await handlers.bulk_delete_messages(
                mock_bot,
                str(mock_text_channel.id),
                message_ids
            )


class TestPinMessage:
    """Tests for pin_message handler."""

    @pytest.mark.asyncio
    async def test_pin_message_success(self, mock_bot, mock_text_channel, mock_message):
        """Test pinning a message."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)
        mock_message.pin = AsyncMock()

        result = await handlers.pin_message(
            mock_bot,
            str(mock_text_channel.id),
            str(mock_message.id),
            reason="Test pin"
        )

        mock_message.pin.assert_called_once()
        assert result["pinned"] is True
        assert result["message_id"] == str(mock_message.id)


class TestUnpinMessage:
    """Tests for unpin_message handler."""

    @pytest.mark.asyncio
    async def test_unpin_message_success(self, mock_bot, mock_text_channel, mock_message):
        """Test unpinning a message."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)
        mock_message.unpin = AsyncMock()

        result = await handlers.unpin_message(
            mock_bot,
            str(mock_text_channel.id),
            str(mock_message.id),
            reason="Test unpin"
        )

        mock_message.unpin.assert_called_once()
        assert result["unpinned"] is True
        assert result["message_id"] == str(mock_message.id)


class TestListPinnedMessages:
    """Tests for list_pinned_messages handler."""

    @pytest.mark.asyncio
    async def test_list_pinned_messages_success(self, mock_bot, mock_text_channel):
        """Test listing pinned messages."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)

        pinned_msg = MagicMock(spec=discord.Message)
        pinned_msg.id = 888888888888888888
        pinned_msg.content = "Pinned message"
        pinned_msg.author = MagicMock()
        pinned_msg.author.id = 222222222222222222
        pinned_msg.author.name = "TestUser"
        pinned_msg.created_at = datetime.now(UTC)
        pinned_msg.jump_url = "https://discord.com/channels/1/2/888888888888888888"

        mock_text_channel.pins = AsyncMock(return_value=[pinned_msg])

        result = await handlers.list_pinned_messages(
            mock_bot,
            str(mock_text_channel.id)
        )

        assert len(result) == 1
        assert result[0]["message_id"] == str(pinned_msg.id)
        assert result[0]["content"] == "Pinned message"

    @pytest.mark.asyncio
    async def test_list_pinned_messages_empty(self, mock_bot, mock_text_channel):
        """Test listing pinned messages when none exist."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.pins = AsyncMock(return_value=[])

        result = await handlers.list_pinned_messages(
            mock_bot,
            str(mock_text_channel.id)
        )

        assert len(result) == 0
