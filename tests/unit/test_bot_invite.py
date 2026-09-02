"""Unit tests for bot invite workflow: URL generation, guild listing, permission audit."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord.ext import commands

from discord_mcp import handlers, resources
from discord_mcp.handlers import PERMISSION_PRESETS, _describe_permissions

# ---------------------------------------------------------------------------
# generate_invite_url
# ---------------------------------------------------------------------------


class TestGenerateInviteUrl:
    """Tests for handlers.generate_invite_url."""

    @pytest.mark.asyncio
    async def test_default_preset_is_read_only(self):
        client = MagicMock(spec=commands.Bot)
        client.user = MagicMock()
        client.user.id = 111222333444555666

        result = await handlers.generate_invite_url(client)

        assert result["preset"] == "read_only"
        assert result["permissions_value"] == PERMISSION_PRESETS["read_only"]
        assert "client_id=111222333444555666" in result["url"]
        assert f"permissions={PERMISSION_PRESETS['read_only']}" in result["url"]

    @pytest.mark.asyncio
    async def test_read_only_preset(self):
        client = MagicMock(spec=commands.Bot)
        client.user = MagicMock()
        client.user.id = 100

        result = await handlers.generate_invite_url(client, preset="read_only")

        assert result["preset"] == "read_only"
        assert result["permissions_value"] == 66560

    @pytest.mark.asyncio
    async def test_moderate_preset(self):
        client = MagicMock(spec=commands.Bot)
        client.user = MagicMock()
        client.user.id = 100

        result = await handlers.generate_invite_url(client, preset="moderate")

        assert result["preset"] == "moderate"
        assert result["permissions_value"] == PERMISSION_PRESETS["moderate"]

    @pytest.mark.asyncio
    async def test_full_preset(self):
        client = MagicMock(spec=commands.Bot)
        client.user = MagicMock()
        client.user.id = 100

        result = await handlers.generate_invite_url(client, preset="full")

        assert result["preset"] == "full"
        assert result["permissions_value"] == PERMISSION_PRESETS["full"]

    @pytest.mark.asyncio
    async def test_custom_permissions_override(self):
        client = MagicMock(spec=commands.Bot)
        client.user = MagicMock()
        client.user.id = 100

        result = await handlers.generate_invite_url(client, permissions=8)

        assert result["permissions_value"] == 8
        assert result["preset"] is None
        assert "permissions=8" in result["url"]

    @pytest.mark.asyncio
    async def test_unknown_preset_raises(self):
        client = MagicMock(spec=commands.Bot)
        client.user = MagicMock()
        client.user.id = 100

        with pytest.raises(ValueError, match="Unknown preset"):
            await handlers.generate_invite_url(client, preset="nonexistent")

    @pytest.mark.asyncio
    async def test_fallback_to_env_var(self):
        client = MagicMock(spec=commands.Bot)
        client.user = None

        with patch.dict("os.environ", {"DISCORD_CLIENT_ID": "999888777"}):
            result = await handlers.generate_invite_url(client)

        assert "client_id=999888777" in result["url"]

    @pytest.mark.asyncio
    async def test_missing_app_id_raises(self):
        client = MagicMock(spec=commands.Bot)
        client.user = None

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Cannot determine application ID"):
                await handlers.generate_invite_url(client)


# ---------------------------------------------------------------------------
# _describe_permissions helper
# ---------------------------------------------------------------------------


class TestDescribePermissions:
    """Tests for the _describe_permissions helper."""

    def test_known_bits(self):
        names = _describe_permissions(0x00000400 | 0x00010000)
        assert "View Channels" in names
        assert "Read Message History" in names
        assert len(names) == 2

    def test_zero_returns_empty(self):
        assert _describe_permissions(0) == []

    def test_administrator(self):
        names = _describe_permissions(0x00000008)
        assert names == ["Administrator"]


# ---------------------------------------------------------------------------
# list_bot_guilds
# ---------------------------------------------------------------------------


class TestListBotGuilds:
    """Tests for resources.list_bot_guilds."""

    @pytest.mark.asyncio
    async def test_guild_with_read_access(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock(spec=discord.Guild)
        guild.id = 111
        guild.name = "Readable Guild"

        me = MagicMock(spec=discord.Member)
        perms = discord.Permissions(66560)  # View Channels + Read Message History
        me.guild_permissions = perms
        guild.me = me

        client.guilds = [guild]

        result = await resources.list_bot_guilds(client)

        assert len(result) == 1
        assert result[0]["id"] == "111"
        assert result[0]["name"] == "Readable Guild"
        assert result[0]["has_read_access"] is True

    @pytest.mark.asyncio
    async def test_guild_without_read_access(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock(spec=discord.Guild)
        guild.id = 222
        guild.name = "No Read Guild"

        me = MagicMock(spec=discord.Member)
        perms = discord.Permissions(0)
        me.guild_permissions = perms
        guild.me = me

        client.guilds = [guild]

        result = await resources.list_bot_guilds(client)

        assert result[0]["has_read_access"] is False

    @pytest.mark.asyncio
    async def test_empty_guilds(self):
        client = MagicMock(spec=commands.Bot)
        client.guilds = []

        result = await resources.list_bot_guilds(client)
        assert result == []


# ---------------------------------------------------------------------------
# audit_bot_permissions
# ---------------------------------------------------------------------------


class TestAuditBotPermissions:
    """Tests for resources.audit_bot_permissions."""

    @pytest.mark.asyncio
    async def test_partial_permissions(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock(spec=discord.Guild)
        guild.id = 111
        guild.name = "Partial Guild"

        me = MagicMock(spec=discord.Member)
        perms = discord.Permissions(66560)  # read_only satisfied only
        perms.administrator = False
        me.guild_permissions = perms
        guild.me = me

        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.audit_bot_permissions(client, "111")

        assert result["guild_id"] == "111"
        assert result["is_admin"] is False
        assert result["presets"]["read_only"]["satisfied"] is True
        assert result["presets"]["read_only"]["missing"] == []
        assert result["presets"]["moderate"]["satisfied"] is False
        assert len(result["presets"]["moderate"]["missing"]) > 0
        assert result["presets"]["full"]["satisfied"] is False

    @pytest.mark.asyncio
    async def test_admin_satisfies_all(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock(spec=discord.Guild)
        guild.id = 333
        guild.name = "Admin Guild"

        me = MagicMock(spec=discord.Member)
        perms = discord.Permissions(8)  # Administrator
        perms.administrator = True
        me.guild_permissions = perms
        guild.me = me

        client.fetch_guild = AsyncMock(return_value=guild)

        result = await resources.audit_bot_permissions(client, "333")

        assert result["is_admin"] is True
        for preset_info in result["presets"].values():
            assert preset_info["satisfied"] is True
            assert preset_info["missing"] == []

    @pytest.mark.asyncio
    async def test_missing_bot_member_raises(self):
        client = MagicMock(spec=commands.Bot)
        guild = MagicMock(spec=discord.Guild)
        guild.id = 444
        guild.me = None

        client.fetch_guild = AsyncMock(return_value=guild)

        with pytest.raises(ValueError, match="Bot member not found"):
            await resources.audit_bot_permissions(client, "444")
