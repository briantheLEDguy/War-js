"""Independent actual-export topology, door, defense-route and tread audit."""
import hashlib
import json
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/'source/architecture.json').read_text())

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_for(objects):
    vertices=[];faces=[]
    for obj in objects:
        offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in polygon.vertices) for polygon in obj.data.polygons)
    return BVHTree.FromPolygons(vertices,faces)


def doorway(tree,contract):
    width,height=contract['front_door_clearance'];floor=contract['floor_height'];y=-contract['front_door_runtime']['z'];hits=[];samples=0
    for xi in range(31):
        x=-width/2+.04+xi*(width-.08)/30
        for zi in range(26):
            z=floor+.12+zi*(height-.16)/25;samples+=1
            point,_,_,_=tree.ray_cast(Vector((x,y-.6,z)),Vector((0,1,0)),1.2)
            if point is not None:hits.append(list(point))
    return {'width':width,'height':height,'floor_height':floor,'ray_samples':samples,'wall_depth_tested':1.2,'floor_tolerance':.12,'edge_tolerance':.04,'blocked_rays':hits}


def crosswalk(tree):
    hits=[];samples=0
    for yi in range(17):
        y=-.76+yi*.095
        for zi in range(21):
            z=6.42+zi*.105;samples+=1
            point,_,_,_=tree.ray_cast(Vector((-14.02,y,z)),Vector((1,0,0)),28.04)
            if point is not None:hits.append(list(point))
    return {'clear_width':1.52,'clear_height':2.22,'floor_height':6.3,'length':28.04,'ray_samples':samples,'blocked_rays':hits}


def supports(tree,contract):
    records=[]
    for surface in contract.get('walkableSurfaces',[]):
        samples=[]
        # Offset fractions avoid deliberate millimetre drainage gaps between
        # the separately closed deck boards, rather than masking floor errors.
        for u in (.19,.43,.71):
            for v in (.23,.47,.79):
                dx=(u-.5)*surface['width'];dz=(v-.5)*surface['depth'];angle=surface.get('rotY',0)
                x=surface.get('x',0)+dx*math.cos(angle)+dz*math.sin(angle);z=surface.get('z',0)-dx*math.sin(angle)+dz*math.cos(angle)
                a=surface.get('fromY',0);b=surface.get('toY',a);height=a+(b-a)*(u if surface.get('axis')=='x' else v)
                contacts=[]
                for dx,dz in [(0,0),(-.035,0),(.035,0),(0,-.035),(0,.035)]:
                    change=(b-a)*(dx/surface['width'] if surface.get('axis')=='x' else dz/surface['depth'])
                    expected=height+change;point,_,_,_=tree.ray_cast(Vector((x+dx,-z-dz,expected+.06)),Vector((0,0,-1)),.16)
                    if point is not None:contacts.append({'height':point.z,'error':point.z-expected,'foot_contact_offset':[dx,dz]})
                contact=min(contacts,key=lambda p:abs(p['error'])) if contacts else {'height':None,'error':None,'foot_contact_offset':None}
                samples.append({'x':x,'z':z,'expected_height':height,**contact})
        records.append({'surface':surface['id'],'samples':samples,'missing':sum(s['height'] is None for s in samples),'max_error':max((abs(s['error']) for s in samples if s['error'] is not None),default=0)})
    return records


if __name__=='__main__':
    report=[]
    for path in sorted((ROOT/'runtime').glob('*.glb')):
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path));objects=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']
        boundary=multiple=0;shared_segments=[]
        for obj in objects:
            bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
            boundary+=sum(len(edge.link_faces)==1 for edge in bm.edges);multiple+=sum(len(edge.link_faces)>2 for edge in bm.edges)
            shared_segments.extend({'vertices':[list(obj.matrix_world@v.co) for v in edge.verts],'incident_faces':len(edge.link_faces)} for edge in bm.edges if len(edge.link_faces)>2);bm.free()
        asset_id=path.stem.rsplit('_lod',1)[0];contract=SOURCE['assets'][asset_id]['contract'];tree=tree_for(objects)
        item={'model':path.name,'sha256':sha(path),'boundary_edges_after_positional_weld':boundary,'multi_face_edges_after_positional_weld':multiple,'coincident_join_segments':shared_segments,'weld_tolerance_m':.000001,'audit_tool_sha256':sha(__file__),'walkable_surfaces':supports(tree,contract)}
        if 'front_door_clearance' in contract:item['doorway']=doorway(tree,contract)
        if 'gatehouse' in asset_id:item['defense_crosswalk']=crosswalk(tree)
        report.append(item);print('AUDITED '+path.name,flush=True)
    (ROOT/'review/geometry_audit.json').write_text(json.dumps({'source_sha256':sha(ROOT/'source/architecture.json'),'models':report,'method':'Actual GLB import; weld only coincident material/UV/normal split vertices at one micrometre. Every separately fitted construction shell must remain closed; coincident multi-face joins require exact measured exceptions. Support uses downward rays from six centimetres above the contracted height across a 3.5cm foot-contact radius, explicitly retaining the selected contact offset so small real drainage gaps are distinguished from missing floor geometry.'},indent=2)+'\n')
