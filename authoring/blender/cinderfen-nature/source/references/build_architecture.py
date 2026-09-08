"""Cinderfen exporter; adapted from the accepted Sunmeadow finishing utilities.

Only finishing/export mechanics are reused. Source cages, construction layout,
painted pixels and physical UV projection are original to this package.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Matrix,Vector,Euler
ROOT=Path(__file__).resolve().parents[1]
SOURCE_PATH=ROOT/'source/architecture.json'
SOURCE=json.loads(SOURCE_PATH.read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def material(name):
    item=SOURCE['materials'][name];result=bpy.data.materials.new('cinderfen.'+name);result.use_nodes=True
    tree=result.node_tree;shader=tree.nodes.get('Principled BSDF');uv=tree.nodes.new('ShaderNodeUVMap');uv.uv_map='authored_uv'
    maps={}
    for channel in ('baseColor','normal','orm'):
        node=tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(ROOT/'textures/source'/f'{name}_{channel}.png'),check_existing=True)
        node.image.colorspace_settings.name='sRGB' if channel=='baseColor' else 'Non-Color';node.extension='REPEAT';tree.links.new(uv.outputs['UV'],node.inputs['Vector']);maps[channel]=node
    tree.links.new(maps['baseColor'].outputs['Color'],shader.inputs['Base Color'])
    normal=tree.nodes.new('ShaderNodeNormalMap');normal.uv_map='authored_uv';tree.links.new(maps['normal'].outputs['Color'],normal.inputs['Color']);tree.links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    split=tree.nodes.new('ShaderNodeSeparateColor');tree.links.new(maps['orm'].outputs['Color'],split.inputs[0]);tree.links.new(split.outputs['Green'],shader.inputs['Roughness']);tree.links.new(split.outputs['Blue'],shader.inputs['Metallic'])
    group=bpy.data.node_groups.get('glTF Material Output')
    if not group:
        group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');group.interface.new_socket('Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
    occlusion=tree.nodes.new('ShaderNodeGroup');occlusion.node_tree=group;tree.links.new(split.outputs['Red'],occlusion.inputs['Occlusion'])
    result.diffuse_color=(*(value/255 for value in item['color']),1)
    return result


def prototype(name,lod,materials,collection):
    base=SOURCE['parts'][name];record=base.get(f'lod{lod}',base)
    data=bpy.data.meshes.new(f'{name}.literal_cage');data.from_pydata(record['vertices'],[],record['faces']);data.update()
    uv=data.uv_layers.new(name='authored_uv')
    for polygon,coords in zip(data.polygons,record['corner_uv']):
        for index,corner in zip(polygon.loop_indices,coords):uv.data[index].uv=corner
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for edge in bm.edges:edge.smooth=edge.is_manifold and edge.calc_face_angle()<math.radians(35)
    bm.to_mesh(data);bm.free()
    for polygon in data.polygons:polygon.use_smooth=True
    face_materials=record.get('face_materials',[record['material']]*len(data.polygons));names=list(dict.fromkeys(face_materials))
    for material_name in names:data.materials.append(materials[material_name])
    for polygon,material_name in zip(data.polygons,face_materials):polygon.material_index=names.index(material_name)
    obj=bpy.data.objects.new(f'cage.{name}',data);collection.objects.link(obj)
    obj['description']=record['description'];obj['source']='literal_authored_mesh';obj['visible_geometry_source']='source/architecture.json'
    if lod<2 and record['bevel']>.001 and not name.startswith('fen_basalt') and name not in ('reed_roof_bundle','reed_wall_panel'):
        bevel=obj.modifiers.new('fitted_edge_finish','BEVEL');bevel.width=record['bevel'];bevel.segments=2-lod;bevel.limit_method='ANGLE';bevel.angle_limit=.40
    normals=obj.modifiers.new('construction_normals','WEIGHTED_NORMAL');normals.keep_sharp=True;normals.weight=50
    if lod>0 and not base.get('protected') and not (lod==2 and 'lod2' in base):
        reduction=obj.modifiers.new('distance_surface_reduction','DECIMATE')
        reduction.ratio=base.get('reduce',.58) if lod==1 else .36
        reduction.use_collapse_triangulate=True
    graph=bpy.context.evaluated_depsgraph_get();bpy.context.view_layer.update()
    evaluated=bpy.data.meshes.new_from_object(obj.evaluated_get(graph),preserve_all_data_layers=True,depsgraph=graph)
    if lod>0:
        # Quadric collapse can extrapolate beyond fitted end planes. Preserve
        # each original piece's envelope so doorways and module joins stay open.
        lower=[min(v[i] for v in record['vertices']) for i in range(3)]
        upper=[max(v[i] for v in record['vertices']) for i in range(3)]
        for vertex in evaluated.vertices:
            for axis in range(3):vertex.co[axis]=max(lower[axis],min(upper[axis],vertex.co[axis]))
        evaluated.update()
    evaluated.name=f'{name}.finished_lod{lod}'
    return obj,evaluated


def placement(instance):
    rotation=Euler(tuple(math.radians(value) for value in instance['rotation_degrees']),'XYZ').to_matrix().to_4x4()
    return Matrix.Translation(Vector(instance['location']))@rotation@Matrix.Diagonal(Vector((*instance['scale'],1)))


def physical_uvs(data,scale,material_name,phase=(0,0)):
    """Retain metre-scaled weave/grain after construction pieces are fitted."""
    points=[Vector((v.co.x*scale[0],v.co.y*scale[1],v.co.z*scale[2])) for v in data.vertices]
    lower=[min(p[axis] for p in points) for axis in range(3)]
    dimensions=[max(p[axis] for p in points)-lower[axis] for axis in range(3)]
    directional=SOURCE['materials'][material_name]['kind'] in ('wood','reed')
    result=[]
    for polygon in data.polygons:
        normal=Vector((0,0,0));vertices=[points[index] for index in polygon.vertices]
        for a,b in zip(vertices,vertices[1:]+vertices[:1]):normal+=a.cross(b)
        excluded=max(range(3),key=lambda axis:abs(normal[axis]));axes=[axis for axis in range(3) if axis!=excluded]
        if material_name=='roof_reed':
            # Reed fibres follow the roof camber, including steep eaves; a
            # longest-axis projection would turn them along the ridge there.
            slope=math.hypot(dimensions[0],dimensions[2])/max(dimensions[0],.001)
            if abs(normal.z)>normal.length*.20:
                result.append([(float(p.y-lower[1]+phase[0]),float((p.x-lower[0])*slope+phase[1])) for p in vertices])
            else:
                result.append([(float(p.y-lower[1]+phase[0]),float(p.z-lower[2]+phase[1])) for p in vertices])
            continue
        if directional:
            along=max(axes,key=lambda axis:dimensions[axis]);axes=[next(axis for axis in axes if axis!=along),along]
        result.append([(float(p[axes[0]]-lower[axes[0]]+phase[0]),float(p[axes[1]]-lower[axes[1]]+phase[1])) for p in vertices])
    return result


def combined(asset_id,lod,prototypes,materials,save_instances=False,rigid_group=None):
    vertices=[];faces=[];corners=[];face_materials=[];used_names=[]
    collection=bpy.data.collections.new(f'{asset_id}.placed_authoring_lod{lod}');bpy.context.scene.collection.children.link(collection)
    for number,instance in enumerate(SOURCE['assets'][asset_id]['instances']):
        if lod not in instance.get('lod_levels',[0,1,2]):continue
        if rigid_group and instance.get('rigid_group')!=rigid_group:continue
        if lod==2 and instance['detail']>0:continue
        name=instance['part'];data=prototypes[name];transform=placement(instance);offset=len(vertices)
        vertices.extend(tuple(transform@vertex.co) for vertex in data.vertices)
        material_name=instance.get('material',SOURCE['parts'][name]['material'])
        # Stable per-piece phases prevent identical knots and clefts repeating
        # across every course while preserving physical scale and grain direction.
        phase=((number*.61803398875)%1,(number*.41421356237)%1)
        fitted_uvs=physical_uvs(data,instance['scale'],material_name,phase)
        for polygon,coords in zip(data.polygons,fitted_uvs):
            face_material=instance.get('material',data.materials[polygon.material_index].name.removeprefix('cinderfen.').split('.')[0])
            if face_material not in used_names:used_names.append(face_material)
            material_index=used_names.index(face_material)
            faces.append(tuple(offset+index for index in polygon.vertices))
            corners.append(coords);face_materials.append(material_index)
        if save_instances:
            fitted_data=data.copy()
            for polygon,coords in zip(fitted_data.polygons,fitted_uvs):
                for loop,uv in zip(polygon.loop_indices,coords):fitted_data.uv_layers.active.data[loop].uv=uv
            obj=bpy.data.objects.new(f'{name}.{number:04}',fitted_data);collection.objects.link(obj);obj.matrix_world=transform;obj['authored_part']=name
            if 'material' in instance:
                for slot in obj.material_slots:slot.link='OBJECT';slot.material=materials[material_name]
    data=bpy.data.meshes.new(f'{asset_id}.lod{lod}');data.from_pydata(vertices,[],faces);data.update()
    for name in used_names:data.materials.append(materials[name])
    uv=data.uv_layers.new(name='authored_uv')
    for polygon,coords,index in zip(data.polygons,corners,face_materials):
        polygon.material_index=index;polygon.use_smooth=True
        for loop,corner in zip(polygon.loop_indices,coords):uv.data[loop].uv=corner
    bm=bmesh.new();bm.from_mesh(data)
    for edge in bm.edges:edge.smooth=edge.is_manifold and edge.calc_face_angle()<math.radians(35)
    bm.to_mesh(data);bm.free()
    if rigid_group and bpy.data.objects.get(rigid_group):bpy.data.objects[rigid_group].name+=f'.retained_before_lod{lod}'
    obj=bpy.data.objects.new(rigid_group or f'{asset_id}_LOD{lod}',data);bpy.context.scene.collection.objects.link(obj)
    normals=obj.modifiers.new('construction_normal_finish','WEIGHTED_NORMAL');normals.keep_sharp=True;normals.weight=50
    triangulate=obj.modifiers.new('stable_export_triangles','TRIANGULATE')
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    for modifier in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=modifier.name)
    for item in collection.objects:item.hide_render=True;item.hide_set(True)
    if rigid_group:
        pivot=Vector((-3 if rigid_group=='gate_leaf_left' else 3,0,0));obj.data.transform(Matrix.Translation(-pivot));obj.location=pivot
    return obj,collection


def render(objects,path,front=False):
    for item in list(bpy.data.objects):
        if item.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(item,do_unlink=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
    scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.world=bpy.data.worlds.new('architecture_review_world');scene.world.color=(.22,.22,.22)
    points=[obj.matrix_world@Vector(corner) for obj in objects for corner in obj.bound_box]
    lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)]);centre=(lo+hi)/2;extent=max(hi-lo)
    data=bpy.data.cameras.new('review_camera');camera=bpy.data.objects.new('review_camera',data);scene.collection.objects.link(camera)
    camera.location=centre+Vector((extent*.95 if not front else 0,-extent*1.5,extent*.85 if not front else extent*.05));camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';scene.camera=camera
    inverse=camera.rotation_euler.to_matrix().transposed();projected=[inverse@(point-centre) for point in points]
    width=max(p.x for p in projected)-min(p.x for p in projected);height=max(p.y for p in projected)-min(p.y for p in projected)
    data.ortho_scale=max(width,height*1600/1200)*1.16
    for name,delta,power,size,color in [('key',(-4,-6,8),2200,5,(1,.91,.77)),('fill',(6,-3,5),1700,5,(.80,.90,1)),('rim',(0,6,8),2000,5,(1,.94,.84))]:
        light_data=bpy.data.lights.new(name,'AREA');light_data.energy=power*(extent/7)**2;light_data.shape='DISK';light_data.size=size*extent/7;light_data.color=color
        light=bpy.data.objects.new(name,light_data);scene.collection.objects.link(light);light.location=centre+Vector(delta)*extent/7;light.rotation_euler=(centre-light.location).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.view_transform='AgX';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    return {'minimum':list(lo),'maximum':list(hi),'dimensions':list(hi-lo)}


def animate_leaves(objects):
    scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=1;scene.frame_end=86
    for obj in objects:
        sign=1 if obj.name=='gate_leaf_left' else -1
        for clip,start,angles in [('gate_open',1,(0,90)),('gate_close',50,(90,0))]:
            obj.animation_data_create();action=bpy.data.actions.new(obj.name+'.'+clip);obj.animation_data.action=action
            for frame,angle in zip((start,start+36),angles):
                obj.rotation_euler=(0,0,sign*math.radians(angle));obj.keyframe_insert(data_path='rotation_euler',frame=frame)
            track=obj.animation_data.nla_tracks.new();track.name=clip
            strip=track.strips.new(clip,start,action);strip.extrapolation='NOTHING';strip.blend_type='REPLACE'
            obj.animation_data.action=None
        obj.rotation_euler=(0,0,0)
    scene.frame_set(1)


def build_asset(asset_id,args):
    bpy.ops.wm.read_factory_settings(use_empty=True);materials={name:material(name) for name in SOURCE['materials']}
    record={'asset_id':asset_id,'source_sha256':sha(SOURCE_PATH),'builder_sha256':sha(Path(__file__)),
            'paint_records_sha256':sha(ROOT/'textures/paint_records.json'),'texture_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted((ROOT/'textures/source').glob('*.png'))},
            'contract':SOURCE['assets'][asset_id]['contract'],'approval':'pending_visual_review','lods':[]}
    for lod in args.lods:
        cages=bpy.data.collections.new(f'Original_control_cages_lod{lod}');bpy.context.scene.collection.children.link(cages)
        prototypes={}
        for name in SOURCE['parts']:
            source,data=prototype(name,lod,materials,cages);prototypes[name]=data;source.hide_render=True;source.hide_set(True)
        animated=asset_id=='frontier_cinderfen_gate_leaves'
        groups=('gate_leaf_left','gate_leaf_right') if animated else (None,)
        objects=[];placed=[]
        for group in groups:
            obj,instances=combined(asset_id,lod,prototypes,materials,save_instances=lod==0,rigid_group=group)
            objects.append(obj);placed.extend(instances.objects)
        if animated:animate_leaves(objects)
        if lod==0:
            for image in bpy.data.images:
                if image.source=='FILE':image.pack()
            for obj in objects:obj.hide_render=not animated;obj.hide_set(not animated)
            for item in placed:item.hide_render=animated;item.hide_set(animated)
            master=ROOT/'masters'/f'{asset_id}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(master))
            record['master']=str(master.relative_to(ROOT)).replace('\\','/');record['master_sha256']=sha(master)
            for item in placed:item.hide_render=True;item.hide_set(True)
            for obj in objects:obj.hide_render=False;obj.hide_set(False)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        runtime=ROOT/'runtime'/f'{asset_id}_lod{lod}.glb'
        bpy.ops.export_scene.gltf(filepath=str(runtime),export_format='GLB',use_selection=True,export_apply=True,export_animations=animated,export_animation_mode='NLA_TRACKS',export_frame_range=False,export_tangents=True,export_texcoords=True,export_normals=True)
        points=[obj.matrix_world@vertex.co for obj in objects for vertex in obj.data.vertices]
        bounds={'minimum':[min(point[i] for point in points) for i in range(3)],'maximum':[max(point[i] for point in points) for i in range(3)]}
        triangles=sum(len(obj.data.polygons) for obj in objects)
        record['lods'].append({'level':lod,'model':runtime.name,'sha256':sha(runtime),'bytes':runtime.stat().st_size,'triangles':triangles,'vertices':sum(len(obj.data.vertices) for obj in objects),'materials':len({m.name for obj in objects for m in obj.data.materials}),'bounds_z_up':bounds})
        if args.render:render(objects,ROOT/'review'/f'{asset_id}_lod{lod}_source.png')
        for obj in objects:obj.hide_render=True;obj.hide_set(True)
        (ROOT/'review'/f'{asset_id}_build.json').write_text(json.dumps(record,indent=2)+'\n')
        print(f"ARCHITECTURE_EXPORTED {asset_id} LOD{lod} triangles={triangles} bytes={runtime.stat().st_size}",flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default=','.join(SOURCE['assets']));parser.add_argument('--lods',default='0,1,2');parser.add_argument('--render',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);args.lods=list(map(int,args.lods.split(',')))
    for asset_id in args.assets.split(','):build_asset(asset_id,args)
