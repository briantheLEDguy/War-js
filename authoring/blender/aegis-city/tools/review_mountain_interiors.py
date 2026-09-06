"""Inspect the actual mountain exports from inside their playable shells."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

WORK=Path(__file__).resolve().parents[1]
views=[
    ('mountain_passage','mountain-passage-interior',(0,-10,3),(0,9,7),22),
    ('mountain_redoubt','mountain-redoubt-interior',(0,-40,4.5),(0,8,13),18),
    ('mountain_redoubt','mountain-command-chamber',(35,2,6),(-12,43,13),20),
    ('mountain_vault','mountain-vault-interior',(12,-20,4),(-9,33,11),18),
    ('mountain_vault','mountain-vault-portals',(-16,-6,5),(23.5,4,7),16),
    ('mountain_seal','mountain-seal',(19,-31,17),(0,0,7),45),
]
requested=next((arg.split('=',1)[1] for arg in sys.argv if arg.startswith('--view=')),None)
for kind,name,position,target,lens in views:
    if requested and name!=requested: continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime'/f'prop_aegis_{kind}.glb'))
    scene=bpy.context.scene
    scene.world=bpy.data.worlds.new('mountain_review_world')
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
    lights=[(-35,-24,23),(35,-24,23),(-35,25,23),(35,25,23),(0,40,22)] if kind=='mountain_redoubt' else [(0,-26,16),(0,0,16),(0,28,16)] if kind=='mountain_vault' else [(0,-4,12),(0,8,12)]
    for position_light in lights:
        bpy.ops.object.light_add(type='AREA',location=position_light)
        bpy.context.object.data.energy=14000 if kind=='mountain_redoubt' else 6500 if kind=='mountain_vault' else 2000
        bpy.context.object.data.size=22 if kind=='mountain_redoubt' else 10
    bpy.ops.object.camera_add(location=position)
    camera=bpy.context.object
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.lens=lens
    camera.data.clip_start=.1
    camera.data.clip_end=3000
    scene.camera=camera
    scene.render.engine='CYCLES'
    scene.cycles.samples=20
    scene.render.resolution_x=1500
    scene.render.resolution_y=1000
    scene.render.resolution_percentage=100
    scene.render.filepath=str(WORK/'review'/f'{name}.png')
    bpy.ops.render.render(write_still=True)
