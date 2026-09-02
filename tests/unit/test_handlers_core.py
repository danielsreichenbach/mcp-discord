"""Unit tests for handler functions not covered by existing test files.

Tests for send_message, add_role, remove_role, create_text_channel,
delete_channel, add_reaction, add_multiple_reactions, remove_reaction,
and moderate_message.
"""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from discord_mcp import handlers


class TestSendMessage:
    """Tests for send_message handler."""

    @pytest.mark.asyncio
    async def test_success(self, mock_bot, mock_text_channel):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        sent_msg = MagicMock()
        sent_msg.id = 111222333
        mock_text_channel.send = AsyncMock(return_value=sent_msg)

        result = await handlers.send_message(mock_bot, str(mock_text_channel.id), "Hello")

        mock_text_channel.send.assert_called_once_with("Hello")
        assert result["message_id"] == str(sent_msg.id)
        assert result["channel_id"] == str(mock_text_channel.id)

    @pytest.mark.asyncio
    async def test_invalid_channel_id(self, mock_bot):
        with pytest.raises(ValueError, match="Invalid channel_id"):
            await handlers.send_message(mock_bot, "bad", "Hello")

    @pytest.mark.asyncio
    async def test_non_text_channel_raises(self, mock_bot, mock_voice_channel):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_voice_channel)

        with pytest.raises(ValueError, match="not a text channel"):
            await handlers.send_message(mock_bot, str(mock_voice_channel.id), "Hello")


class TestAddRole:
    """Tests for add_role handler."""

    @pytest.mark.asyncio
    async def test_success(self, mock_bot, mock_guild, mock_member, mock_role):
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_guild.fetch_roles = AsyncMock(return_value=[mock_role])

        result = await handlers.add_role(
            mock_bot,
            str(mock_guild.id),
            str(mock_member.id),
            str(mock_role.id),
        )

        mock_member.add_roles.assert_called_once_with(mock_role, reason="Role added via MCP")
        assert result["role_name"] == mock_role.name
        assert result["user_name"] == mock_member.name

    @pytest.mark.asyncio
    async def test_invalid_server_id(self, mock_bot):
        with pytest.raises(ValueError, match="Invalid server_id"):
            await handlers.add_role(mock_bot, "bad", "123", "456")

    @pytest.mark.asyncio
    async def test_invalid_user_id(self, mock_bot, mock_guild):
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        with pytest.raises(ValueError, match="Invalid user_id"):
            await handlers.add_role(mock_bot, str(mock_guild.id), "bad", "456")

    @pytest.mark.asyncio
    async def test_role_not_found(self, mock_bot, mock_guild, mock_member):
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        other_role = MagicMock(spec=discord.Role)
        other_role.id = 999
        mock_guild.fetch_roles = AsyncMock(return_value=[other_role])

        with pytest.raises(ValueError, match="Role .* not found"):
            await handlers.add_role(
                mock_bot,
                str(mock_guild.id),
                str(mock_member.id),
                "444444444444444444",
            )


class TestRemoveRole:
    """Tests for remove_role handler."""

    @pytest.mark.asyncio
    async def test_success(self, mock_bot, mock_guild, mock_member, mock_role):
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_member = AsyncMock(return_value=mock_member)
        mock_guild.fetch_roles = AsyncMock(return_value=[mock_role])

        result = await handlers.remove_role(
            mock_bot,
            str(mock_guild.id),
            str(mock_member.id),
            str(mock_role.id),
        )

        mock_member.remove_roles.assert_called_once_with(mock_role, reason="Role removed via MCP")
        assert result["role_name"] == mock_role.name
        assert result["user_name"] == mock_member.name

    @pytest.mark.asyncio
    async def test_invalid_ids(self, mock_bot):
        with pytest.raises(ValueError, match="Invalid server_id"):
            await handlers.remove_role(mock_bot, "bad", "123", "456")


class TestCreateTextChannel:
    """Tests for create_text_channel handler."""

    @pytest.mark.asyncio
    async def test_success(self, mock_bot, mock_guild):
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        created = MagicMock()
        created.name = "new-channel"
        created.id = 111
        mock_guild.create_text_channel = AsyncMock(return_value=created)

        result = await handlers.create_text_channel(mock_bot, str(mock_guild.id), "new-channel")

        assert result["channel_name"] == "new-channel"
        assert result["channel_id"] == "111"

    @pytest.mark.asyncio
    async def test_with_category(self, mock_bot, mock_guild, mock_category):
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_bot.fetch_channel = AsyncMock(return_value=mock_category)
        created = MagicMock()
        created.name = "new-channel"
        created.id = 111
        mock_guild.create_text_channel = AsyncMock(return_value=created)

        result = await handlers.create_text_channel(
            mock_bot,
            str(mock_guild.id),
            "new-channel",
            category_id=str(mock_category.id),
        )

        call_kwargs = mock_guild.create_text_channel.call_args[1]
        assert call_kwargs["category"] is mock_category
        assert result["channel_name"] == "new-channel"

    @pytest.mark.asyncio
    async def test_with_topic(self, mock_bot, mock_guild):
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        created = MagicMock()
        created.name = "new-channel"
        created.id = 111
        mock_guild.create_text_channel = AsyncMock(return_value=created)

        await handlers.create_text_channel(mock_bot, str(mock_guild.id), "new-channel", topic="My topic")

        call_kwargs = mock_guild.create_text_channel.call_args[1]
        assert call_kwargs["topic"] == "My topic"

    @pytest.mark.asyncio
    async def test_invalid_category_type(self, mock_bot, mock_guild, mock_text_channel):
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)

        with pytest.raises(ValueError, match="not a category channel"):
            await handlers.create_text_channel(
                mock_bot,
                str(mock_guild.id),
                "new-channel",
                category_id=str(mock_text_channel.id),
            )


