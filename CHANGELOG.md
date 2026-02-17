# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

## [Unreleased]

### Added

- `list_roles` tool to list all roles in a server with position, color, and mentionable status
- `_ServerState` class to hold runtime state (bot, MCP server, ready event)
- `_register_handlers` function to register MCP tool handlers on a server instance
- `_parse_id`, `_require_text_channel`, `_require_guild_channel`, `_fetch_role` helper functions
- Startup timeout: bot must connect within 30 seconds or the server exits with an error
- Ruff linter/formatter and pyright type checker as dev dependencies
- Ruff and pyright configuration in `pyproject.toml`
- Type annotations across `server.py` and `__init__.py`
- Conventional Commits guidelines in `AGENTS.md`
- `.mise.toml` for Python and uv tool versions
- Daniel S. Reichenbach as project author
- `client.py` module with Discord bot setup, utilities, and lifespan context manager
- `handlers.py` module with pure async functions for tool actions
- `resources.py` module with pure async functions for read-only data
- Integration test infrastructure using pytest

### Changed

- Minimum Python version lowered from 3.14 to 3.12
- `read_messages` output now includes message IDs (e.g. `[123456] author: content`)
- `get_server_info` uses `fetch_guild(with_counts=True)` for accurate member counts
- Server module import deferred to `main()` in `__init__.py`
- `server.py` restructured: global state replaced with `_ServerState`, handlers extracted to `_register_handlers`
- Startup sequence waits for Discord bot readiness before accepting MCP requests
- `get_channels` tool now raises on errors instead of silently returning error text
- Emoji debug logging changed from `error` to `debug` level
- Import of `timedelta` directly instead of through `datetime` class
- README rewritten with step-by-step Discord bot setup, required permissions, and `claude mcp add` usage
- Codebase formatted with ruff (trailing commas, double quotes, line wrapping)
- Refactored to FastMCP with 4-module split (client.py, handlers.py, resources.py, server.py)
- Discord INFO logging suppressed; only discord-mcp logs at INFO level
- Bot shutdown now has timeouts to prevent hanging on CTRL-C

### Fixed

- `get_server_info` returned `member_count: None` for servers with fewer than 500 members
- `read_messages` did not expose message IDs, making reaction and moderation tools unusable
- `message.delete()` was called with unsupported `reason` keyword argument
- `discord_client.user` access without None guard in `remove_reaction`
- `bot.user.name` access without None guard in `on_ready`
- Unused `fetch_users` variable in `read_messages`
- f-string without placeholders in `get_user_info` response
- `__init__.py` wrapped sync `server.main()` in `asyncio.run()`, causing type error

### Removed

- Hardcoded `DISCORD_TOKEN` environment variable from Dockerfile
- `tracemalloc` import and startup call (unused overhead)
- Redundant `except Exception` re-raise in `__init__.py`
- `server` from `__all__` in `__init__.py`
- Smithery deployment configuration (`smithery.yaml` and README section)

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
