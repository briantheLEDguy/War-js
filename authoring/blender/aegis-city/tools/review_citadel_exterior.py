"""Render the actual runtime exports in daylight, including the distant LOD."""
import bpy
from pathlib import Path
from mathutils import Vector

WORK = Path(__file__).resolve().parents[1]
for name, suffix, location, target, lens in [
    ('citadel-gothic', '', (170, -245, 120), (0, -18, 57), 48),
    ('citadel-gothic-facade', '', (35, -136, 32), (0, -46, 28), 44),
    ('citadel-gothic-lod2', '_lod2', (170, -245, 120), (0, -18, 57), 48),
]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime'/f'prop_aegis_citadel{suffix}.glb'))
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('overcast_daylight')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes['Background']
    background.inputs[0].default_value = (.36, .43, .51, 1)
    background.inputs[1].default_value = .65
    bpy.ops.object.light_add(type='SUN', location=(-90, -100, 140))
    sun = bpy.context.object
    sun.rotation_euler = (Vector((0, 0, 30)) - sun.location).to_track_quat('-Z', 'Y').to_euler()
    sun.data.energy = 2.5
    sun.data.angle = .12
    bpy.ops.mesh.primitive_plane_add(size=2000, location=(0, 0, -.45))
    ground = bpy.context.object
    mat = bpy.data.materials.new('review_ground')
    mat.diffuse_color = (.24, .26, .27, 1)
    ground.data.materials.append(mat)
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.object
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_end = 3000
    scene.camera = cam
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1400 if 'facade' not in name else 1000
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(WORK/'review'/f'{name}.png')
    bpy.ops.render.render(write_still=True)
