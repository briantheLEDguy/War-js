"""Load literal link cages/copies and bake their real geometry to material maps.

Run with Blender --background --factory-startup --python tools/bake_chainmail.py.
There are no primitive, ring-profile, scatter, random or noise operations here.
"""
from __future__ import annotations
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import bpy
import bmesh

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "source/chainmail_detail.dat"
OUTPUT = ROOT / "textures/source"


def validate(data):
    vertices = data["link_vertices"]
    edges = Counter()
    for point in vertices:
        assert len(point) == 3 and all(math.isfinite(v) for v in point)
    for face in data["link_faces"]:
        assert len(face) >= 3 and len(set(face)) == len(face)
        assert all(0 <= index < len(vertices) for index in face)
        for a, b in zip(face, face[1:]+face[:1]):
            edges[tuple(sorted((a, b)))] += 1
    assert all(count == 2 for count in edges.values()), "The authored link cage must be closed"
    assert len({p["id"] for p in data["placements"]}) == len(data["placements"])
    assert data["bake"]["resolution"] <= 1024


def literal_mesh(name, vertices, faces, recalculate_closed=True):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    if recalculate_closed:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
    for face in mesh.polygons:
        face.use_smooth = True
    return mesh


def emission_material(name):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.node_tree.nodes.clear()
    emission = material.node_tree.nodes.new("ShaderNodeEmission")
    output = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
    return material, emission


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    validate(data)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = data["bake"]["samples"]
    scene.world = bpy.data.worlds.new("Chainmail bake world")
    scene.world.color = (.1, .1, .1)
    link_mat, link_emission = emission_material("authored.link_paint")
    backing_mat, backing_emission = emission_material("authored.backing_paint")
    mesh = literal_mesh("authored.closed_link", data["link_vertices"], data["link_faces"])
    mesh.materials.append(link_mat)
    high = []
    for placement in data["placements"]:
        obj = bpy.data.objects.new(placement["id"], mesh)
        scene.collection.objects.link(obj)
        obj.location = placement["location"]
        obj.rotation_euler = [math.radians(v) for v in placement["rotation_degrees"]]
        modifier = obj.modifiers.new("Round authored control cage", "SUBSURF")
        modifier.levels = modifier.render_levels = data["finishing"]["levels"]
        obj["source_placement"] = json.dumps(placement)
        high.append(obj)
    backing = data["bake_backing"]
    # Open bake surfaces use their literal +Z winding; closed-volume normal
    # recalculation can flip an isolated open plane away from the origin.
    backing_mesh = literal_mesh("authored.bake_backing", backing["vertices"], backing["faces"], False)
    backing_mesh.materials.append(backing_mat)
    backing_obj = bpy.data.objects.new("bake_backing", backing_mesh)
    scene.collection.objects.link(backing_obj)
    high.append(backing_obj)
    receiver = data["bake_receiver"]
    receiver_mesh = literal_mesh("bake_receiver", receiver["vertices"], receiver["faces"], False)
    uv = receiver_mesh.uv_layers.new(name="tile_uv")
    for face in receiver_mesh.polygons:
        face.use_smooth = False
        for loop in face.loop_indices:
            uv.data[loop].uv = receiver["uv"][receiver_mesh.loops[loop].vertex_index]
    target = bpy.data.objects.new("bake_receiver", receiver_mesh)
    scene.collection.objects.link(target)
    target_mat = bpy.data.materials.new("bake.image_target")
    target_mat.use_nodes = True
    target.data.materials.append(target_mat)
    image_node = target_mat.node_tree.nodes.new("ShaderNodeTexImage")
    target_mat.node_tree.nodes.active = image_node
    for obj in scene.objects:
        obj.select_set(False)
    for obj in high+[target]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = target
    settings = scene.render.bake
    settings.use_selected_to_active = True
    settings.cage_extrusion = data["bake"]["cage_extrusion"]
    settings.max_ray_distance = data["bake"]["max_ray_distance"]
    settings.margin = 4
    settings.use_clear = True
    settings.normal_space = "TANGENT"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for channel in ("basecolor", "roughness", "metallic", "normal", "occlusion"):
        image = bpy.data.images.new("chainmail_"+channel, width=1024, height=1024, alpha=False)
        image.colorspace_settings.name = "sRGB" if channel == "basecolor" else "Non-Color"
        image_node.image = image
        if channel in ("basecolor", "roughness", "metallic"):
            key = "basecolor_linear" if channel == "basecolor" else channel
            a = data["material_paints"]["link"][key]
            b = data["material_paints"]["backing"][key]
            link_emission.inputs["Color"].default_value = (*a, 1) if isinstance(a, list) else (a, a, a, 1)
            backing_emission.inputs["Color"].default_value = (*b, 1) if isinstance(b, list) else (b, b, b, 1)
            bpy.ops.object.bake(type="EMIT")
        elif channel == "normal":
            bpy.ops.object.bake(type="NORMAL")
        else:
            bpy.ops.object.bake(type="AO")
        path = OUTPUT / f"chainmail_{channel}.png"
        image.filepath_raw = str(path)
        image.file_format = "PNG"
        image.save()
        results[channel] = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    source_hash = hashlib.sha256(DATA.read_bytes()).hexdigest()
    report = {"source_sha256": source_hash, "control_vertices": len(data["link_vertices"]),
              "control_faces": len(data["link_faces"]), "explicit_copies": len(data["placements"]),
              "source_cage_validation": "closed edges checked", "maps": results,
              "notes": data["notes"]}
    (ROOT / "textures/chainmail_bake_report.json").write_text(json.dumps(report, indent=2)+"\n")
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "textures/chainmail_bake_source.blend"))
    print("CHAINMAIL_BAKE_COMPLETE "+json.dumps(report))


if __name__ == "__main__":
    main()
