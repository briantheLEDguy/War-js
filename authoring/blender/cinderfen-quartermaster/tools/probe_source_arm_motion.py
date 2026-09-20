"""Fast source diagnostics only; all final imported clip samples remain required."""
import sys,json,bpy,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
W=Path(__file__).resolve().parents[1];sys.path.insert(0,str(W/'tools'))
from quartermaster_arm_motion import fit_arm_motion
from apron_clearance import _surface,_skin
K='frontier_cinderfen_greenskin_quartermaster'
bpy.ops.wm.open_mainfile(filepath=str(W/'sources'/f'{K}.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
for track in rig.animation_data.nla_tracks:track.mute=True
for obj in bpy.context.scene.objects:
    for mod in obj.modifiers:
        if mod.type=='ARMATURE':mod.show_viewport=False
fit_arm_motion(rig,include_death=False)
outer=[_surface(o) for o in bpy.context.scene.objects if o.type=='MESH' and any(m and m.name=='quartermaster_supply_waistcoat' for m in o.data.materials)]
inner=[_surface(o) for o in bpy.context.scene.objects if o.type=='MESH' and any(m and any(t in m.name for t in ('_woven_linen','_wool','body_mire_brutish_v1_m.body')) for m in o.data.materials)]
def combined(surfaces):
    points=[];faces=[]
    for surface in surfaces:
        base=len(points);points.extend(_skin(surface,rig));faces.extend(tuple(base+i for i in f) for f in surface[1])
    return points,faces
_,faces=combined(outer);edges={tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1])}
records=[]
for clip,duration in [('walk',30),('run',20),('attack_melee',30),('attack_ranged',40),('cast',60)]:
    action=bpy.data.actions[clip];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    counts=[]
    for frame in np.linspace(0,duration,13):
        bpy.context.scene.frame_set(int(frame),subframe=float(frame%1));bpy.context.view_layer.update()
        points,_=combined(outer);target,target_faces=combined(inner);tree=BVHTree.FromPolygons(target,target_faces,all_triangles=True);hits=[]
        for a,b in edges:
            start=Vector(points[a]);delta=Vector(points[b])-start
            if delta.length<.001:continue
            hit=tree.ray_cast(start+delta.normalized()*.00025,delta.normalized(),delta.length-.0005)[0]
            if hit is not None:hits.append(list(hit))
        counts.append({'frame':float(frame),'count':len(hits),'first':hits[:3]})
    records.append({'clip':clip,'samples':counts});print(clip,max(s['count'] for s in counts),flush=True)
(W/'review/source-arm-motion-probe.json').write_text(json.dumps({'diagnosticOnly':True,'clips':records},separators=(',',':')))
