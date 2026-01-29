"""Tests for Draw.io Parser MCP Server."""

import pytest

from drawio_parser_mcp.parser import DrawioParser
from drawio_parser_mcp.validator import DrawioValidator
from drawio_parser_mcp.models import ValidationSeverity


# Sample valid Draw.io XML
VALID_DRAWIO = '''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="2024-01-01T00:00:00.000Z" version="22.0.0">
  <diagram id="test-diagram" name="Page-1">
    <mxGraphModel dx="1000" dy="600" grid="1" gridSize="10">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Hello" style="rounded=1;fillColor=#dae8fc;" vertex="1" parent="1">
          <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="3" value="World" style="rounded=1;fillColor=#d5e8d4;" vertex="1" parent="1">
          <mxGeometry x="300" y="100" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="4" value="" style="endArrow=classic;" edge="1" parent="1" source="2" target="3">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

# Simple mxGraphModel without mxfile wrapper
SIMPLE_GRAPH_MODEL = '''<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <mxCell id="2" value="Box" vertex="1" parent="1">
      <mxGeometry x="50" y="50" width="100" height="50" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>'''

# Invalid XML
INVALID_XML = '''<mxfile>
  <diagram>
    <mxGraphModel>
      <root>
        <mxCell id="0"
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

# Missing root cells
MISSING_ROOT_CELLS = '''<mxGraphModel>
  <root>
    <mxCell id="2" value="Orphan" vertex="1" parent="1">
      <mxGeometry x="50" y="50" width="100" height="50" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>'''

# Invalid edge references
INVALID_EDGE = '''<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <mxCell id="2" value="" edge="1" parent="1" source="99" target="100"/>
  </root>
</mxGraphModel>'''


class TestDrawioParser:
    """Tests for DrawioParser."""

    @pytest.fixture
    def parser(self):
        return DrawioParser()

    def test_parse_valid_mxfile(self, parser):
        """Test parsing a valid mxfile."""
        result = parser.parse(VALID_DRAWIO)

        assert len(result.pages) == 1
        assert result.pages[0].name == "Page-1"
        assert result.total_cells == 5  # 0, 1, 2, 3, 4
        assert result.total_vertices == 2  # 2, 3
        assert result.total_edges == 1  # 4

    def test_parse_simple_graph_model(self, parser):
        """Test parsing a simple mxGraphModel."""
        result = parser.parse(SIMPLE_GRAPH_MODEL)

        assert len(result.pages) == 1
        assert result.total_cells == 3
        assert result.total_vertices == 1

    def test_parse_cell_geometry(self, parser):
        """Test parsing cell geometry."""
        result = parser.parse(SIMPLE_GRAPH_MODEL)
        cell = parser.get_cell_by_id(result, "2")

        assert cell is not None
        assert cell.geometry is not None
        assert cell.geometry.x == 50
        assert cell.geometry.y == 50
        assert cell.geometry.width == 100
        assert cell.geometry.height == 50

    def test_parse_cell_style(self, parser):
        """Test parsing cell style."""
        result = parser.parse(VALID_DRAWIO)
        cell = parser.get_cell_by_id(result, "2")

        assert cell is not None
        assert cell.style is not None
        assert cell.style.rounded is True
        assert cell.style.fill_color == "#dae8fc"

    def test_parse_edge(self, parser):
        """Test parsing edge connections."""
        result = parser.parse(VALID_DRAWIO)
        edge = parser.get_cell_by_id(result, "4")

        assert edge is not None
        assert edge.is_edge is True
        assert edge.source == "2"
        assert edge.target == "3"

    def test_invalid_xml_raises(self, parser):
        """Test that invalid XML raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parser.parse(INVALID_XML)
        assert "Invalid XML" in str(exc_info.value)

    def test_invalid_root_element(self, parser):
        """Test that invalid root element raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parser.parse("<html><body>Not a diagram</body></html>")
        assert "Invalid Draw.io format" in str(exc_info.value)


class TestDrawioValidator:
    """Tests for DrawioValidator."""

    @pytest.fixture
    def validator(self):
        return DrawioValidator()

    def test_valid_diagram(self, validator):
        """Test validating a valid diagram."""
        result = validator.validate(VALID_DRAWIO)

        assert result.valid is True
        assert result.error_count == 0

    def test_invalid_xml_syntax(self, validator):
        """Test detecting XML syntax errors."""
        result = validator.validate(INVALID_XML)

        assert result.valid is False
        assert result.error_count > 0
        assert any(i.code == "XML_SYNTAX_ERROR" for i in result.issues)

    def test_missing_root_cells(self, validator):
        """Test detecting missing root cells (0 and 1)."""
        result = validator.validate(MISSING_ROOT_CELLS)

        assert result.valid is False
        codes = [i.code for i in result.issues]
        assert "MISSING_ROOT_CELL" in codes
        assert "MISSING_DEFAULT_PARENT" in codes

    def test_invalid_edge_references(self, validator):
        """Test detecting invalid edge source/target."""
        result = validator.validate(INVALID_EDGE)

        assert result.valid is False
        codes = [i.code for i in result.issues]
        assert "INVALID_EDGE_SOURCE" in codes or "INVALID_EDGE_TARGET" in codes

    def test_validation_suggestions(self, validator):
        """Test that validation issues include suggestions."""
        result = validator.validate(MISSING_ROOT_CELLS)

        for issue in result.issues:
            if issue.severity == ValidationSeverity.ERROR:
                assert issue.suggestion is not None

    def test_empty_content(self, validator):
        """Test validating empty content."""
        result = validator.validate("")

        assert result.valid is False
        assert result.error_count > 0


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def parser(self):
        return DrawioParser()

    @pytest.fixture
    def validator(self):
        return DrawioValidator()

    def test_negative_geometry(self, validator):
        """Test detecting negative geometry values."""
        xml = '''<mxGraphModel>
          <root>
            <mxCell id="0"/>
            <mxCell id="1" parent="0"/>
            <mxCell id="2" vertex="1" parent="1">
              <mxGeometry x="0" y="0" width="-100" height="50" as="geometry"/>
            </mxCell>
          </root>
        </mxGraphModel>'''

        result = validator.validate(xml)
        codes = [i.code for i in result.issues]
        assert "NEGATIVE_WIDTH" in codes

    def test_floating_edge(self, validator):
        """Test warning for edge without connections."""
        xml = '''<mxGraphModel>
          <root>
            <mxCell id="0"/>
            <mxCell id="1" parent="0"/>
            <mxCell id="2" edge="1" parent="1"/>
          </root>
        </mxGraphModel>'''

        result = validator.validate(xml)
        codes = [i.code for i in result.issues]
        assert "FLOATING_EDGE" in codes

    def test_diagram_with_object_elements(self, parser):
        """Test parsing diagrams with object elements (custom data)."""
        xml = '''<mxGraphModel>
          <root>
            <mxCell id="0"/>
            <mxCell id="1" parent="0"/>
            <object id="2" label="Custom" customAttr="value">
              <mxCell vertex="1" parent="1">
                <mxGeometry x="0" y="0" width="100" height="50" as="geometry"/>
              </mxCell>
            </object>
          </root>
        </mxGraphModel>'''

        result = parser.parse(xml)
        cell = parser.get_cell_by_id(result, "2")

        assert cell is not None
        assert cell.value == "Custom"
        assert cell.attributes.get("customAttr") == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
