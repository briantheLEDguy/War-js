"""Disposable V4-rig fit render; writes only review evidence, never a blend/GLB."""
import hashlib, json, math, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import build_proof as proof
import rig_character as rt

label=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'before'
out=ROOT/'review'/('greave_fit_'+label)
out.mkdir(exist_ok=True)
master=ROOT/'battle_prelate_game_master.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
master_hash=sha(master)
source=(ROOT/'source/legs.json').read_bytes()
record=json.loads(source)
parts={p['id']:p for p in record['parts']}
bpy.ops.wm.open_mainfile(filepath=str(master))
rig=bpy.data.objects['humanoid_game_v2']
assert rig.get('animation_correction_version')=='authored_hammer_grip_v4_book_clearance'
rt.verify_contract_rig(rig)
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks: track.mute=True
rig.data.pose_position='REST'
for bone in rig.pose.bones: bone.matrix_basis=Matrix.Identity(4)
bpy.context.scene.frame_set(1)
scene_data=json.loads((ROOT/'source/scene.json').read_text())
controls,_=proof.load_sources(snapshots={'legs.json':source},scene_data=dict(scene_data,comparison_pose={}))
fresh=bpy.data.collections.new('GREAVE_FIT_DIAGNOSTIC')
bpy.context.scene.collection.children.link(fresh)
leg_objects=[rt.evaluate_runtime_part(o,fresh,rig,0) for o in list(controls.objects) if o.type=='MESH' and rt.source_slot(o)=='legs']
controls.hide_render=controls.hide_viewport=True
for level in (0,1,2):
    coll=bpy.data.collections.get(f'RUNTIME_LOD{level}')
    if coll:
        coll.hide_render=coll.hide_viewport=level!=0
        for o in coll.objects:
            if o.get('slot')=='legs': o.hide_render=True
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_percentage=50
scene.view_layers[0].material_override=None
report={'master_sha256':master_hash,'leg_source_sha256':hashlib.sha256(source).hexdigest(),'animation_version':rig['animation_correction_version'],'images':[],'run_probe_rays':[]}
for clip in ('rest','run'):
    rig.animation_data.action=None
    for bone in rig.pose.bones: bone.matrix_basis=Matrix.Identity(4)
    if clip=='rest':
        rig.data.pose_position='REST'
        frame=1
    else:
        rig.data.pose_position='POSE'
        action=bpy.data.actions[clip]
        rig.animation_data.action=action
        rig.animation_data.action_slot=action.slots[0]
        a,b=action.frame_range
        frame=float(a+(b-a)*.5)
    camera_id='full_front' if clip=='rest' else 'full_three_quarter'
    camera_data=next(c for c in scene_data['cameras'] if c['id']==camera_id)
    scene.camera=bpy.data.objects['comparison.'+camera_id]
    scene.render.resolution_x,scene.render.resolution_y=camera_data['resolution']
    scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame))
    bpy.context.view_layer.update()
    if clip=='run':
        deps=bpy.context.evaluated_depsgraph_get()
        bvhs=[]
        for obj in leg_objects:
            ev=obj.evaluated_get(deps)
            mesh=ev.to_mesh()
            verts=[obj.matrix_world@v.co for v in mesh.vertices]
            bvh=BVHTree.FromPolygons(verts,[list(p.vertices) for p in mesh.polygons],all_triangles=False)
            bvhs.append((obj,bvh))
            ev.to_mesh_clear()
        camera=scene.camera
        corners=camera.data.view_frame(scene=scene)
        xmin,xmax=min(v.x for v in corners),max(v.x for v in corners)
        ymin,ymax=min(v.y for v in corners),max(v.y for v in corners)
        width=scene.render.resolution_x*.5
        height=scene.render.resolution_y*.5
        direction=camera.matrix_world.to_quaternion()@Vector((0,0,-1))
        for px,py in ((317,518),(320,524),(320,530),(321,536),(325,535),(310,530),(332,545)):
            origin=camera.matrix_world@Vector((xmin+(xmax-xmin)*px/width,ymax-(ymax-ymin)*py/height,0))
            hits=[]
            for obj,bvh in bvhs:
                hit,normal,index,distance=bvh.ray_cast(origin,direction,10)
                if hit is not None:
                    bone='shin_L' if hit.x>=0 else 'shin_R'
                    pose=rig.pose.bones[bone].matrix@rig.data.bones[bone].matrix_local.inverted()
                    rest=pose.inverted()@hit
                    part=parts[obj['source_part']]
                    sign=1 if rest.x>=0 else -1
                    near=sorted(part['vertices'],key=lambda v:(Vector((sign*v['co'][0],v['co'][1],v['co'][2]))-rest).length)[:4]
                    hits.append({'part':obj['source_part'],'distance':distance,'world':list(hit),'rest':list(rest),'nearest_authored_ids':[v['id'] for v in near]})
            report['run_probe_rays'].append({'pixel':[px,py],'hits':sorted(hits,key=lambda h:h['distance'])})
    path=out/(clip+'_50.png')
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    report['images'].append({'path':str(path.relative_to(ROOT)),'sha256':sha(path),'clip':clip,'frame':frame,'camera':camera_id})
report['master_unchanged']=master_hash==sha(master)
assert report['master_unchanged']
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('GREAVE_FIT_REPORT',out/'report.json',flush=True)
