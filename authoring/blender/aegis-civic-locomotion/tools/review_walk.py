"""Clean-import walking exports and render their actual deformed skin at contact and swing."""
import bpy
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 20
scene.cycles.use_denoising = True
scene.render.resolution_x = 1400
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world = bpy.data.worlds.new('Review studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.13, .15, .18, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .4
scene.view_settings.view_transform = 'AgX'
for name, pos, energy in [('Key',(-3,-4,5),700), ('Fill',(4,-2,3),500), ('Rim',(2,3,4),800)]:
    data = bpy.data.lights.new(name, 'AREA'); data.energy = energy; data.size = 4
    obj = bpy.data.objects.new(name, data); scene.collection.objects.link(obj)
    obj.location = pos; obj.rotation_euler = (Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=200)
floor = bpy.context.object
material = bpy.data.materials.new('Matte stone'); material.diffuse_color = (.16,.18,.21,1)
floor.data.materials.append(material)
camera_data = bpy.data.cameras.new('Review camera'); camera_data.type='ORTHO'; camera_data.ortho_scale=3.8
camera = bpy.data.objects.new('Review camera', camera_data); scene.collection.objects.link(camera); scene.camera=camera
camera.location=(3,-7,2.4); camera.rotation_euler=(Vector((0,0,1.05))-camera.location).to_track_quat('-Z','Y').to_euler()
rigs = []
for variant, x in [('civilian_male',-.75), ('civilian_female',.75)]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'runtime'/f'chr_aegis_people_{variant}_walk.glb'))
    objects = set(bpy.data.objects)-before
    rig = next(obj for obj in objects if obj.type == 'ARMATURE')
    actions = {strip.action for track in rig.animation_data.nla_tracks for strip in track.strips if strip.action}
    if rig.animation_data.action: actions.add(rig.animation_data.action)
    walk = next(action for action in actions if action.name.split('.')[0] == 'walk')
    rig.animation_data.action=walk
    if hasattr(walk,'slots') and walk.slots: rig.animation_data.action_slot=walk.slots[0]
    for track in rig.animation_data.nla_tracks: track.mute=True
    for obj in objects:
        if obj.parent not in objects: obj.location.x+=x
    rigs.append((rig, walk))
for phase in [.1,.4,.8]:
    frame = 1 + phase * (rigs[0][1].frame_range[1]-1)
    scene.frame_set(int(frame), subframe=frame-int(frame))
    scene.render.filepath=str(ROOT/'review'/f'walking_phase_{int(phase*100):02}.png')
    bpy.ops.render.render(write_still=True)
camera.location=(6,-.5,1.8); camera.rotation_euler=(Vector((0,0,1))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(ROOT/'review'/'walking_side.png')
bpy.ops.render.render(write_still=True)
