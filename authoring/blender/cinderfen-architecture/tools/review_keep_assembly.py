"""Reimport every placed keep module and audit the actual connected enclosures."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('actual_export_review',ROOT/'tools/review_exports.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
source_path=ROOT/'review/keep-assembly-source.json';source=json.loads(source_path.read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
library={};objects=[];inputs=[]
for entry in source['props']:
    key=entry['assetKey'];folder=ROOT/'junction' if key.endswith('corner_access') else ROOT
    path=folder/'runtime'/f'{key}_lod1.glb'
    if key not in library:
        old=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(path));created=[o for o in bpy.context.scene.objects if o not in old]
        bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
        library[key]=[(o.data,o.matrix_world.copy()) for o in created if o.type=='MESH']
        for obj in created:bpy.data.objects.remove(obj,do_unlink=True)
        inputs.append({'model':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':sha(path)})
    scale=entry.get('scale',1);sx=scale*entry.get('scaleX',1);sy=scale*entry.get('scaleY',1);sz=scale*entry.get('scaleZ',1)
    transform=Matrix.Translation((entry['x'],-entry['z'],entry.get('y',0)))@Matrix.Rotation(entry.get('rotY',0),4,'Z')@Matrix.Diagonal(Vector((sx,sz,sy,1)))
    for index,(data,local) in enumerate(library[key]):
        obj=bpy.data.objects.new(entry['id']+f'.{index}',data);bpy.context.scene.collection.objects.link(obj)
        obj.matrix_world=transform@local;objects.append(obj)
bpy.context.view_layer.update()
vertices=[];faces=[]
for obj in objects:
    offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
    faces.extend([offset+i for i in polygon.vertices] for polygon in obj.data.polygons)
tree=BVHTree.FromPolygons(vertices,faces)
routes=[]
def audit_route(name,points,support=True,head_offsets=None):
    hits=[];missing=[];samples=0
    for a,b in zip(points,points[1:]):
        distance=math.dist(a,b);count=max(1,math.ceil(distance/.18))
        for i in range(count+1):
            t=i/count;x,y,z=[a[axis]+(b[axis]-a[axis])*t for axis in range(3)];samples+=1
            if support:
                contacts=[]
                for dx,dz in ((0,0),(.035,0),(-.035,0),(0,.035),(0,-.035),(.035,.035),(.035,-.035),(-.035,.035),(-.035,-.035)):
                    p,_,_,_=tree.ray_cast(Vector((x+dx,-z-dz,y+.07)),Vector((0,0,-1)),.17)
                    if p is not None and abs(p.z-y)<=.03:contacts.append(p.z)
                if not contacts:missing.append([x,y,z])
            for dx,dz in head_offsets or ((0,0),(.4,0),(-.4,0),(0,.4),(0,-.4)):
                p,_,_,_=tree.ray_cast(Vector((x+dx,-z-dz,y+.15)),Vector((0,0,1)),1.65)
                if p is not None:hits.append([x,y,z,*p])
    routes.append({'id':name,'samples':samples,'head_hits':hits,'missing_support':missing})
for stage,half,front,rear in [('outer',32.4,-24,52.8),('inner',24.4,-7.5,21.3)]:
    audit_route(stage+'_perimeter',[[-half,6.3,front],[half,6.3,front],[half,6.3,rear],[-half,6.3,rear],[-half,6.3,front]])
audit_route('oil_platform',[[0,6.3,-24],[1.8,6.3,-24]])
audit_route('delivery_to_outer_passage',[[0,0,-78],[0,0,-33]],False)
audit_route('outer_to_inner_passage',[[0,0,-27],[0,0,-16.5]],False)
audit_route('inner_passage_to_commander',[[0,0,-10.5],[0,0,4]],False)
audit_route('delivery_to_quartermaster',[[0,0,-78],[0,0,-60],[-13,0,-60]],False)
stair_contract=json.loads((ROOT/'source/architecture.json').read_text())['assets']['frontier_cinderfen_wall_stair']['contract']
corner_contract=json.loads((ROOT/'junction/source/architecture.json').read_text())['assets']['frontier_cinderfen_corner_access']['contract']
for entry in source['props']:
    yaw=entry.get('rotY',0)
    def point(x,y,z):return [entry['x']+x*math.cos(yaw)+z*math.sin(yaw),y,entry['z']-x*math.sin(yaw)+z*math.cos(yaw)]
    if entry['assetKey'].endswith('wall_stair'):
        # Inspect head clearance across each tread, perpendicular to ascent.
        # Longitudinal offsets have a different foot height on adjacent steps;
        # finite-footprint stepping is tested separately by shared navigation.
        lateral=[(distance*math.cos(yaw),-distance*math.sin(yaw)) for distance in (-.4,0,.4)]
        for step in stair_contract['walkableSurfaces']:
            p=point(step['x'],step['fromY'],step['z']);audit_route(entry['id']+'/'+step['id'],[p,p],head_offsets=lateral)
        p=point(-1.3,0,4.35);audit_route(entry['id']+'/ground_entry',[p,p],False,head_offsets=lateral)
    if entry['assetKey'].endswith('corner_access'):
        socket=corner_contract['stair_socket_runtime'];audit_route(entry['id']+'/gangway',[point(*socket),point(0,6.3,0)])
preview=ROOT/'review/keep_full_assembly.png';camera=review.render(objects,preview,frame=155)
# The keep's southern entrance faces world -Z; rotate only its presentation
# after all geometry measurements so the front view shows the real gate mouths.
for obj in objects:obj.matrix_world=Matrix.Rotation(math.pi,4,'Z')@obj.matrix_world
bpy.context.view_layer.update()
front=ROOT/'review/keep_full_front.png';front_camera=review.render(objects,front,front=True,frame=92)
front_camera['presentation_rotation_y_runtime']=math.pi
record={'source_sha256':sha(source_path),'placement_source_sha256':source['placementSourceSha256'],'tool_sha256':sha(__file__),
 'models':inputs,'lod':1,'instances':len(source['props']),'triangles':len(faces),'routes':routes,
 'head_hits':sum(len(route['head_hits']) for route in routes),'missing_support':sum(len(route['missing_support']) for route in routes),
 'previews':{preview.name:sha(preview),front.name:sha(front)},'cameras':[camera,front_camera],
 'method':'Actual complete LOD1 GLBs, physical perimeter and gangway support rays, 80cm body corridor with 1.8m head clearance, every stair tread sampled laterally across its own level and preserved ground approach. Finite-footprint stepping and closed owner portals are separately tested with the shared movement implementation.'}
(ROOT/'review/keep-assembly.json').write_text(json.dumps(record,indent=2)+'\n')
print(f'Complete assembly: {len(objects)} meshes, {record["head_hits"]} head hits, {record["missing_support"]} missing supports',flush=True)
