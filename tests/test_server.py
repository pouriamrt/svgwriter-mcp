"""Tests for svgwriter-mcp server tools.

Tools are called directly as plain Python functions — no MCP process needed.
SVG output is verified by parsing with xml.etree.ElementTree.
"""

import json
import xml.etree.ElementTree as ET

import pytest

import server


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NS = {"svg": "http://www.w3.org/2000/svg"}


def parse_svg(svg_str: str) -> ET.Element:
    return ET.fromstring(svg_str)


def count_elements(svg_str: str, tag: str) -> int:
    root = parse_svg(svg_str)
    return len(root.findall(f".//svg:{tag}", NS))


def ok(raw: str) -> dict:
    data = json.loads(raw)
    assert data["status"] == "ok", f"Expected ok, got: {raw}"
    return data


def err(raw: str) -> dict:
    data = json.loads(raw)
    assert data["status"] == "error", f"Expected error, got: {raw}"
    return data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_state():
    server._documents.clear()
    server._groups.clear()
    server._gradients.clear()
    yield
    server._documents.clear()
    server._groups.clear()
    server._gradients.clear()


@pytest.fixture
def doc():
    """Create a fresh 400x300 document and return its doc_id."""
    result = ok(server.create_document(width="400px", height="300px"))
    return result["doc_id"]


# ---------------------------------------------------------------------------
# TestDocuments
# ---------------------------------------------------------------------------


class TestDocuments:
    def test_create_returns_doc_id(self):
        result = ok(server.create_document())
        assert "doc_id" in result

    def test_create_with_custom_id(self):
        result = ok(server.create_document(doc_id="my_doc"))
        assert result["doc_id"] == "my_doc"

    def test_create_duplicate_id_errors(self):
        server.create_document(doc_id="dup")
        err(server.create_document(doc_id="dup"))

    def test_list_documents_empty(self):
        result = ok(server.list_documents())
        assert result["documents"] == []

    def test_list_documents_shows_created(self):
        server.create_document(doc_id="a")
        server.create_document(doc_id="b")
        result = ok(server.list_documents())
        ids = [d["doc_id"] for d in result["documents"]]
        assert "a" in ids and "b" in ids

    def test_delete_document(self):
        server.create_document(doc_id="del_me")
        ok(server.delete_document(doc_id="del_me"))
        result = ok(server.list_documents())
        assert not any(d["doc_id"] == "del_me" for d in result["documents"])

    def test_delete_unknown_errors(self):
        err(server.delete_document(doc_id="ghost"))

    def test_get_svg_string_returns_xml(self, doc):
        result = ok(server.get_svg_string(doc_id=doc))
        assert result["svg"].startswith("<svg")

    def test_get_svg_string_unknown_errors(self):
        err(server.get_svg_string(doc_id="nope"))

    def test_get_svg_preview_returns_list(self, doc):
        result = server.get_svg_preview(doc_id=doc)
        assert isinstance(result, list)
        assert len(result) == 2
        # First item is JSON status string
        status = json.loads(result[0])
        assert status["status"] == "ok"
        assert "width" in status
        # Second item is an Image object with SVG mime type
        from mcp.server.fastmcp.utilities.types import Image
        assert isinstance(result[1], Image)
        img_content = result[1].to_image_content()
        assert img_content.mimeType == "image/svg+xml"

    def test_get_svg_preview_unknown_errors(self):
        result = server.get_svg_preview(doc_id="nope")
        data = json.loads(result)
        assert data["status"] == "error"

    def test_save_file(self, doc, tmp_path):
        path = str(tmp_path / "out.svg")
        result = ok(server.save_file(doc_id=doc, filepath=path))
        assert result["filepath"] == path
        content = open(path).read()
        assert "<svg" in content

    def test_save_file_unknown_doc_errors(self, tmp_path):
        err(server.save_file(doc_id="ghost", filepath=str(tmp_path / "x.svg")))


# ---------------------------------------------------------------------------
# TestShapes
# ---------------------------------------------------------------------------


