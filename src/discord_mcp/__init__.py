"""Discord integration for Model Context Protocol."""

import asyncio
import warnings

from . import server

__version__ = "0.1.0"


def main() -> None:
    """Main entry point for the package."""
    # Suppress PyNaCl warning since we don't use voice features
    warnings.filterwarnings("ignore", module="discord.client", message="PyNaCl is not installed")

    try:
        asyncio.run(server.main())
    except KeyboardInterrupt:
        print("\nShutting down Discord MCP server...")


# Expose important items at package level
__all__ = ["main", "server"]
