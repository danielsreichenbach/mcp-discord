"""Discord integration for Model Context Protocol."""

import warnings

__version__ = "0.1.0"


def main() -> None:
    """Main entry point for the package."""
    # Suppress PyNaCl warning since we don't use voice features
    warnings.filterwarnings("ignore", module="discord.client", message="PyNaCl is not installed")

    from . import server

    try:
        server.main()
    except KeyboardInterrupt:
        pass  # MCP closes stdout during shutdown


# Expose important items at package level
__all__ = ["main"]
