"""Check the actual deformed equipped surfaces against the entire rigid hammer.

Run in Blender after build-combat-animations.py. Only measured hand contacts
are exempt; torso, clothing, legs, head and forearms are checked at 120 Hz.
"""
import json
import hashlib
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/combat-animation/prelate'
(OUT/'clearance.json').unlink(missing_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'choreography.blend'))
rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE')
rig.animation_data.use_nla=False
weapon=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH' and 'head_center_local' in obj)
meshes=[obj for obj in bpy.context.scene.objects if obj.type=='MESH' and obj!=weapon]


def geometry(obj,depsgraph):
    evaluated=obj.evaluated_get(depsgraph)
    mesh=evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        points=[evaluated.matrix_world @ v.co for v in mesh.vertices]
        triangles=[tuple(t.vertices) for t in mesh.loop_triangles]
        hand_groups={group.index for group in obj.vertex_groups if any(part in group.name.lower() for part in ('hand','finger','thumb','index','middle','ring','pinky'))}
        grip_vertices={v.index for v in mesh.vertices if sum(g.weight for g in v.groups if g.group in hand_groups)>.5}
    finally:
        evaluated.to_mesh_clear()
    return points,triangles,grip_vertices


records=[]
for action in sorted(bpy.data.actions,key=lambda a:a.name):
    if not action.name.startswith('prelate_'): continue
    rig.animation_data.action=action
    rig.animation_data.action_slot=action.slots[0]
    first,last=action.frame_range
    collisions=[]
    min_height=float('inf')
    for frame in range(round(first),round(last)+1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        graph=bpy.context.evaluated_depsgraph_get()
        wp,wt,_=geometry(weapon,graph)
        min_height=min(min_height,min(p.z for p in wp))
        weapon_bvh=BVHTree.FromPolygons(wp,wt,all_triangles=True)
        weapon_min=[min(p[i] for p in wp) for i in range(3)]
        weapon_max=[max(p[i] for p in wp) for i in range(3)]
        hands=[(rig.evaluated_get(graph).pose.bones['hand_'+side].matrix.translation) for side in ('L','R')]
        for obj in meshes:
            evaluated=obj.evaluated_get(graph)
            corners=[evaluated.matrix_world @ Vector(p) for p in evaluated.bound_box]
            if any(max(p[i] for p in corners)<weapon_min[i] or min(p[i] for p in corners)>weapon_max[i] for i in range(3)):
                continue
            points,triangles,grip_vertices=geometry(obj,graph)
            hits=weapon_bvh.overlap(BVHTree.FromPolygons(points,triangles,all_triangles=True))
            blocked=[]
            for weapon_index,body_index in hits:
                triangle=[points[i] for i in triangles[body_index]]
                # Contact is only allowed at an actual hand, never by excluding
                # an entire glove/body mesh that could hide a forearm collision.
                if not (all(i in grip_vertices for i in triangles[body_index])
                        # The equipped glove's gripping knuckles reach 12.35 cm
                        # from the wrist; retain a 13 cm cap plus skin ownership.
                        and any(all((point-hand).length < .13 for point in triangle) for hand in hands)):
                    blocked.append((weapon_index,body_index))
            if blocked:
                collisions.append({'frame':frame,'seconds':frame/120,'slot':obj.get('combat_slot','unknown'),'triangles':len(blocked)})
        if frame%30==0: print('CLEARANCE',action.name,frame,flush=True)
    records.append({'clip':action.name,'sampleCount':round(last-first)+1,'collisions':collisions,'minimumWeaponHeightMeters':min_height})
report={'fps':120,'fbxSha256':hashlib.sha256((OUT/'choreography.fbx').read_bytes()).hexdigest(),
        'scope':'Entire hammer versus evaluated equipped surfaces and ground; grip exceptions require hand/finger skin weights AND proximity within 13 cm of a wrist',
        'clips':records,'passed':len(records)==3 and not any(r['collisions'] or r['minimumWeaponHeightMeters']<0 for r in records),'visualApproval':False}
(OUT/'clearance.json').write_text(json.dumps(report,indent=2)+'\n')
if not report['passed']: raise RuntimeError('Hammer intersects equipped body or ground, or clips are missing; see clearance.json')
print('HAMMER_CLEARANCE_PASSED',flush=True)
