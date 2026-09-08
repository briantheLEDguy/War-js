"""Finish explicit original ecology meshes, retain masters and export all LODs.

Material/export mechanics are adapted from the retained architecture utility.
No mesh source or texture pixel from that package is reused.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from bake_bark_projection import bake_bark
SOURCE_PATH=ROOT/'source/nature.json';SOURCE=json.loads(SOURCE_PATH.read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def material(name):
    definition=SOURCE['materials'][name];result=bpy.data.materials.new('cinderfen_nature.'+name);result.use_nodes=True
    nodes=result.node_tree.nodes;links=result.node_tree.links;shader=nodes.get('Principled BSDF');uv=nodes.new('ShaderNodeUVMap');uv.uv_map='authored_uv';maps={}
    for channel in ('baseColor','normal','orm'):
        node=nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(ROOT/'textures/source'/f'{name}_{channel}.png'),check_existing=True)
        node.image.colorspace_settings.name='sRGB' if channel=='baseColor' else 'Non-Color';node.extension='REPEAT';links.new(uv.outputs['UV'],node.inputs['Vector']);maps[channel]=node
    links.new(maps['baseColor'].outputs['Color'],shader.inputs['Base Color'])
    normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='authored_uv';links.new(maps['normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    split=nodes.new('ShaderNodeSeparateColor');links.new(maps['orm'].outputs['Color'],split.inputs[0]);links.new(split.outputs['Green'],shader.inputs['Roughness']);links.new(split.outputs['Blue'],shader.inputs['Metallic'])
    group=bpy.data.node_groups.get('glTF Material Output')
    if not group:
        group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');group.interface.new_socket('Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
    output=nodes.new('ShaderNodeGroup');output.node_tree=group;links.new(split.outputs['Red'],output.inputs['Occlusion'])
    result.diffuse_color=(*(x/255 for x in definition['color']),1);result.use_backface_culling=True
    return result

def mesh(record,lod,materials,collection):
    data=bpy.data.meshes.new(record['name']+'.literal_source');data.from_pydata(record['vertices'],[],record['faces']);data.update()
    data.materials.append(materials[record['material']]);data.uv_layers.new(name='authored_uv')
    # Reacquire after creating all CustomData layers; Blender 5 can invalidate
    # retained layer pointers when later attributes are added.
    uv=data.uv_layers['authored_uv']
    for polygon,coords in zip(data.polygons,record['corner_uv']):
        for loop,coordinate in zip(polygon.loop_indices,coords):uv.data[loop].uv=coordinate
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    sharp_angle=27 if record['material']=='basalt' else 60 if record['smooth'] else 27
    for edge in bm.edges:edge.smooth=edge.is_manifold and edge.calc_face_angle()<math.radians(sharp_angle)
    bm.to_mesh(data);bm.free()
    for polygon in data.polygons:polygon.use_smooth=record['smooth']
    obj=bpy.data.objects.new(record['name']+f'.lod{lod}',data);collection.objects.link(obj)
    obj['source']='source/nature.json';obj['visible_geometry_source']='original_explicit_mesh_records';obj['lod']=lod
    if record['material']=='basalt' and lod<2:
        bevel=obj.modifiers.new('small_fracture_edge_finish','BEVEL');bevel.width=.020 if lod==0 else .012;bevel.segments=2-lod;bevel.limit_method='ANGLE';bevel.angle_limit=.48
        normal=obj.modifiers.new('fracture_plane_normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=50
    obj.modifiers.new('stable_export_triangles','TRIANGULATE')
    return obj

def joined_bark(record,lod,materials,collection):
    """Join the original bole and primary branches at their intersections.

    The retained source consists of art-directed closed branch cages. Exact
    union removes buried end caps, and a small concave-edge finish creates a
    continuous main bark surface without remeshing away the authored UV fields.
    """
    connected={i:set() for i in range(len(record['vertices']))}
    for face in record['faces']:
        for a,b in zip(face,face[1:]+face[:1]):connected[a].add(b);connected[b].add(a)
    unseen=set(connected);components=[]
    while unseen:
        first=min(unseen);unseen.remove(first);indices={first};queue=[first]
        while queue:
            for other in connected[queue.pop()]:
                if other in unseen:unseen.remove(other);indices.add(other);queue.append(other)
        components.append(indices)
    primary=components[:16];branch_indices=set().union(*components[16:])
    def subset(indices,name):
        ordered=sorted(indices);mapping={old:new for new,old in enumerate(ordered)};faces=[];uv=[]
        for face,coords in zip(record['faces'],record['corner_uv']):
            if face[0] in indices:faces.append([mapping[v] for v in face]);uv.append(coords)
        return {**record,'name':name,'vertices':[record['vertices'][i] for i in ordered],'faces':faces,'corner_uv':uv}
    retained=bpy.data.collections.new('Retained_original_primary_bark_cages');bpy.context.scene.collection.children.link(retained)
    primary_objects=[mesh(subset(indices,'original_primary_bark_'+str(i)),lod,materials,retained) for i,indices in enumerate(primary)]
    base=primary_objects[0].copy();base.data=primary_objects[0].data.copy();base.name=record['name']+f'.joined_lod{lod}';collection.objects.link(base)
    for modifier in list(base.modifiers):base.modifiers.remove(modifier)
    bpy.context.view_layer.objects.active=base
    for child in primary_objects[1:]:
        modifier=base.modifiers.new('join_authored_branch','BOOLEAN');modifier.operation='UNION';modifier.solver='EXACT';modifier.object=child
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    if lod<2:
        bm=bmesh.new();bm.from_mesh(base.data);weight=bm.edges.layers.float.new('bevel_weight_edge')
        for edge in bm.edges:edge[weight]=1 if edge.is_manifold and edge.calc_face_angle_signed()<-.42 else 0
        bm.to_mesh(base.data);bm.free()
        bevel=base.modifiers.new('rounded_bark_intersections','BEVEL');bevel.width=.047 if lod==0 else .028;bevel.segments=2-lod;bevel.limit_method='WEIGHT';bevel.use_clamp_overlap=True
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    bm=bmesh.new();bm.from_mesh(base.data);bmesh.ops.dissolve_degenerate(bm,dist=.0000001,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(base.data);bm.free()
    for polygon in base.data.polygons:polygon.use_smooth=True
    triangulate=base.modifiers.new('stable_join_triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=triangulate.name)
    bm=bmesh.new();bm.from_mesh(base.data)
    # Exact intersections can leave micrometre slivers, below float32/MikkTSpace
    # resolution at a ten-metre asset scale. Weld only the primary bark skin;
    # its smallest radius is 6mm, while attached fine shoots remain untouched.
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00005)
    bmesh.ops.dissolve_degenerate(bm,dist=.00005,edges=list(bm.edges))
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(base.data);bm.free()
    uv=base.data.uv_layers['authored_uv']
    for polygon in base.data.polygons:
        coords=[uv.data[i].uv.copy() for i in polygon.loop_indices]
        area=sum(a.x*b.y-b.x*a.y for a,b in zip(coords,coords[1:]+coords[:1]))
        if abs(area)<1e-9:
            axes=[axis for axis in range(3) if axis!=max(range(3),key=lambda k:abs(polygon.normal[k]))]
            for loop in polygon.loop_indices:
                point=base.data.vertices[base.data.loops[loop].vertex_index].co;uv.data[loop].uv=(point[axes[0]]*.58,point[axes[1]]*.58)
    twigs=mesh(subset(branch_indices,'small_attached_shoots_and_petioles'),lod,materials,collection)
    for original in primary_objects:original.hide_render=True;original.hide_set(True)
    # Join material batches after modifiers are evaluated; the editable master
    # also retains all unmerged original primary cages in the hidden collection.
    bpy.ops.object.select_all(action='DESELECT');base.select_set(True);twigs.select_set(True);bpy.context.view_layer.objects.active=base
    for obj in (base,twigs):
        bpy.context.view_layer.objects.active=obj
        for modifier in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.context.view_layer.objects.active=base;bpy.ops.object.join()
    bm=bmesh.new();bm.from_mesh(base.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    # Remove an exposed microscopic Boolean fin and redundant internal caps
    # where distant shoots share an exact base ring. Keep their outer surfaces.
    redundant=[face for face in bm.faces if
        (sum(edge.is_boundary for edge in face.edges)>=2 and any(len(edge.link_faces)>2 for edge in face.edges) and face.calc_area()<.0001)
        or (sum(len(edge.link_faces)>2 for edge in face.edges)>=2 and all(len(edge.link_faces)>=2 for edge in face.edges) and face.calc_area()<.002)]
    if redundant:bmesh.ops.delete(bm,geom=redundant,context='FACES_ONLY')
    loose=[edge for edge in bm.edges if not edge.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='EDGES')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    invalid=[edge for edge in bm.edges if len(edge.link_faces)!=2]
    if invalid:raise RuntimeError(f'Joined bark LOD{lod} has {len(invalid)} nonmanifold edges before export')
    bm.to_mesh(base.data);bm.free()
    return base

def build(key):
    bpy.ops.wm.read_factory_settings(use_empty=True);definition=SOURCE['assets'][key]
    materials={name:material(name) for name in SOURCE['materials']}
    record={'asset_id':key,'displayName':definition['name'],'source_sha256':sha(SOURCE_PATH),'builder_sha256':sha(Path(__file__)),'paint_records_sha256':sha(ROOT/'textures/paint-records.json'),'contract':definition['contract'],'approval':'pending_visual_review','lods':[]}
    record['texture_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted((ROOT/'textures/source').glob('*.png'))}
    for level in definition['lods']:
        lod=level['level'];collection=bpy.data.collections.new(f'{key}.authored_lod{lod}');bpy.context.scene.collection.children.link(collection)
        objects=[joined_bark(item,lod,materials,collection) if key.endswith('marsh_alder') and item['material']=='alder_bark' else mesh(item,lod,materials,collection) for item in level['objects']]
        bark_projection=bake_bark(objects[0],lod) if key.endswith('marsh_alder') else None
        bpy.context.view_layer.update()
        if lod==0:
            for image in bpy.data.images:
                if image.source in ('FILE','GENERATED'):image.pack()
            master=ROOT/'masters'/f'{key}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(master))
            record['master']=str(master.relative_to(ROOT)).replace('\\','/');record['master_sha256']=sha(master)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        target=ROOT/'runtime'/f'{key}_lod{lod}.glb'
        bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True,export_texcoords=True,export_normals=True)
        graph=bpy.context.evaluated_depsgraph_get();points=[]
        for obj in objects:
            evaluated=obj.evaluated_get(graph);points.extend(obj.matrix_world@vertex.co for vertex in evaluated.data.vertices)
        bounds={'minimum':[min(p[i] for p in points) for i in range(3)],'maximum':[max(p[i] for p in points) for i in range(3)]}
        import struct
        raw=target.read_bytes();size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size]);counts=[sum(doc['accessors'][p['indices']]['count']//3 for p in m['primitives']) for m in doc['meshes']]
        triangles=sum(counts[n['mesh']] for n in doc['nodes'] if 'mesh' in n)
        record['lods'].append({'level':lod,'model':target.name,'sha256':sha(target),'bytes':target.stat().st_size,'triangles':triangles,'materials':len(doc['materials']),'bounds_z_up':bounds})
        if bark_projection:record['lods'][-1]['bark_projection']=bark_projection
        for obj in objects:obj.hide_render=True;obj.hide_set(True)
        (ROOT/'review'/f'{key}_build.json').write_text(json.dumps(record,indent=2)+'\n')
        print('NATURE_EXPORTED',key,lod,triangles,flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default=','.join(SOURCE['assets']));args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for key in args.assets.split(','):build(key)
