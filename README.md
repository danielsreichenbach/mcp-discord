# Discord MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that exposes Discord bot operations as tools. MCP clients like Claude Desktop connect via stdio transport, and the server proxies requests to the Discord API through `discord.py`.

This is a fork of [hanweg/mcp-discord](https://github.com/hanweg/mcp-discord), modified for personal use. It may diverge from upstream as features are added or changed to fit specific workflows.

## Available Tools

### Server Information
- `list_servers` -- List available servers
- `get_server_info` -- Get detailed server information
- `get_channels` -- List channels in a server
- `list_members` -- List server members and their roles
- `list_roles` -- List roles in a server
- `get_user_info` -- Get detailed information about a user

### Message Management
- `send_message` -- Send a message to a channel
- `read_messages` -- Read recent message history
- `edit_message` -- Edit a message sent by the bot
- `delete_message` -- Delete a single message
- `bulk_delete_messages` -- Delete multiple messages at once (2-100)
- `pin_message` -- Pin a message to the channel
- `unpin_message` -- Unpin a message
- `list_pinned_messages` -- List all pinned messages
- `add_reaction` -- Add a reaction to a message
- `add_multiple_reactions` -- Add multiple reactions to a message
- `remove_reaction` -- Remove a reaction from a message
- `moderate_message` -- Delete messages and timeout users

### Channel Management
- `create_text_channel` -- Create a new text channel
- `create_voice_channel` -- Create a new voice channel
- `create_category` -- Create a channel category
- `edit_channel` -- Modify channel properties (name, topic, slowmode, NSFW)
- `delete_channel` -- Delete an existing channel
- `reorder_channels` -- Change channel positions

### Member Moderation
- `kick_member` -- Kick a member from the server
- `ban_member` -- Ban a user with optional message deletion
- `unban_member` -- Remove a ban for a user
- `list_bans` -- List all banned users
- `edit_member` -- Modify member (nickname, timeout, mute/deafen)
- `remove_timeout` -- Remove a timeout from a member

### Role Management
- `add_role` -- Add a role to a user
- `remove_role` -- Remove a role from a user
- `create_role` -- Create a new role
- `edit_role` -- Modify role properties
- `delete_role` -- Delete a role
- `reorder_roles` -- Change role positions

### Invite Management
- `create_invite` -- Create a channel invite
- `list_server_invites` -- List all server invites
- `list_channel_invites` -- List channel-specific invites
- `delete_invite` -- Revoke an invite

### Audit & Emojis
- `get_audit_log` -- Retrieve server audit logs
- `list_emojis` -- List all custom emojis
- `create_emoji` -- Upload a new emoji
- `delete_emoji` -- Delete an emoji

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- A Discord bot token (see below)

### Creating the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application.
2. Go to **Bot** and click **Reset Token** to generate a bot token. Save it -- you will not see it again.
3. Under **Privileged Gateway Intents**, enable:
   - **Server Members Intent** -- required for member operations
   - **Message Content Intent** -- required for reading message text
4. Go to **OAuth2 > URL Generator**. Select the scopes:
   - `bot`
5. Under **Bot Permissions**, select the permissions below based on which features you need:

### Required Permissions

Permission names match the Discord Developer Portal (OAuth2 > URL Generator > Bot Permissions).

#### General Permissions

| Permission | Tools That Require It |
|------------|----------------------|
| **View Channels** | All read operations (`list_servers`, `get_server_info`, `get_channels`, `list_members`, `list_roles`, `get_user_info`) |
| **View Audit Log** | `get_audit_log` |
| **Manage Server** | `list_server_invites` |
| **Manage Roles** | `add_role`, `remove_role`, `create_role`, `edit_role`, `delete_role`, `reorder_roles` |
| **Manage Channels** | `create_text_channel`, `create_voice_channel`, `create_category`, `edit_channel`, `delete_channel`, `reorder_channels`, `list_channel_invites`, `delete_invite` |
| **Kick Members** | `kick_member` |
| **Ban Members** | `ban_member`, `unban_member`, `list_bans` |
| **Create Instant Invite** | `create_invite` |
| **Manage Nicknames** | `edit_member` (nickname changes) |
| **Manage Expressions** | `create_emoji`, `delete_emoji` |
| **Moderate Members** | `moderate_message`, `edit_member` (timeout), `remove_timeout` |

#### Text Permissions

| Permission | Tools That Require It |
|------------|----------------------|
| **Send Messages** | `send_message` |
| **Manage Messages** | `delete_message`, `bulk_delete_messages`, `moderate_message` |
| **Pin Messages** | `pin_message`, `unpin_message` |
| **Read Message History** | `read_messages`, `list_pinned_messages` |
| **Add Reactions** | `add_reaction`, `add_multiple_reactions`, `remove_reaction` |

#### Voice Permissions

| Permission | Tools That Require It |
|------------|----------------------|
| **Mute Members** | `edit_member` (voice mute) |
| **Deafen Members** | `edit_member` (voice deafen) |

#### Administrator (Recommended for full functionality)
For servers where the bot needs all management capabilities, enable **Administrator** which includes every permission listed above.

#### Minimal Permission Setup
For messaging and reactions only:
- View Channels
- Send Messages
- Read Message History
- Add Reactions

6. Copy the generated URL, open it in your browser, and add the bot to your server.

## Installation

```bash
git clone https://github.com/danielsreichenbach/mcp-discord.git
cd mcp-discord
uv sync
```

On Python 3.13+, install the `audioop-lts` compatibility package:

```bash
uv pip install audioop-lts
```

## Usage

### Running directly

```bash
DISCORD_TOKEN=<your_bot_token> uv run mcp-discord
```

### Claude Desktop

Add the following to your Claude Desktop configuration file:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "discord": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/mcp-discord",
        "run",
        "mcp-discord"
      ],
      "env": {
        "DISCORD_TOKEN": "your_bot_token"
      }
    }
  }
}
```

### Claude Code

Register the server with `claude mcp add`:

```bash
# Project-scoped (writes .mcp.json in the current directory)
claude mcp add -s project -e DISCORD_TOKEN="${DISCORD_TOKEN}" \
  discord -- uv --directory /absolute/path/to/mcp-discord run mcp-discord

