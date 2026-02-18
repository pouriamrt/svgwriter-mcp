"""svgwriter-mcp: MCP server wrapping the svgwrite library."""

import json
import re
import uuid
from typing import Any, Optional

import svgwrite
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("svgwriter-mcp")

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_documents: dict[str, svgwrite.Drawing] = {}
_groups: dict[str, dict[str, Any]] = {}   # doc_id → {group_id → Group}
_gradients: dict[str, list[dict]] = {}    # doc_id → [{id, type}]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_doc(doc_id: str) -> svgwrite.Drawing:
    if doc_id not in _documents:
        raise ValueError(f"Document '{doc_id}' not found.")
    return _documents[doc_id]


def _get_target(doc_id: str, group_id: Optional[str]):
    """Return (dwg, target) where target is a Group or the Drawing itself."""
    dwg = _get_doc(doc_id)
    if group_id:
        groups = _groups.get(doc_id, {})
        if group_id not in groups:
            raise ValueError(
                f"Group '{group_id}' not found in document '{doc_id}'."
            )
        return dwg, groups[group_id]
    return dwg, dwg


def _ok(**kwargs) -> str:
    return json.dumps({"status": "ok", **kwargs})


def _err(message: str) -> str:
    return json.dumps({"status": "error", "message": message})


def _new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def _parse_size(value: str) -> float:
    """Extract the numeric portion of a size string like '800px' or '100%'."""
    m = re.match(r"[\d.]+", str(value).strip())
    return float(m.group()) if m else 800.0


# ---------------------------------------------------------------------------
# Document lifecycle (5 tools)
# ---------------------------------------------------------------------------


@mcp.tool()
def create_document(
    width: str = "800px",
    height: str = "600px",
    doc_id: Optional[str] = None,
) -> str:
    """Create a new SVG document. Returns the doc_id used to reference it.

    Args:
        width: SVG viewport width (e.g. '800px', '100%'). Default '800px'.
        height: SVG viewport height (e.g. '600px'). Default '600px'.
        doc_id: Optional custom identifier; auto-generated if omitted.
    """
    did = doc_id or _new_id("doc_")
    if did in _documents:
        return _err(f"Document '{did}' already exists.")
    dwg = svgwrite.Drawing(size=(width, height), debug=False)
    _documents[did] = dwg
    _groups[did] = {}
    _gradients[did] = []
    return _ok(doc_id=did, width=width, height=height)


@mcp.tool()
def list_documents() -> str:
    """List all open SVG documents with their ids and viewport sizes."""
    docs = [
        {"doc_id": did, "width": dwg["width"], "height": dwg["height"]}
        for did, dwg in _documents.items()
    ]
    return _ok(documents=docs)


@mcp.tool()
def delete_document(doc_id: str) -> str:
    """Delete a document and all its associated groups and gradients.

    Args:
        doc_id: The document to delete.
    """
    if doc_id not in _documents:
        return _err(f"Document '{doc_id}' not found.")
    del _documents[doc_id]
    _groups.pop(doc_id, None)
    _gradients.pop(doc_id, None)
    return _ok(doc_id=doc_id)


@mcp.tool()
def get_svg_string(doc_id: str) -> str:
    """Return the current SVG XML string for a document.

    Args:
        doc_id: The document to serialise.
    """
    try:
        dwg = _get_doc(doc_id)
        return _ok(svg=dwg.tostring())
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def save_file(doc_id: str, filepath: str, pretty: bool = False) -> str:
    """Save the SVG document to a file on disk.

    Args:
        doc_id: The document to save.
        filepath: Destination file path (e.g. 'output/diagram.svg').
        pretty: If True, output is indented for readability.
    """
    try:
        dwg = _get_doc(doc_id)
        dwg.saveas(filepath, pretty=pretty)
        return _ok(doc_id=doc_id, filepath=filepath)
    except ValueError as e:
        return _err(str(e))
    except OSError as e:
        return _err(f"File error: {e}")


# ---------------------------------------------------------------------------
# Shapes (7 tools)
# ---------------------------------------------------------------------------


