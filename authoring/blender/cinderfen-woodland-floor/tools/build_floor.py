"""Finish the original woodland-floor meshes and retain their editable cages."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
SOURCE_PATH=ROOT/'source/floor.json';SOURCE=json.loads(SOURCE_PATH.read_text());DESIGN=json.loads((ROOT/'source/design.json').read_text())
sys.path.insert(0,str(ROOT/'tools'))
from review_floor import render,audit

COLORS={'fallen_bark':(.053,.042,.030,1),'broken_heartwood':(.105,.060,.028,1),'pale_fracture':(.30,.215,.128,1),'fern_stem':(.051,.075,.022,1),'fern_leaf':(.071,.13,.036,1),'wood_sedge':(.080,.115,.040,1)}

def mesh(record,lod,collection,materials):
    data=bpy.data.meshes.new(record['name']+'.literal_source');data.from_pydata(record['vertices'],[],record['faces']);data.update()
    for name in record['materials']:data.materials.append(materials[name])
    grain=data.attributes.new(name='wood_grain',type='FLOAT_VECTOR',domain='POINT')
    for vertex,coordinate in zip(grain.data,record['grain_coordinates']):vertex.vector=coordinate
    data.uv_layers.new(name='source_uv')
    for polygon,coords,material in zip(data.polygons,record['corner_uv'],record['face_materials']):
        polygon.material_index=material;polygon.use_smooth=True
        for loop,coord in zip(polygon.loop_indices,coords):data.uv_layers['source_uv'].data[loop].uv=coord
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for edge in bm.edges:edge.smooth=edge.is_manifold and edge.calc_face_angle()<math.radians(55) and len({f.material_index for f in edge.link_faces})==1
    bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(record['name']+f'.lod{lod}',data);collection.objects.link(obj)
    obj['source']='source/floor.json';obj['source_construction']='original authored paths, sections and thick botanical outlines';obj['lod']=lod
    return obj

def finish_limb(objects,lod,collection):
    retained=bpy.data.collections.new('Retained_original_broken_limb_cages');bpy.context.scene.collection.children.link(retained)
    for obj in objects:
        copy=obj.copy();copy.data=obj.data.copy();copy.name='retained_'+obj.name;retained.objects.link(copy);copy.hide_set(True);copy.hide_render=True
    base=objects[0];bpy.context.view_layer.objects.active=base
    for child in objects[1:]:
        union=base.modifiers.new('continuous_authored_fork_union','BOOLEAN');union.operation='UNION';union.solver='EXACT';union.object=child
        bpy.ops.object.modifier_apply(modifier=union.name);bpy.data.objects.remove(child,do_unlink=True)
    if lod<2:
        bm=bmesh.new();bm.from_mesh(base.data);weight=bm.edges.layers.float.new('bevel_weight_edge')
        sockets=[(Vector(path[0][:3]),radius) for path,radius in zip(DESIGN['limbPaths'][1:],[.33,.26])]
        for edge in bm.edges:
            middle=(edge.verts[0].co+edge.verts[1].co)*.5
            edge[weight]=1 if edge.is_manifold and all(f.material_index==0 for f in edge.link_faces) and edge.calc_face_angle_signed()<-.4 and any((middle-p).length<radius for p,radius in sockets) else 0
        bm.to_mesh(base.data);bm.free()
        bevel=base.modifiers.new('soft_living_fork_transition','BEVEL');bevel.limit_method='WEIGHT';bevel.width=.018 if lod==0 else .010;bevel.segments=2 if lod==0 else 1;bevel.use_clamp_overlap=True
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    bm=bmesh.new();bm.from_mesh(base.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.dissolve_degenerate(bm,dist=.000001,edges=list(bm.edges));bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));
    # Exact fork intersection can retain a coincident pair of microscopic
    # opposite internal faces. Remove that zero-thickness membrane, not skin.
    bm.verts.index_update();groups={}
    for face in bm.faces:groups.setdefault(tuple(sorted(v.index for v in face.verts)),[]).append(face)
    membranes=[face for group in groups.values() if len(group)==2 and group[0].normal.dot(group[1].normal)<-.99 and all(f.calc_area()<1e-5 and sum(len(e.link_faces)>2 for e in f.edges)>=1 for f in group) for face in group]
    if membranes:bmesh.ops.delete(bm,geom=membranes,context='FACES_ONLY')
    loose=[edge for edge in bm.edges if not edge.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='EDGES')
    invalid=[edge for edge in bm.edges if len(edge.link_faces)!=2]
    if invalid:
        (ROOT/'review/limb_topology_diagnosis.json').write_text(json.dumps([{'points':[list(v.co) for v in edge.verts],'faces':[{'area':f.calc_area(),'indices':[v.index for v in f.verts]} for f in edge.link_faces]} for edge in invalid],indent=2)+'\n')
    bm.to_mesh(base.data);bm.free()
    return [base]

def build(key,lod,preview):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials={}
    for name,color in COLORS.items():
        material=bpy.data.materials.new(name+'.source_preview');material.diffuse_color=color;material.use_nodes=True;shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=color;shader.inputs['Roughness'].default_value=.86;materials[name]=material
    collection=bpy.data.collections.new(key+f'.authored_lod{lod}');bpy.context.scene.collection.children.link(collection)
    objects=[mesh(record,lod,collection,materials) for record in SOURCE['assets'][key]['lods'][lod]['objects']]
    if key.endswith('fallen_alder_limb'):objects=finish_limb(objects,lod,collection)
    for obj in objects:
        bpy.context.view_layer.objects.active=obj;tri=obj.modifiers.new('stable_finished_triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    result=audit(objects)
    if any(result[k] for k in ('totalBoundaryEdges','totalMultiFaceEdges','totalLooseEdges')):raise RuntimeError(f'Finished source topology failed: {result}')
    target=ROOT/'masters'/f'{key}_lod{lod}.source-preview.blend';bpy.ops.wm.save_as_mainfile(filepath=str(target))
    proof={'asset':key,'lod':lod,'sourceSha256':hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(),'builderSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'master':str(target.relative_to(ROOT)),'masterSha256':hashlib.sha256(target.read_bytes()).hexdigest(),'stage':'source geometry with flat material colors; not exported or approved','triangles':sum(len(o.data.polygons) for o in objects),'audit':result}
    if preview:
        image=ROOT/'review'/f'{key}_lod{lod}_source.png';render(objects,image);proof['image']=image.name;proof['imageSha256']=hashlib.sha256(image.read_bytes()).hexdigest()
    (ROOT/'review'/f'{key}_lod{lod}_source.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('FLOOR_SOURCE_FINISHED',key,lod,proof['triangles'],flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default=','.join(SOURCE['assets']));parser.add_argument('--lods',default='0');parser.add_argument('--preview',action='store_true');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for key in args.assets.split(','):
        for lod in args.lods.split(','):build(key,int(lod),args.preview)
