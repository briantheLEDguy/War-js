"""Render the delivered GLBs after a clean import, including actual idle poses."""
import json
import hashlib
import sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_guards import studio, camera, VARIANTS

bpy.ops.wm.read_factory_settings(use_empty=True)
studio()
groups=[]
variant_actions={}
grip_audit=[]
for i,variant in enumerate(VARIANTS):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'runtime'/f'chr_aegis_city_guard_{variant}.glb'))
    objects=set(bpy.data.objects)-before
    rig=next(o for o in objects if o.type=='ARMATURE')
    rig.data.pose_position='POSE'
    actions={strip.action for track in rig.animation_data.nla_tracks for strip in track.strips if strip.action}
    if rig.animation_data.action: actions.add(rig.animation_data.action)
    if len(actions)!=9: raise ValueError(f"Expected 9 imported clips for {variant}, got {len(actions)}")
    variant_actions[variant]=actions
    idle=next((a for a in actions if a.name=='idle' or a.name.startswith('idle.')),None)
    if idle:
        rig.animation_data_create(); rig.animation_data.action=idle
        if hasattr(idle,'slots') and idle.slots: rig.animation_data.action_slot=idle.slots[0]
        for track in rig.animation_data.nla_tracks: track.mute=True
    mesh=next(o for o in objects if o.type=='MESH' and o.get('guard_variant')==variant)
    anchors=json.loads(mesh.get('weapon_grip_bind_points','{}'))
    if set(anchors)!={'L','R'}: raise ValueError(f'Missing exported anchors for {variant}')
    local=Vector(mesh.get('hand_grip_local',(0,.075,-.01)))
    if variant!='captain':
        for action in actions:
            rig.animation_data.action=action; rig.animation_data.action_slot=action.slots[0]
            start,end=action.frame_range
            for step in range(5):
                frame=start+(end-start)*step/4
                bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame))
                for side,anchor in anchors.items():
                    hand=rig.pose.bones['hand_'+side].matrix @ local
                    driver='hand_'+anchor['driver']
                    contact=(rig.pose.bones[driver].matrix @ rig.data.bones[driver].matrix_local.inverted()) @ Vector(anchor['point'])
                    gap=(hand-contact).length
                    grip_audit.append({'variant':variant,'clip':action.name,'frame':round(frame,3),'hand':side,'gap_m':round(gap,6)})
                    if gap>.015: raise ValueError(f'Exported grip lost contact: {variant}/{action.name}/{side}: {gap}')
        rig.animation_data.action=idle; rig.animation_data.action_slot=idle.slots[0]
    # Imported GLB transforms use Blender Z-up; translation is applied at roots.
    for o in objects:
        if o.parent not in objects: o.location.x+=i*1.35
    groups.append(objects)
bpy.context.scene.frame_set(1)
scene=bpy.context.scene
scene.render.resolution_x=1800; scene.render.resolution_y=900
scene.camera=camera('Delivered lineup',(3.6,-8,2.8),(2.02,0,1.1),5.8)
scene.render.filepath=str(ROOT/'review/exported_idle_lineup.png')
bpy.ops.render.render(write_still=True)
for index,objects in enumerate(groups):
    if index:
        for o in objects: o.hide_render=True
scene.render.resolution_x=800; scene.render.resolution_y=900
for view,position in [('front',(0,-5,1.4)),('side',(5,0,1.4)),('back',(0,5,1.4))]:
    scene.camera=camera(view,position,(0,0,1.12),2.5)
    scene.render.filepath=str(ROOT/'review'/f'exported_standard_{view}.png')
    bpy.ops.render.render(write_still=True)
for i,variant in [(1,'halberd'),(2,'crossbow')]:
    for index,objects in enumerate(groups):
        for o in objects: o.hide_render=index!=i
    x=i*1.35
    for view,position in [('front',(x,-5,1.5)),('side',(x+4,-.3,1.5))]:
        scene.camera=camera(variant+'_'+view,position,(x,-.20,1.3),1.15)
        scene.render.filepath=str(ROOT/'review'/f'{variant}_grip_{view}.png')
        bpy.ops.render.render(write_still=True)
    rig=next(o for o in groups[i] if o.type=='ARMATURE')
    walk=next(a for a in variant_actions[variant] if a.name=='walk' or a.name.startswith('walk.'))
    rig.animation_data.action=walk; rig.animation_data.action_slot=walk.slots[0]
    scene.frame_set(10)
    scene.camera=camera(variant+'_walk',(x+2,-5,2.1),(x,0,1.15),2.5)
    scene.render.filepath=str(ROOT/'review'/f'{variant}_walk.png')
    bpy.ops.render.render(write_still=True)
(ROOT/'review/exported-grip-audit.json').write_text(json.dumps({'models':{v:hashlib.sha256((ROOT/'runtime'/f'chr_aegis_city_guard_{v}.glb').read_bytes()).hexdigest() for v in VARIANTS},'max_gap_m':max((r['gap_m'] for r in grip_audit),default=0),'samples':grip_audit},indent=2)+'\n')
for objects in groups:
    for o in objects: o.hide_render=False
scene.camera=bpy.data.objects['Delivered lineup']; scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'aegis_city_guards_export_review.blend'),compress=True)