@mcp.tool()
def add_circle(
    doc_id: str,
    cx: float,
    cy: float,
    r: float,
    fill: str = "black",
    stroke: str = "none",
    stroke_width: float = 1.0,
    opacity: float = 1.0,
    group_id: Optional[str] = None,
) -> str:
    """Add a circle to a document or group.

    Args:
        doc_id: Target document.
        cx: Centre X coordinate.
        cy: Centre Y coordinate.
        r: Radius.
        fill: Fill colour (CSS colour string). Default 'black'.
        stroke: Stroke colour. Default 'none'.
        stroke_width: Stroke width. Default 1.0.
        opacity: Opacity 0–1. Default 1.0.
        group_id: If provided, add to this group instead of the document root.
    """
    try:
        dwg, target = _get_target(doc_id, group_id)
        eid = _new_id("circle_")
        elem = dwg.circle(
            center=(cx, cy),
            r=r,
            fill=fill,
            stroke=stroke,
            stroke_width=stroke_width,
            opacity=opacity,
            id=eid,
        )
        target.add(elem)
        return _ok(element_id=eid)
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def add_rect(
    doc_id: str,
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str = "black",
    stroke: str = "none",
    stroke_width: float = 1.0,
    rx: float = 0.0,
    ry: float = 0.0,
    opacity: float = 1.0,
    group_id: Optional[str] = None,
) -> str:
    """Add a rectangle to a document or group.

    Args:
        doc_id: Target document.
        x: Left edge X.
        y: Top edge Y.
        width: Rectangle width.
        height: Rectangle height.
        fill: Fill colour. Default 'black'.
        stroke: Stroke colour. Default 'none'.
        stroke_width: Stroke width. Default 1.0.
        rx: Horizontal corner radius. Default 0.
        ry: Vertical corner radius. Default 0.
        opacity: Opacity 0–1. Default 1.0.
        group_id: If provided, add to this group instead of document root.
    """
    try:
        dwg, target = _get_target(doc_id, group_id)
        eid = _new_id("rect_")
        kwargs: dict[str, Any] = dict(
            insert=(x, y),
            size=(width, height),
            fill=fill,
            stroke=stroke,
            stroke_width=stroke_width,
            opacity=opacity,
            id=eid,
        )
        if rx:
            kwargs["rx"] = rx
        if ry:
            kwargs["ry"] = ry
        elem = dwg.rect(**kwargs)
        target.add(elem)
        return _ok(element_id=eid)
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def add_line(
    doc_id: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    stroke: str = "black",
    stroke_width: float = 1.0,
    opacity: float = 1.0,
    group_id: Optional[str] = None,
) -> str:
    """Add a line segment to a document or group.

    Args:
        doc_id: Target document.
        x1: Start X.
        y1: Start Y.
        x2: End X.
        y2: End Y.
        stroke: Stroke colour. Default 'black'.
        stroke_width: Stroke width. Default 1.0.
        opacity: Opacity 0–1. Default 1.0.
        group_id: If provided, add to this group instead of document root.
    """
    try:
        dwg, target = _get_target(doc_id, group_id)
        eid = _new_id("line_")
        elem = dwg.line(
            start=(x1, y1),
            end=(x2, y2),
            stroke=stroke,
            stroke_width=stroke_width,
            opacity=opacity,
            id=eid,
        )
        target.add(elem)
        return _ok(element_id=eid)
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def add_ellipse(
    doc_id: str,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    fill: str = "black",
    stroke: str = "none",
    stroke_width: float = 1.0,
    opacity: float = 1.0,
    group_id: Optional[str] = None,
) -> str:
    """Add an ellipse to a document or group.

    Args:
        doc_id: Target document.
        cx: Centre X.
        cy: Centre Y.
        rx: Horizontal radius.
        ry: Vertical radius.
        fill: Fill colour. Default 'black'.
        stroke: Stroke colour. Default 'none'.
        stroke_width: Stroke width. Default 1.0.
        opacity: Opacity 0–1. Default 1.0.
        group_id: If provided, add to this group instead of document root.
    """
    try:
        dwg, target = _get_target(doc_id, group_id)
        eid = _new_id("ellipse_")
        elem = dwg.ellipse(
            center=(cx, cy),
            r=(rx, ry),
            fill=fill,
            stroke=stroke,
            stroke_width=stroke_width,
            opacity=opacity,
            id=eid,
        )
        target.add(elem)
        return _ok(element_id=eid)
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def add_text(
    doc_id: str,
    text: str,
    x: float,
    y: float,
    font_size: str = "16px",
    font_family: str = "sans-serif",
    fill: str = "black",
    text_anchor: str = "start",
    opacity: float = 1.0,
    group_id: Optional[str] = None,
) -> str:
    """Add a text element to a document or group.

    Args:
        doc_id: Target document.
        text: The text string to render.
        x: Text insertion X.
        y: Text insertion Y (baseline).
        font_size: CSS font size (e.g. '16px', '1.2em'). Default '16px'.
        font_family: CSS font family. Default 'sans-serif'.
        fill: Text colour. Default 'black'.
        text_anchor: SVG text-anchor ('start', 'middle', 'end'). Default 'start'.
        opacity: Opacity 0–1. Default 1.0.
        group_id: If provided, add to this group instead of document root.
    """
    try:
        dwg, target = _get_target(doc_id, group_id)
        eid = _new_id("text_")
        elem = dwg.text(
            text,
            insert=(x, y),
            font_size=font_size,
            font_family=font_family,
            fill=fill,
            text_anchor=text_anchor,
            opacity=opacity,
            id=eid,
        )
        target.add(elem)
        return _ok(element_id=eid)
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def add_polygon(
    doc_id: str,
    points: list[list[float]],
    fill: str = "black",
    stroke: str = "none",
    stroke_width: float = 1.0,
    opacity: float = 1.0,
    group_id: Optional[str] = None,
) -> str:
    """Add a closed polygon to a document or group.

    Args:
        doc_id: Target document.
        points: List of [x, y] pairs, e.g. [[0,0],[100,0],[50,100]].
        fill: Fill colour. Default 'black'.
        stroke: Stroke colour. Default 'none'.
        stroke_width: Stroke width. Default 1.0.
        opacity: Opacity 0–1. Default 1.0.
        group_id: If provided, add to this group instead of document root.
    """
    try:
        dwg, target = _get_target(doc_id, group_id)
        eid = _new_id("polygon_")
        pts = [tuple(p) for p in points]
        elem = dwg.polygon(
            pts,
            fill=fill,
            stroke=stroke,
            stroke_width=stroke_width,
            opacity=opacity,
            id=eid,
        )
        target.add(elem)
        return _ok(element_id=eid)
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def add_path(
    doc_id: str,
    d: str,
    fill: str = "none",
    stroke: str = "black",
    stroke_width: float = 1.0,
    opacity: float = 1.0,
    group_id: Optional[str] = None,
) -> str:
    """Add an SVG path to a document or group.

    Args:
        doc_id: Target document.
        d: SVG path data string (e.g. 'M 10 10 L 100 10 Z').
        fill: Fill colour. Default 'none'.
        stroke: Stroke colour. Default 'black'.
        stroke_width: Stroke width. Default 1.0.
        opacity: Opacity 0–1. Default 1.0.
        group_id: If provided, add to this group instead of document root.
    """
    try:
        dwg, target = _get_target(doc_id, group_id)
        eid = _new_id("path_")
        elem = dwg.path(
            d=d,
            fill=fill,
            stroke=stroke,
            stroke_width=stroke_width,
            opacity=opacity,
            id=eid,
        )
        target.add(elem)
        return _ok(element_id=eid)
    except ValueError as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# Groups (2 tools)
