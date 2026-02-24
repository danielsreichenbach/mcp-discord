"""Unit test fixtures with mocked Discord objects."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mocked Discord bot instance."""
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock()
    bot.user.id = 123456789012345678
    bot.user.name = "TestBot"
    bot.is_closed = MagicMock(return_value=False)
    return bot


@pytest.fixture
def mock_guild() -> MagicMock:
    """Create a mocked Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 987654321098765432
    guild.name = "Test Server"
    guild.owner_id = 111111111111111111

    # Async methods
    guild.fetch_member = AsyncMock()
    guild.ban = AsyncMock()
    guild.unban = AsyncMock()
    guild.bans = AsyncMock()
    guild.kick = AsyncMock()
    guild.create_role = AsyncMock()
    guild.edit = AsyncMock()
    guild.fetch_roles = AsyncMock()
    guild.fetch_emojis = AsyncMock()
    guild.create_custom_emoji = AsyncMock()
    guild.create_category = AsyncMock()
    guild.create_voice_channel = AsyncMock()
    guild.create_text_channel = AsyncMock()
    guild.edit_role_positions = AsyncMock()
    guild.audit_logs = MagicMock()
    guild.invites = AsyncMock()

    return guild


@pytest.fixture
def mock_member() -> MagicMock:
    """Create a mocked Discord member."""
    member = MagicMock(spec=discord.Member)
    member.id = 222222222222222222
    member.name = "TestUser"
    member.display_name = "Test User"
    member.discriminator = "1234"
    member.bot = False
    member.nick = None
    member.timed_out_until = None
    member.guild_permissions = MagicMock()
    member.guild_permissions.kick_members = True
    member.guild_permissions.ban_members = True
    member.guild_permissions.administrator = False
    member.top_role = MagicMock()
    member.top_role.position = 1

    # Async methods
    member.kick = AsyncMock()
    member.ban = AsyncMock()
    member.edit = AsyncMock()
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
    member.timeout = AsyncMock()

    return member


@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mocked Discord user (not a guild member)."""
    user = MagicMock(spec=discord.User)
    user.id = 333333333333333333
    user.name = "ExternalUser"
    user.discriminator = "5678"
    user.bot = False
    return user


@pytest.fixture
def mock_role() -> MagicMock:
    """Create a mocked Discord role."""
    role = MagicMock(spec=discord.Role)
    role.id = 444444444444444444
    role.name = "Test Role"
    role.color = MagicMock()
    role.color.value = 0x5865F2
    role.position = 5
    role.mentionable = True
    role.hoist = False
    role.permissions = MagicMock()
    role.permissions.value = 2048

    # Async methods
    role.edit = AsyncMock()
    role.delete = AsyncMock()

    return role


