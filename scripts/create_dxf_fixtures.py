#!/usr/bin/env python3
"""Create DXF test fixtures required by SN-003 and SN-010."""
import ezdxf
from pathlib import Path

FIXTURES = Path("tests/fixtures/dxf")
FIXTURES.mkdir(parents=True, exist_ok=True)


def make_doc():
    doc = ezdxf.new("R2010")
    doc.layers.add("OUTLINE")
    return doc


def add_square_lines(msp, corners, layer="OUTLINE"):
    """Add 4 LINE entities forming a closed square from a list of 4 corners."""
    n = len(corners)
    for i in range(n):
        p0 = corners[i]
        p1 = corners[(i + 1) % n]
        msp.add_line(p0, p1, dxfattribs={"layer": layer})


# ---------- square_clean.dxf ----------
doc = make_doc()
msp = doc.modelspace()
corners_clean = [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)]
add_square_lines(msp, corners_clean)
doc.saveas(FIXTURES / "square_clean.dxf")
print("Created square_clean.dxf")

# ---------- square_microgap.dxf ----------
# 5-micron (0.005 mm) gap at corner (10, 0)
doc = make_doc()
msp = doc.modelspace()
msp.add_line((0, 0, 0), (10, 0, 0), dxfattribs={"layer": "OUTLINE"})
msp.add_line((10.005, 0, 0), (10, 10, 0), dxfattribs={"layer": "OUTLINE"})  # 5 µm gap
msp.add_line((10, 10, 0), (0, 10, 0), dxfattribs={"layer": "OUTLINE"})
msp.add_line((0, 10, 0), (0, 0, 0), dxfattribs={"layer": "OUTLINE"})
doc.saveas(FIXTURES / "square_microgap.dxf")
print("Created square_microgap.dxf")

# ---------- square_large_gap.dxf ----------
# 100-micron (0.1 mm) gap at corner (10, 0)
doc = make_doc()
msp = doc.modelspace()
msp.add_line((0, 0, 0), (10, 0, 0), dxfattribs={"layer": "OUTLINE"})
msp.add_line((10.1, 0, 0), (10, 10, 0), dxfattribs={"layer": "OUTLINE"})   # 100 µm gap
msp.add_line((10, 10, 0), (0, 10, 0), dxfattribs={"layer": "OUTLINE"})
msp.add_line((0, 10, 0), (0, 0, 0), dxfattribs={"layer": "OUTLINE"})
doc.saveas(FIXTURES / "square_large_gap.dxf")
print("Created square_large_gap.dxf")

# ---------- washer.dxf ----------
# Outer circle r=10mm + inner circle r=4mm (hole)
doc = make_doc()
doc.layers.add("CUTOUT")
msp = doc.modelspace()
msp.add_circle((0, 0, 0), radius=10, dxfattribs={"layer": "OUTLINE"})
msp.add_circle((0, 0, 0), radius=4,  dxfattribs={"layer": "CUTOUT"})
doc.saveas(FIXTURES / "washer.dxf")
print("Created washer.dxf")

# ---------- three_parts.dxf ----------
# Three closed rectangles on OUTLINE layer, clearly separated
doc = make_doc()
msp = doc.modelspace()
rects = [
    [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)],
    [(20, 0, 0), (30, 0, 0), (30, 10, 0), (20, 10, 0)],
    [(40, 0, 0), (50, 0, 0), (50, 10, 0), (40, 10, 0)],
]
for rect in rects:
    add_square_lines(msp, rect)
doc.saveas(FIXTURES / "three_parts.dxf")
print("Created three_parts.dxf")

print("All DXF fixtures created successfully.")
