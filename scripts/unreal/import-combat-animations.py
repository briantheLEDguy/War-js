"""Import isolated native review assets and verify raw/compressed pose parity.

Run with UnrealEditor-Cmd -run=pythonscript -script=<this file> -nullrhi.
Does not add these unapproved assets to the gameplay visual admission registry.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/combat-animation'
(OUT/'native-import.json').unlink(missing_ok=True)


def module(name, filename):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(filename))
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


imports=module('combat_import_helpers','import-models.py')
parity=module('combat_pose_parity','pose_parity.py')
motion_audit=module('combat_motion_audit','combat_motion_audit.py')
unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
records={}
for character in ('prelate','ember'):
    folder=OUT/character
    build=json.loads((folder/'build.json').read_text())
    fbx=folder/'choreography.fbx'
    imports.require(hashlib.sha256(fbx.read_bytes()).hexdigest()==build['fbxSha256'],'Stale combat FBX')
    source=ROOT/build['source']
    imports.require(hashlib.sha256(source.read_bytes()).hexdigest()==build['sourceSha256'],'Source model changed')
    for name,digest in build['dependencies'].items():
        imports.require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'Equipped source changed: '+name)
    if character=='prelate':
        clearance=json.loads((folder/'clearance.json').read_text())
        imports.require(clearance['passed'] and clearance['fbxSha256']==build['fbxSha256'],
                        'Hammer/body clearance has not passed for this exact bake')
    gltf,images=imports.read_glb(folder/'choreography.glb')
    # Versioned destinations keep prior review assets and unrelated work intact.
    version=build['fbxSha256'][:12]
    context={'profile':'combat_'+character,'directory':folder,'destination':f'/Game/Imported/ThematicCombat/{character}_{version}',
             'fbx':fbx,'gltf':gltf,'images':images,
             'conversion':{'kind':'characterProfiles','sourceSha256':build['sourceSha256'],
                           'verification':{'bakeFramesPerSecond':120}}}
    imports.import_mesh(unreal,context)
    textures,_=imports.import_textures(unreal,context)
    materials,_=imports.create_materials(unreal,context,textures)
    assets=imports.collect_assets(unreal,context)
    meshes=[a for a in assets if isinstance(a,unreal.SkeletalMesh)]
    imports.require(len(meshes)==1,'Expected one complete authored character')
    mesh=meshes[0]
    mapping=imports.material_slot_mapping(materials)
    slots=list(mesh.get_editor_property('materials'))
    for slot in slots:
        name=str(slot.get_editor_property('imported_material_slot_name'))
        original=name if name in materials else mapping.get(name)
        imports.require(original in materials,'Unmapped authored material: '+name)
        slot.set_editor_property('material_interface',materials[original])
    mesh.set_editor_property('materials',slots)
    animations=[]
    for asset in assets:
        if not isinstance(asset,unreal.AnimSequence): continue
        name=unreal.WarImportLibrary.get_source_animation_name(asset)
        animations.append({'path':asset.get_path_name(),'sourceClipName':name})
    expected={row['id'] for row in build['clips']}
    imports.require(len(animations)==len(expected) and {row['sourceClipName'] for row in animations}==expected,'Missing or duplicate combat clips')
    imports.configure_animation_compression(unreal,context,True)
    samples=json.loads((folder/'samples.json').read_text())
    whole_body={name:motion_audit.audit_samples(clip['samples']) for name,clip in samples.items()}
    if character=='prelate':
        whole_body['prelate_sunfall']['heavyWeaponPath']=motion_audit.audit_heavy_path(samples['prelate_sunfall']['samples'])
    evidence=parity.verify_animations(unreal,animations,samples)
    for asset in imports.collect_assets(unreal,context):
        unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
    records[character]={'mesh':mesh.get_path_name(),'animations':animations,'poseParity':evidence,'wholeBody':whole_body,'build':build}
(OUT/'native-import.json').write_text(json.dumps({'characters':records,'visualApproval':False},indent=2)+'\n')
unreal.log('THEMATIC_COMBAT_IMPORT_PASSED')
