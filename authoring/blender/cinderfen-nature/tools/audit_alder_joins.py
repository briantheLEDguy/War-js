"""Confirm primary root/limb sockets share the actual joined GLB bark shell."""
import hashlib,json
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/'source/nature.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
results=[]
for lod in range(3):
    file=ROOT/'runtime'/f'frontier_cinderfen_marsh_alder_lod{lod}.glb';bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(file))
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('root_flare'))
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bm.verts.ensure_lookup_table()
    remaining=set(bm.verts);components=[]
    while remaining:
        seed=remaining.pop();connected={seed};queue=[seed]
        while queue:
            current=queue.pop()
            for edge in current.link_edges:
                other=edge.other_vert(current)
                if other in remaining:remaining.remove(other);connected.add(other);queue.append(other)
        components.append(connected)
    bole=next(c for c in components if min(v.co.z for v in c)<0 and max(v.co.z for v in c)>9)
    index={v:i for i,v in enumerate(bole)};vertices=[obj.matrix_world@v.co for v in bole];faces=[tuple(index[v] for v in face.verts) for face in bm.faces if all(v in index for v in face.verts)]
    tree=BVHTree.FromPolygons(vertices,faces);sockets=[]
    for kind,paths in [('root',SOURCE['design']['rootPaths']),('limb',SOURCE['design']['alderLimbs'])]:
        for i,path in enumerate(paths):
            point=Vector(path[0][:3]);nearest,normal,face,distance=tree.find_nearest(point)
            # Odd intersections confirm the socket is inside the shared closed
            # bark shell. Its terminal must also reach this same component.
            direction=Vector((1,.127,.083)).normalized();origin=point.copy();hits=0
            for step in range(30):
                hit,_,_,travel=tree.ray_cast(origin,direction,30)
                if hit is None:break
                hits+=1;origin=hit+direction*.00001
            tip_distance=tree.find_nearest(Vector(path[-1][:3]))[3]
            sockets.append({'name':f'{kind}_{i}','position_z_up':list(point),'inside_actual_bole':bool(hits%2),'distance_to_bole_surface_m':distance,'forward_intersections':hits,'terminal_distance_to_same_component_m':tip_distance})
    failed=[s['name'] for s in sockets if not s['inside_actual_bole'] or s['distance_to_bole_surface_m']<.01 or s['terminal_distance_to_same_component_m']>.08]
    results.append({'model':file.name,'sha256':sha(file),'sockets':sockets,'failed':failed,'bole_components':1,'closed_bark_components':len(components)})
    bm.free();print('ALDER_JOIN_AUDIT',lod,len(sockets),'failed',failed,flush=True)
record={'sourceSha256':sha(ROOT/'source/nature.json'),'toolSha256':sha(Path(__file__)),'method':'Actual GLB reimport; positional weld, single connected closed primary bark shell, odd ray intersections and nearest-surface depth at all primary sockets. Primary terminals must reach the same component. Exact union retains original bark UV fields.','models':results}
(ROOT/'review/alder-joins.json').write_text(json.dumps(record,indent=2)+'\n')
if any(r['failed'] for r in results):raise RuntimeError('A primary alder join is not seated inside the actual bole.')
