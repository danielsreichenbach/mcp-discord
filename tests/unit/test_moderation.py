"""Unit tests for member moderation handlers.

Tests for kick_member, ban_member, unban_member, list_bans, and edit_member.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from discord_mcp import handlers


class TestKickMember:
    """Tests for kick_member handler."""

    @pytest.mark.asyncio
    async def test_kick_member_success(self, mock_bot, mock_guild, mock_member):
        """Test successful member kick."""
        # Setup
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_member.kick = AsyncMock()

        # Execute
        result = await handlers.kick_member(mock_bot, str(mock_guild.id), str(mock_member.id), "Test kick reason")

        # Verify
        mock_member.kick.assert_called_once_with(reason="Test kick reason")
        assert result["kicked"] is True
        assert result["user_id"] == str(mock_member.id)
        assert result["user_name"] == mock_member.name
        assert result["reason"] == "Test kick reason"

    @pytest.mark.asyncio
    async def test_kick_member_no_reason(self, mock_bot, mock_guild, mock_member):
        """Test member kick without a reason."""
        # Setup
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_member.kick = AsyncMock()

        # Execute
        result = await handlers.kick_member(mock_bot, str(mock_guild.id), str(mock_member.id))

        # Verify
        mock_member.kick.assert_called_once_with(reason=None)
        assert result["kicked"] is True
        assert result["reason"] is None

    @pytest.mark.asyncio
    async def test_kick_member_invalid_server_id(self, mock_bot):
        """Test kick with invalid server ID format."""
        with pytest.raises(ValueError, match="Invalid server_id"):
            await handlers.kick_member(mock_bot, "invalid", "123456789")

    @pytest.mark.asyncio
    async def test_kick_member_server_not_found(self, mock_bot):
        """Test kick with server that doesn't exist."""
        mock_bot.fetch_guild = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Guild not found"))

        with pytest.raises(ValueError, match="Server.*not found"):
            await handlers.kick_member(mock_bot, "999999999999999999", "123456789012345678")

    @pytest.mark.asyncio
    async def test_kick_member_invalid_user_id(self, mock_bot, mock_guild):
        """Test kick with user that doesn't exist."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Member not found"))

        with pytest.raises(ValueError, match="Member.*not found"):
            await handlers.kick_member(mock_bot, str(mock_guild.id), "999999999999999999")

    @pytest.mark.asyncio
    async def test_kick_member_forbidden(self, mock_bot, mock_guild, mock_member):
        """Test kick when bot lacks permissions."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_member.kick = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Missing permissions"))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.kick_member(mock_bot, str(mock_guild.id), str(mock_member.id))


class TestBanMember:
    """Tests for ban_member handler."""

    @pytest.mark.asyncio
    async def test_ban_member_success(self, mock_bot, mock_guild, mock_member):
        """Test successful member ban."""
        # Setup
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_guild.ban = AsyncMock()

        # Execute
        result = await handlers.ban_member(
            mock_bot, str(mock_guild.id), str(mock_member.id), reason="Test ban reason", delete_message_days=1
        )

        # Verify
        mock_guild.ban.assert_called_once_with(mock_member, reason="Test ban reason", delete_message_days=1)
        assert result["banned"] is True
        assert result["user_id"] == str(mock_member.id)
        assert result["user_name"] == mock_member.name
        assert result["reason"] == "Test ban reason"
        assert result["messages_deleted_days"] == 1

    @pytest.mark.asyncio
    async def test_ban_member_by_user_id(self, mock_bot, mock_guild, mock_user):
        """Test banning a user who is not in the server by ID."""
        # Setup
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Member not found"))
        mock_bot.fetch_user = AsyncMock(return_value=mock_user)
        mock_guild.ban = AsyncMock()

        # Execute
        result = await handlers.ban_member(mock_bot, str(mock_guild.id), str(mock_user.id), reason="Ban by user ID")

        # Verify
        mock_guild.ban.assert_called_once_with(mock_user, reason="Ban by user ID", delete_message_days=0)
        assert result["banned"] is True

    @pytest.mark.asyncio
    async def test_ban_member_default_delete_days(self, mock_bot, mock_guild, mock_member):
        """Test ban with default delete_message_days."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_guild.ban = AsyncMock()

        result = await handlers.ban_member(mock_bot, str(mock_guild.id), str(mock_member.id))

        mock_guild.ban.assert_called_once_with(mock_member, reason=None, delete_message_days=0)
        assert result["messages_deleted_days"] == 0

    @pytest.mark.asyncio
    async def test_ban_member_forbidden(self, mock_bot, mock_guild, mock_member):
        """Test ban when bot lacks permissions."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_guild.ban = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Missing permissions"))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.ban_member(mock_bot, str(mock_guild.id), str(mock_member.id))


