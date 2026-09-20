"""Render original GLB geometry in disposable Blender state for import comparison."""
import json
import hashlib
import argparse
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
registry = json.loads((ROOT / "public/assets/models/asset-index.json").read_text())
parser = argparse.ArgumentParser()
parser.add_argument("--profile", action="append", choices=sorted(registry["characterProfiles"]))
options = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
for profile in options.profile or ("npc_frontier_sunmeadow_empire_herbalist", "mire_warbrute_m"):
    record = registry["characterProfiles"][profile]
    source = ROOT / "public/assets/models" / record["model"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != record["modelSha256"]:
        raise RuntimeError("Source bytes do not match the registry")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source), disable_bone_shape=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 8
    scene.render.resolution_x = 640
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new("InspectionWorld")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.3, 0.3, 1)
    camera = bpy.data.objects.new("InspectionCamera", bpy.data.cameras.new("InspectionCamera"))
    scene.collection.objects.link(camera)
    camera.location = (0, -5, 1.1)
    camera.rotation_euler = (Vector((0, 0, 1.1)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.6
    scene.camera = camera
    light = bpy.data.objects.new("InspectionLight", bpy.data.lights.new("InspectionLight", "AREA"))
    scene.collection.objects.link(light)
    light.location = (2, -3, 4)
    light.rotation_euler = (Vector((0, 0, 1)) - light.location).to_track_quat("-Z", "Y").to_euler()
    light.data.energy = 400
    light.data.shape = "DISK"
    light.data.size = 4
    scene.render.filepath = str(ROOT / "artifacts/unreal/visual-proof" / (profile + "-source.png"))
    bpy.ops.render.render(write_still=True)
