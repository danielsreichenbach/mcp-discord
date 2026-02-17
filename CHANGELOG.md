# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

## [Unreleased]

### Added

- Ruff linter/formatter and pyright type checker as dev dependencies
- Ruff and pyright configuration in `pyproject.toml`
- Type annotations across `server.py` and `__init__.py`
- None checks after `guild.get_role()`, `guild.get_channel()`, and `discord_client.user` calls
- Conventional Commits guidelines in `AGENTS.md`
- `.mise.toml` for Python and uv tool versions
- Daniel S. Reichenbach as project author

### Changed

- Minimum Python version raised from 3.10 to 3.14
- `get_channels` tool now raises on errors instead of silently returning error text
- Emoji debug logging changed from `error` to `debug` level
- Import of `timedelta` directly instead of through `datetime` class
- README rewritten with step-by-step Discord bot setup, required permissions, and `claude mcp add` usage
- Codebase formatted with ruff (trailing commas, double quotes, line wrapping)

### Fixed

- `message.delete()` was called with unsupported `reason` keyword argument
- `discord_client.user` access without None guard in `remove_reaction`
- `bot.user.name` access without None guard in `on_ready`
- Unused `fetch_users` variable in `read_messages`
- f-string without placeholders in `get_user_info` response

### Removed

- `tracemalloc` import and startup call (unused overhead)
- Redundant `except Exception` re-raise in `__init__.py`
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