# ---------------------------------------------------------------------------


@mcp.tool()
def create_group(
    doc_id: str,
    group_id: Optional[str] = None,
    opacity: float = 1.0,
    transform: Optional[str] = None,
) -> str:
    """Create a <g> group element in a document.

    Args:
        doc_id: Target document.
        group_id: Optional custom id; auto-generated if omitted.
        opacity: Group opacity 0–1. Default 1.0.
        transform: Optional SVG transform string (e.g. 'translate(10, 20)').
    """
    try:
        dwg = _get_doc(doc_id)
        gid = group_id or _new_id("group_")
        if gid in _groups.get(doc_id, {}):
            return _err(f"Group '{gid}' already exists in document '{doc_id}'.")
        kwargs: dict[str, Any] = {"id": gid, "opacity": opacity}
        if transform:
            kwargs["transform"] = transform
        grp = dwg.g(**kwargs)
        dwg.add(grp)
        _groups[doc_id][gid] = grp
        return _ok(group_id=gid)
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def list_groups(doc_id: str) -> str:
    """List all group ids in a document.

    Args:
        doc_id: Target document.
    """
    try:
        _get_doc(doc_id)
        groups = list(_groups.get(doc_id, {}).keys())
        return _ok(doc_id=doc_id, groups=groups)
    except ValueError as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# Gradients (3 tools)
# ---------------------------------------------------------------------------


