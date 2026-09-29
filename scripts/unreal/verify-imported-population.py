"""Sample supplied NPC poses and materials before any live population mutation."""
import json
import math
import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from imported_population import ROOT, OUT, LEDGER, digest, models, verify_sources

verify_sources()
sets = json.loads((OUT/'presentations.json').read_text())['profiles']
installed = json.loads((OUT/'installed.json').read_text())
failures, reports, packages = [], {}, {}
for row in models().values():
    profile = row['profile']; entry = sets[profile]
    mesh = unreal.load_asset(entry['mesh'])
    options = []
    for kind in (unreal.AnimDataEvalType.RAW,unreal.AnimDataEvalType.COMPRESSED):
        opt = unreal.AnimPoseEvaluationOptions()
        opt.set_editor_properties(dict(optional_skeletal_mesh=mesh,evaluation_type=kind)); options.append(opt)
    observations = []
    for path in sorted(set(entry['bindings'].values())):
        clip = unreal.load_asset(path)
        if not clip or clip.get_editor_property('skeleton') != mesh.skeleton: raise RuntimeError('Wrong skeleton: '+path)
        duration = unreal.AnimationLibrary.get_sequence_length(clip)
        error, stretch = 0., 0.
        for fraction in (0,.25,.5,.75,1):
            raw, compressed = [unreal.AnimPoseExtensions.get_anim_pose_at_time(clip,duration*fraction,opt) for opt in options]
            for name in unreal.AnimPoseExtensions.get_bone_names(raw):
                a,b = [unreal.AnimPoseExtensions.get_bone_pose(p,name,unreal.AnimPoseSpaces.WORLD) for p in (raw,compressed)]
                error = max(error,(a.translation-b.translation).length())
                local = unreal.AnimPoseExtensions.get_bone_pose(raw,name,unreal.AnimPoseSpaces.LOCAL)
                if not all(math.isfinite(v) for v in (local.translation.x,local.translation.y,local.translation.z,local.scale3d.x,local.rotation.w)):
                    failures.append(profile+': non-finite pose')
                if str(name) not in ('root','hips'):
                    ref = unreal.AnimPoseExtensions.get_ref_bone_pose(raw,name,unreal.AnimPoseSpaces.LOCAL)
                    stretch = max(stretch,abs(local.translation.length()-ref.translation.length()))
        if error > .25 or stretch > .005 or duration <= 0:
            failures.append(profile+': invalid sampled motion '+path)
        observations.append(dict(path=path,compressionErrorCm=error,localLimbLengthDelta=stretch,duration=duration))
    for asset_path in [entry['mesh'],installed['profiles'][profile]['visual'],*entry['bindings'].values()]:
        package = ROOT/'unreal/AegisWar/Content'/(asset_path.split('.')[0].removeprefix('/Game/')+'.uasset')
        packages[asset_path] = digest(package)
    reports[profile] = observations
for folder in [installed['catalog'].split('.')[0], *{r['mesh'].rsplit('/',1)[0] for r in installed['profiles'].values()}]:
    paths = unreal.EditorAssetLibrary.list_assets(folder,recursive=True) if not folder.endswith('StagedLoadouts') else [installed['catalog']]
    for asset_path in paths:
        package = ROOT/'unreal/AegisWar/Content'/(asset_path.split('.')[0].removeprefix('/Game/')+'.uasset')
        packages[asset_path] = digest(package)
report = dict(schemaVersion=1,ledgerSha256=digest(LEDGER),installedSha256=digest(OUT/'installed.json'),
    profiles=reports,packages=packages,failures=failures,structuralChecksPassed=not failures,
    nativeVisualVerified=False,gameplayVerified=False)
(OUT/'technical-verification.json').write_text(json.dumps(report,indent=2)+'\n')
if failures: raise RuntimeError('\n'.join(failures))