# User-scoped (available in all projects)
claude mcp add -s user -e DISCORD_TOKEN="${DISCORD_TOKEN}" \
  discord -- uv --directory /absolute/path/to/mcp-discord run mcp-discord
```

Or add a `.mcp.json` file to your project root manually:

```json
{
  "mcpServers": {
    "discord": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/mcp-discord",
        "run",
        "mcp-discord"
      ],
      "env": {
        "DISCORD_TOKEN": "${DISCORD_TOKEN}"
      }
    }
  }
}
```

`DISCORD_TOKEN` must be set in your shell environment. Claude Code expands `${VAR}` references at runtime.

### Crush

Add the server to your `crush.json`:

```json
{
  "mcp": {
    "discord": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/mcp-discord",
        "run",
        "mcp-discord"
      ],
      "env": {
        "DISCORD_TOKEN": "$(echo $DISCORD_TOKEN)"
      }
    }
  }
}
```

### Docker

```bash
docker build -t mcp-discord .
docker run -e DISCORD_TOKEN=your_bot_token mcp-discord
```

## Development

### Running Tests

```bash
# Unit tests (mocked)
uv run pytest tests/unit/ -v

# Integration tests (requires real Discord token)
DISCORD_TOKEN=your_token TEST_SERVER_ID=123... uv run pytest tests/integration/ -v
```

### Code Quality

```bash
# Linting
uv run ruff check src/ tests/

# Type checking
uv run pyright src/ tests/
```

## License

MIT License -- see [`LICENSE`](./LICENSE) for details.
