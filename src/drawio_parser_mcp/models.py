"""Data models for Draw.io diagram elements."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """A single validation issue found in the diagram."""
    severity: ValidationSeverity
    code: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    element: Optional[str] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of validating a Draw.io diagram."""
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0


class CellGeometry(BaseModel):
    """Geometry of a cell (position and size)."""
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    relative: bool = False
    points: list[dict[str, float]] = Field(default_factory=list)


class CellStyle(BaseModel):
    """Parsed style properties of a cell."""
    raw: str = ""
    properties: dict[str, str] = Field(default_factory=dict)
    shape: Optional[str] = None
    fill_color: Optional[str] = None
    stroke_color: Optional[str] = None
    font_color: Optional[str] = None
    font_size: Optional[int] = None
    rounded: bool = False
    edge_style: Optional[str] = None


class DiagramCell(BaseModel):
    """A cell (vertex or edge) in the diagram."""
    id: str
    value: str = ""
    parent: Optional[str] = None
    source: Optional[str] = None
    target: Optional[str] = None
    is_vertex: bool = False
    is_edge: bool = False
    is_connectable: bool = True
    geometry: Optional[CellGeometry] = None
    style: Optional[CellStyle] = None
    children: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class DiagramLayer(BaseModel):
    """A layer in the diagram."""
    id: str
    name: str = ""
    visible: bool = True
    locked: bool = False
    cells: list[str] = Field(default_factory=list)


class DiagramPage(BaseModel):
    """A page in the Draw.io document."""
    id: str
    name: str = ""
    cells: list[DiagramCell] = Field(default_factory=list)
    layers: list[DiagramLayer] = Field(default_factory=list)
    root_id: Optional[str] = None
    default_parent_id: Optional[str] = None


class DiagramStructure(BaseModel):
    """Complete structure of a Draw.io diagram."""
    pages: list[DiagramPage] = Field(default_factory=list)
    version: Optional[str] = None
    host: Optional[str] = None
    modified: Optional[str] = None
    agent: Optional[str] = None
    compressed: bool = False

    # Statistics
    total_cells: int = 0
    total_vertices: int = 0
    total_edges: int = 0
    total_layers: int = 0


class AnalysisResult(BaseModel):
    """Complete analysis result including validation and structure."""
    validation: ValidationResult
    structure: DiagramStructure
    raw_xml: str = ""
