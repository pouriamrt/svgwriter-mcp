"""Demonstration of svgwriter-mcp tools.

Run with:  uv run python example.py
Output:    example_output.svg
"""

import json
import server


def main():
    # 1. Create a 600x400 document
    result = json.loads(server.create_document(width="600px", height="400px", doc_id="demo"))
    doc_id = result["doc_id"]
    print(f"Created document: {doc_id}")

    # 2. Add a sky-blue linear gradient
    grad = json.loads(server.add_linear_gradient(
        doc_id=doc_id,
        stops=[["0%", "#87CEEB"], ["100%", "#1E90FF"]],
        gradient_id="sky",
        x1="0%", y1="0%", x2="0%", y2="100%",
    ))
    sky_ref = grad["url_ref"]
    print(f"Added gradient: {sky_ref}")

    # 3. Background rectangle filled with gradient
    server.add_rect(
        doc_id=doc_id,
        x=0, y=0, width=600, height=400,
        fill=sky_ref,
        stroke="none",
    )
    print("Added background rect")

    # 4. Create a group for the grid overlay
    grp = json.loads(server.create_group(doc_id=doc_id, group_id="grid_group", opacity=0.3))
    grid_gid = grp["group_id"]
    server.add_grid_pattern(
        doc_id=doc_id,
        cell_size=30.0,
        stroke="white",
        stroke_width=0.5,
        group_id=grid_gid,
    )
    print("Added grid pattern")

    # 5. Concentric circles pattern centred at (300, 200)
    cc = json.loads(server.add_concentric_circles_pattern(
        doc_id=doc_id,
        cx=300, cy=200,
        min_radius=20, max_radius=160, step=20,
        stroke="white",
        stroke_width=1.5,
        fill="none",
    ))
    print(f"Added {cc['circles_added']} concentric circles")

    # 6. White dot at centre
    server.add_circle(
        doc_id=doc_id,
        cx=300, cy=200, r=8,
        fill="white",
        stroke="none",
    )
    print("Added centre dot")

    # 7. Title text
    server.add_text(
        doc_id=doc_id,
        text="svgwriter-mcp",
        x=300, y=385,
        font_size="18px",
        font_family="sans-serif",
        fill="white",
        text_anchor="middle",
    )
    print("Added title text")

    # 8. Export
    svg_result = json.loads(server.get_svg_string(doc_id=doc_id))
    print(f"SVG size: {len(svg_result['svg'])} chars")

    save_result = json.loads(server.save_file(doc_id=doc_id, filepath="example_output.svg", pretty=True))
    print(f"Saved to: {save_result['filepath']}")


if __name__ == "__main__":
    main()
