"""Measure facade attachment planes from the frozen gatehouse export."""
import hashlib
import json
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'runtime/frontier_cinderfen_gatehouse_lod0.glb'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path))
vertices=[];faces=[]
for obj in [item for item in bpy.context.scene.objects if item.type=='MESH']:
    offset=len(vertices);vertices.extend(obj.matrix_world@vertex.co for vertex in obj.data.vertices)
    faces.extend([offset+index for index in face.vertices] for face in obj.data.polygons)
tree=BVHTree.FromPolygons(vertices,faces);sockets=[]
for x in (-6.7,6.7):
    hit,normal,_,_=tree.ray_cast(Vector((x,-7,3.8)),Vector((0,1,0)),3)
    if hit is None:raise RuntimeError('Missing measured facade at banner socket.')
    sockets.append({'id':'left_facade' if x<0 else 'right_facade','surface_runtime':[hit.x,hit.z,-hit.y],
      'attachment_runtime':[hit.x,hit.z,-hit.y+.04],'outward_runtime':[0,0,1],
      'usage':'Hanging realm cloth attachment, not a grounded pole origin. Keep root yawPI places this on the southern facade; keep the cloth clear of the central six-metre passage.'})
record={'model':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'sockets':sockets,'keep_centres_runtime':{'outer':[0,0,-24],'inner':[0,0,-7.5]},'keep_rotation_y':3.141592653589793}
(ROOT/'review/banner-sockets.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(sockets))
