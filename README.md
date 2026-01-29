# Draw.io Parser MCP Server

一个用于验证和分析 Draw.io XML 语法的 MCP (Model Context Protocol) 服务器，专为检查 AI 生成的 Draw.io 图表内容设计。

## 功能特性

- **语法验证** - 检查 Draw.io XML 的语法正确性，发现错误和警告
- **结构解析** - 解析图表结构，提取单元格、边、图层等信息
- **图表分析** - 完整分析图表，同时返回验证结果和结构信息
- **摘要统计** - 快速获取图表统计信息（形状数、连接数等）
- **单元格查询** - 列出所有单元格或按 ID 查找特定单元格

## 安装

### 使用 uv (推荐)

```bash
# 克隆项目
git clone https://github.com/dabian321/pyDrawioParserMCP.git
cd pyDrawioParserMCP

# 安装依赖
uv sync
```

### 使用 pip

```bash
pip install -e .
```

## MCP 配置

将以下配置添加到你的 MCP 配置文件 (如 Claude Desktop 的 `mcp.json`)：

```json
{
  "mcpServers": {
    "drawio-parser-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/pyDrawioParserMCP",
        "run",
        "drawio-parser-mcp"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

> 将 `/path/to/pyDrawioParserMCP` 替换为项目实际路径

## MCP 工具

| 工具名 | 描述 |
|--------|------|
| `validate_drawio` | 验证 Draw.io XML 语法和结构，返回错误、警告和建议 |
| `parse_drawio` | 解析 Draw.io XML，提取单元格、边、图层和统计信息 |
| `analyze_drawio` | 完整分析：同时执行验证和解析 |
| `get_diagram_summary` | 获取图表摘要统计信息 |
| `list_cells` | 列出图表中所有单元格（形状和连接） |
| `find_cell` | 按 ID 查找特定单元格 |

## 命令行使用

```bash
# 启动 MCP 服务器 (stdio 模式)
drawio-parser-mcp

# 验证单个文件
drawio-parser-mcp --check mydiagram.drawio

# 启用详细日志
drawio-parser-mcp -v
```

## 使用示例

### 验证 AI 生成的 Draw.io 内容

```python
from drawio_parser_mcp import DrawioValidator

validator = DrawioValidator()
xml_content = """
<mxfile>
  <diagram id="test" name="Page-1">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Hello" style="rounded=1;" vertex="1" parent="1">
          <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""

result = validator.validate(xml_content)
print(f"Valid: {result.valid}")
print(f"Errors: {result.error_count}, Warnings: {result.warning_count}")
```

### 解析图表结构

```python
from drawio_parser_mcp import DrawioParser

parser = DrawioParser()
structure = parser.parse(xml_content)

print(f"Pages: {len(structure.pages)}")
print(f"Total shapes: {structure.total_vertices}")
print(f"Total connections: {structure.total_edges}")
```

## 项目结构

```
pyDrawioParserMCP/
├── src/drawio_parser_mcp/
│   ├── __init__.py      # 包入口
│   ├── cli.py           # 命令行接口
│   ├── server.py        # MCP Server 实现
│   ├── parser.py        # XML 解析器
│   ├── validator.py     # 语法验证器
│   └── models.py        # 数据模型
├── tests/               # 测试文件
├── architecture.drawio  # 架构图
└── pyproject.toml       # 项目配置
```

## 验证规则

| 错误代码 | 描述 |
|----------|------|
| `XML_SYNTAX_ERROR` | XML 语法错误 |
| `INVALID_ROOT` | 无效的根元素 |
| `NO_DIAGRAM` | 缺少 diagram 元素 |
| `MISSING_ROOT_CELL` | 缺少 id="0" 的根单元格 |
| `MISSING_DEFAULT_PARENT` | 缺少 id="1" 的默认父单元格 |
| `INVALID_PARENT` | 引用了不存在的父单元格 |
| `INVALID_EDGE_SOURCE` | 边的源单元格不存在 |
| `INVALID_EDGE_TARGET` | 边的目标单元格不存在 |
| `NEGATIVE_WIDTH/HEIGHT` | 负数的宽度或高度 |

## 依赖

- Python >= 3.10
- mcp >= 1.0.0
- pydantic >= 2.0.0
- lxml >= 5.0.0

## 开发

```bash
# 安装开发依赖
uv sync --extra dev

# 运行测试
pytest

# 代码格式检查
ruff check src/
```

## License

MIT License
