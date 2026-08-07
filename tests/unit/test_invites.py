"""Unit tests for invite management handlers.

Tests for create_invite, list_server_invites, list_channel_invites, and delete_invite.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from discord_mcp import handlers


class TestCreateInvite:
    """Tests for create_invite handler."""

    @pytest.mark.asyncio
    async def test_create_invite_success(self, mock_bot, mock_text_channel, mock_invite):
        """Test creating an invite with default settings."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.create_invite = AsyncMock(return_value=mock_invite)

        result = await handlers.create_invite(mock_bot, str(mock_text_channel.id))

        mock_text_channel.create_invite.assert_called_once()
        assert result["code"] == mock_invite.code
        assert result["url"] == f"https://discord.gg/{mock_invite.code}"
        assert "channel_id" in result

    @pytest.mark.asyncio
    async def test_create_invite_with_options(self, mock_bot, mock_text_channel, mock_invite):
        """Test creating an invite with custom options."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_invite.max_age = 3600
        mock_invite.max_uses = 5
        mock_invite.temporary = True
        mock_text_channel.create_invite = AsyncMock(return_value=mock_invite)

        result = await handlers.create_invite(
            mock_bot,
            str(mock_text_channel.id),
            max_age=3600,
            max_uses=5,
            temporary=True,
            unique=True,
            reason="Test invite creation",
        )

        assert result["max_age"] == 3600
        assert result["max_uses"] == 5
        assert result["temporary"] is True

    @pytest.mark.asyncio
    async def test_create_invite_never_expire(self, mock_bot, mock_text_channel, mock_invite):
        """Test creating an invite that never expires."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_invite.max_age = 0
        mock_text_channel.create_invite = AsyncMock(return_value=mock_invite)

        result = await handlers.create_invite(
            mock_bot,
            str(mock_text_channel.id),
            max_age=0,  # Never expire
        )

        assert result["max_age"] == 0

    @pytest.mark.asyncio
    async def test_create_invite_invalid_channel(self, mock_bot):
        """Test creating invite with invalid channel ID."""
        with pytest.raises(ValueError, match="Invalid channel_id"):
            await handlers.create_invite(mock_bot, "invalid")

    @pytest.mark.asyncio
    async def test_create_invite_channel_not_found(self, mock_bot):
        """Test creating invite for a channel that doesn't exist."""
        mock_bot.fetch_channel = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Channel not found"))

        with pytest.raises(ValueError, match="Channel.*not found"):
            await handlers.create_invite(mock_bot, "999999999999999999")

    @pytest.mark.asyncio
    async def test_create_invite_forbidden(self, mock_bot, mock_text_channel):
        """Test creating invite when bot lacks permissions."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.create_invite = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Missing permissions"))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.create_invite(mock_bot, str(mock_text_channel.id))


class TestListServerInvites:
    """Tests for list_server_invites handler."""

    @pytest.mark.asyncio
    async def test_list_server_invites_success(self, mock_bot, mock_guild, mock_invite):
        """Test listing all invites for a server."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

        invite1 = MagicMock()
        invite1.code = "abc123"
        invite1.channel = MagicMock()
        invite1.channel.id = 555555555555555555
        invite1.channel.name = "general"
        invite1.inviter = MagicMock()
        invite1.inviter.id = 123456789012345678
        invite1.inviter.name = "TestBot"
        invite1.uses = 10
        invite1.max_uses = 50
        invite1.max_age = 86400
        invite1.temporary = False
        invite1.created_at = datetime.now(UTC)

        mock_guild.invites = AsyncMock(return_value=[invite1])

        result = await handlers.list_server_invites(mock_bot, str(mock_guild.id))

        assert len(result) == 1
        assert result[0]["code"] == "abc123"
        assert result[0]["channel_name"] == "general"

    @pytest.mark.asyncio
    async def test_list_server_invites_empty(self, mock_bot, mock_guild):
        """Test listing invites when none exist."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.invites = AsyncMock(return_value=[])

        result = await handlers.list_server_invites(mock_bot, str(mock_guild.id))

        assert len(result) == 0


class TestListChannelInvites:
    """Tests for list_channel_invites handler."""

    @pytest.mark.asyncio
    async def test_list_channel_invites_success(self, mock_bot, mock_text_channel, mock_invite):
        """Test listing invites for a specific channel."""
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.invites = AsyncMock(return_value=[mock_invite])

        result = await handlers.list_channel_invites(mock_bot, str(mock_text_channel.id))

        assert len(result) == 1
        assert result[0]["channel_id"] == str(mock_text_channel.id)


class TestDeleteInvite:
    """Tests for delete_invite handler."""

    @pytest.mark.asyncio
    async def test_delete_invite_success(self, mock_bot, mock_invite):
        """Test deleting an invite by code."""
        mock_bot.fetch_invite = AsyncMock(return_value=mock_invite)
        mock_invite.delete = AsyncMock()

        result = await handlers.delete_invite(mock_bot, mock_invite.code, reason="Test cleanup")

        mock_invite.delete.assert_called_once()
        assert result["deleted"] is True
        assert result["code"] == mock_invite.code

    @pytest.mark.asyncio
    async def test_delete_invite_not_found(self, mock_bot):
        """Test deleting an invite that doesn't exist."""
        mock_bot.fetch_invite = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Invite not found"))

        with pytest.raises(ValueError, match="Invite.*not found"):
            await handlers.delete_invite(mock_bot, "invalid")

    @pytest.mark.asyncio
    async def test_delete_invite_forbidden(self, mock_bot, mock_invite):
        """Test deleting invite when bot lacks permissions."""
        mock_bot.fetch_invite = AsyncMock(return_value=mock_invite)
        mock_invite.delete = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Missing permissions"))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.delete_invite(mock_bot, mock_invite.code)
