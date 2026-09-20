"""Read the retained authored yoke ends against their intended jerkin seams."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from surface_bindings import ClothSurface
WORK=Path(__file__).resolve().parents[1];KEY='frontier_sunmeadow_high_elf_scout'
bpy.ops.wm.open_mainfile(filepath=str(WORK/'sources'/f'{KEY}.authored.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
if rig.animation_data:
    rig.animation_data.action=None
    for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update();host=ClothSurface(bpy.data.objects['scout_fitted_jerkin']);records=[]
shirt=bpy.data.objects['shirt_continuous_tailored_surface']
for modifier in shirt.modifiers:
    if modifier.type=='SOLIDIFY':modifier.show_viewport=False
bpy.context.view_layer.update();support=ClothSurface(shirt)
shape=lambda p:Vector((p[0]*.94,p[1]*.97,p[2]*1.055))
def proposal(side):
    stations=[shape(p) for p in [(side*.12,-.145,1.400),(side*.17,-.12,1.49),(side*.18,-.075,1.534),
                                (side*.18,-.015,1.55),(side*.17,.04,1.515),(side*.108,.11,1.350)]]
    path=[]
    for a,b in zip(stations,stations[1:]):path.extend(a.lerp(b,i/16) for i in range(16))
    path.append(stations[-1]);points=[]
    def outer(p):
        c=shape((0,-.015,1.43));d=Vector((0,c.y-p.y,c.z-p.z)).normalized()
        return support.tree.ray_cast(p-d*2,d)
    for i,p in enumerate(path):
        tangent=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
        hit,n,triangle,_=outer(p);across=tangent.cross(n).normalized()
        for edge in (-1,1):
            hit,n,triangle,_=outer(p+across*.033*.5*edge);points.append(hit+n*.016)
    return points
for obj in bpy.data.objects:
    if not obj.name.startswith('scout_tapered_shoulder_yoke'):continue
    points=proposal(-1 if obj.name=='scout_tapered_shoulder_yoke' else 1);rows=len(points)//2;ends=[]
    for row in (0,rows-1):
        center=(points[row*2]+points[row*2+1])*.5
        hit,n,triangle,distance=host.tree.find_nearest(center);delta=hit+n*.001-center
        ends.append({'row':row,'center':list(center),'support':list(hit),'distance':distance,'delta':list(delta)})
        corrections=[]
        for i in range(row*2,row*2+2):
            edge_hit,edge_normal,_,_=host.tree.find_nearest(points[i]);corrections.append(edge_hit+edge_normal*.001-points[i])
        for r in range(max(0,row-10),min(rows,row+11)):
            t=max(0,1-abs(r-row)/10);t=t*t*(3-2*t)
            for i in range(r*2,r*2+2):points[i]+=corrections[i%2]*t
    centers=[(points[i]+points[i+1])*.5 for i in range(0,len(points),2)]
    deltas=[b-a for a,b in zip(centers,centers[1:])]
    records.append({'name':obj.name,'ends':ends,'proposedMaximumRowStep':max(v.length for v in deltas),
                    'proposedMaximumTurnDegrees':max(math.degrees(a.angle(b)) for a,b in zip(deltas,deltas[1:])),
                    'endEdgeGaps':[host.tree.find_nearest(points[i])[3] for i in (0,1,len(points)-2,len(points)-1)]})
out=WORK/'review/yoke-endpoint-proposal-k.json';out.write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records))
