"""Unit tests for role management handlers.

Tests for create_role, edit_role, delete_role, and reorder_roles.
"""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from discord_mcp import handlers


class TestCreateRole:
    """Tests for create_role handler."""

    @pytest.mark.asyncio
    async def test_create_role_success(self, mock_bot, mock_guild):
        """Test creating a role with all parameters."""
        # Setup
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_role = MagicMock()
        mock_role.id = 444444444444444444
        mock_role.name = "Test Role"
        mock_role.color = MagicMock()
        mock_role.color.value = 0x5865F2
        mock_role.position = 1
        mock_role.mentionable = True
        mock_role.hoist = False
        mock_role.permissions = MagicMock()
        mock_role.permissions.value = 2048
        mock_guild.create_role = AsyncMock(return_value=mock_role)

        # Execute
        result = await handlers.create_role(
            mock_bot,
            str(mock_guild.id),
            name="Test Role",
            permissions=2048,
            color=0x5865F2,
            hoist=False,
            mentionable=True,
            reason="Test role creation",
        )

        # Verify
        mock_guild.create_role.assert_called_once()
        assert result["role_id"] == str(mock_role.id)
        assert result["role_name"] == "Test Role"
        assert result["color"] == 0x5865F2
        assert result["mentionable"] is True

    @pytest.mark.asyncio
    async def test_create_role_minimal(self, mock_bot, mock_guild):
        """Test creating a role with only required parameters."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_role = MagicMock()
        mock_role.id = 444444444444444444
        mock_role.name = "Simple Role"
        mock_role.color = MagicMock()
        mock_role.color.value = 0x000000
        mock_role.position = 1
        mock_role.mentionable = False
        mock_role.hoist = False
        mock_role.permissions = MagicMock()
        mock_role.permissions.value = 0
        mock_guild.create_role = AsyncMock(return_value=mock_role)

        result = await handlers.create_role(mock_bot, str(mock_guild.id), name="Simple Role")

        assert result["role_id"] == str(mock_role.id)
        assert result["role_name"] == "Simple Role"

    @pytest.mark.asyncio
    async def test_create_role_invalid_server(self, mock_bot):
        """Test create role with invalid server ID format."""
        with pytest.raises(ValueError, match="Invalid server_id"):
            await handlers.create_role(mock_bot, "invalid", name="Test")

    @pytest.mark.asyncio
    async def test_create_role_server_not_found(self, mock_bot):
        """Test create role when server doesn't exist."""
        mock_bot.fetch_guild = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Guild not found"))

        with pytest.raises(ValueError, match="Server.*not found"):
            await handlers.create_role(mock_bot, "999999999999999999", name="Test")

    @pytest.mark.asyncio
    async def test_create_role_forbidden(self, mock_bot, mock_guild):
        """Test create role when bot lacks permissions."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.create_role = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Missing permissions"))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.create_role(mock_bot, str(mock_guild.id), name="Test Role")


class TestEditRole:
    """Tests for edit_role handler."""

    @pytest.mark.asyncio
    async def test_edit_role_name(self, mock_bot, mock_guild, mock_role):
        """Test editing role name."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_roles = AsyncMock(return_value=[mock_role])
        mock_role.edit = AsyncMock()
        mock_role.name = "Updated Name"

        result = await handlers.edit_role(mock_bot, str(mock_guild.id), str(mock_role.id), name="Updated Name")

        mock_role.edit.assert_called_once()
        assert "name" in result["changes"]
        assert result["role_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_edit_role_color(self, mock_bot, mock_guild, mock_role):
        """Test editing role color."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_roles = AsyncMock(return_value=[mock_role])
        mock_role.edit = AsyncMock()
        mock_role.color = MagicMock()
        mock_role.color.value = 0xFF0000

        result = await handlers.edit_role(mock_bot, str(mock_guild.id), str(mock_role.id), color=0xFF0000)

        assert "color" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_role_permissions(self, mock_bot, mock_guild, mock_role):
        """Test editing role permissions."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_roles = AsyncMock(return_value=[mock_role])
        mock_role.edit = AsyncMock()

        result = await handlers.edit_role(
            mock_bot,
            str(mock_guild.id),
            str(mock_role.id),
            permissions=8,  # Administrator
        )

        assert "permissions" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_role_multiple_properties(self, mock_bot, mock_guild, mock_role):
        """Test editing multiple role properties at once."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_roles = AsyncMock(return_value=[mock_role])
        mock_role.edit = AsyncMock()

        result = await handlers.edit_role(
            mock_bot,
            str(mock_guild.id),
            str(mock_role.id),
            name="New Name",
            color=0x00FF00,
            mentionable=True,
            hoist=True,
        )

        assert "name" in result["changes"]
        assert "color" in result["changes"]
        assert "mentionable" in result["changes"]
        assert "hoist" in result["changes"]

    @pytest.mark.asyncio
    async def test_edit_role_not_found(self, mock_bot, mock_guild):
        """Test editing a role that doesn't exist."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_roles = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="Role.*not found"):
            await handlers.edit_role(mock_bot, str(mock_guild.id), "999999999999999999", name="Test")


class TestDeleteRole:
    """Tests for delete_role handler."""

    @pytest.mark.asyncio
    async def test_delete_role_success(self, mock_bot, mock_guild, mock_role):
        """Test deleting a role."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_roles = AsyncMock(return_value=[mock_role])
        mock_role.delete = AsyncMock()

        result = await handlers.delete_role(mock_bot, str(mock_guild.id), str(mock_role.id), reason="Test cleanup")

        mock_role.delete.assert_called_once()
        assert result["deleted"] is True
        assert result["role_name"] == mock_role.name
        assert result["role_id"] == str(mock_role.id)

    @pytest.mark.asyncio
    async def test_delete_role_forbidden(self, mock_bot, mock_guild, mock_role):
        """Test deleting a role when bot lacks permissions."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)
        mock_guild.fetch_roles = AsyncMock(return_value=[mock_role])
        mock_role.delete = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Cannot delete managed role"))

        with pytest.raises(PermissionError, match="Missing permissions"):
            await handlers.delete_role(mock_bot, str(mock_guild.id), str(mock_role.id))


class TestReorderRoles:
    """Tests for reorder_roles handler."""

    @pytest.mark.asyncio
    async def test_reorder_roles_success(self, mock_bot, mock_guild, mock_role):
        """Test reordering roles."""
        mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)

        role1 = MagicMock()
        role1.id = 111111111111111111
        role1.name = "Role A"
        role1.position = 1

        role2 = MagicMock()
        role2.id = 222222222222222222
        role2.name = "Role B"
        role2.position = 2

        mock_guild.fetch_roles = AsyncMock(return_value=[role1, role2])
        mock_guild.edit_role_positions = AsyncMock(return_value=[role1, role2])

        result = await handlers.reorder_roles(
            mock_bot,
            str(mock_guild.id),
            [{"id": str(role1.id), "position": 2}, {"id": str(role2.id), "position": 1}],
            reason="Reorder test",
        )

        assert result["reordered"] is True
        assert len(result["roles"]) == 2
