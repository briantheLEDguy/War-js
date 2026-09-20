import bpy,sys,json
from pathlib import Path
from mathutils import Vector
WORK=Path(__file__).resolve().parents[1];sys.path.insert(0,str(WORK/'tools'))
from surface_bindings import ClothSurface
bpy.ops.wm.open_mainfile(filepath=str(WORK/'sources/frontier_cinderfen_greenskin_peat_worker.blend'))
surface=ClothSurface(bpy.data.objects['work_belt']);hit,n,_,d=surface.tree.find_nearest(Vector((-.24,.13,1.02*1.11)))
print(json.dumps({'hit':list(hit),'normal':list(n),'outwardDot':n.dot(Vector((hit.x,hit.y,0))),'distance':d,
 'toolBounds':{o.name:[[min(v.co[i] for v in o.data.vertices),max(v.co[i] for v in o.data.vertices)] for i in range(3)] for o in bpy.context.scene.objects if o.name in ['peat_knife_closed_wet_leather_sheath','peat_knife_shaped_ash_grip']}}))
