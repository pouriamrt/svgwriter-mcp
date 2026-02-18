# svgwriter-mcp

An MCP server that wraps the [svgwrite](https://svgwrite.readthedocs.io/) Python library, enabling LLM agents to create, compose, and export SVG documents through tool calls.

## Features

- 21 tools covering the full SVG creation workflow
- In-memory document state — create multiple documents in a session
- Groups, gradients, shapes, text, paths, and pattern generators
- Returns SVG as a string or saves directly to disk

## Installation

```bash
git clone <repo>
cd svgwriter-mcp
uv sync
```

## Usage

### As an MCP server (stdio)

```bash
uv run python main.py
```

### As a library (direct function calls)

```python
import json, server

result = json.loads(server.create_document(width="800px", height="600px"))
doc_id = result["doc_id"]

server.add_rect(doc_id=doc_id, x=0, y=0, width=800, height=600, fill="#eef")
server.add_text(doc_id=doc_id, text="Hello SVG", x=400, y=300, text_anchor="middle")

server.save_file(doc_id=doc_id, filepath="hello.svg")
```

### Run the demo

```bash
uv run python example.py
# produces example_output.svg
```

## MCP Client Configuration

Add to your Claude Desktop `claude_desktop_config.json`
(`%APPDATA%\Claude\claude_desktop_config.json` on Windows,
`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "svgwriter": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "/path/to/svgwriter-mcp/main.py"
      ]
    }
  }
}
```

> **Note:** Use the absolute path to `main.py` on your machine (e.g. `C:\\Users\\you\\svgwriter-mcp\\main.py` on Windows).
> Using the full path avoids working-directory issues with Claude Desktop.

## Tool Reference

### Document Lifecycle

| Tool | Description |
|------|-------------|
| `create_document` | Create a new SVG document; returns `doc_id` |
| `list_documents` | List all open documents with their sizes |
| `delete_document` | Delete a document and free its state |
| `get_svg_string` | Return the SVG XML as a string |
| `save_file` | Write the SVG to a file on disk |

### Shapes

All shape tools accept an optional `group_id` to target a group instead of the document root.

| Tool | Key Parameters |
|------|----------------|
| `add_circle` | `cx`, `cy`, `r`, `fill`, `stroke` |
| `add_rect` | `x`, `y`, `width`, `height`, `rx`, `ry` |
| `add_line` | `x1`, `y1`, `x2`, `y2`, `stroke` |
| `add_ellipse` | `cx`, `cy`, `rx`, `ry` |
| `add_text` | `text`, `x`, `y`, `font_size`, `font_family`, `text_anchor` |
| `add_polygon` | `points` (list of `[x, y]` pairs) |
| `add_path` | `d` (SVG path data string) |

### Groups

| Tool | Description |
|------|-------------|
| `create_group` | Create a `<g>` element; optionally set `opacity` or `transform` |
| `list_groups` | List all group ids in a document |

### Gradients

Use the returned `url_ref` (e.g. `url(#grad1)`) as a `fill` value for shapes.

| Tool | Description |
|------|-------------|
| `add_linear_gradient` | Add a `linearGradient`; specify `stops`, `x1/y1/x2/y2` |
| `add_radial_gradient` | Add a `radialGradient`; specify `stops`, `cx/cy/r/fx/fy` |
| `list_gradients` | List all gradients in a document |

### Pattern Generators

| Tool | Description |
|------|-------------|
| `add_grid_pattern` | Grid of lines at `cell_size` intervals |
| `add_checkerboard_pattern` | Alternating `color1`/`color2` squares |
| `add_dot_grid_pattern` | Small circles at `spacing` intervals |
| `add_concentric_circles_pattern` | Circles from `min_radius` to `max_radius` |

## Development

```bash
# Install with dev deps
uv sync --group dev

# Run tests
uv run pytest -v

# Syntax check
uv run python -c "import server; print('OK')"
```

## Response Format

All tools return a JSON string:

```json
{"status": "ok", "doc_id": "doc_abc123"}
{"status": "error", "message": "Document 'x' not found."}
```
