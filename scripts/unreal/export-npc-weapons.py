"""Extract existing authored guard equipment, retaining UVs and finished geometry."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'artifacts/unreal/npc-equipment'
SOURCE = ROOT/'authoring/blender/aegis-city-guards'
sys.path.insert(0, str(SOURCE/'tools'))
sys.path.insert(0, str(ROOT/'scripts/unreal'))
import build_guards
from world_static import read_glb, combine_parts


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    document = json.loads((ROOT/'migration/npc-equipment-sources.json').read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    records = {}
    for key, definition in document['weapons'].items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        build_guards.materials()
        source = ROOT/definition['source']
        if digest(source) != definition['sha256']: raise RuntimeError('Weapon authoring source changed: '+key)
        data = json.loads(source.read_text())
        data['parts'] = [part for part in data['parts'] if part['id'] in definition['parts']]
        if {part['id'] for part in data['parts']} != set(definition['parts']): raise RuntimeError('Weapon parts missing')
        collection, _ = build_guards.proof.load_sources(root=SOURCE,
            snapshots={source.name:json.dumps(data).encode()}, scene_data={'comparison_pose':{}})
        objects = []
        for obj in list(collection.all_objects):
            if obj.type != 'MESH': continue
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True,
                                                 depsgraph=bpy.context.evaluated_depsgraph_get())
            mesh.transform(Matrix.Translation(-Vector(definition['pivot'])) @ obj.matrix_world)
            copy = bpy.data.objects.new('weapon_'+obj['source_part'], mesh)
            bpy.context.scene.collection.objects.link(copy)
            objects.append(copy)
        for obj in list(bpy.data.objects):
            if obj not in objects: bpy.data.objects.remove(obj, do_unlink=True)
        bpy.ops.object.select_all(action='SELECT')
        glb = OUT/(key+'.glb')
        bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', export_animations=False,
            use_selection=True, export_extras=False)
        geometry = combine_parts(read_glb(glb)['parts'])
        # Parts with identical PBR bindings share a draw section; no source surfaces are discarded.
        materials, slots = [], {}
        remap = []
        for material in geometry['materials']:
            signature = json.dumps(material,sort_keys=True)
            if signature not in slots:
                slots[signature] = len(materials); materials.append(material)
            remap.append(slots[signature])
        geometry['materials'] = materials
        geometry['triangleMaterials'] = [remap[index] for index in geometry['triangleMaterials']]
        output = OUT/(key+'.json')
        output.write_text(json.dumps(geometry,separators=(',',':')))
        records[key] = {**definition,'glb':glb.relative_to(ROOT).as_posix(),'glbSha256':digest(glb),
                        'geometry':output.relative_to(ROOT).as_posix(),'geometrySha256':digest(output),
                        'triangles':len(geometry['indices'])//3}
    (OUT/'export.json').write_text(json.dumps({'schemaVersion':1,'weapons':records,
        'sourcesSha256':digest(ROOT/'migration/npc-equipment-sources.json'),'nativeArtApproved':False},indent=2)+'\n')
    print('WAR_NPC_WEAPONS_EXPORTED='+str(len(records)))


if __name__ == '__main__': main()
