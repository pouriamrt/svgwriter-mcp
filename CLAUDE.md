# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (including dev)
uv sync --group dev

# Run all tests
uv run pytest -v

# Run a single test
uv run pytest tests/test_server.py::TestShapes::test_add_circle -v

# Syntax check
uv run python -c "import server; print('OK')"

# Run the demo (produces example_output.svg)
uv run python example.py

# Start the MCP server
uv run python main.py
```

## Architecture

Everything lives flat at the project root — no packages, no src layout.

**`server.py`** is the entire MCP server. Structure:

1. **Module-level state** — three dicts keyed by `doc_id`:
   - `_documents: dict[str, svgwrite.Drawing]`
   - `_groups: dict[str, dict[str, Any]]` — group_id → svgwrite Group object
   - `_gradients: dict[str, list[dict]]` — list of `{id, type}` records
   - `_gradient_ids: dict[str, set[str]]` — O(1) duplicate check for gradient ids

2. **Helpers** — `_get_doc`, `_get_target`, `_ok`, `_err`, `_new_id`, `_parse_size` (uses pre-compiled `_SIZE_RE`)

3. **22 tools** registered with `@mcp.tool()` (requires parentheses — bare `@mcp.tool` raises `TypeError` in mcp 1.26.0):
   - 5 document lifecycle tools
   - 7 shape tools (all accept optional `group_id`)
   - 2 group tools
   - 3 gradient tools
   - 4 pattern generators
   - `get_svg_preview` — converts SVG → PNG via cairosvg and returns an `Image` object so MCP clients render it inline

**`main.py`** — two lines: imports `mcp` from `server` and calls `mcp.run()`.

## Key svgwrite Conventions

- Always `svgwrite.Drawing(size=(...), debug=False)` — avoids false validation errors on valid CSS properties.
- Underscore → hyphen conversion is automatic (`stroke_width` → `stroke-width`).
- `dwg["width"]` / `dwg["height"]` access viewport dimensions after init.
- Polygon `points` must be `list[tuple]`, not `list[list]`.
- Gradient factory: `dwg.linearGradient(id=, start=(x1,y1), end=(x2,y2))`, then `grad.add_stop_color(offset, color, opacity)`, then `dwg.defs.add(grad)`.

## Testing Pattern

Tests call tool functions directly as plain Python — no MCP server process needed. All state is cleared by an `autouse` fixture:

```python
@pytest.fixture(autouse=True)
def clear_state():
    server._documents.clear()
    server._groups.clear()
    server._gradients.clear()
    server._gradient_ids.clear()
    yield
```

SVG assertions parse output with `xml.etree.ElementTree` using the `{"svg": "http://www.w3.org/2000/svg"}` namespace.

## Claude Desktop Config

```json
{
  "mcpServers": {
    "svgwriter": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/svgwriter-mcp", "python", "main.py"]
    }
  }
}
```

`--directory` is required so uv finds `pyproject.toml` and the `.venv`.
