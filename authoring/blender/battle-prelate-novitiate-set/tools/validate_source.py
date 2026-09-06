"""Validate authored records without importing Blender or changing any geometry."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATERIALS = {"skin", "skin_ear", "lip", "eye_white", "iris", "pupil", "brow", "steel", "brass", "dark_steel", "chainmail", "leather", "crimson", "parchment"}
MODIFIERS = {"MIRROR", "SUBSURF", "BEVEL", "SOLIDIFY"}


def finite_vector(value, size, label):
    if not isinstance(value, list) or len(value) != size or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value):
        raise ValueError(f"{label}: expected {size} finite coordinates")


def validate_component(data):
    if data.get("schema_version") != 1 or not isinstance(data.get("component"), str) or not data["component"].strip():
        raise ValueError("Expected schema_version=1 and component name")
    if not isinstance(data.get("parts"),list) or not data["parts"]:
        raise ValueError("Expected at least one authored part")
    result = []
    part_ids = set()
    for part in data["parts"]:
        name = part["id"]
        if not isinstance(name,str) or not name.strip() or not part.get("vertices") or not part.get("faces"):
            raise ValueError("Expected named part with vertices and faces")
        if name in part_ids:
            raise ValueError(f"Duplicate part {name}")
        part_ids.add(name)
        vertices = {}
        for vertex in part["vertices"]:
            if vertex["id"] in vertices:
                raise ValueError(f"{name}: duplicate vertex {vertex['id']}")
            finite_vector(vertex["co"], 3, f"{name}.{vertex['id']}")
            vertices[vertex["id"]] = vertex["co"]
        face_ids, edges = set(), Counter()
        triangles = 0
        for face in part["faces"]:
            ids = face["vertices"]
            if face["id"] in face_ids:
                raise ValueError(f"{name}: duplicate face {face['id']}")
            face_ids.add(face["id"])
            if len(ids) < 3 or len(set(ids)) != len(ids) or any(v not in vertices for v in ids):
                raise ValueError(f"{name}.{face['id']}: invalid face indices")
            if face["material"] not in MATERIALS:
                raise ValueError(f"{name}.{face['id']}: unknown material")
            if len(face["uv"]) != len(ids):
                raise ValueError(f"{name}.{face['id']}: per-corner UV count mismatch")
            for uv in face["uv"]:
                finite_vector(uv, 2, f"{name}.{face['id']} UV")
            # Newell's area vector works for triangles, quads and concave planar faces.
            normal = [0.0, 0.0, 0.0]
            for a, b in zip(ids, ids[1:] + ids[:1]):
                pa, pb = vertices[a], vertices[b]
                edges[tuple(sorted((a, b)))] += 1
                normal[0] += (pa[1] - pb[1]) * (pa[2] + pb[2])
                normal[1] += (pa[2] - pb[2]) * (pa[0] + pb[0])
                normal[2] += (pa[0] - pb[0]) * (pa[1] + pb[1])
            if sum(n*n for n in normal) <= 1e-20:
                raise ValueError(f"{name}.{face['id']}: degenerate face")
            triangles += len(ids)-2
        if any(count > 2 for count in edges.values()):
            raise ValueError(f"{name}: nonmanifold control edge")
        boundary = sum(count == 1 for count in edges.values())
        if part.get("closed") and boundary:
            raise ValueError(f"{name}: declared closed but has {boundary} boundary edges")
        for field in ("seams", "sharp_edges"):
            for edge in part.get(field, []):
                if tuple(sorted(edge)) not in edges:
                    raise ValueError(f"{name}: {field} references nonexistent edge {edge}")
        for crease in part.get("creases", []):
            if tuple(sorted(crease["edge"])) not in edges or not 0 <= crease["value"] <= 1:
                raise ValueError(f"{name}: invalid crease")
        for landmark, vertex in part.get("landmarks", {}).items():
            if vertex not in vertices:
                raise ValueError(f"{name}: missing landmark {landmark}")
        for transform in [part.get("transform", {})] + part.get("instances", []):
            if "matrix" in transform:
                matrix=transform["matrix"]
                if not isinstance(matrix,list) or len(matrix)!=4:
                    raise ValueError(f"{name}: expected explicit 4x4 matrix")
                for row in matrix:
                    finite_vector(row,4,f"{name} transform matrix")
                if matrix[3] != [0,0,0,1]:
                    raise ValueError(f"{name}: expected affine transform matrix")
            for field, default in (("location", [0,0,0]), ("rotation_degrees", [0,0,0]), ("scale", [1,1,1])):
                finite_vector(transform.get(field, default), 3, f"{name} {field}")
            if any(abs(v) < 1e-8 for v in transform.get("scale", [1,1,1])):
                raise ValueError(f"{name}: singular scale")
        for modifier in part.get("modifiers", []):
            if modifier["type"] not in MODIFIERS:
                raise ValueError(f"{name}: prohibited modifier {modifier['type']}")
            if modifier["type"] == "SUBSURF" and not 0 <= modifier["levels"] <= 4:
                raise ValueError(f"{name}: excessive subdivision")
            if modifier["type"] == "MIRROR" and modifier.get("axis", "X") not in ("X", "Y", "Z"):
                raise ValueError(f"{name}: invalid mirror axis")
            if modifier["type"] == "BEVEL":
                width=modifier.get("width")
                if not isinstance(width,(int,float)) or not math.isfinite(width) or not 0 < width <= .05 or not isinstance(modifier.get("segments",2),int) or not 1 <= modifier.get("segments",2) <= 8:
                    raise ValueError(f"{name}: invalid bevel settings")
            if modifier["type"] == "SOLIDIFY":
                thickness,offset=modifier.get("thickness"),modifier.get("offset",0)
                if not isinstance(thickness,(int,float)) or not math.isfinite(thickness) or not 0 < thickness <= .05 or not isinstance(offset,(int,float)) or not math.isfinite(offset) or not -1 <= offset <= 1:
                    raise ValueError(f"{name}: invalid solidify settings")
        result.append({"part":name,"control_vertices":len(vertices),"control_faces":len(face_ids),"control_triangles":triangles,"control_boundary_edges":boundary})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    reports = []
    for path in args.paths or sorted((ROOT/"source").glob("*.json")):
        path=path.resolve()
        if path.name == "scene.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        reports.append({"file":str(path.relative_to(ROOT)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"parts":validate_component(data)})
    print(json.dumps({"status":"passed","components":reports}, indent=2))


if __name__ == "__main__":
    main()
