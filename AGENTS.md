# AGENTS.md

Guidance for coding agents working in this repository. Follows the [agents.md](https://agents.md/) convention.

## Project Overview

MCP server that exposes Discord bot operations as MCP tools. Clients connect via stdio transport, and the server proxies requests to the Discord API through `discord.py`.

## Setup Commands

```bash
uv venv && source .venv/bin/activate
uv sync --dev
```

## Development Commands

```bash
# Run (requires DISCORD_TOKEN env var)
DISCORD_TOKEN=<token> uv run mcp-discord

# Lint
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type check
uv run pyright src/

# Auto-fix lint issues and format
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/
```

## Testing Instructions

```bash
# Unit tests
uv run pytest tests/unit/ -v

# Integration tests (require live Discord bot token and test server)
DISCORD_TOKEN=<token> TEST_SERVER_ID=<id> uv run pytest tests/integration/ -v
```

Unit tests use `pytest` with `pytest-asyncio` and mocked `discord.py` objects. Integration tests require a live Discord bot token and test server.

## Code Style

Ruff (linter/formatter) and pyright (type checker) are configured in `pyproject.toml`. Run lint and type checks before submitting changes.

## Architecture

The server is split into four modules under `src/discord_mcp/`:

- `__init__.py` -- Package entry point. Defines `main()` which calls `asyncio.run(server.main())`. Suppresses PyNaCl warning (voice features unused).
- `client.py` -- Discord client setup. Creates the `commands.Bot` instance with required intents, reads `DISCORD_TOKEN` from environment.
- `server.py` -- FastMCP server with tool and resource registrations. Each tool is a function decorated with `@mcp.tool()` that validates inputs, calls a handler, and returns the result dict. FastMCP handles serialization.
- `handlers.py` -- Business logic. Pure async functions that take a `commands.Bot` and parameters, call `discord.py` APIs, and return dicts. No MCP dependency.
- `resources.py` -- Read-only MCP resources (server info, channels, members, messages, roles, user info).

### Runtime Flow

1. `client.py` creates the `commands.Bot` with message_content, members, and guilds intents
2. `server.py` creates a `FastMCP` instance, registers tools and resources
3. `main()` starts the Discord bot as a background task, then runs the MCP stdio transport

### Adding a New Tool

1. Add a handler function in `handlers.py` that takes `client: commands.Bot` and typed parameters, returns a dict
2. Add a `@mcp.tool()` decorated function in `server.py` that calls the handler and returns the result directly (dict or list)
3. Add unit tests in `tests/unit/` using mocked `discord.py` objects

### Test Structure

```
tests/
├── integration/       # Tests against a live Discord server (skipped without DISCORD_TOKEN)
│   └── test_handlers.py
├── mcp/               # MCP protocol-level tests with mock bot via lifespan patching
│   ├── conftest.py    # ClientSession fixture with mock Discord bot
│   └── test_mcp_tools.py
└── unit/              # Mocked tests for all handlers
    ├── conftest.py    # Shared fixtures (mock_bot, mock_guild, mock_member, etc.)
    ├── test_channels.py
    ├── test_guild.py  # Audit log, emojis
    ├── test_invites.py
    ├── test_messages.py
    ├── test_moderation.py
    └── test_roles.py
```

## Environment

- `DISCORD_TOKEN` (required) -- Discord bot token. The bot needs MESSAGE CONTENT and SERVER MEMBERS privileged intents enabled.

## Communication and Writing Guidelines

Use Markdown, no emojis.

These guidelines apply to all communication: conversations, documentation, commit messages, changelogs, and code comments.

### Honesty and Accuracy

All statements must be realistic and factual. Provide honest assessments rather than making things sound like achievements. Prefer simple factual statements over posturing.

- Do not glorify, overstate, or exaggerate capabilities
- Describe what actually exists and works, not what might work or is planned
- Avoid "complete" unless every feature is implemented and tested
- Use accurate terms: "working", "functional", "pending", or "planned"
- Clearly state when you do not know something
- Say when you consider something a bad plan rather than avoiding the topic
- Be the devil's advocate when appropriate

### Language Style

- Use simple, direct language
- Write short sentences that state facts
- Remove filler words and subjective qualifiers
- Every sentence should convey necessary information

### Avoid These Words

These restrictions apply to prose (conversations, documentation, comments, commit messages). They do not apply when the words are used as programming language keywords, identifiers, or technical terms in code.

- Quality descriptors: "robust", "excellent", "comprehensive", "powerful"
- Subjective terms: "clean", "safe", "elegant", "beautiful"
- Unnecessary modifiers: "very", "really", "quite", "extremely"
- Marketing language: "cutting-edge", "state-of-the-art", "modern"

### Structure

- Lead with facts, not descriptions
- Remove redundant explanations
- Focus on what users need to know
- List what exists, not its quality

## Pull Request and Commit Guidelines

Follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification. Apply the same honesty and language rules to commit messages and tag annotations.

## Key Dependencies

- `discord.py` (>=2.3.0) -- Discord API wrapper
- `mcp[cli]` (>=1.26.0) -- Model Context Protocol SDK (provides `FastMCP`, stdio transport, CLI tools)

## References

- MCP Python SDK (authoritative for MCP patterns): https://github.com/modelcontextprotocol/python-sdk
- Discord API: https://docs.discord.com/developers/reference