@mcp.tool()
def add_linear_gradient(
    doc_id: str,
    stops: list[list],
    gradient_id: Optional[str] = None,
    x1: str = "0%",
    y1: str = "0%",
    x2: str = "100%",
    y2: str = "0%",
) -> str:
    """Add a linearGradient to the document defs.

    Args:
        doc_id: Target document.
        stops: List of [offset, color] or [offset, color, opacity] entries.
               offset is a string like '0%' or '50%'.
        gradient_id: Optional custom id; auto-generated if omitted.
        x1: Gradient start X (default '0%').
        y1: Gradient start Y (default '0%').
        x2: Gradient end X (default '100%').
        y2: Gradient end Y (default '0%').

    Returns JSON with url_ref field (e.g. 'url(#my_gradient)') to use as fill.
    """
    try:
        dwg = _get_doc(doc_id)
        gid = gradient_id or _new_id("lg_")
        existing_ids = {g["id"] for g in _gradients.get(doc_id, [])}
        if gid in existing_ids:
            return _err(
                f"Gradient id '{gid}' already exists in document '{doc_id}'."
            )
        grad = dwg.linearGradient(id=gid, start=(x1, y1), end=(x2, y2))
        for stop in stops:
            offset = stop[0]
            color = stop[1]
            stop_opacity = float(stop[2]) if len(stop) > 2 else 1.0
            grad.add_stop_color(offset=offset, color=color, opacity=stop_opacity)
        dwg.defs.add(grad)
        _gradients[doc_id].append({"id": gid, "type": "linear"})
        return _ok(gradient_id=gid, url_ref=f"url(#{gid})")
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def add_radial_gradient(
    doc_id: str,
    stops: list[list],
    gradient_id: Optional[str] = None,
    cx: str = "50%",
    cy: str = "50%",
    r: str = "50%",
    fx: Optional[str] = None,
    fy: Optional[str] = None,
) -> str:
    """Add a radialGradient to the document defs.

    Args:
        doc_id: Target document.
        stops: List of [offset, color] or [offset, color, opacity] entries.
        gradient_id: Optional custom id; auto-generated if omitted.
        cx: Centre X of the gradient circle (default '50%').
        cy: Centre Y of the gradient circle (default '50%').
        r: Radius of the gradient circle (default '50%').
        fx: Focal point X (defaults to cx).
        fy: Focal point Y (defaults to cy).

    Returns JSON with url_ref field to use as fill.
    """
    try:
        dwg = _get_doc(doc_id)
        gid = gradient_id or _new_id("rg_")
        existing_ids = {g["id"] for g in _gradients.get(doc_id, [])}
        if gid in existing_ids:
            return _err(
                f"Gradient id '{gid}' already exists in document '{doc_id}'."
            )
        center = (cx, cy)
        focal = (fx or cx, fy or cy)
        grad = dwg.radialGradient(id=gid, center=center, r=r, focal=focal)
        for stop in stops:
            offset = stop[0]
            color = stop[1]
            stop_opacity = float(stop[2]) if len(stop) > 2 else 1.0
            grad.add_stop_color(offset=offset, color=color, opacity=stop_opacity)
        dwg.defs.add(grad)
        _gradients[doc_id].append({"id": gid, "type": "radial"})
        return _ok(gradient_id=gid, url_ref=f"url(#{gid})")
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def list_gradients(doc_id: str) -> str:
    """List all gradients registered for a document.

    Args:
        doc_id: Target document.
    """
    try:
        _get_doc(doc_id)
        return _ok(doc_id=doc_id, gradients=_gradients.get(doc_id, []))
    except ValueError as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# Pattern generators (4 tools)
# ---------------------------------------------------------------------------


