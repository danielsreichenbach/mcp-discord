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

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- A Discord bot token with the following privileged intents enabled:
  - MESSAGE CONTENT INTENT
  - PRESENCE INTENT
  - SERVER MEMBERS INTENT

Create a bot at the [Discord Developer Portal](https://discord.com/developers/applications) and invite it to your server using the OAuth2 URL Generator.

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

Add a `.mcp.json` file to your project root:

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

Set `DISCORD_TOKEN` in your shell environment so that Claude Code can expand it at runtime.

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

### Smithery

This server is also available via [Smithery](https://smithery.ai). See `smithery.yaml` for the configuration schema.

## License

MIT License -- see [`LICENSE`](./LICENSE) for details.
