"""Command-line interface for Draw.io Parser MCP Server."""

import argparse
import asyncio
import logging
import sys
from typing import NoReturn

from mcp.server.stdio import stdio_server

from . import __version__
from .server import DrawioParserMCPServer


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Draw.io Parser MCP Server - validates and analyzes Draw.io XML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start MCP server (stdio mode for Claude Desktop)
  drawio-parser-mcp

  # Verbose logging
  drawio-parser-mcp -v

  # Quick validation from command line
  drawio-parser-mcp --check mydiagram.drawio
        """,
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--check",
        type=str,
        metavar="FILE",
        help="Validate a .drawio file and exit (standalone mode)",
    )

    return parser.parse_args()


async def run_stdio_server() -> None:
    """Run the MCP server with stdio transport."""
    mcp_server = DrawioParserMCPServer()

    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.get_server().run(
            read_stream,
            write_stream,
            mcp_server.get_server().create_initialization_options(),
        )


def check_file(filepath: str) -> int:
    """Validate a .drawio file and print results."""

    from .parser import DrawioParser
    from .validator import DrawioValidator

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    validator = DrawioValidator()
    result = validator.validate(content)

    # Print results
    if result.valid:
        print(f"OK: {filepath}")
    else:
        print(f"INVALID: {filepath}")

    for issue in result.issues:
        prefix = "ERROR" if issue.severity.value == "error" else "WARN"
        location = ""
        if issue.line:
            location = f" (line {issue.line})"
        elif issue.element:
            location = f" [{issue.element}]"

        print(f"  {prefix}: {issue.message}{location}")
        if issue.suggestion:
            print(f"         Suggestion: {issue.suggestion}")

    # Print summary
    parser = DrawioParser()
    try:
        structure = parser.parse(content)
        print(f"\nDiagram: {structure.total_vertices} shapes, {structure.total_edges} connections")
    except ValueError:
        pass

    return 0 if result.valid else 1


def main() -> NoReturn:
    """Main entry point."""
    args = parse_args()
    setup_logging(args.verbose)

    # Standalone validation mode
    if args.check:
        sys.exit(check_file(args.check))

    # MCP server mode
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Draw.io Parser MCP Server v{__version__}")

    try:
        asyncio.run(run_stdio_server())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
