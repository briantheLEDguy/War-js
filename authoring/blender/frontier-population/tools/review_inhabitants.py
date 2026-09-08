"""Review clean runtime imports, including actual skinned animation poses."""
import bpy
import json
import hashlib
import sys
from pathlib import Path
from mathutils import Vector

WORK = Path(__file__).resolve().parents[1]
key = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--asset=')), 'frontier_sunmeadow_dwarf_artisan')
lod = int(next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--lod=')), '0'))
views = next((a.split('=', 1)[1].split(',') for a in sys.argv if a.startswith('--views=')), ['front', 'side', 'head', 'walk'])
sheet = '--motion-sheet' in sys.argv
if sheet:
    views=[f'{clip}:{phase}' for clip,phases in [('idle',[0,1,2]),('walk',[0,.25,.5]),('run',[0,1/6,1/3]),
           ('combat_idle',[0,1,2]),('attack_melee',[.2,.5,.8]),('attack_ranged',[.2,.65,1.1]),
           ('cast',[.25,1,1.75]),('death',[.2,1,2]),('jump',[.2,.65,1.1])] for phase in phases]
override=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--model=')),None)
suffix=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--suffix=')),'')
model = Path(override).resolve() if override else WORK / 'runtime' / f'{key}_lod{lod}.glb'
digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
original_hash = digest(model)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(model))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
actions = {strip.action.name: strip.action for track in rig.animation_data.nla_tracks for strip in track.strips if strip.action}
for track in rig.animation_data.nla_tracks: track.mute = True

def pose(clip, seconds):
    action = next(a for name, a in actions.items() if name == clip or name.endswith('_' + clip))
    rig.animation_data.action = action
    if action.slots: rig.animation_data.action_slot = action.slots[0]
    frame = 1 + seconds * bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
    bpy.context.view_layer.update()

pose('idle', 0)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and
          any(mod.type == 'ARMATURE' and mod.object == rig for mod in o.modifiers)]
evaluated_meshes = [o.evaluated_get(bpy.context.evaluated_depsgraph_get()) for o in meshes]
bounds = [o.matrix_world @ Vector(corner) for o in evaluated_meshes for corner in o.bound_box]
low = Vector([min(v[i] for v in bounds) for i in range(3)])
high = Vector([max(v[i] for v in bounds) for i in range(3)])
center = (low + high) / 2
height = high.z - low.z
scene = bpy.context.scene
mesh = bpy.data.meshes.new('inspection_floor')
mesh.from_pydata([(-20,-20,-.001),(20,-20,-.001),(20,20,-.001),(-20,20,-.001)], [], [(0,1,2,3)])
floor = bpy.data.objects.new('inspection_floor', mesh); scene.collection.objects.link(floor)
mat = bpy.data.materials.new('inspection_neutral'); mat.diffuse_color = (.17,.19,.21,1); mesh.materials.append(mat)
world = bpy.data.worlds.new('inspection_daylight'); world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.58,.66,.76,1)
world.node_tree.nodes['Background'].inputs[1].default_value = .5; scene.world = world
for name, position, power, size in [('key',(-3,-4,5),450,3),('fill',(3,-1,3),260,2),('rim',(1,3,4),380,2)]:
    data = bpy.data.lights.new(name, 'AREA'); data.energy = power; data.shape = 'DISK'; data.size = size
    light = bpy.data.objects.new(name, data); scene.collection.objects.link(light); light.location = position
    light.rotation_euler = (center-light.location).to_track_quat('-Z','Y').to_euler()
data = bpy.data.cameras.new('inspection_camera'); camera = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(camera); scene.camera = camera; data.type = 'ORTHO'
scene.render.engine = 'CYCLES'; scene.cycles.samples = 16; scene.cycles.use_denoising = True
scene.render.resolution_x = 900; scene.render.resolution_y = 1100; scene.render.resolution_percentage = 100
if sheet:
    scene.render.resolution_x=420;scene.render.resolution_y=500;scene.cycles.samples=8
scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'
scene.render.image_settings.file_format = 'PNG'
records = []
for view in views:
    clip = view.split(':')[0] if ':' in view else 'walk' if view.startswith('walk') else 'run' if view.startswith('run') else 'idle'
    seconds = float(view.split(':')[1]) if ':' in view else 1/3 if clip == 'walk' else 1/6 if clip == 'run' else 0
    pose(clip, seconds)
    target = center.copy()
    direction = Vector((.23,-1,.10))
    data.ortho_scale = height * 1.2
    if view == 'side': direction = Vector((1,-.2,.06))
    if view == 'rear': direction = Vector((.3,1,.10))
    if view == 'head':
        target = rig.matrix_world @ rig.pose.bones['head'].head
        target.z += .025; data.ortho_scale = .56
    if 'forearm' in view:
        target = rig.matrix_world @ rig.pose.bones['forearm_R'].head.lerp(rig.pose.bones['hand_R'].tail, .6)
        data.ortho_scale = .65
        direction = Vector((-.3,-1,.18))
        if view.endswith('_side'): direction = Vector((-1,-.15,.05))
    camera.location = target + direction.normalized() * height * 3
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
    safe_view=view.replace(':','_')
    output = WORK/'review'/f'{key}_lod{lod}_{safe_view}{suffix}.png'; scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    records.append({'view':view,'image':str(output.relative_to(WORK)),'sha256':digest(output),'clip':clip,'seconds':seconds})
if digest(model) != original_hash: raise RuntimeError('Export changed during review')
(WORK/'review'/f'{key}_lod{lod}_{"motion_sheet" if sheet else "review"}{suffix}.json').write_text(json.dumps({'modelSha256':original_hash,'bounds':{'min':list(low),'max':list(high)},'images':records,'status':'pending'},indent=2))
