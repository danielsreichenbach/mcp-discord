"""MCP-level integration tests.

Tests tool and resource discovery and execution through the MCP protocol
with a mock Discord bot injected via lifespan patching.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest


class TestToolDiscovery:
    """Tests for MCP tool listing."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_all(self, mcp_session):
        session, _ = mcp_session
        result = await session.list_tools()
        tool_names = {t.name for t in result.tools}

        expected = {
            "send_message",
            "add_role",
            "remove_role",
            "create_text_channel",
            "delete_channel",
            "add_reaction",
            "add_multiple_reactions",
            "remove_reaction",
            "moderate_message",
            "kick_member",
            "ban_member",
            "unban_member",
            "list_bans",
            "edit_member",
            "remove_timeout",
            "create_role",
            "edit_role",
            "delete_role",
            "reorder_roles",
            "edit_channel",
            "create_category",
            "create_voice_channel",
            "reorder_channels",
            "create_invite",
            "list_server_invites",
            "list_channel_invites",
            "delete_invite",
            "edit_message",
            "delete_message",
            "bulk_delete_messages",
            "pin_message",
            "unpin_message",
            "list_pinned_messages",
            "get_audit_log",
            "list_emojis",
            "create_emoji",
            "delete_emoji",
            "list_threads",
            "list_servers",
            "get_server_info",
            "get_channels",
            "list_members",
            "list_roles",
            "read_messages",
            "get_user_info",
            "generate_invite_url",
            "list_bot_guilds",
            "audit_bot_permissions",
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"

    @pytest.mark.asyncio
    async def test_tool_count(self, mcp_session):
        session, _ = mcp_session
        result = await session.list_tools()
        # At least 48 tools registered
        assert len(result.tools) >= 48


class TestResourceDiscovery:
    """Tests for MCP resource listing."""

    @pytest.mark.asyncio
    async def test_list_resources(self, mcp_session):
        session, _ = mcp_session
        result = await session.list_resource_templates()
        uris = {str(r.uriTemplate) for r in result.resourceTemplates}

        expected_patterns = {
            "discord://servers/{server_id}",
            "discord://servers/{server_id}/channels",
            "discord://servers/{server_id}/members",
            "discord://servers/{server_id}/roles",
            "discord://channels/{channel_id}/messages",
        }
        assert expected_patterns.issubset(uris), f"Missing: {expected_patterns - uris}"

    @pytest.mark.asyncio
    async def test_static_resources(self, mcp_session):
        session, _ = mcp_session
        result = await session.list_resources()
        uris = {str(r.uri) for r in result.resources}
        assert "discord://servers" in uris


class TestToolExecution:
    """Tests for representative tool execution through MCP."""

    @pytest.mark.asyncio
    async def test_send_message(self, mcp_session):
        session, mock_bot = mcp_session
        sent_msg = MagicMock()
        sent_msg.id = 111222333

        channel = mock_bot.fetch_channel.return_value
        channel.send = AsyncMock(return_value=sent_msg)

        result = await session.call_tool(
            "send_message",
            {"channel_id": "555555555555555555", "content": "Hello from MCP"},
        )

        assert not result.isError
        data = json.loads(result.content[0].text)
        assert "message_id" in data

    @pytest.mark.asyncio
    async def test_kick_member(self, mcp_session):
        session, mock_bot = mcp_session
        guild = mock_bot.fetch_guild.return_value
        member = MagicMock(spec=discord.Member)
        member.id = 222222222222222222
        member.name = "TestUser"
        member.kick = AsyncMock()
        guild.fetch_member = AsyncMock(return_value=member)

        result = await session.call_tool(
            "kick_member",
            {
                "server_id": "987654321098765432",
                "user_id": "222222222222222222",
                "reason": "test",
            },
        )

        assert not result.isError
        data = json.loads(result.content[0].text)
        assert data["kicked"] is True
        assert data["user_name"] == "TestUser"

    @pytest.mark.asyncio
    async def test_create_role(self, mcp_session):
        session, mock_bot = mcp_session
        guild = mock_bot.fetch_guild.return_value
        new_role = MagicMock(spec=discord.Role)
        new_role.id = 999
        new_role.name = "NewRole"
        new_role.position = 3
        guild.create_role = AsyncMock(return_value=new_role)

        result = await session.call_tool(
            "create_role",
            {"server_id": "987654321098765432", "name": "NewRole"},
        )

        assert not result.isError
        data = json.loads(result.content[0].text)
        assert data["role_name"] == "NewRole"

    @pytest.mark.asyncio
    async def test_list_servers(self, mcp_session):
        session, _ = mcp_session

        result = await session.call_tool("list_servers", {})

        assert not result.isError
        assert len(result.content) >= 1
        data = json.loads(result.content[0].text)
        assert data["name"] == "Test Server"

    @pytest.mark.asyncio
    async def test_get_user_info(self, mcp_session):
        session, _ = mcp_session

        result = await session.call_tool("get_user_info", {"user_id": "222222222222222222"})

        assert not result.isError
        data = json.loads(result.content[0].text)
        assert data["name"] == "TestUser"

    @pytest.mark.asyncio
    async def test_read_messages_with_pagination(self, mcp_session):
        session, mock_bot = mcp_session

        msg = MagicMock()
        msg.id = 999
        msg.author = MagicMock()
        msg.author.__str__ = lambda self: "Author"
        msg.content = "Historical message"
        msg.created_at = MagicMock()
        msg.created_at.isoformat = MagicMock(return_value="2024-01-01T00:00:00+00:00")
        msg.reactions = []
        msg.attachments = []
        msg.embeds = []

        channel = mock_bot.fetch_channel.return_value

        async def mock_history(**kwargs):
            yield msg

        channel.history = MagicMock(side_effect=mock_history)

        result = await session.call_tool(
            "read_messages",
            {
                "channel_id": "555555555555555555",
                "before": "123456789012345678",
                "limit": 50,
            },
        )

        assert not result.isError
        assert len(result.content) >= 1
        data = json.loads(result.content[0].text)
        assert data["content"] == "Historical message"

    @pytest.mark.asyncio
    async def test_list_threads(self, mcp_session):
        session, mock_bot = mcp_session
        guild = mock_bot.fetch_guild.return_value

        ch = MagicMock(spec=discord.TextChannel)
        ch.id = 555555555555555555
        ch.name = "general"

        thread = MagicMock(spec=discord.Thread)
        thread.id = 1001
        thread.name = "help-thread"
        thread.archived = False
        thread.message_count = 42
        thread.member_count = 5
        thread.created_at = MagicMock()
        thread.created_at.isoformat = MagicMock(return_value="2024-01-01T00:00:00+00:00")
        ch.threads = [thread]

        guild.fetch_channels = AsyncMock(return_value=[ch])

        result = await session.call_tool(
            "list_threads",
            {"server_id": "987654321098765432"},
        )

        assert not result.isError
        data = json.loads(result.content[0].text)
        assert data["count"] >= 1
        assert data["threads"][0]["name"] == "help-thread"


    @pytest.mark.asyncio
    async def test_generate_invite_url(self, mcp_session):
        session, _ = mcp_session

        result = await session.call_tool("generate_invite_url", {})

        assert not result.isError
        data = json.loads(result.content[0].text)
        assert "url" in data
        assert data["preset"] == "read_only"
        assert "discord.com/oauth2/authorize" in data["url"]

    @pytest.mark.asyncio
    async def test_generate_invite_url_with_preset(self, mcp_session):
        session, _ = mcp_session

        result = await session.call_tool("generate_invite_url", {"preset": "moderate"})

        assert not result.isError
        data = json.loads(result.content[0].text)
        assert data["preset"] == "moderate"

    @pytest.mark.asyncio
    async def test_list_bot_guilds(self, mcp_session):
        session, _ = mcp_session

        result = await session.call_tool("list_bot_guilds", {})

        assert not result.isError
        data = json.loads(result.content[0].text)
        assert data["id"] == "987654321098765432"
        assert data["name"] == "Test Server"
        assert "has_read_access" in data

    @pytest.mark.asyncio
    async def test_audit_bot_permissions(self, mcp_session):
        session, _ = mcp_session

        result = await session.call_tool(
            "audit_bot_permissions",
            {"server_id": "987654321098765432"},
        )

        assert not result.isError
        data = json.loads(result.content[0].text)
        assert "presets" in data
        assert "read_only" in data["presets"]


class TestErrorHandling:
    """Tests for error propagation through MCP."""

    @pytest.mark.asyncio
    async def test_value_error_returns_error(self, mcp_session):
        session, _ = mcp_session

        result = await session.call_tool(
            "send_message",
            {"channel_id": "invalid", "content": "test"},
        )

        assert result.isError
        assert "Invalid channel_id" in result.content[0].text

    @pytest.mark.asyncio
    async def test_permission_error_returns_error(self, mcp_session):
        session, mock_bot = mcp_session
        guild = mock_bot.fetch_guild.return_value
        member = MagicMock(spec=discord.Member)
        member.id = 222222222222222222
        member.name = "TestUser"
        member.kick = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Missing permissions"))
        guild.fetch_member = AsyncMock(return_value=member)

        result = await session.call_tool(
            "kick_member",
            {
                "server_id": "987654321098765432",
                "user_id": "222222222222222222",
            },
        )

        assert result.isError

    @pytest.mark.asyncio
    async def test_missing_required_arg_returns_error(self, mcp_session):
        session, _ = mcp_session

        result = await session.call_tool(
            "send_message",
            {"channel_id": "555555555555555555"},
        )

        assert result.isError
