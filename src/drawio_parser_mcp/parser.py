"""Draw.io XML Parser - parses .drawio XML files into structured data."""

import base64
import zlib
from typing import Optional
from urllib.parse import unquote
from xml.etree import ElementTree as ET

from .models import (
    CellGeometry,
    CellStyle,
    DiagramCell,
    DiagramLayer,
    DiagramPage,
    DiagramStructure,
)


class DrawioParser:
    """
    Parser for Draw.io XML files.

    Handles both compressed and uncompressed .drawio formats,
    extracting cells, layers, and diagram structure.
    """

    def __init__(self):
        """Initialize the parser."""
        self._root: Optional[ET.Element] = None
        self._raw_xml: str = ""

    def parse(self, xml_content: str) -> DiagramStructure:
        """
        Parse Draw.io XML content into a structured format.

        Args:
            xml_content: The raw XML content of a .drawio file

        Returns:
            DiagramStructure containing all parsed elements

        Raises:
            ValueError: If the XML is invalid or not a Draw.io format
        """
        self._raw_xml = xml_content.strip()

        try:
            self._root = ET.fromstring(self._raw_xml)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}") from e

        structure = DiagramStructure()

        # Check root element
        if self._root.tag == "mxfile":
            structure = self._parse_mxfile(self._root, structure)
        elif self._root.tag == "mxGraphModel":
            # Direct mxGraphModel without mxfile wrapper
            page = self._parse_mxgraph_model(self._root, "page-1", "Page 1")
            structure.pages.append(page)
        else:
            raise ValueError(
                f"Invalid Draw.io format: expected 'mxfile' or 'mxGraphModel', "
                f"got '{self._root.tag}'"
            )

        # Calculate statistics
        structure.total_cells = sum(len(p.cells) for p in structure.pages)
        structure.total_vertices = sum(
            sum(1 for c in p.cells if c.is_vertex) for p in structure.pages
        )
        structure.total_edges = sum(
            sum(1 for c in p.cells if c.is_edge) for p in structure.pages
        )
        structure.total_layers = sum(len(p.layers) for p in structure.pages)

        return structure

    def _parse_mxfile(
        self, root: ET.Element, structure: DiagramStructure
    ) -> DiagramStructure:
        """Parse the mxfile root element."""
        # Extract file-level attributes
        structure.host = root.get("host")
        structure.modified = root.get("modified")
        structure.agent = root.get("agent")
        structure.version = root.get("version")

        # Parse each diagram (page)
        for diagram in root.findall("diagram"):
            page = self._parse_diagram(diagram)
            if page:
                structure.pages.append(page)

        return structure

    def _parse_diagram(self, diagram: ET.Element) -> Optional[DiagramPage]:
        """Parse a single diagram element."""
        page_id = diagram.get("id", "")
        page_name = diagram.get("name", "")

        # Check for compressed content
        mxgraph_model = diagram.find("mxGraphModel")
        if mxgraph_model is not None:
            # Uncompressed format
            return self._parse_mxgraph_model(mxgraph_model, page_id, page_name)

        # Try to decompress text content
        text_content = diagram.text
        if text_content:
            text_content = text_content.strip()
            if text_content:
                try:
                    decompressed = self._decompress_diagram(text_content)
                    model_root = ET.fromstring(decompressed)
                    return self._parse_mxgraph_model(model_root, page_id, page_name)
                except Exception:
                    # Could not decompress, skip this diagram
                    pass

        return None

    def _decompress_diagram(self, compressed: str) -> str:
        """Decompress a compressed diagram string."""
        # URL decode
        decoded = unquote(compressed)
        # Base64 decode
        raw = base64.b64decode(decoded)
        # Inflate (decompress)
        decompressed = zlib.decompress(raw, -15)
        # URL decode again
        return unquote(decompressed.decode("utf-8"))

    def _parse_mxgraph_model(
        self, model: ET.Element, page_id: str, page_name: str
    ) -> DiagramPage:
        """Parse an mxGraphModel element."""
        page = DiagramPage(id=page_id, name=page_name)

        root_elem = model.find("root")
        if root_elem is None:
            return page

        cells_by_id: dict[str, DiagramCell] = {}
        layers: list[DiagramLayer] = []

        # First pass: create all cells
        for mx_cell in root_elem.findall("mxCell"):
            cell = self._parse_cell(mx_cell)
            cells_by_id[cell.id] = cell

            # Identify root and default parent
            if cell.id == "0":
                page.root_id = cell.id
            elif cell.id == "1" or (cell.parent == "0" and not cell.is_vertex):
                page.default_parent_id = cell.id

        # Also check for object elements (cells with custom data)
        for obj in root_elem.findall("object"):
            cell = self._parse_object(obj)
            cells_by_id[cell.id] = cell

        # Second pass: identify layers and build hierarchy
        for cell_id, cell in cells_by_id.items():
            # Layer detection: cells with parent "0" that are not the default parent
            if cell.parent == "0" and cell_id != page.root_id:
                layer = DiagramLayer(
                    id=cell.id,
                    name=cell.value or f"Layer {cell.id}",
                )
                layers.append(layer)

            # Track children
            if cell.parent and cell.parent in cells_by_id:
                cells_by_id[cell.parent].children.append(cell.id)

        # Assign cells to layers
        for layer in layers:
            layer.cells = [
                c.id for c in cells_by_id.values() if c.parent == layer.id
            ]

        page.cells = list(cells_by_id.values())
        page.layers = layers

        return page

    def _parse_cell(self, mx_cell: ET.Element) -> DiagramCell:
        """Parse an mxCell element."""
        cell = DiagramCell(
            id=mx_cell.get("id", ""),
            value=mx_cell.get("value", ""),
            parent=mx_cell.get("parent"),
            source=mx_cell.get("source"),
            target=mx_cell.get("target"),
            is_vertex=mx_cell.get("vertex") == "1",
            is_edge=mx_cell.get("edge") == "1",
            is_connectable=mx_cell.get("connectable", "1") != "0",
        )

        # Parse style
        style_str = mx_cell.get("style", "")
        if style_str:
            cell.style = self._parse_style(style_str)

        # Parse geometry
        geom = mx_cell.find("mxGeometry")
        if geom is not None:
            cell.geometry = self._parse_geometry(geom)

        return cell

    def _parse_object(self, obj: ET.Element) -> DiagramCell:
        """Parse an object element (cell with custom attributes)."""
        # Get the nested mxCell
        mx_cell = obj.find("mxCell")
        if mx_cell is not None:
            cell = self._parse_cell(mx_cell)
            # Override id with object id
            cell.id = obj.get("id", cell.id)
        else:
            cell = DiagramCell(id=obj.get("id", ""))

        # Extract custom attributes
        cell.value = obj.get("label", obj.get("value", cell.value))
        for key, value in obj.attrib.items():
            if key not in ("id", "label", "value"):
                cell.attributes[key] = value

        return cell

    def _parse_style(self, style_str: str) -> CellStyle:
        """Parse a style string into structured properties."""
        style = CellStyle(raw=style_str)

        # Parse semicolon-separated key=value pairs
        parts = style_str.split(";")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                key, value = part.split("=", 1)
                style.properties[key.strip()] = value.strip()
            else:
                # Shape name or flag
                style.properties[part] = "1"
                if not style.shape:
                    style.shape = part

        # Extract common properties
        style.fill_color = style.properties.get("fillColor")
        style.stroke_color = style.properties.get("strokeColor")
        style.font_color = style.properties.get("fontColor")
        style.rounded = style.properties.get("rounded") == "1"
        style.edge_style = style.properties.get("edgeStyle")

        font_size = style.properties.get("fontSize")
        if font_size and font_size.isdigit():
            style.font_size = int(font_size)

        return style

    def _parse_geometry(self, geom: ET.Element) -> CellGeometry:
        """Parse an mxGeometry element."""
        geometry = CellGeometry(
            relative=geom.get("relative") == "1",
        )

        # Parse numeric attributes
        for attr in ("x", "y", "width", "height"):
            value = geom.get(attr)
            if value:
                try:
                    setattr(geometry, attr, float(value))
                except ValueError:
                    pass

        # Parse points for edges
        for point in geom.findall(".//mxPoint"):
            x = point.get("x")
            y = point.get("y")
            if x and y:
                try:
                    geometry.points.append({"x": float(x), "y": float(y)})
                except ValueError:
                    pass

        return geometry

    def get_cell_by_id(
        self, structure: DiagramStructure, cell_id: str
    ) -> Optional[DiagramCell]:
        """Find a cell by its ID across all pages."""
        for page in structure.pages:
            for cell in page.cells:
                if cell.id == cell_id:
                    return cell
        return None