class TestShapes:
    def test_add_circle(self, doc):
        result = ok(server.add_circle(doc_id=doc, cx=50, cy=50, r=20))
        assert result["element_id"].startswith("circle_")
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "circle") == 1

    def test_add_circle_unknown_doc_errors(self):
        err(server.add_circle(doc_id="nope", cx=0, cy=0, r=5))

    def test_add_rect(self, doc):
        result = ok(server.add_rect(doc_id=doc, x=10, y=10, width=80, height=60))
        assert result["element_id"].startswith("rect_")
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "rect") == 1

    def test_add_rect_with_rounded_corners(self, doc):
        ok(server.add_rect(doc_id=doc, x=0, y=0, width=100, height=100, rx=10, ry=10))
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert 'rx="10"' in svg

    def test_add_line(self, doc):
        result = ok(server.add_line(doc_id=doc, x1=0, y1=0, x2=100, y2=100))
        assert result["element_id"].startswith("line_")
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "line") == 1

    def test_add_ellipse(self, doc):
        ok(server.add_ellipse(doc_id=doc, cx=100, cy=100, rx=50, ry=30))
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "ellipse") == 1

    def test_add_text(self, doc):
        result = ok(server.add_text(doc_id=doc, text="Hello", x=10, y=20))
        assert result["element_id"].startswith("text_")
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert "Hello" in svg

    def test_add_polygon(self, doc):
        ok(server.add_polygon(doc_id=doc, points=[[0, 0], [100, 0], [50, 100]]))
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "polygon") == 1

    def test_add_path(self, doc):
        ok(server.add_path(doc_id=doc, d="M 10 10 L 100 10 Z"))
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "path") == 1

    def test_multiple_shapes(self, doc):
        server.add_circle(doc_id=doc, cx=50, cy=50, r=10)
        server.add_circle(doc_id=doc, cx=100, cy=100, r=20)
        server.add_rect(doc_id=doc, x=0, y=0, width=50, height=50)
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "circle") == 2
        assert count_elements(svg, "rect") == 1


# ---------------------------------------------------------------------------
# TestGroups
# ---------------------------------------------------------------------------


class TestGroups:
    def test_create_group(self, doc):
        result = ok(server.create_group(doc_id=doc, group_id="g1"))
        assert result["group_id"] == "g1"

    def test_create_group_auto_id(self, doc):
        result = ok(server.create_group(doc_id=doc))
        assert result["group_id"].startswith("group_")

    def test_create_group_duplicate_errors(self, doc):
        server.create_group(doc_id=doc, group_id="g1")
        err(server.create_group(doc_id=doc, group_id="g1"))

    def test_list_groups_empty(self, doc):
        result = ok(server.list_groups(doc_id=doc))
        assert result["groups"] == []

    def test_list_groups(self, doc):
        server.create_group(doc_id=doc, group_id="g1")
        server.create_group(doc_id=doc, group_id="g2")
        result = ok(server.list_groups(doc_id=doc))
        assert "g1" in result["groups"] and "g2" in result["groups"]

    def test_add_shape_to_group(self, doc):
        server.create_group(doc_id=doc, group_id="mygroup")
        ok(server.add_circle(doc_id=doc, cx=50, cy=50, r=10, group_id="mygroup"))
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "circle") == 1

    def test_add_to_unknown_group_errors(self, doc):
        err(server.add_circle(doc_id=doc, cx=0, cy=0, r=5, group_id="ghost_group"))

    def test_group_in_svg_output(self, doc):
        server.create_group(doc_id=doc, group_id="g1")
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert 'id="g1"' in svg


# ---------------------------------------------------------------------------
# TestGradients
# ---------------------------------------------------------------------------


