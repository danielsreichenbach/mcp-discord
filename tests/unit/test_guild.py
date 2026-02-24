"""Unit tests for audit log and emoji management handlers.

Tests for get_audit_log, list_emojis, create_emoji, and delete_emoji.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from discord_mcp import handlers


class TestGetAuditLog:
    """Tests for get_audit_log handler."""

    @pytest.mark.asyncio
    async def test_get_audit_log_success(self, mock_bot, mock_guild, mock_audit_log_entry):
        """Test retrieving audit log entries."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

        entry1 = MagicMock()
        entry1.id = 111111111111111111
        entry1.action = MagicMock()
        entry1.action.value = 20  # MEMBER_KICK
        entry1.action.name = "kick"
        entry1.user = MagicMock()
        entry1.user.id = 123456789012345678
        entry1.user.name = "TestBot"
        entry1.target = MagicMock()
        entry1.target.id = 222222222222222222
        entry1.reason = "Test reason"
        entry1.created_at = datetime.now(UTC)
        entry1.before = None
        entry1.after = None

        async def async_audit_logs():
            yield entry1

        mock_guild.audit_logs = MagicMock(return_value=async_audit_logs())

        result = await handlers.get_audit_log(mock_bot, str(mock_guild.id))

        assert "entries" in result
        assert len(result["entries"]) == 1
        assert result["entries"][0]["action_type"] == 20

    @pytest.mark.asyncio
    async def test_get_audit_log_with_user_filter(self, mock_bot, mock_guild):
        """Test audit log with user filter."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_bot.fetch_user = AsyncMock(return_value=MagicMock())

        entry = MagicMock()
        entry.id = 111111111111111111
        entry.action = MagicMock()
        entry.action.value = 20
        entry.user = MagicMock()
        entry.user.id = 123456789012345678
        entry.user.name = "TestBot"
        entry.target = MagicMock()
        entry.target.id = 222222222222222222
        entry.reason = None
        entry.created_at = datetime.now(UTC)
        entry.before = None
        entry.after = None

        async def async_audit_logs(**kwargs):
            yield entry

        mock_guild.audit_logs = MagicMock(return_value=async_audit_logs())

        await handlers.get_audit_log(
            mock_bot,
            str(mock_guild.id),
            user_id="123456789012345678",
            limit=10,
        )

    @pytest.mark.asyncio
    async def test_get_audit_log_forbidden(self, mock_bot, mock_guild):
        """Test audit log when bot lacks permissions."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.audit_logs = MagicMock(side_effect=discord.Forbidden(
            MagicMock(), "Missing permissions"
        ))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.get_audit_log(mock_bot, str(mock_guild.id))


class TestListEmojis:
    """Tests for list_emojis handler."""

    @pytest.mark.asyncio
    async def test_list_emojis_success(self, mock_bot, mock_guild, mock_emoji):
        """Test listing all custom emojis."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

        emoji1 = MagicMock()
        emoji1.id = 999999999999999991
        emoji1.name = "test_emoji_1"
        emoji1.animated = False
        emoji1.available = True
        emoji1.managed = False
        emoji1.require_colons = True

        emoji2 = MagicMock()
        emoji2.id = 999999999999999992
        emoji2.name = "test_emoji_2"
        emoji2.animated = True
        emoji2.available = True
        emoji2.managed = False

        mock_guild.fetch_emojis = AsyncMock(return_value=[emoji1, emoji2])

        result = await handlers.list_emojis(mock_bot, str(mock_guild.id))

        assert len(result) == 2
        assert result[0]["name"] == "test_emoji_1"
        assert result[1]["animated"] is True

    @pytest.mark.asyncio
    async def test_list_emojis_empty(self, mock_bot, mock_guild):
        """Test listing emojis when none exist."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_emojis = AsyncMock(return_value=[])

        result = await handlers.list_emojis(mock_bot, str(mock_guild.id))

        assert len(result) == 0


class TestCreateEmoji:
    """Tests for create_emoji handler."""

    @pytest.mark.asyncio
    async def test_create_emoji_success(self, mock_bot, mock_guild, mock_emoji):
        """Test creating a custom emoji."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.create_custom_emoji = AsyncMock(return_value=mock_emoji)

        # Base64 encoded minimal PNG
        image_data = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
            "CAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJ"
            "RU5ErkJggg=="
        )

        result = await handlers.create_emoji(
            mock_bot,
            str(mock_guild.id),
            name="test_emoji",
            image=image_data
        )

        mock_guild.create_custom_emoji.assert_called_once()
        assert result["emoji_id"] == str(mock_emoji.id)
        assert result["name"] == mock_emoji.name

    @pytest.mark.asyncio
    async def test_create_emoji_with_roles(self, mock_bot, mock_guild, mock_emoji, mock_role):
        """Test creating emoji with role restrictions."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_roles = AsyncMock(return_value=[mock_role])
        mock_guild.create_custom_emoji = AsyncMock(return_value=mock_emoji)

        image_data = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
            "CAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJ"
            "RU5ErkJggg=="
        )

        await handlers.create_emoji(
            mock_bot,
            str(mock_guild.id),
            name="restricted_emoji",
            image=image_data,
            roles=[str(mock_role.id)]
        )

    @pytest.mark.asyncio
    async def test_create_emoji_invalid_name(self, mock_bot, mock_guild):
        """Test creating emoji with invalid name."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

        with pytest.raises(ValueError, match="name"):
            await handlers.create_emoji(
                mock_bot,
                str(mock_guild.id),
                name="a",  # Too short
                image="data:image/png;base64,xxx"
            )


class TestDeleteEmoji:
    """Tests for delete_emoji handler."""

    @pytest.mark.asyncio
    async def test_delete_emoji_success(self, mock_bot, mock_guild, mock_emoji):
        """Test deleting a custom emoji."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_emojis = AsyncMock(return_value=[mock_emoji])
        mock_emoji.delete = AsyncMock()

        result = await handlers.delete_emoji(
            mock_bot,
            str(mock_guild.id),
            str(mock_emoji.id),
            reason="Test cleanup"
        )

        mock_emoji.delete.assert_called_once()
        assert result["deleted"] is True
        assert result["emoji_name"] == mock_emoji.name

    @pytest.mark.asyncio
    async def test_delete_emoji_not_found(self, mock_bot, mock_guild):
        """Test deleting an emoji that doesn't exist."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_emojis = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="Emoji.*not found"):
            await handlers.delete_emoji(
                mock_bot,
                str(mock_guild.id),
                "999999999999999999"
            )

    @pytest.mark.asyncio
    async def test_delete_emoji_forbidden(self, mock_bot, mock_guild, mock_emoji):
        """Test deleting emoji when bot lacks permissions."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_emojis = AsyncMock(return_value=[mock_emoji])
        mock_emoji.delete = AsyncMock(side_effect=discord.Forbidden(
            MagicMock(), "Cannot delete managed emoji"
        ))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.delete_emoji(
                mock_bot, str(mock_guild.id), str(mock_emoji.id)
            )
