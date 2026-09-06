import bpy
from pathlib import Path
from mathutils import Vector
WORK=Path(__file__).resolve().parents[1]
OUT=WORK/'runtime'
# Reimport actual exports into a single architectural review stage.
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for i,kind in enumerate(['house_1','house_2','tavern_1','chapel','gatehouse','bridge_wide']):
    bpy.ops.import_scene.gltf(filepath=str(OUT/f'prop_aegis_{kind}.glb'))
    for ob in bpy.context.selected_objects: ob.location.x+=(i%3)*20-20; ob.location.y+=(i//3)*25
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=24
scene.world=bpy.data.worlds.new('Aegis review world'); scene.world.color=(.35,.35,.35)
bpy.ops.object.light_add(type='AREA',location=(5,-15,40)); bpy.context.object.data.energy=14000; bpy.context.object.data.shape='DISK'; bpy.context.object.data.size=30
bpy.ops.object.camera_add(location=(62,-75,58)); cam=bpy.context.object; cam.rotation_euler=(Vector((0,10,7))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=88; scene.camera=cam
scene.render.resolution_x=1800; scene.render.resolution_y=1300; scene.render.resolution_percentage=100
scene.render.filepath=str(WORK/'review'/'exported-kit.png'); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'aegis_city_review.blend'))
