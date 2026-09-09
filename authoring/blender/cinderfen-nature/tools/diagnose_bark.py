"""Separate exported bark texture, tangent normals and geometric shading."""
import bpy
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
model = ROOT / 'runtime/frontier_cinderfen_marsh_alder_lod0.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(model))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 1400
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world = bpy.data.worlds.new('neutral_bark_diagnostic_world')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.25, .25, .25, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .7
target = Vector((0, 0, 2.42))
data = bpy.data.cameras.new('exported_bark_diagnostic_camera')
camera = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.location = Vector((3.5, -7.2, 3.4))
camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
data.type = 'ORTHO'
data.ortho_scale = 5.5
for name, position, power in [('key',(-4,-6,8),1800),('fill',(6,-3,5),1300),('rim',(0,6,8),1600)]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = 5
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = Vector(position)
    light.rotation_euler = (target-light.location).to_track_quat('-Z', 'Y').to_euler()
scene.view_settings.view_transform = 'AgX'
bark = next(m for m in bpy.data.materials if 'alder_bark' in m.name)
shader = next(n for n in bark.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
for link in list(shader.inputs['Normal'].links):
    bark.node_tree.links.remove(link)
scene.render.filepath = str(ROOT / 'review/diagnostic_bark_normal_off.png')
bpy.ops.render.render(write_still=True)
for name in ['Base Color', 'Roughness', 'Metallic']:
    for link in list(shader.inputs[name].links):
        bark.node_tree.links.remove(link)
shader.inputs['Base Color'].default_value = (.16, .16, .16, 1)
shader.inputs['Roughness'].default_value = .85
shader.inputs['Metallic'].default_value = 0
scene.render.filepath = str(ROOT / 'review/diagnostic_bark_geometry_only.png')
bpy.ops.render.render(write_still=True)