class TestDeleteChannel:
    """Tests for delete_channel handler."""

    @pytest.mark.asyncio
    async def test_success(self, mock_bot, mock_text_channel):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)

        result = await handlers.delete_channel(mock_bot, str(mock_text_channel.id))

        mock_text_channel.delete.assert_called_once()
        assert result["channel_id"] == str(mock_text_channel.id)

    @pytest.mark.asyncio
    async def test_non_guild_channel_raises(self, mock_bot):
        dm_channel = MagicMock(spec=discord.DMChannel)
        mock_bot.fetch_channel = AsyncMock(return_value=dm_channel)

        with pytest.raises(ValueError, match="not a guild channel"):
            await handlers.delete_channel(mock_bot, "123456789012345678")

    @pytest.mark.asyncio
    async def test_reason_passed_through(self, mock_bot, mock_text_channel):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)

        await handlers.delete_channel(mock_bot, str(mock_text_channel.id), reason="Cleanup")

        mock_text_channel.delete.assert_called_once_with(reason="Cleanup")


class TestAddReaction:
    """Tests for add_reaction handler."""

    @pytest.mark.asyncio
    async def test_success(self, mock_bot, mock_text_channel, mock_message):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)

        result = await handlers.add_reaction(
            mock_bot,
            str(mock_text_channel.id),
            str(mock_message.id),
            "👍",
        )

        mock_message.add_reaction.assert_called_once_with("👍")
        assert result["emoji"] == "👍"
        assert result["message_id"] == str(mock_message.id)

    @pytest.mark.asyncio
    async def test_invalid_ids(self, mock_bot):
        with pytest.raises(ValueError, match="Invalid channel_id"):
            await handlers.add_reaction(mock_bot, "bad", "123", "👍")


class TestAddMultipleReactions:
    """Tests for add_multiple_reactions handler."""

    @pytest.mark.asyncio
    async def test_success(self, mock_bot, mock_text_channel, mock_message):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)

        result = await handlers.add_multiple_reactions(
            mock_bot,
            str(mock_text_channel.id),
            str(mock_message.id),
            ["👍", "❤️", "🎉"],
        )

        assert mock_message.add_reaction.call_count == 3
        assert result["emojis"] == ["👍", "❤️", "🎉"]

    @pytest.mark.asyncio
    async def test_empty_list(self, mock_bot, mock_text_channel, mock_message):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)

        result = await handlers.add_multiple_reactions(
            mock_bot,
            str(mock_text_channel.id),
            str(mock_message.id),
            [],
        )

        mock_message.add_reaction.assert_not_called()
        assert result["emojis"] == []


class TestRemoveReaction:
    """Tests for remove_reaction handler."""

    @pytest.mark.asyncio
    async def test_success(self, mock_bot, mock_text_channel, mock_message):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)

        result = await handlers.remove_reaction(
            mock_bot,
            str(mock_text_channel.id),
            str(mock_message.id),
            "👍",
        )

        mock_message.remove_reaction.assert_called_once_with("👍", mock_bot.user)
        assert result["emoji"] == "👍"

    @pytest.mark.asyncio
    async def test_client_user_none_raises(self, mock_bot, mock_text_channel, mock_message):
        mock_bot.user = None
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)

        with pytest.raises(RuntimeError, match="client user not available"):
            await handlers.remove_reaction(
                mock_bot,
                str(mock_text_channel.id),
                str(mock_message.id),
                "👍",
            )


class TestModerateMessage:
    """Tests for moderate_message handler."""

    @pytest.mark.asyncio
    async def test_delete_only(self, mock_bot, mock_text_channel, mock_message):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)

        result = await handlers.moderate_message(
            mock_bot,
            str(mock_text_channel.id),
            str(mock_message.id),
            "spam",
        )

        mock_message.delete.assert_called_once()
        assert result["deleted"] is True
        assert result["timeout_applied"] is False
        assert result["timeout_minutes"] is None

    @pytest.mark.asyncio
    async def test_with_timeout(self, mock_bot, mock_text_channel, mock_message):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)
        mock_member = MagicMock()
        mock_member.timeout = AsyncMock()
        mock_text_channel.guild.fetch_member = AsyncMock(return_value=mock_member)

        result = await handlers.moderate_message(
            mock_bot,
            str(mock_text_channel.id),
            str(mock_message.id),
            "spam",
            timeout_minutes=10,
        )

        mock_member.timeout.assert_called_once()
        assert result["deleted"] is True
        assert result["timeout_applied"] is True
        assert result["timeout_minutes"] == 10

    @pytest.mark.asyncio
    async def test_member_not_found_raises(self, mock_bot, mock_text_channel, mock_message):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)
        mock_text_channel.guild.fetch_member = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Not found"))

        with pytest.raises(ValueError, match="member not found"):
            await handlers.moderate_message(
                mock_bot,
                str(mock_text_channel.id),
                str(mock_message.id),
                "spam",
                timeout_minutes=10,
            )

    @pytest.mark.asyncio
    async def test_timeout_zero_treated_as_no_timeout(self, mock_bot, mock_text_channel, mock_message):
        mock_bot.fetch_channel = AsyncMock(return_value=mock_text_channel)
        mock_text_channel.fetch_message = AsyncMock(return_value=mock_message)

        result = await handlers.moderate_message(
            mock_bot,
            str(mock_text_channel.id),
            str(mock_message.id),
            "spam",
            timeout_minutes=0,
        )

        assert result["timeout_applied"] is False
