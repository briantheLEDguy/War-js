"""Explicit dielectric adaptations for legacy Phong clothing; retain supplied image bytes."""
import importlib.util
import json
import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from imported_population import ROOT, OUT, ledger

spec=importlib.util.spec_from_file_location('source_materials',Path(__file__).with_name('import-models.py'))
source_materials=importlib.util.module_from_spec(spec); spec.loader.exec_module(source_materials)
bodies=json.loads((OUT/'bodies.json').read_text())['profiles']
for row in ledger()['models']:
    overrides=row.get('materialOverrides')
    if not overrides: continue
    body=bodies[row['profile']]
    gltf,images=source_materials.read_glb(ROOT/body['source'])
    if set(overrides)-{m['name'] for m in gltf['materials']}: raise RuntimeError('Adapted source material disappeared')
    for material in gltf['materials']:
        if material['name'] in overrides:
            correction=overrides[material['name']]
            material['pbrMetallicRoughness'].update(metallicFactor=correction['metallic'],roughnessFactor=correction['roughness'])
            material.setdefault('extensions',{})['KHR_materials_specular']={'specularColorFactor':[1,1,1]}
    folder=body['mesh'].rsplit('/',1)[0]
    textures={i['index']:unreal.load_asset(folder+'/Textures/T_%03d_'%i['index']+source_materials.safe_name(i['name'])) for i in images}
    if any(not t for t in textures.values()): raise RuntimeError('Source texture missing during material adaptation')
    context=dict(profile=row['profile'],gltf=gltf,destination=folder,
        conversion=dict(kind='characterProfiles',sourceSha256=body['sourceSha256']))
    materials,_=source_materials.create_materials(unreal,context,textures)
    for name,material in materials.items():
        unreal.EditorAssetLibrary.set_metadata_tag(material,'WarPopulationMaterialAdaptation',json.dumps(overrides.get(name,{}),sort_keys=True))
        if not unreal.EditorAssetLibrary.save_loaded_asset(material,False): raise RuntimeError('Material adaptation save failed')
