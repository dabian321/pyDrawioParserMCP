"""MCP Server implementation for Draw.io Parser."""

import json
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from .models import DiagramStructure, ValidationResult
from .parser import DrawioParser
from .validator import DrawioValidator


# Tool definitions
TOOLS: list[Tool] = [
    Tool(
        name="validate_drawio",
        description=(
            "Validate Draw.io XML syntax and structure. "
            "Returns validation result with errors, warnings, and suggestions."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "xml_content": {
                    "type": "string",
                    "description": "The Draw.io XML content to validate",
                },
            },
            "required": ["xml_content"],
        },
    ),
    Tool(
        name="parse_drawio",
        description=(
            "Parse Draw.io XML and extract diagram structure. "
            "Returns cells, edges, layers, and statistics."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "xml_content": {
                    "type": "string",
                    "description": "The Draw.io XML content to parse",
                },
            },
            "required": ["xml_content"],
        },
    ),
    Tool(
        name="analyze_drawio",
        description=(
            "Fully analyze Draw.io XML: validate syntax and parse structure. "
            "Returns both validation issues and parsed diagram structure."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "xml_content": {
                    "type": "string",
                    "description": "The Draw.io XML content to analyze",
                },
            },
            "required": ["xml_content"],
        },
    ),
    Tool(
        name="get_diagram_summary",
        description=(
            "Get a concise summary of a Draw.io diagram. "
            "Returns statistics and overview without full structure details."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "xml_content": {
                    "type": "string",
                    "description": "The Draw.io XML content to summarize",
                },
            },
            "required": ["xml_content"],
        },
    ),
    Tool(
        name="list_cells",
        description=(
            "List all cells (shapes and connections) in a Draw.io diagram. "
            "Returns cell IDs, types, labels, and connections."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "xml_content": {
                    "type": "string",
                    "description": "The Draw.io XML content",
                },
                "include_system_cells": {
                    "type": "boolean",
                    "description": "Include system cells (id 0, 1). Default: false",
                    "default": False,
                },
            },
            "required": ["xml_content"],
        },
    ),
    Tool(
        name="find_cell",
        description="Find a specific cell by ID in a Draw.io diagram.",
        inputSchema={
            "type": "object",
            "properties": {
                "xml_content": {
                    "type": "string",
                    "description": "The Draw.io XML content",
                },
                "cell_id": {
                    "type": "string",
                    "description": "The ID of the cell to find",
                },
            },
            "required": ["xml_content", "cell_id"],
        },
    ),
]


class DrawioParserMCPServer:
    """MCP Server for Draw.io XML parsing and validation."""

    def __init__(self):
        """Initialize the server."""
        self.server = Server("drawio-parser-mcp")
        self.parser = DrawioParser()
        self.validator = DrawioValidator()
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up MCP request handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            return TOOLS

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict[str, Any] | None
        ) -> list[TextContent]:
            arguments = arguments or {}

            try:
                result = self._execute_tool(name, arguments)
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False),
                    )
                ]
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": str(e), "type": type(e).__name__},
                            ensure_ascii=False,
                        ),
                    )
                ]

    def _execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool by name."""
        xml_content = arguments.get("xml_content", "")

        if name == "validate_drawio":
            result = self.validator.validate(xml_content)
            return self._validation_to_dict(result)

        elif name == "parse_drawio":
            structure = self.parser.parse(xml_content)
            return self._structure_to_dict(structure)

        elif name == "analyze_drawio":
            validation = self.validator.validate(xml_content)
            try:
                structure = self.parser.parse(xml_content)
            except ValueError:
                structure = DiagramStructure()

            return {
                "validation": self._validation_to_dict(validation),
                "structure": self._structure_to_dict(structure),
            }

        elif name == "get_diagram_summary":
            validation = self.validator.validate(xml_content)
            try:
                structure = self.parser.parse(xml_content)
            except ValueError:
                return {
                    "valid": False,
                    "error": "Failed to parse diagram",
                    "issues": [i.model_dump() for i in validation.issues],
                }

            return {
                "valid": validation.valid,
                "error_count": validation.error_count,
                "warning_count": validation.warning_count,
                "pages": len(structure.pages),
                "total_cells": structure.total_cells,
                "total_vertices": structure.total_vertices,
                "total_edges": structure.total_edges,
                "total_layers": structure.total_layers,
                "page_names": [p.name for p in structure.pages],
            }

        elif name == "list_cells":
            include_system = arguments.get("include_system_cells", False)
            structure = self.parser.parse(xml_content)

            cells_list = []
            for page in structure.pages:
                for cell in page.cells:
                    if not include_system and cell.id in ("0", "1"):
                        continue

                    cell_info: dict[str, Any] = {
                        "id": cell.id,
                        "type": "edge" if cell.is_edge else "vertex" if cell.is_vertex else "other",
                        "value": cell.value,
                        "parent": cell.parent,
                    }

                    if cell.is_edge:
                        cell_info["source"] = cell.source
                        cell_info["target"] = cell.target

                    if cell.style and cell.style.shape:
                        cell_info["shape"] = cell.style.shape

                    cells_list.append(cell_info)

            return {"cells": cells_list, "count": len(cells_list)}

        elif name == "find_cell":
            cell_id = arguments.get("cell_id", "")
            structure = self.parser.parse(xml_content)
            cell = self.parser.get_cell_by_id(structure, cell_id)

            if cell is None:
                return {"found": False, "cell_id": cell_id}

            return {
                "found": True,
                "cell": cell.model_dump(),
            }

        else:
            raise ValueError(f"Unknown tool: {name}")

    def _validation_to_dict(self, result: ValidationResult) -> dict[str, Any]:
        """Convert ValidationResult to dictionary."""
        return {
            "valid": result.valid,
            "error_count": result.error_count,
            "warning_count": result.warning_count,
            "issues": [issue.model_dump() for issue in result.issues],
        }

    def _structure_to_dict(self, structure: DiagramStructure) -> dict[str, Any]:
        """Convert DiagramStructure to dictionary."""
        return {
            "version": structure.version,
            "host": structure.host,
            "total_cells": structure.total_cells,
            "total_vertices": structure.total_vertices,
            "total_edges": structure.total_edges,
            "total_layers": structure.total_layers,
            "pages": [
                {
                    "id": page.id,
                    "name": page.name,
                    "cell_count": len(page.cells),
                    "layer_count": len(page.layers),
                    "cells": [cell.model_dump() for cell in page.cells],
                    "layers": [layer.model_dump() for layer in page.layers],
                }
                for page in structure.pages
            ],
        }

    def get_server(self) -> Server:
        """Get the MCP server instance."""
        return self.server
