# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

## [Unreleased]

## [0.2.0] - 2026-09-02

### Added

- 27 server management tools: member moderation (`kick_member`, `ban_member`, `unban_member`, `list_bans`, `edit_member`, `remove_timeout`), role management (`create_role`, `edit_role`, `delete_role`, `reorder_roles`), channel management (`create_voice_channel`, `create_category`, `reorder_channels`), invites (`create_invite`, `list_server_invites`, `list_channel_invites`, `delete_invite`), audit log (`get_audit_log`), emojis (`list_emojis`, `create_emoji`, `delete_emoji`), and pin/delete reactions.
- Bot invite and permission tools: `generate_invite_url`, `list_bot_guilds`, `audit_bot_permissions`
- `list_roles` tool and `list_threads` tool
- `read_messages` pagination (`limit`, `before`, `after`, `oldest_first`) plus attachment and embed metadata
- `client.py`, `handlers.py`, `resources.py` modules (4-module split with pure async handlers that take a `commands.Bot`)
- Unit, MCP protocol-level, and live integration test suites (mocked `discord.py` objects)
- Ruff linter/formatter and pyright type checker as dev dependencies, configured in `pyproject.toml`
- Type annotations across the source
- Conventional Commits and communication guidelines in `AGENTS.md`
- `DISCORD_TOKEN` read from the environment; startup requires it

### Changed

- Migrated from MCP SDK v1 (`FastMCP`) to MCP SDK v2 (`MCPServer` with a lifespan that manages the Discord bot connection)
- Split the server into `client.py`, `handlers.py`, `resources.py`, `server.py` modules
- Moved to `discord.py>=2.3.0` with `message_content` and `members` intents enabled
- `read_messages` output now includes message IDs, authors, content, and attachment/embed fields
- `get_server_info` uses `fetch_guild(with_counts=True)` for accurate member counts
- Tool functions return structured data (`dict`/`list`) instead of text
- `get_channels` now raises on errors instead of returning an error string
- Bot shutdown has timeouts to prevent hanging on Ctrl-C
- Moved the server import into `main()` in `__init__.py` and dropped the `asyncio.run` wrapper

### Fixed

- `get_server_info` returned `member_count: None` for servers with fewer than 500 members
- `read_messages` did not expose message IDs, making reaction and moderation tools unusable
- `message.delete()` was called with an unsupported `reason` keyword argument
- `remove_reaction` and `on_ready` accessed `.user`/`.name` without a None guard
- f-string without placeholders in the `get_user_info` response

### Removed

- Real-time monitoring implementation plan (`TODO-MONITORING.md`)
- Hardcoded `DISCORD_TOKEN` from the Dockerfile
- Smithery deployment configuration
- `tracemalloc` import and startup call

## [0.1.0] - 2026-02-17

Forked from [hanweg/mcp-discord](https://github.com/hanweg/mcp-discord). This version captures the state of the upstream project plus fork setup.

### Added

- MCP server exposing Discord bot operations over stdio transport
- Tools: `send_message`, `read_messages`, `get_user_info`, `moderate_message`
- Tools: `get_server_info`, `get_channels`, `list_members`, `list_servers`
- Tools: `add_role`, `remove_role`
- Tools: `create_text_channel`, `delete_channel`
- Tools: `add_reaction`, `add_multiple_reactions`, `remove_reaction`
- Windows stdout encoding fix for Unicode support
- `@require_discord_client` decorator to guard tool calls until bot is connected
- Dockerfile and Smithery configuration for deployment
- `AGENTS.md` with architecture documentation

### Changed

- Switched package management from pip/requirements.txt to uv
- Updated repository URLs to point to the fork
