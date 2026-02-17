# Discord MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that exposes Discord bot operations as tools. MCP clients like Claude Desktop connect via stdio transport, and the server proxies requests to the Discord API through `discord.py`.

This is a fork of [hanweg/mcp-discord](https://github.com/hanweg/mcp-discord), modified for personal use. It may diverge from upstream as features are added or changed to fit specific workflows.

## Available Tools

### Server Information
- `list_servers` -- List available servers
- `get_server_info` -- Get detailed server information
- `get_channels` -- List channels in a server
- `list_members` -- List server members and their roles
- `get_user_info` -- Get detailed information about a user

### Message Management
- `send_message` -- Send a message to a channel
- `read_messages` -- Read recent message history
- `add_reaction` -- Add a reaction to a message
- `add_multiple_reactions` -- Add multiple reactions to a message
- `remove_reaction` -- Remove a reaction from a message
- `moderate_message` -- Delete messages and timeout users

### Channel Management
- `create_text_channel` -- Create a new text channel
- `delete_channel` -- Delete an existing channel

### Role Management
- `add_role` -- Add a role to a user
- `remove_role` -- Remove a role from a user

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- A Discord bot token (see below)

### Creating the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application.
2. Go to **Bot** and click **Reset Token** to generate a bot token. Save it -- you will not see it again.
3. Under **Privileged Gateway Intents**, enable:
   - **Server Members Intent** -- required for `list_members`, `add_role`, `remove_role`
   - **Message Content Intent** -- required for `read_messages` to access message text
4. Go to **OAuth2 > URL Generator**. Select the scopes:
   - `bot`
5. Under **Bot Permissions**, select:
   - **Manage Channels** -- `create_text_channel`, `delete_channel`
   - **Manage Roles** -- `add_role`, `remove_role`
   - **Manage Messages** -- `moderate_message` (delete messages)
   - **Moderate Members** -- `moderate_message` (timeout users)
   - **Send Messages** -- `send_message`
   - **Read Message History** -- `read_messages`
   - **Add Reactions** -- `add_reaction`, `add_multiple_reactions`, `remove_reaction`
   - **View Channels** -- all channel and server read operations
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

## License

MIT License -- see [`LICENSE`](./LICENSE) for details.
