"""Integration tests for Discord tool handlers."""

import pytest

from discord_mcp import handlers, resources


class TestSendMessage:
    """Tests for send_message handler."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, discord_bot, test_channel_id):
        """Test sending a message to a channel."""
        result = await handlers.send_message(
            discord_bot, test_channel_id, "Test message from integration test"
        )

        assert "message_id" in result
        assert result["channel_id"] == test_channel_id

    @pytest.mark.asyncio
    async def test_send_message_invalid_channel(self, discord_bot):
        """Test sending to an invalid channel raises error."""
        with pytest.raises(ValueError, match="Invalid channel_id"):
            await handlers.send_message(discord_bot, "invalid", "test")


class TestReactions:
    """Tests for reaction handlers."""

    @pytest.mark.asyncio
    async def test_add_reaction(self, discord_bot, test_channel_id):
        """Test adding a reaction to a message."""
        # First send a message
        msg_result = await handlers.send_message(
            discord_bot, test_channel_id, "Reaction test message"
        )
        message_id = msg_result["message_id"]

        # Add reaction
        result = await handlers.add_reaction(
            discord_bot, test_channel_id, message_id, "👍"
        )

        assert result["emoji"] == "👍"
        assert result["message_id"] == message_id

    @pytest.mark.asyncio
    async def test_add_multiple_reactions(self, discord_bot, test_channel_id):
        """Test adding multiple reactions to a message."""
        msg_result = await handlers.send_message(
            discord_bot, test_channel_id, "Multiple reactions test"
        )
        message_id = msg_result["message_id"]

        result = await handlers.add_multiple_reactions(
            discord_bot, test_channel_id, message_id, ["👍", "❤️"]
        )

        assert result["emojis"] == ["👍", "❤️"]

    @pytest.mark.asyncio
    async def test_remove_reaction(self, discord_bot, test_channel_id):
        """Test removing a reaction from a message."""
        msg_result = await handlers.send_message(
            discord_bot, test_channel_id, "Remove reaction test"
        )
        message_id = msg_result["message_id"]

        # Add then remove
        await handlers.add_reaction(discord_bot, test_channel_id, message_id, "👍")
        result = await handlers.remove_reaction(
            discord_bot, test_channel_id, message_id, "👍"
        )

        assert result["emoji"] == "👍"


class TestChannels:
    """Tests for channel handlers."""

    @pytest.mark.asyncio
    async def test_create_and_delete_channel(self, discord_bot, test_server_id):
        """Test creating and deleting a text channel."""
        # Create channel
        create_result = await handlers.create_text_channel(
            discord_bot, test_server_id, "test-channel-temp"
        )

        assert "channel_id" in create_result
        assert create_result["channel_name"] == "test-channel-temp"

        # Delete channel
        delete_result = await handlers.delete_channel(
            discord_bot, create_result["channel_id"], reason="Test cleanup"
        )

        assert delete_result["channel_id"] == create_result["channel_id"]


class TestModeration:
    """Tests for moderation handlers."""

    @pytest.mark.asyncio
    async def test_moderate_message_delete_only(self, discord_bot, test_channel_id):
        """Test deleting a message without timeout."""
        msg_result = await handlers.send_message(
            discord_bot, test_channel_id, "Message to moderate"
        )
        message_id = msg_result["message_id"]

        result = await handlers.moderate_message(
            discord_bot, test_channel_id, message_id, "Test moderation"
        )

        assert result["deleted"] is True
        assert result["timeout_applied"] is False


class TestRoleManagement:
    """Tests for role management handlers. Requires TEST_ROLE_ID."""

    @pytest.mark.asyncio
    async def test_add_and_remove_role(
        self, discord_bot, test_server_id, test_user_id, test_role_id
    ):
        """Test adding then removing a role from a member."""
        add_result = await handlers.add_role(
            discord_bot, test_server_id, test_user_id, test_role_id
        )
        assert "role_name" in add_result
        assert "user_name" in add_result

        remove_result = await handlers.remove_role(
            discord_bot, test_server_id, test_user_id, test_role_id
        )
        assert "role_name" in remove_result
        assert "user_name" in remove_result


class TestMemberOperations:
    """Tests for member edit operations."""

    @pytest.mark.asyncio
    async def test_edit_member_nickname(self, discord_bot, test_server_id, test_user_id):
        """Test changing and clearing a member nickname."""
        result = await handlers.edit_member(
            discord_bot, test_server_id, test_user_id, nick="IntegrationTest"
        )
        assert "nick" in result["changes"]

        # Clear nickname
        await handlers.edit_member(
            discord_bot, test_server_id, test_user_id, nick=""
        )


class TestResources:
    """Tests for resource functions against a live server."""

    @pytest.mark.asyncio
    async def test_list_servers(self, discord_bot):
        """Test listing servers the bot is in."""
        result = await resources.list_servers(discord_bot)
        assert isinstance(result, list)
        if result:
            assert "id" in result[0]
            assert "name" in result[0]

    @pytest.mark.asyncio
    async def test_get_server_info(self, discord_bot, test_server_id):
        """Test getting server info."""
        result = await resources.get_server_info(discord_bot, test_server_id)
        assert result["id"] == test_server_id
        assert "name" in result
        assert "owner_id" in result

    @pytest.mark.asyncio
    async def test_get_channels(self, discord_bot, test_server_id):
        """Test listing channels in a server."""
        result = await resources.get_channels(discord_bot, test_server_id)
        assert isinstance(result, list)
        if result:
            assert "id" in result[0]
            assert "name" in result[0]

    @pytest.mark.asyncio
    async def test_list_members(self, discord_bot, test_server_id):
        """Test listing members in a server."""
        result = await resources.list_members(discord_bot, test_server_id, limit=5)
        assert isinstance(result, list)
        if result:
            assert "id" in result[0]
            assert "name" in result[0]

    @pytest.mark.asyncio
    async def test_list_roles(self, discord_bot, test_server_id):
        """Test listing roles in a server."""
        result = await resources.list_roles(discord_bot, test_server_id)
        assert isinstance(result, list)
        if result:
            assert "id" in result[0]
            assert "name" in result[0]

    @pytest.mark.asyncio
    async def test_read_messages(self, discord_bot, test_channel_id):
        """Test reading messages from a channel."""
        result = await resources.read_messages(discord_bot, test_channel_id, limit=5)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_user_info(self, discord_bot, test_user_id):
        """Test getting user info."""
        result = await resources.get_user_info(discord_bot, test_user_id)
        assert result["id"] == test_user_id
        assert "name" in result
