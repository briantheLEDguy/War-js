"""Bake exact finished workshop batches and retain source cages/material graphs."""
import argparse,hashlib,json,math,struct,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from materials_items import apply_materials
from review_items import audit
SOURCE_PATH=ROOT/'source/items.json';SOURCE=json.loads(SOURCE_PATH.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)
def geometry_hash(objects):
    return hashlib.sha256(json.dumps([{'vertices':[list(o.matrix_world@v.co) for v in o.data.vertices],'faces':[list(p.vertices) for p in o.data.polygons]} for o in objects],separators=(',',':')).encode()).hexdigest()

def image_material(name,images):
    material=bpy.data.materials.new('workshop_pbr.'+name);material.use_nodes=True;material.use_backface_culling=True;nodes=material.node_tree.nodes;links=material.node_tree.links;shader=nodes.get('Principled BSDF');uv=nodes.new('ShaderNodeUVMap');uv.uv_map='runtime_uv';maps={}
    for channel,image in images.items():
        node=nodes.new('ShaderNodeTexImage');node.image=image;node.extension='EXTEND';links.new(uv.outputs['UV'],node.inputs['Vector']);maps[channel]=node
    links.new(maps['baseColor'].outputs['Color'],shader.inputs['Base Color']);normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='runtime_uv';links.new(maps['normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal']);split=nodes.new('ShaderNodeSeparateColor');links.new(maps['orm'].outputs['Color'],split.inputs[0]);links.new(split.outputs['Green'],shader.inputs['Roughness']);links.new(split.outputs['Blue'],shader.inputs['Metallic'])
    group=bpy.data.node_groups.get('glTF Material Output')
    if not group:
        group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');group.interface.new_socket('Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
    node=nodes.new('ShaderNodeGroup');node.node_tree=group;links.new(split.outputs['Red'],node.inputs['Occlusion']);return material