class TestUnbanMember:
    """Tests for unban_member handler."""

    @pytest.mark.asyncio
    async def test_unban_member_success(self, mock_bot, mock_guild, mock_user):
        """Test successful member unban."""
        # Setup
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_bot.fetch_user = AsyncMock(return_value=mock_user)
        mock_guild.unban = AsyncMock()

        # Execute
        result = await handlers.unban_member(
            mock_bot, str(mock_guild.id), str(mock_user.id), reason="Test unban reason"
        )

        # Verify
        mock_guild.unban.assert_called_once_with(mock_user, reason="Test unban reason")
        assert result["unbanned"] is True
        assert result["user_id"] == str(mock_user.id)
        assert result["reason"] == "Test unban reason"

    @pytest.mark.asyncio
    async def test_unban_member_not_banned(self, mock_bot, mock_guild, mock_user):
        """Test unban when user is not banned."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_bot.fetch_user = AsyncMock(return_value=mock_user)
        mock_guild.unban = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Ban not found"))

        with pytest.raises(ValueError, match="not banned"):
            await handlers.unban_member(mock_bot, str(mock_guild.id), str(mock_user.id))


class TestListBans:
    """Tests for list_bans resource handler."""

    @pytest.mark.asyncio
    async def test_list_bans_success(self, mock_bot, mock_guild, mock_ban_entry):
        """Test listing bans successfully."""
        # Setup
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

        # Create multiple ban entries
        ban1 = MagicMock()
        ban1.user = MagicMock()
        ban1.user.id = 111111111111111111
        ban1.user.name = "BannedUser1"
        ban1.reason = "Spam"

        ban2 = MagicMock()
        ban2.user = MagicMock()
        ban2.user.id = 222222222222222222
        ban2.user.name = "BannedUser2"
        ban2.reason = "Harassment"

        # Mock the async iterator
        async def async_bans():
            yield ban1
            yield ban2

        mock_guild.bans = MagicMock(return_value=async_bans())

        # Execute
        result = await handlers.list_bans(mock_bot, str(mock_guild.id))

        # Verify
        assert len(result) == 2
        assert result[0]["user_id"] == str(ban1.user.id)
        assert result[0]["user_name"] == ban1.user.name
        assert result[0]["reason"] == "Spam"
        assert result[1]["user_id"] == str(ban2.user.id)

    @pytest.mark.asyncio
    async def test_list_bans_empty(self, mock_bot, mock_guild):
        """Test listing bans when none exist."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

        async def async_bans():
            return
            yield  # Never reached

        mock_guild.bans = MagicMock(return_value=async_bans())

        result = await handlers.list_bans(mock_bot, str(mock_guild.id))

        assert len(result) == 0


class TestEditMember:
    """Tests for edit_member handler."""

    @pytest.mark.asyncio
    async def test_edit_member_nickname(self, mock_bot, mock_guild, mock_member):
        """Test changing member nickname."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_member.edit = AsyncMock()

        result = await handlers.edit_member(mock_bot, str(mock_guild.id), str(mock_member.id), nick="NewNickname")

        mock_member.edit.assert_called_once()
        assert result["user_id"] == str(mock_member.id)
        assert "nick" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_member_timeout(self, mock_bot, mock_guild, mock_member):
        """Test timing out a member."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_member.edit = AsyncMock()

        timeout_until = datetime.now(UTC) + timedelta(hours=1)

        result = await handlers.edit_member(
            mock_bot,
            str(mock_guild.id),
            str(mock_member.id),
            timeout_until=timeout_until.isoformat(),
            reason="Timeout test",
        )

        mock_member.edit.assert_called_once()
        assert "timeout_until" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_member_remove_timeout(self, mock_bot, mock_guild, mock_member):
        """Test removing a timeout from a member."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_member.edit = AsyncMock()

        result = await handlers.edit_member(mock_bot, str(mock_guild.id), str(mock_member.id), timeout_until=None)

        mock_member.edit.assert_called_once()
        assert "timeout_until" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_member_voice_mute(self, mock_bot, mock_guild, mock_member):
        """Test muting a member in voice."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_member.edit = AsyncMock()

        result = await handlers.edit_member(mock_bot, str(mock_guild.id), str(mock_member.id), mute=True)

        assert "mute" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_member_voice_deafen(self, mock_bot, mock_guild, mock_member):
        """Test deafening a member in voice."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_member.edit = AsyncMock()

        result = await handlers.edit_member(mock_bot, str(mock_guild.id), str(mock_member.id), deafen=True)

        assert "deafen" in result["changes"]


class TestRemoveTimeout:
    """Tests for remove_timeout convenience handler."""

    @pytest.mark.asyncio
    async def test_remove_timeout_success(self, mock_bot, mock_guild, mock_member):
        """Test removing a timeout from a member."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_member.edit = AsyncMock()

        result = await handlers.remove_timeout(
            mock_bot, str(mock_guild.id), str(mock_member.id), reason="Timeout served"
        )

        assert result["timeout_removed"] is True
        assert result["user_id"] == str(mock_member.id)
