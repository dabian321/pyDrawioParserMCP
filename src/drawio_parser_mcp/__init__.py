"""Draw.io XML Parser MCP Server - validates and analyzes Draw.io diagram syntax."""

__version__ = "1.0.0"

from .parser import DrawioParser
from .validator import DrawioValidator

__all__ = ["DrawioParser", "DrawioValidator", "__version__"]