class TestGradients:
    def test_add_linear_gradient(self, doc):
        result = ok(server.add_linear_gradient(
            doc_id=doc,
            stops=[["0%", "red"], ["100%", "blue"]],
            gradient_id="grad1",
        ))
        assert result["url_ref"] == "url(#grad1)"

    def test_add_linear_gradient_auto_id(self, doc):
        result = ok(server.add_linear_gradient(
            doc_id=doc,
            stops=[["0%", "red"], ["100%", "blue"]],
        ))
        assert result["url_ref"].startswith("url(#lg_")

    def test_add_linear_gradient_in_svg(self, doc):
        server.add_linear_gradient(
            doc_id=doc, stops=[["0%", "red"], ["100%", "blue"]], gradient_id="g1"
        )
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert "linearGradient" in svg

    def test_add_radial_gradient(self, doc):
        result = ok(server.add_radial_gradient(
            doc_id=doc,
            stops=[["0%", "white"], ["100%", "black"]],
            gradient_id="rg1",
        ))
        assert result["url_ref"] == "url(#rg1)"

    def test_duplicate_gradient_id_errors(self, doc):
        server.add_linear_gradient(doc_id=doc, stops=[["0%", "red"]], gradient_id="g1")
        err(server.add_linear_gradient(doc_id=doc, stops=[["0%", "blue"]], gradient_id="g1"))

    def test_list_gradients(self, doc):
        server.add_linear_gradient(doc_id=doc, stops=[["0%", "red"]], gradient_id="g1")
        server.add_radial_gradient(doc_id=doc, stops=[["0%", "blue"]], gradient_id="r1")
        result = ok(server.list_gradients(doc_id=doc))
        ids = [g["id"] for g in result["gradients"]]
        assert "g1" in ids and "r1" in ids

    def test_use_gradient_as_fill(self, doc):
        grad = ok(server.add_linear_gradient(
            doc_id=doc, stops=[["0%", "red"], ["100%", "blue"]], gradient_id="sky"
        ))
        ok(server.add_rect(
            doc_id=doc, x=0, y=0, width=400, height=300, fill=grad["url_ref"]
        ))
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert "url(#sky)" in svg


# ---------------------------------------------------------------------------
# TestPatterns
# ---------------------------------------------------------------------------


class TestPatterns:
    def test_add_grid_pattern(self, doc):
        ok(server.add_grid_pattern(doc_id=doc, cell_size=50.0))
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        # 400px wide / 50 = 8+1 vertical lines; 300px tall / 50 = 6+1 horizontal = 17 total
        assert count_elements(svg, "line") >= 10

    def test_add_checkerboard_pattern(self, doc):
        result = ok(server.add_checkerboard_pattern(doc_id=doc, cell_size=100.0))
        assert result["cols"] >= 4
        assert result["rows"] >= 3
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "rect") >= 1

    def test_add_dot_grid_pattern(self, doc):
        ok(server.add_dot_grid_pattern(doc_id=doc, spacing=50.0, dot_radius=3.0))
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "circle") >= 1

    def test_add_concentric_circles_pattern(self, doc):
        result = ok(server.add_concentric_circles_pattern(
            doc_id=doc, cx=200, cy=150,
            min_radius=10, max_radius=100, step=10,
        ))
        assert result["circles_added"] == 10
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "circle") == 10

    def test_pattern_in_group(self, doc):
        server.create_group(doc_id=doc, group_id="pg")
        ok(server.add_grid_pattern(doc_id=doc, cell_size=50.0, group_id="pg"))
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "line") >= 1

    def test_grid_with_explicit_dimensions(self, doc):
        ok(server.add_grid_pattern(
            doc_id=doc, cell_size=50.0, width=200.0, height=200.0
        ))
        svg = ok(server.get_svg_string(doc_id=doc))["svg"]
        assert count_elements(svg, "line") >= 8


# ---------------------------------------------------------------------------
# TestErrors
# ---------------------------------------------------------------------------


class TestErrors:
    def test_shape_on_unknown_doc(self):
        err(server.add_circle(doc_id="missing", cx=0, cy=0, r=1))
        err(server.add_rect(doc_id="missing", x=0, y=0, width=10, height=10))
        err(server.add_line(doc_id="missing", x1=0, y1=0, x2=1, y2=1))
        err(server.add_ellipse(doc_id="missing", cx=0, cy=0, rx=5, ry=5))
        err(server.add_text(doc_id="missing", text="hi", x=0, y=0))
        err(server.add_polygon(doc_id="missing", points=[[0, 0], [1, 0], [0, 1]]))
        err(server.add_path(doc_id="missing", d="M 0 0"))

    def test_gradient_on_unknown_doc(self):
        err(server.add_linear_gradient(doc_id="missing", stops=[["0%", "red"]]))
        err(server.add_radial_gradient(doc_id="missing", stops=[["0%", "red"]]))
        err(server.list_gradients(doc_id="missing"))

    def test_group_on_unknown_doc(self):
        err(server.create_group(doc_id="missing"))
        err(server.list_groups(doc_id="missing"))

    def test_pattern_on_unknown_doc(self):
        err(server.add_grid_pattern(doc_id="missing"))
        err(server.add_checkerboard_pattern(doc_id="missing"))
        err(server.add_dot_grid_pattern(doc_id="missing"))
        err(server.add_concentric_circles_pattern(doc_id="missing", cx=0, cy=0))
