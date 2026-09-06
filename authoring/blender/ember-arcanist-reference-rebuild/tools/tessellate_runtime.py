"""Tessellate authored n-gons so Blender can export explicit MikkTSpace tangents."""
import math

import bmesh


def prepare_tangents(obj):
    mesh = obj.data
    before = [(tuple(v.co), tuple((g.group, g.weight) for g in v.groups)) for v in mesh.vertices]
    mesh.calc_loop_triangles()
    triangle_count = len(mesh.loop_triangles)
    ngon_count = sum(len(face.vertices) > 4 for face in mesh.polygons)
    if ngon_count:
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=[face for face in bm.faces if len(face.verts) > 4],
                                 quad_method='FIXED', ngon_method='BEAUTY')
            bm.to_mesh(mesh)
        finally:
            bm.free()
        mesh.update()
    after = [(tuple(v.co), tuple((g.group, g.weight) for g in v.groups)) for v in mesh.vertices]
    if before != after:
        raise ValueError(f"Tessellation changed positions or skin weights: {obj.name}")
    mesh.calc_loop_triangles()
    if len(mesh.loop_triangles) != triangle_count:
        raise ValueError(f"Tessellation changed the triangle budget: {obj.name}")
    mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
    if any(not math.isfinite(value) for loop in mesh.loops for value in (*loop.tangent, loop.bitangent_sign)):
        raise ValueError(f"Nonfinite runtime tangent: {obj.name}")
    return {"authored_ngons_tessellated": ngon_count, "triangles": triangle_count,
            "positions_and_weights_unchanged": True, "explicit_tangents": True}
