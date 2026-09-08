"""Independent positional topology and local doorway audit of final exported GLBs."""
import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def doorway(objects,width,height,y):
    vertices=[];faces=[]
    for obj in objects:
        offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in polygon.vertices) for polygon in obj.data.polygons)
    tree=BVHTree.FromPolygons(vertices,faces);hits=[];samples=0
    for xi in range(21):
        x=-width/2+.04+xi*(width-.08)/20
        for zi in range(21):
            z=.3+zi*(height-.36)/20;samples+=1
            point,_,_,_=tree.ray_cast(Vector((x,y-.8,z)),Vector((0,1,0)),1.6)
            if point is not None:hits.append(list(point))
    return {'width':width,'height':height,'front_wall_y_z_up':y,'ray_samples':samples,'wall_depth_tested':1.6,'floor_tolerance':.3,'edge_tolerance':.04,'blocked_rays':hits}


if __name__=='__main__':
    report=[]
    for path in sorted((ROOT/'runtime').glob('*.glb')):
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path));objects=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']
        boundary=multiple=0;shared_segments=[]
        for obj in objects:
            bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
            boundary+=sum(len(edge.link_faces)==1 for edge in bm.edges);multiple+=sum(len(edge.link_faces)>2 for edge in bm.edges)
            shared_segments.extend({'vertices':[list(obj.matrix_world@v.co) for v in edge.verts],'incident_faces':len(edge.link_faces)} for edge in bm.edges if len(edge.link_faces)>2);bm.free()
        item={'model':path.name,'sha256':sha(path),'boundary_edges_after_positional_weld':boundary,'multi_face_edges_after_positional_weld':multiple,'coincident_join_segments':shared_segments,'weld_tolerance_m':.000001,'audit_tool_sha256':sha(__file__)}
        if 'farmhouse' in path.name:item['doorway']=doorway(objects,1.6,2.5,-5)
        if 'workshop' in path.name:item['doorway']=doorway(objects,2.6,3,-4)
        if 'supply_post' in path.name:item['doorway']=doorway(objects,5.6,3.1,-2.5)
        report.append(item);print('AUDITED '+path.name,flush=True)
    (ROOT/'review/geometry_audit.json').write_text(json.dumps({'models':report,'method':'Per exported rigid mesh: weld glTF material/UV/normal split vertices at 1 micrometre and count incident faces. This is a geometric seam audit, not a boolean solid-union test.'},indent=2)+'\n')
