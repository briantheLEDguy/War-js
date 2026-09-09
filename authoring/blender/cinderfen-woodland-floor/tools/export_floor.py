"""Export three exact floor LODs with retained geometry/material source masters."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from materials_floor import apply_materials
from bake_floor_wood import bake_wood,save,geometry_hash
from review_floor import audit
SOURCE_PATH=ROOT/'source/floor.json';SOURCE=json.loads(SOURCE_PATH.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def export(key,lods):
    definition=SOURCE['assets'][key];target_record=ROOT/'review'/f'{key}_build.json'
    record={'asset_id':key,'displayName':definition['name'],'source_sha256':sha(SOURCE_PATH),'builder_sha256':sha(Path(__file__)),'material_tool_sha256':sha(ROOT/'tools/materials_floor.py'),'paint_records_sha256':sha(ROOT/'textures/paint-records.json'),'contract':definition['contract'],'approval':'pending_visual_review','lods':[]}
    record['texture_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted((ROOT/'textures/source').glob('*.png'))}
    if target_record.exists():
        previous=json.loads(target_record.read_text())
        if previous['source_sha256']!=record['source_sha256']:raise RuntimeError('Source changed since partial export; archive old build before continuing')
        record['lods']=[row for row in previous['lods'] if row['level'] not in lods]
    for lod in lods:
        source_master=ROOT/'masters'/f'{key}_lod{lod}.source-preview.blend';source_receipt=ROOT/'review'/f'{key}_lod{lod}_source.json';proof=json.loads(source_receipt.read_text())
        if proof['sourceSha256']!=record['source_sha256'] or proof['masterSha256']!=sha(source_master) or proof['builderSha256']!=sha(ROOT/'tools/build_floor.py'):raise RuntimeError('Stale finished source master')
        bpy.ops.wm.open_mainfile(filepath=str(source_master));objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
        fields=apply_materials(objects);wood=bake_wood(objects[0],lod,fields) if key.endswith('fallen_alder_limb') else None
        result=audit(objects)
        if any(result[k] for k in ('totalBoundaryEdges','totalMultiFaceEdges','totalLooseEdges')):raise RuntimeError('Export source topology failed')
        for obj in objects:
            uv_name='runtime_uv' if wood else 'source_uv';obj.data.calc_tangents(uvmap=uv_name)
            invalid=[loop.index for loop in obj.data.loops if loop.tangent.length<.99];obj.data.free_tangents()
            if invalid:raise RuntimeError(f'{obj.name} invalid source tangents: {invalid[:8]}')
        for image in bpy.data.images:
            if image.source in ('FILE','GENERATED'):image.pack()
        master=ROOT/'masters'/f'{key}_lod{lod}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(master))
        if wood:
            for obj in objects:
                obj.data.uv_layers.remove(obj.data.uv_layers['source_uv']);obj.data.uv_layers.active_index=0;obj.data.uv_layers[0].active_render=True
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0];target=ROOT/'runtime'/f'{key}_lod{lod}.glb'
        bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True,export_texcoords=True,export_normals=True)
        raw=target.read_bytes();length=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+length]);counts=[sum(doc['accessors'][p['indices']]['count']//3 for p in mesh['primitives']) for mesh in doc['meshes']]
        triangles=sum(counts[n['mesh']] for n in doc['nodes'] if 'mesh' in n)
        row={'level':lod,'model':target.name,'sha256':sha(target),'bytes':target.stat().st_size,'triangles':triangles,'materials':len(doc['materials']),'master':str(master.relative_to(ROOT)).replace('\\','/'),'master_sha256':sha(master),'source_master_sha256':sha(source_master),'source_receipt_sha256':sha(source_receipt),'bounds_z_up':result['bounds_z_up'],'source_audit':result}
        if wood:row['wood_projection']=wood
        record['lods'].append(row);record['lods'].sort(key=lambda row:row['level']);save(target_record,record)
        print('FLOOR_EXPORTED',key,lod,triangles,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default=','.join(SOURCE['assets']));parser.add_argument('--lods',default='0,1,2');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for key in args.assets.split(','):export(key,[int(x) for x in args.lods.split(',')])
