"""Reimport the real corner, two curtains and stair; audit their joined route."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('review_export_tools',ROOT/'tools/review_exports.py');review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
bpy.ops.wm.read_factory_settings(use_empty=True)
theta=math.pi/4;socket=(-3.5,-3.5)
stair=(socket[0]-1.3*math.cos(theta)-4.5*math.sin(theta),socket[1]+1.3*math.sin(theta)-4.5*math.cos(theta))
entries=[(ROOT/'runtime/frontier_cinderfen_corner_access_lod0.glb',0,0,0),
 (ROOT.parent/'runtime/frontier_cinderfen_curtain_walk_lod0.glb',-6.4,0,0),
 (ROOT.parent/'runtime/frontier_cinderfen_curtain_walk_lod0.glb',0,-6.4,math.pi/2),
 (ROOT.parent/'runtime/frontier_cinderfen_wall_stair_lod0.glb',*stair,theta)]
objects=[];inputs=[]
for path,x,z,yaw in entries:
    old=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(path));created=[o for o in bpy.context.scene.objects if o not in old]
    transform=Matrix.Translation((x,-z,0))@Matrix.Rotation(yaw,4,'Z')
    for obj in created:
        if obj.type=='MESH':obj.matrix_world=transform@obj.matrix_world;objects.append(obj)
    inputs.append({'model':str(path.relative_to(ROOT.parent)).replace('\\','/'),'sha256':sha(path),'x':x,'z':z,'rotY':yaw})
bpy.context.view_layer.update()
vertices=[];faces=[]
for obj in objects:
    offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend([offset+i for i in p.vertices] for p in obj.data.polygons)
tree=BVHTree.FromPolygons(vertices,faces)
hits=[];support=[]
# Three actual paths through the shared landing, sampled with a 45cm body radius.
routes=[((-5,0),(0,0)),((0,0),(0,-5)),(socket,(0,0))]
for a,b in routes:
    dx,dz=b[0]-a[0],b[1]-a[1];distance=math.hypot(dx,dz);nx,nz=-dz/distance,dx/distance
    for i in range(math.ceil(distance/.15)+1):
        t=i/math.ceil(distance/.15);x=a[0]+dx*t;z=a[1]+dz*t
        contacts=[]
        for ox,oz in ((0,0),(.035,0),(-.035,0),(0,.035),(0,-.035),(.035,.035),(.035,-.035),(-.035,.035),(-.035,-.035)):
            point,_,_,_=tree.ray_cast(Vector((x+ox,-z-oz,6.36)),Vector((0,0,-1)),.15)
            if point is not None:contacts.append(point.z)
        support.append({'x':x,'z':z,'height':min(contacts,key=lambda y:abs(y-6.3)) if contacts else None})
        for side in (-.45,0,.45):
            origin=Vector((x+nx*side,-z-nz*side,6.44));point,_,_,_=tree.ray_cast(origin,Vector((0,0,1)),1.9)
            if point is not None:hits.append(list(point))
stair_contract=json.loads((ROOT.parent/'navigation-contract.json').read_text())['assets']
stair_contract=next(item for item in stair_contract if item['assetId']=='frontier_cinderfen_wall_stair')
stair_hits=[]
for step in stair_contract['walkableSurfaces']:
    for offset in (-.45,0,.45):
        lx=step['x']+offset;lz=step['z'];x=stair[0]+lx*math.cos(theta)+lz*math.sin(theta);z=stair[1]-lx*math.sin(theta)+lz*math.cos(theta)
        origin=Vector((x,-z,step['fromY']+.16));point,_,_,_=tree.ray_cast(origin,Vector((0,0,1)),1.8)
        if point is not None:stair_hits.append({'step':step['id'],'hit':list(point)})
gx=stair[0]-1.3*math.cos(theta)+4.35*math.sin(theta);gz=stair[1]+1.3*math.sin(theta)+4.35*math.cos(theta)
for offset in (-.45,0,.45):
    point,_,_,_=tree.ray_cast(Vector((gx+offset*math.cos(theta),-gz+offset*math.sin(theta),.25)),Vector((0,0,1)),1.8)
    if point is not None:stair_hits.append({'step':'ground_entry','hit':list(point)})
# Rotate the whole measured assembly for a clear courtyard view; relative fits remain exact.
for obj in objects:obj.matrix_world=Matrix.Rotation(math.pi,4,'Z')@obj.matrix_world
bpy.context.view_layer.update();preview=ROOT/'review/corner_stair_assembly.png';camera=review.render(objects,preview)
record={'inputs':inputs,'tool_sha256':sha(__file__),'preview':preview.name,'preview_sha256':sha(preview),'camera':camera,'clearance_hits':hits,'stair_route_clearance_hits':stair_hits,'support_samples':support,'stair_position_runtime':[*stair],'stair_top_socket_runtime':[*socket],'ground_entry_runtime':[gx,0,gz],'method':'Actual exported meshes. Three joined routes, 90cm body corridor, 1.9m head rays, support height rays, and every stair tread plus ground entry; physical stair landing joins the diagonal open edge.'}
(ROOT/'review/assembly.json').write_text(json.dumps(record,indent=2)+'\n')
print(f'Assembly clearance hits: {len(hits)}, stair hits: {len(stair_hits)}, support misses: {sum(p["height"] is None for p in support)}')
