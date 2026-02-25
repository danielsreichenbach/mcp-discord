"""Unit tests for resource handler functions.

Tests for list_servers, get_server_info, get_channels, list_members,
list_roles, read_messages, and get_user_info.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from discord_mcp import resources


class TestListServers:
    """Tests for list_servers resource."""

    @pytest.mark.asyncio
    async def test_populated_guilds(self):
        client = MagicMock(spec=commands.Bot)
        guild1 = MagicMock()
        guild1.id = 111
        guild1.name = "Server One"
        guild1.member_count = 50
        guild1.created_at = datetime(2023, 1, 1, tzinfo=UTC)
        guild2 = MagicMock()
        guild2.id = 222
        guild2.name = "Server Two"
        guild2.member_count = 100
        guild2.created_at = datetime(2024, 6, 15, tzinfo=UTC)
        client.guilds = [guild1, guild2]

        result = await resources.list_servers(client)

        assert len(result) == 2
        assert result[0]["id"] == "111"
        assert result[0]["name"] == "Server One"
        assert result[0]["member_count"] == 50
        assert "created_at" in result[0]
        assert result[1]["id"] == "222"

    @pytest.mark.asyncio
    async def test_empty_guilds(self):
        client = MagicMock(spec=commands.Bot)
        client.guilds = []

        result = await resources.list_servers(client)
        assert result == []


class TestGetServerInfo:
    """Tests for get_server_info resource."""

    @pytest.mark.asyncio
    async def test_success(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock()
        guild.name = "Test Server"
        guild.id = 123
        guild.owner_id = 456
        guild.approximate_member_count = 200
        guild.created_at = datetime(2023, 1, 1, tzinfo=UTC)
        guild.description = "A test server"
        guild.premium_tier = 2
        guild.explicit_content_filter = MagicMock()
        guild.explicit_content_filter.__str__ = lambda self: "all_members"
        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.get_server_info(client, "123")

        client.fetch_guild.assert_called_once_with(123, with_counts=True)
        assert result["name"] == "Test Server"
        assert result["id"] == "123"
        assert result["owner_id"] == "456"
        assert result["member_count"] == 200
        assert result["description"] == "A test server"
        assert result["premium_tier"] == 2
        assert "created_at" in result
        assert "explicit_content_filter" in result

    @pytest.mark.asyncio
    async def test_invalid_id_raises(self):
        client = MagicMock(spec=commands.Bot)
        with pytest.raises(ValueError, match="Invalid server_id"):
            await resources.get_server_info(client, "bad")


class TestGetChannels:
    """Tests for get_channels resource."""

    @pytest.mark.asyncio
    async def test_returns_channels(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock()
        ch1 = MagicMock()
        ch1.id = 100
        ch1.name = "general"
        ch1.type = discord.ChannelType.text
        ch2 = MagicMock()
        ch2.id = 200
        ch2.name = "voice"
        ch2.type = discord.ChannelType.voice
        guild.fetch_channels = AsyncMock(return_value=[ch1, ch2])
        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.get_channels(client, "999")

        assert len(result) == 2
        assert result[0]["id"] == "100"
        assert result[0]["name"] == "general"
        assert result[1]["name"] == "voice"

    @pytest.mark.asyncio
    async def test_empty_channels(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock()
        guild.fetch_channels = AsyncMock(return_value=[])
        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.get_channels(client, "999")
        assert result == []


class TestListMembers:
    """Tests for list_members resource."""

    @pytest.mark.asyncio
    async def test_returns_members(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock()

        everyone_role = MagicMock(spec=discord.Role)
        everyone_role.id = 1
        admin_role = MagicMock(spec=discord.Role)
        admin_role.id = 2

        member = MagicMock()
        member.id = 555
        member.name = "TestUser"
        member.nick = "Testy"
        member.joined_at = datetime(2024, 1, 1, tzinfo=UTC)
        member.roles = [everyone_role, admin_role]

        async def mock_fetch_members(limit):
            yield member

        guild.fetch_members = MagicMock(side_effect=mock_fetch_members)
        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.list_members(client, "999", limit=50)

        assert len(result) == 1
        assert result[0]["id"] == "555"
        assert result[0]["name"] == "TestUser"
        assert result[0]["nick"] == "Testy"
        # roles[1:] skips @everyone
        assert result[0]["roles"] == ["2"]

    @pytest.mark.asyncio
    async def test_limit_capped_at_1000(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock()

        async def mock_fetch_members(limit):
            assert limit == 1000
            return
            yield

        guild.fetch_members = MagicMock(side_effect=mock_fetch_members)
        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.list_members(client, "999", limit=5000)
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_members(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock()

        async def mock_fetch_members(limit):
            return
            yield

        guild.fetch_members = MagicMock(side_effect=mock_fetch_members)
        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.list_members(client, "999")
        assert result == []

    @pytest.mark.asyncio
    async def test_member_without_joined_at(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock()

        everyone_role = MagicMock(spec=discord.Role)
        everyone_role.id = 1
        member = MagicMock()
        member.id = 555
        member.name = "Ghost"
        member.nick = None
        member.joined_at = None
        member.roles = [everyone_role]

        async def mock_fetch_members(limit):
            yield member

        guild.fetch_members = MagicMock(side_effect=mock_fetch_members)
        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.list_members(client, "999")
        assert result[0]["joined_at"] is None


class TestListRoles:
    """Tests for list_roles resource."""

    @pytest.mark.asyncio
    async def test_returns_sorted_roles(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock()

        role_low = MagicMock()
        role_low.id = 1
        role_low.name = "Low"
        role_low.color = MagicMock()
        role_low.color.__str__ = lambda self: "#000000"
        role_low.position = 1
        role_low.mentionable = False
        role_low.members = []

        role_high = MagicMock()
        role_high.id = 2
        role_high.name = "High"
        role_high.color = MagicMock()
        role_high.color.__str__ = lambda self: "#ff0000"
        role_high.position = 5
        role_high.mentionable = True
        role_high.members = [MagicMock(), MagicMock()]

        guild.fetch_roles = AsyncMock(return_value=[role_low, role_high])
        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.list_roles(client, "999")

        # Sorted by position descending
        assert result[0]["name"] == "High"
        assert result[0]["position"] == 5
        assert result[0]["member_count"] == 2
        assert result[1]["name"] == "Low"
        assert result[1]["position"] == 1

    @pytest.mark.asyncio
    async def test_role_without_members(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock()

        role = MagicMock()
        role.id = 1
        role.name = "Empty"
        role.color = MagicMock()
        role.color.__str__ = lambda self: "#000000"
        role.position = 0
        role.mentionable = False
        role.members = None

        guild.fetch_roles = AsyncMock(return_value=[role])
        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.list_roles(client, "999")
        assert result[0]["member_count"] is None

    @pytest.mark.asyncio
    async def test_dict_keys(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock()

        role = MagicMock()
        role.id = 1
        role.name = "Role"
        role.color = MagicMock()
        role.color.__str__ = lambda self: "#000000"
        role.position = 0
        role.mentionable = True
        role.members = []

        guild.fetch_roles = AsyncMock(return_value=[role])
        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.list_roles(client, "999")
        expected_keys = {"id", "name", "color", "position", "mentionable", "member_count"}
        assert set(result[0].keys()) == expected_keys


class TestReadMessages:
    """Tests for read_messages resource."""

    @pytest.mark.asyncio
    async def test_returns_messages(self):
        client = MagicMock(spec=commands.Bot)
        channel = MagicMock(spec=discord.TextChannel)

        msg = MagicMock()
        msg.id = 888
        msg.author = MagicMock()
        msg.author.__str__ = lambda self: "User#1234"
        msg.content = "Hello world"
        msg.created_at = datetime(2024, 1, 1, tzinfo=UTC)
        msg.reactions = []

        async def mock_history(limit):
            yield msg

        channel.history = MagicMock(side_effect=mock_history)
        client.fetch_channel = AsyncMock(return_value=channel)

        result = await resources.read_messages(client, "555", limit=10)

        assert len(result) == 1
        assert result[0]["id"] == "888"
        assert result[0]["content"] == "Hello world"
        assert result[0]["reactions"] == []

    @pytest.mark.asyncio
    async def test_limit_capped_at_100(self):
        client = MagicMock(spec=commands.Bot)
        channel = MagicMock(spec=discord.TextChannel)

        async def mock_history(limit):
            assert limit == 100
            return
            yield

        channel.history = MagicMock(side_effect=mock_history)
        client.fetch_channel = AsyncMock(return_value=channel)

        await resources.read_messages(client, "555", limit=500)

    @pytest.mark.asyncio
    async def test_str_emoji_reaction(self):
        client = MagicMock(spec=commands.Bot)
        channel = MagicMock(spec=discord.TextChannel)

        reaction = MagicMock()
        reaction.emoji = "👍"
        reaction.count = 3

        msg = MagicMock()
        msg.id = 888
        msg.author = MagicMock()
        msg.author.__str__ = lambda self: "User"
        msg.content = "test"
        msg.created_at = datetime(2024, 1, 1, tzinfo=UTC)
        msg.reactions = [reaction]

        async def mock_history(limit):
            yield msg

        channel.history = MagicMock(side_effect=mock_history)
        client.fetch_channel = AsyncMock(return_value=channel)

        result = await resources.read_messages(client, "555")
        assert result[0]["reactions"][0]["emoji"] == "👍"
        assert result[0]["reactions"][0]["count"] == 3

    @pytest.mark.asyncio
    async def test_named_emoji_reaction(self):
        client = MagicMock(spec=commands.Bot)
        channel = MagicMock(spec=discord.TextChannel)

        # Not a str, has .name attribute — takes the hasattr(emoji, "name") path
        emoji_obj = MagicMock(spec=["name"])
        emoji_obj.name = "custom_emoji"
        reaction = MagicMock()
        reaction.emoji = emoji_obj
        reaction.count = 1

        msg = MagicMock()
        msg.id = 888
        msg.author = MagicMock()
        msg.author.__str__ = lambda self: "User"
        msg.content = "test"
        msg.created_at = datetime(2024, 1, 1, tzinfo=UTC)
        msg.reactions = [reaction]

        async def mock_history(limit):  # noqa: ANN001
            yield msg

        channel.history = MagicMock(side_effect=mock_history)
        client.fetch_channel = AsyncMock(return_value=channel)

        result = await resources.read_messages(client, "555")
        assert result[0]["reactions"][0]["emoji"] == "custom_emoji"

    @pytest.mark.asyncio
    async def test_id_only_emoji_reaction(self):
        client = MagicMock(spec=commands.Bot)
        channel = MagicMock(spec=discord.TextChannel)

        # Has .name but it's None, and has .id — takes the str(emoji.id) path
        emoji_obj = MagicMock(spec=["name", "id"])
        emoji_obj.name = None
        emoji_obj.id = 999999
        reaction = MagicMock()
        reaction.emoji = emoji_obj
        reaction.count = 2

        msg = MagicMock()
        msg.id = 888
        msg.author = MagicMock()
        msg.author.__str__ = lambda self: "User"
        msg.content = "test"
        msg.created_at = datetime(2024, 1, 1, tzinfo=UTC)
        msg.reactions = [reaction]

        async def mock_history(limit):  # noqa: ANN001
            yield msg

        channel.history = MagicMock(side_effect=mock_history)
        client.fetch_channel = AsyncMock(return_value=channel)

        result = await resources.read_messages(client, "555")
        # Falls through to str(emoji.id) path
        assert result[0]["reactions"][0]["emoji"] == "999999"

    @pytest.mark.asyncio
    async def test_non_text_channel_raises(self):
        client = MagicMock(spec=commands.Bot)
        channel = MagicMock(spec=discord.VoiceChannel)
        client.fetch_channel = AsyncMock(return_value=channel)

        with pytest.raises(ValueError, match="not a text channel"):
            await resources.read_messages(client, "555")


class TestGetUserInfo:
    """Tests for get_user_info resource."""

    @pytest.mark.asyncio
    async def test_success(self):
        client = MagicMock(spec=commands.Bot)
        user = MagicMock()
        user.id = 333
        user.name = "TestUser"
        user.discriminator = "1234"
        user.bot = False
        user.created_at = datetime(2023, 6, 1, tzinfo=UTC)
        client.fetch_user = AsyncMock(return_value=user)

        result = await resources.get_user_info(client, "333")

        assert result["id"] == "333"
        assert result["name"] == "TestUser"
        assert result["discriminator"] == "1234"
        assert result["bot"] is False
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_invalid_id_raises(self):
        client = MagicMock(spec=commands.Bot)
        with pytest.raises(ValueError, match="Invalid user_id"):
            await resources.get_user_info(client, "not_an_id")