@mcp.tool()
def add_grid_pattern(
    doc_id: str,
    cell_size: float = 20.0,
    stroke: str = "#cccccc",
    stroke_width: float = 1.0,
    width: Optional[float] = None,
    height: Optional[float] = None,
    group_id: Optional[str] = None,
) -> str:
    """Add a grid of horizontal and vertical lines to a document or group.

    Args:
        doc_id: Target document.
        cell_size: Distance between grid lines in px. Default 20.
        stroke: Line colour. Default '#cccccc'.
        stroke_width: Line width. Default 1.0.
        width: Grid width in px; defaults to document width.
        height: Grid height in px; defaults to document height.
        group_id: If provided, add to this group instead of document root.
    """
    try:
        dwg, target = _get_target(doc_id, group_id)
        w = width if width is not None else _parse_size(dwg["width"])
        h = height if height is not None else _parse_size(dwg["height"])
        x = 0.0
        while x <= w:
            target.add(
                dwg.line(
                    start=(x, 0), end=(x, h),
                    stroke=stroke, stroke_width=stroke_width,
                )
            )
            x += cell_size
        y = 0.0
        while y <= h:
            target.add(
                dwg.line(
                    start=(0, y), end=(w, y),
                    stroke=stroke, stroke_width=stroke_width,
                )
            )
            y += cell_size
        return _ok(cell_size=cell_size, lines_added=True)
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def add_checkerboard_pattern(
    doc_id: str,
    cell_size: float = 20.0,
    color1: str = "white",
    color2: str = "black",
    width: Optional[float] = None,
    height: Optional[float] = None,
    group_id: Optional[str] = None,
) -> str:
    """Add a checkerboard pattern of alternating coloured rectangles.

    Args:
        doc_id: Target document.
        cell_size: Size of each square in px. Default 20.
        color1: Colour for even cells. Default 'white'.
        color2: Colour for odd cells. Default 'black'.
        width: Pattern width; defaults to document width.
        height: Pattern height; defaults to document height.
        group_id: If provided, add to this group instead of document root.
    """
    try:
        dwg, target = _get_target(doc_id, group_id)
        w = width if width is not None else _parse_size(dwg["width"])
        h = height if height is not None else _parse_size(dwg["height"])
        cols = int(w / cell_size) + 1
        rows = int(h / cell_size) + 1
        for row in range(rows):
            for col in range(cols):
                color = color1 if (row + col) % 2 == 0 else color2
                target.add(
                    dwg.rect(
                        insert=(col * cell_size, row * cell_size),
                        size=(cell_size, cell_size),
                        fill=color,
                    )
                )
        return _ok(cell_size=cell_size, cols=cols, rows=rows)
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def add_dot_grid_pattern(
    doc_id: str,
    spacing: float = 20.0,
    dot_radius: float = 2.0,
    fill: str = "#cccccc",
    width: Optional[float] = None,
    height: Optional[float] = None,
    group_id: Optional[str] = None,
) -> str:
    """Add a grid of small circles at regular intervals.

    Args:
        doc_id: Target document.
        spacing: Distance between dot centres in px. Default 20.
        dot_radius: Radius of each dot. Default 2.
        fill: Dot colour. Default '#cccccc'.
        width: Grid width; defaults to document width.
        height: Grid height; defaults to document height.
        group_id: If provided, add to this group instead of document root.
    """
    try:
        dwg, target = _get_target(doc_id, group_id)
        w = width if width is not None else _parse_size(dwg["width"])
        h = height if height is not None else _parse_size(dwg["height"])
        y = spacing
        while y <= h:
            x = spacing
            while x <= w:
                target.add(dwg.circle(center=(x, y), r=dot_radius, fill=fill))
                x += spacing
            y += spacing
        return _ok(spacing=spacing, dot_radius=dot_radius)
    except ValueError as e:
        return _err(str(e))


@mcp.tool()
def add_concentric_circles_pattern(
    doc_id: str,
    cx: float,
    cy: float,
    min_radius: float = 10.0,
    max_radius: float = 100.0,
    step: float = 10.0,
    stroke: str = "black",
    stroke_width: float = 1.0,
    fill: str = "none",
    group_id: Optional[str] = None,
) -> str:
    """Add concentric circles radiating out from a centre point.

    Args:
        doc_id: Target document.
        cx: Centre X coordinate.
        cy: Centre Y coordinate.
        min_radius: Innermost circle radius. Default 10.
        max_radius: Outermost circle radius. Default 100.
        step: Radius increment between circles. Default 10.
        stroke: Stroke colour. Default 'black'.
        stroke_width: Stroke width. Default 1.0.
        fill: Fill colour. Default 'none'.
        group_id: If provided, add to this group instead of document root.
    """
    try:
        dwg, target = _get_target(doc_id, group_id)
        r = min_radius
        count = 0
        while r <= max_radius + 1e-9:
            target.add(
                dwg.circle(
                    center=(cx, cy),
                    r=r,
                    stroke=stroke,
                    stroke_width=stroke_width,
                    fill=fill,
                )
            )
            r += step
            count += 1
        return _ok(circles_added=count)
    except ValueError as e:
        return _err(str(e))
