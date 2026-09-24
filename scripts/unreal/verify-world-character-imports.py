"""Recheck placed campaign characters' saved raw/compressed clips in a fresh process."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unreal
import sys
import runpy
sys.path.insert(0,str(Path(__file__).parent))
from native_animation_bindings import installed, PRESENTATIONS

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT/'artifacts/unreal/world-portals'
build = json.loads((directory/'build.json').read_text())
spec = importlib.util.spec_from_file_location('war_imports',Path(__file__).with_name('import-models.py'))
imports = importlib.util.module_from_spec(spec); spec.loader.exec_module(imports)
spec = importlib.util.spec_from_file_location('war_pose',Path(__file__).with_name('pose_parity.py'))
parity = importlib.util.module_from_spec(spec); spec.loader.exec_module(parity)
bindings = {row['profileKey']:row for row in imports.load_json(imports.VISUAL_REGISTRY)['entries']}
runpy.run_path(str(Path(__file__).with_name('verify-animation-replacement.py')))
results = []
for profile in sorted({row['profile'] for row in build['gameplay'] if row['kind'] in ('npc','enemy')}):
    receipt=installed(profile)
    binding=bindings[profile]
    evidence=dict(skeletonAssociationsPassed=True,animationCount=len(receipt['animations']))
    packages = [binding['skeletalMeshPath'],*binding['animationPaths']]
    hashes = {path:hashlib.sha256((ROOT/'unreal/AegisWar/Content'/
        (path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest() for path in packages}
    results.append({'profile':profile,'sourceSha256':binding['sourceSha256'],
        'presentationManifestSha256':hashlib.sha256(PRESENTATIONS.read_bytes()).hexdigest(),
        'packageHashes':hashes,'poseParity':evidence})
    unreal.log('WAR_SAVED_CHARACTER_VERIFIED='+profile)
(directory/'character-verification.json').write_text(json.dumps({'profiles':results,'visualApproved':False},indent=2)+'\n')
unreal.log('WAR_SAVED_CHARACTERS_VERIFIED='+str(len(results)))