@pytest.fixture
def mock_text_channel() -> MagicMock:
    """Create a mocked Discord text channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 555555555555555555
    channel.name = "test-channel"
    channel.type = discord.ChannelType.text
    channel.guild = MagicMock(spec=discord.Guild)
    channel.guild.id = 987654321098765432
    channel.topic = "Test channel topic"
    channel.nsfw = False
    channel.slowmode_delay = 0
    channel.position = 1

    # Async methods
    channel.send = AsyncMock()
    channel.fetch_message = AsyncMock()
    channel.edit = AsyncMock()
    channel.delete = AsyncMock()
    channel.create_invite = AsyncMock()
    channel.invites = AsyncMock()
    channel.pins = AsyncMock()
    channel.delete_messages = AsyncMock()

    return channel


@pytest.fixture
def mock_voice_channel() -> MagicMock:
    """Create a mocked Discord voice channel."""
    channel = MagicMock(spec=discord.VoiceChannel)
    channel.id = 666666666666666666
    channel.name = "Test Voice"
    channel.guild = MagicMock(spec=discord.Guild)
    channel.guild.id = 987654321098765432
    channel.bitrate = 64000
    channel.user_limit = 10
    channel.position = 1

    # Async methods
    channel.edit = AsyncMock()
    channel.delete = AsyncMock()

    return channel


@pytest.fixture
def mock_category() -> MagicMock:
    """Create a mocked Discord category channel."""
    category = MagicMock(spec=discord.CategoryChannel)
    category.id = 777777777777777777
    category.name = "Test Category"
    category.guild = MagicMock(spec=discord.Guild)
    category.guild.id = 987654321098765432
    category.position = 0
    category.is_nsfw = MagicMock(return_value=False)

    # Async methods
    category.edit = AsyncMock()
    category.delete = AsyncMock()

    return category


@pytest.fixture
def mock_message() -> MagicMock:
    """Create a mocked Discord message."""
    message = MagicMock(spec=discord.Message)
    message.id = 888888888888888888
    message.content = "Test message content"
    message.author = MagicMock()
    message.author.id = 222222222222222222
    message.author.name = "TestUser"
    message.author.bot = False
    message.channel = MagicMock()
    message.channel.id = 555555555555555555
    message.guild = MagicMock()
    message.guild.id = 987654321098765432
    message.created_at = datetime.now(UTC)
    message.edited_at = None
    message.pinned = False
    message.mentions = []
    message.reactions = []
    message.jump_url = "https://discord.com/channels/987654321098765432/555555555555555555/888888888888888888"

    # Async methods
    message.delete = AsyncMock()
    message.edit = AsyncMock()
    message.pin = AsyncMock()
    message.unpin = AsyncMock()
    message.add_reaction = AsyncMock()
    message.remove_reaction = AsyncMock()

    return message


@pytest.fixture
def mock_invite() -> MagicMock:
    """Create a mocked Discord invite."""
    invite = MagicMock(spec=discord.Invite)
    invite.code = "abc123xyz"
    invite.guild = MagicMock()
    invite.guild.id = 987654321098765432
    invite.guild.name = "Test Server"
    invite.channel = MagicMock()
    invite.channel.id = 555555555555555555
    invite.channel.name = "test-channel"
    invite.inviter = MagicMock()
    invite.inviter.id = 123456789012345678
    invite.inviter.name = "TestBot"
    invite.uses = 5
    invite.max_uses = 10
    invite.max_age = 86400
    invite.temporary = False
    invite.created_at = datetime.now(UTC)
    invite.expires_at = None

    # Async methods
    invite.delete = AsyncMock()

    return invite


@pytest.fixture
def mock_ban_entry() -> MagicMock:
    """Create a mocked Discord ban entry."""
    ban = MagicMock(spec=discord.BanEntry)
    ban.user = MagicMock()
    ban.user.id = 333333333333333333
    ban.user.name = "BannedUser"
    ban.reason = "Test ban reason"
    return ban


@pytest.fixture
def mock_emoji() -> MagicMock:
    """Create a mocked Discord custom emoji."""
    emoji = MagicMock(spec=discord.Emoji)
    emoji.id = 999999999999999999
    emoji.name = "test_emoji"
    emoji.animated = False
    emoji.available = True
    emoji.managed = False
    emoji.require_colons = True
    emoji.url = "https://cdn.discordapp.com/emojis/999999999999999999.png"

    # Async methods
    emoji.delete = AsyncMock()

    return emoji


@pytest.fixture
def mock_audit_log_entry() -> MagicMock:
    """Create a mocked Discord audit log entry."""
    entry = MagicMock(spec=discord.AuditLogEntry)
    entry.id = 111111111111111111
    entry.action = MagicMock()
    entry.action.value = 20  # MEMBER_KICK
    entry.action.name = "kick"
    entry.user = MagicMock()
    entry.user.id = 123456789012345678
    entry.user.name = "TestBot"
    entry.target = MagicMock()
    entry.target.id = 222222222222222222
    entry.reason = "Test audit reason"
    entry.created_at = datetime.now(UTC)
    entry.before = None
    entry.after = None

    return entry


def setup_mock_guild_fetch(mock_bot: MagicMock, mock_guild: MagicMock) -> None:
    """Configure mock_bot to return mock_guild on fetch_guild."""
    mock_bot.fetch_guild = AsyncMock(return_value=mock_guild)


def setup_mock_channel_fetch(mock_bot: MagicMock, channel: MagicMock) -> None:
    """Configure mock_bot to return channel on fetch_channel."""
    mock_bot.fetch_channel = AsyncMock(return_value=channel)


def setup_mock_member_fetch(mock_guild: MagicMock, mock_member: MagicMock) -> None:
    """Configure mock_guild to return mock_member on fetch_member."""
    mock_guild.fetch_member = AsyncMock(return_value=mock_member)


def setup_mock_user_fetch(mock_bot: MagicMock, mock_user: MagicMock) -> None:
    """Configure mock_bot to return mock_user on fetch_user."""
    mock_bot.fetch_user = AsyncMock(return_value=mock_user)
