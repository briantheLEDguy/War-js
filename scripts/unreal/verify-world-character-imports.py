"""Recheck placed campaign characters' saved raw/compressed clips in a fresh process."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT/'artifacts/unreal/world-portals'
build = json.loads((directory/'build.json').read_text())
spec = importlib.util.spec_from_file_location('war_imports',Path(__file__).with_name('import-models.py'))
imports = importlib.util.module_from_spec(spec); spec.loader.exec_module(imports)
spec = importlib.util.spec_from_file_location('war_pose',Path(__file__).with_name('pose_parity.py'))
parity = importlib.util.module_from_spec(spec); spec.loader.exec_module(parity)
bindings = {row['profileKey']:row for row in imports.load_json(imports.VISUAL_REGISTRY)['entries']}
results = []
for profile in sorted({row['profile'] for row in build['gameplay'] if row['kind'] in ('npc','enemy')}):
    context = imports.validate_inputs(profile)
    receipt_file = context['directory']/'editor-import.json'
    receipt = imports.load_json(receipt_file)
    binding = bindings[profile]
    if (not receipt['importSucceeded'] or receipt['conversionSha256']!=context['conversionSha256']
            or receipt['sourceSha256']!=binding['sourceSha256']
            or receipt['meshes'][0]['path']!=binding['skeletalMeshPath']
            or sorted(a['path'] for a in receipt['animations'])!=sorted(binding['animationPaths'])):
        raise RuntimeError('Stale native character binding: '+profile)
    unreal.WarImportLibrary.prepare_preview_frame(None)
    evidence = parity.verify_animations(unreal,receipt['animations'],imports.load_json(context['samples'])['source'])
    packages = [binding['skeletalMeshPath'],*binding['animationPaths']]
    hashes = {path:hashlib.sha256((ROOT/'unreal/AegisWar/Content'/
        (path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest() for path in packages}
    results.append({'profile':profile,'sourceSha256':binding['sourceSha256'],
        'importReceiptSha256':hashlib.sha256(receipt_file.read_bytes()).hexdigest(),
        'packageHashes':hashes,'poseParity':evidence})
    unreal.log('WAR_SAVED_CHARACTER_VERIFIED='+profile)
(directory/'character-verification.json').write_text(json.dumps({'profiles':results,'visualApproved':False},indent=2)+'\n')
unreal.log('WAR_SAVED_CHARACTERS_VERIFIED='+str(len(results)))
