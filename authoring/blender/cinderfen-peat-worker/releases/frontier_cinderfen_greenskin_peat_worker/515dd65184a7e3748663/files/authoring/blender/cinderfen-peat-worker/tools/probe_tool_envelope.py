"""Find outward scabbard curvature against the actual final running stride."""
import bpy,sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
WORK=Path(__file__).resolve().parents[1];sys.path.insert(0,str(WORK/'tools'))
from apron_clearance import _surface,_skin
bpy.ops.wm.open_mainfile(filepath=str(WORK/'sources/frontier_cinderfen_greenskin_peat_worker.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
cloth=[_surface(o) for o in bpy.context.scene.objects if o.type=='MESH' and ('continuous_tailored_surface' in o.name or 'folded_work_apron' in o.name)]
sheath=_surface(bpy.data.objects['peat_knife_closed_wet_leather_sheath'])
from surface_bindings import ClothSurface
support=ClothSurface(bpy.data.objects['work_belt']);point,n,_,_=support.tree.find_nearest(Vector((-.24,.13,1.1322)))
out=Vector((n.x,n.y,0)).normalized()
if out.dot(Vector((point.x,point.y,0)))<0:out=-out
for obj in bpy.context.scene.objects:
    for modifier in obj.modifiers:
        if modifier.type=='ARMATURE':modifier.show_viewport=False
action=bpy.data.actions['run'];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
edges=sorted({tuple(sorted((a,b))) for f in sheath[1] for a,b in zip(f,f[1:]+f[:1])})
records=[]
for extra in [0,.02,.035,.05,.065]:
    adjusted=sheath[0].copy();amount=np.clip((1.1322-adjusted[:,2])/.28,0,2)*extra
    adjusted[:,:3]+=amount[:,None]*np.array(out)[None,:]
    fitted=(adjusted,*sheath[1:]);maximum=0
    for half_frame in range(41):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        frame=half_frame/2;bpy.context.scene.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update()
        vertices=[];faces=[];offset=0
        for surface in cloth:
            points=_skin(surface,rig);vertices.extend(points);faces.extend(tuple(i+offset for i in f) for f in surface[1]);offset+=len(points)
        tree=BVHTree.FromPolygons(vertices,faces,all_triangles=True);points=_skin(fitted,rig);crossings=0
        for a,b in edges:
            start=Vector(points[a]);delta=Vector(points[b])-start
            if delta.length<.001:continue
            direction=delta.normalized()
            if tree.ray_cast(start+direction*.00025,direction,delta.length-.0005)[0] is not None:crossings+=1
        maximum=max(maximum,crossings)
    records.append({'extraTipOutset':extra,'maximumRunCrossings':maximum});print(records[-1],flush=True)
(WORK/'review/tool-envelope-probe.json').write_text(json.dumps(records,indent=2))
