"""Review the exported keep at player height, including the open doorway and gallery."""
import bpy
from pathlib import Path
from mathutils import Vector

work = Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(work / 'runtime/prop_aegis_citadel.glb'))
scene = bpy.context.scene
scene.world = bpy.data.worlds.new('hall_review_world')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6
for x in [-20, 0, 20]:
    bpy.ops.object.light_add(type='AREA', location=(x, 0, 12))
    bpy.context.object.data.energy = 2400
    bpy.context.object.data.size = 12
bpy.ops.object.camera_add(location=(0, -10, 2.5))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 10, 5)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.lens = 18
camera.data.clip_start = .1
scene.camera = camera
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.render.resolution_x = 1400
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.filepath = str(work / 'review/citadel-interior.png')
bpy.ops.render.render(write_still=True)
