"""Bake original branch-local wood fields on the unchanged finished limb."""
import hashlib,json,math
from pathlib import Path
import bpy
from materials_floor import image_material
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)
def geometry_hash(obj):
    return hashlib.sha256(json.dumps({'vertices':[list(v.co) for v in obj.data.vertices],'faces':[list(p.vertices) for p in obj.data.polygons]},separators=(',',':')).encode()).hexdigest()

def bake_wood(obj,lod,fields):
    before=geometry_hash(obj);scene=bpy.context.scene;data=obj.data
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.hide_render=False;obj.select_set(True);bpy.context.view_layer.objects.active=obj
    data.uv_layers.new(name='runtime_uv');data.uv_layers.active_index=len(data.uv_layers)-1;data.uv_layers['runtime_uv'].active_render=True
    resolution=[2048,1024,512][lod];margin=4/resolution
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(62),island_margin=margin,area_weight=.85,correct_aspect=True,scale_to_bounds=True)
    bpy.ops.uv.pack_islands(rotate=True,rotate_method='ANY',scale=True,margin_method='FRACTION',margin=margin,shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')
    uv=data.uv_layers['runtime_uv'].data;occupied=0
    for face in data.polygons:
        coords=[uv[i].uv for i in face.loop_indices];occupied+=abs(sum(a.x*b.y-b.x*a.y for a,b in zip(coords,coords[1:]+coords[:1])))*.5
    data.calc_tangents(uvmap='runtime_uv');invalid=[loop.index for loop in data.loops if loop.tangent.length<.99];data.free_tangents()
    if invalid:
        save(ROOT/'review'/f'wood_tangent_diagnosis_lod{lod}.json',{'invalidLoops':invalid,'faces':[{'index':f.index,'area':f.area,'vertices':[list(data.vertices[v].co) for v in f.vertices],'uv':[list(uv[i].uv) for i in f.loop_indices]} for f in data.polygons if any(i in invalid for i in f.loop_indices)]})
        raise RuntimeError(f'Wood LOD{lod} has {len(invalid)} invalid atlas tangents; diagnose before export')
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=False;scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=False;scene.render.bake.margin=2;scene.render.bake.normal_space='TANGENT'
    folder=ROOT/'textures/wood-projection';folder.mkdir(exist_ok=True);images={};channels={}
    for entry in fields.values():
        nodes=entry['material'].node_tree.nodes;entry['target']=nodes.new('ShaderNodeTexImage');entry['emission']=nodes.new('ShaderNodeEmission')
    for channel in ('baseColor','orm','normal'):
        image=bpy.data.images.new(f'fallen_alder_lod{lod}_{channel}',width=resolution,height=resolution,alpha=False)
        image.colorspace_settings.name='sRGB' if channel=='baseColor' else 'Non-Color';image.generated_color=(.5,.5,1,1) if channel=='normal' else (1,.86,0,1) if channel=='orm' else (.30,.26,.21,1)
        for entry in fields.values():
            tree=entry['material'].node_tree;entry['target'].image=image;tree.nodes.active=entry['target']
            for link in list(entry['output'].inputs[0].links):tree.links.remove(link)
            if channel=='normal':tree.links.new(entry['shader'].outputs[0],entry['output'].inputs[0])
            else:
                tree.links.new(entry['color' if channel=='baseColor' else 'orm'],entry['emission'].inputs['Color']);tree.links.new(entry['emission'].outputs[0],entry['output'].inputs[0])
        bpy.ops.object.bake(type='NORMAL' if channel=='normal' else 'EMIT')
        path=folder/f'fallen_alder_lod{lod}_{channel}.png';image.filepath_raw=str(path);image.file_format='PNG';image.save();images[channel]=image
        channels[channel]={'file':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':sha(path),'resolution':resolution}
        print('FLOOR_WOOD_CHANNEL',lod,channel,flush=True)
    # Source graphs remain editable and shaded correctly in the packed master.
    for entry in fields.values():
        tree=entry['material'].node_tree
        for link in list(entry['output'].inputs[0].links):tree.links.remove(link)
        tree.links.new(entry['shader'].outputs[0],entry['output'].inputs[0])
    result=image_material(f'fallen_alder_lod{lod}',images,'runtime_uv');data.materials.clear();data.materials.append(result)
    for face in data.polygons:face.material_index=0
    after=geometry_hash(obj)
    if before!=after:raise RuntimeError('Wood bake changed finished source geometry')
    record={'tool':'tools/bake_floor_wood.py','toolSha256':sha(Path(__file__)),'materialToolSha256':sha(ROOT/'tools/materials_floor.py'),'geometrySha256Before':before,'geometrySha256After':after,'atlas':{'resolution':resolution,'occupiedFraction':occupied,'marginPixels':4,'dilationPixels':2},'channels':channels,'method':'Branch-local grain vectors continue into original broken-end surveys; broad pigment/lichen share object coordinates. All channels bake directly onto unchanged source-finished triangles.'}
    save(ROOT/'review'/f'wood_projection_lod{lod}.json',record);return record