def bake(obj,name,lod,fields):
    scene=bpy.context.scene;data=obj.data;before=geometry_hash([obj]);bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    data.uv_layers.new(name='runtime_uv');data.uv_layers.active_index=len(data.uv_layers)-1;data.uv_layers['runtime_uv'].active_render=True;resolution=[2048,1024,512][lod];margin=4/resolution
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=margin,area_weight=.9,correct_aspect=True,scale_to_bounds=True);bpy.ops.uv.pack_islands(rotate=True,rotate_method='ANY',scale=True,margin_method='FRACTION',margin=margin,shape_method='CONCAVE');bpy.ops.object.mode_set(mode='OBJECT')
    uv=data.uv_layers['runtime_uv'].data;occupied=0
    for face in data.polygons:
        coords=[uv[i].uv for i in face.loop_indices];occupied+=abs(sum(a.x*b.y-b.x*a.y for a,b in zip(coords,coords[1:]+coords[:1])))*.5
    data.calc_tangents(uvmap='runtime_uv');invalid=[l.index for l in data.loops if l.tangent.length<.99];data.free_tangents();chart_repairs=[]
    if invalid:
        # The fitted tool-rest has long sub-millimetre edge strips. A purely
        # area-proportional atlas makes their UV altitude smaller than a pixel
        # and can collapse a Mikk tangent. Allocate a separate measurable chart
        # to those actual strips; never alter geometry or bypass tangent checks.
        for face in data.polygons:
            if not any(i in invalid for i in face.loop_indices):continue
            points=[data.vertices[i].co for i in face.vertices];a,b=max(((0,1),(1,2),(2,0)),key=lambda pair:(points[pair[1]]-points[pair[0]]).length);c=3-a-b;edge=points[b]-points[a];length=edge.length;altitude=2*face.area/(length*length)
            if altitude>.001 or min(data.corner_normals[i].vector.dot(face.normal) for i in face.loop_indices)<.99:continue
            projection=(points[c]-points[a]).dot(edge)/(length*length)
            for index,point in [(a,(0,0)),(b,(1,0)),(c,(projection,.006))]:data.uv_layers['runtime_uv'].data[face.loop_indices[index]].uv=point
            chart_repairs.append({'face':face.index,'areaM2':face.area,'originalRelativeAltitude':altitude,'allocatedRelativeAltitude':.006})
        if chart_repairs:
            bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.pack_islands(rotate=True,rotate_method='ANY',scale=True,margin_method='FRACTION',margin=margin,shape_method='CONCAVE');bpy.ops.object.mode_set(mode='OBJECT')
            data.calc_tangents(uvmap='runtime_uv');invalid=[l.index for l in data.loops if l.tangent.length<.99];data.free_tangents()
    uv=data.uv_layers['runtime_uv'].data;occupied=0
    for face in data.polygons:
        coords=[uv[i].uv for i in face.loop_indices];occupied+=abs(sum(a.x*b.y-b.x*a.y for a,b in zip(coords,coords[1:]+coords[:1])))*.5
    if invalid:
        save(ROOT/'review'/f'{name}_lod{lod}_invalid_tangents.json',{'loops':invalid,'faces':[{'index':f.index,'area':f.area,'vertices':[list(data.vertices[i].co) for i in f.vertices],'uv':[list(uv[i].uv) for i in f.loop_indices],'cornerAlignment':[data.corner_normals[i].vector.dot(f.normal) for i in f.loop_indices]} for f in data.polygons if any(i in invalid for i in f.loop_indices)]});raise RuntimeError(f'Invalid atlas tangents in {name}: {len(invalid)}')
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=False;scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=False;scene.render.bake.margin=2;scene.render.bake.normal_space='TANGENT'
    folder=ROOT/'textures/baked';folder.mkdir(exist_ok=True);images={};channels={}
    used={data.materials[p.material_index].name for p in data.polygons};entries=[entry for entry in fields.values() if entry['material'].name in used]
    for entry in entries:
        nodes=entry['material'].node_tree.nodes;entry['target']=nodes.new('ShaderNodeTexImage');entry['emission']=nodes.new('ShaderNodeEmission')
    for channel in ('baseColor','orm','normal'):
        image=bpy.data.images.new(f'{name}_lod{lod}_{channel}',width=resolution,height=resolution,alpha=False);image.colorspace_settings.name='sRGB' if channel=='baseColor' else 'Non-Color';image.generated_color=(.5,.5,1,1) if channel=='normal' else (1,.85,0,1) if channel=='orm' else(.23,.17,.10,1)
        for entry in entries:
            tree=entry['material'].node_tree;entry['target'].image=image;tree.nodes.active=entry['target']
            for link in list(entry['output'].inputs[0].links):tree.links.remove(link)
            if channel=='normal':tree.links.new(entry['shader'].outputs[0],entry['output'].inputs[0])
            else:tree.links.new(entry['color' if channel=='baseColor' else 'orm'],entry['emission'].inputs['Color']);tree.links.new(entry['emission'].outputs[0],entry['output'].inputs[0])
        bpy.ops.object.bake(type='NORMAL' if channel=='normal' else 'EMIT');path=folder/f'{name}_lod{lod}_{channel}.png';image.filepath_raw=str(path);image.file_format='PNG';image.save();images[channel]=image;channels[channel]={'file':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':sha(path),'resolution':resolution};print('WORKSHOP_BAKE_CHANNEL',name,lod,channel,flush=True)
    for entry in entries:
        tree=entry['material'].node_tree
        for link in list(entry['output'].inputs[0].links):tree.links.remove(link)
        tree.links.new(entry['shader'].outputs[0],entry['output'].inputs[0])
    material=image_material(name,images);data.materials.clear();data.materials.append(material)
    for face in data.polygons:face.material_index=0
    after=geometry_hash([obj])
    if before!=after:raise RuntimeError('Bake changed finished geometry')
    return {'group':name,'geometrySha256Before':before,'geometrySha256After':after,'atlas':{'resolution':resolution,'occupiedFraction':occupied,'marginPixels':4,'dilationPixels':2,'uvChartRepairs':chart_repairs},'channels':channels}

def export(key,lods):
    target_record=ROOT/'review'/f'{key}_build.json';record={'asset_id':key,'displayName':SOURCE['assets'][key]['name'],'source_sha256':sha(SOURCE_PATH),'builder_sha256':sha(Path(__file__)),'material_tool_sha256':sha(ROOT/'tools/materials_items.py'),'contract':SOURCE['assets'][key]['contract'],'approval':'standing_user_approval_pending_technical_validation','lods':[]}
    retained_tools=ROOT/'review/tool_sources';retained_tools.mkdir(exist_ok=True);retained_exporter=retained_tools/f'export_items_{record["builder_sha256"]}.py'
    if not retained_exporter.exists():retained_exporter.write_bytes(Path(__file__).read_bytes())
    if target_record.exists():
        previous=json.loads(target_record.read_text())
        if previous['source_sha256']!=record['source_sha256']:raise RuntimeError('Partial export source changed')
        record['lods']=[row for row in previous['lods'] if row['level'] not in lods]
    for lod in lods:
        source_master=ROOT/'masters'/f'{key}_lod{lod}.source.blend';source_proof=ROOT/'review'/f'{key}_lod{lod}_source.json';proof=json.loads(source_proof.read_text())
        if proof['masterSha256']!=sha(source_master) or proof['sourceSha256']!=record['source_sha256'] or proof['builderSha256']!=sha(ROOT/'tools/build_items.py'):raise RuntimeError('Stale finished source master')
        bpy.ops.wm.open_mainfile(filepath=str(source_master));objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render];fields=apply_materials(objects)
        retained=bpy.data.collections.new('Retained_individual_finished_parts');bpy.context.scene.collection.children.link(retained)
        batches={}
        for obj in objects:
            original=obj.copy();original.data=obj.data.copy();original.name='retained_finished_'+obj['original_piece'];retained.objects.link(original);original.hide_set(True);original.hide_render=True
            names={obj.data.materials[p.material_index].name.split('.')[-1] for p in obj.data.polygons}
            batch='timber' if names<={'oak','oak_end','working_oak'} else 'metal' if names<={'forged_iron','worked_steel'} else 'loads'
            batches.setdefault(batch,[]).append(obj)
        export_objects=[];projections=[]
        for group,parts in batches.items():
            bpy.ops.object.select_all(action='DESELECT')
            for obj in parts:obj.select_set(True)
            bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();obj=parts[0];obj.name=key+'.'+group
            projection=bake(obj,key+'_'+group,lod,fields);projections.append(projection);export_objects.append(obj)
        result=audit(export_objects)
        if any(result[k] for k in ('totalBoundaryEdges','totalMultiFaceEdges','totalLooseEdges')):raise RuntimeError('Finished export batch topology failed')
        for image in bpy.data.images:
            if image.source in ('FILE','GENERATED'):image.pack()
        master=ROOT/'masters'/f'{key}_lod{lod}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(master))
        for obj in export_objects:
            obj.data.uv_layers.remove(obj.data.uv_layers['source_uv']);obj.data.uv_layers.active_index=0;obj.data.uv_layers[0].active_render=True
        bpy.ops.object.select_all(action='DESELECT')
        for obj in export_objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=export_objects[0];target=ROOT/'runtime'/f'{key}_lod{lod}.glb';bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True,export_texcoords=True,export_normals=True)
        raw=target.read_bytes();length=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+length]);counts=[sum(doc['accessors'][p['indices']]['count']//3 for p in mesh['primitives']) for mesh in doc['meshes']];triangles=sum(counts[node['mesh']] for node in doc['nodes'] if 'mesh' in node)
        record['lods'].append({'level':lod,'model':target.name,'sha256':sha(target),'bytes':target.stat().st_size,'triangles':triangles,'materials':len(doc['materials']),'exporter_sha256':record['builder_sha256'],'master':str(master.relative_to(ROOT)).replace('\\','/'),'master_sha256':sha(master),'source_master_sha256':sha(source_master),'source_receipt_sha256':sha(source_proof),'source_audit':result,'bounds_z_up':result['bounds_z_up'],'material_projections':projections,'stoneSupports':proof['stoneSupports']});record['lods'].sort(key=lambda row:row['level']);save(target_record,record);print('WORKSHOP_EXPORTED',key,lod,triangles,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default=','.join(SOURCE['assets']));parser.add_argument('--lods',default='0,1,2');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for key in args.assets.split(','):export(key,[int(x) for x in args.lods.split(',')])
