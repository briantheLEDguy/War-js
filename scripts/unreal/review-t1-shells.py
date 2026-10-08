"""Read-only native eave ray witnesses, bound to frozen parent and repaired homes."""
import json
from pathlib import Path
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from t1_materials import protected_saved, verify_protected, sha, same_state
from t1_material_clone import inventory
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'
receipt=json.loads((DIRECTORY/'shells-latest.json').read_text())
parent=json.loads((DIRECTORY/'atmosphere-latest.json').read_text())
if receipt['study']!='home-shell-refit' or parent['signature']!=receipt['inputs']['parentAtmosphereSignature']:
    raise RuntimeError('Shell review requires its frozen atmosphere parent')
protected=protected_saved(ROOT)
verify_protected(ROOT,receipt['inputs']['protectedHashes'])
for file,digest in {**receipt['inputs']['sourceHashes'],**receipt['inputs']['tools'],**receipt['inputs']['parentAssetHashes'],**receipt['assetHashes']}.items():
    if sha(ROOT/file)!=digest: raise RuntimeError('Shell inputs, binaries or assets changed')
for package,digest in receipt['inputs']['dependencyHashes'].items():
    if sha(ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.uasset'))!=digest:
        raise RuntimeError('Frozen kit dependency changed')
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
checks=[]
try:
    for label,study in [('parent',parent),('refit',receipt)]:
        for zone in study['zones']:
            if not levels.load_level(zone['map']): raise RuntimeError('Shell witness map unavailable')
            world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
            if not same_state(inventory(actors),zone['actorInventory']): raise RuntimeError('Saved shell inventory changed')
            for home in zone['homes']:
                house=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==home['id'])
                transform=house.get_actor_transform(); probes=receipt['templates'][home['template']]['seamProbes']
                rows=[]
                for probe in probes:
                    start=transform.transform_location(unreal.Vector(*probe['start']))
                    end=transform.transform_location(unreal.Vector(*probe['end']))
                    hit=unreal.SystemLibrary.line_trace_single(world,start,end,unreal.TraceTypeQuery.ECC_VISIBILITY,
                        True,[],unreal.DrawDebugTrace.NONE,True)
                    parts=hit.to_tuple() if hit else None
                    blocked=bool(parts and parts[0] and parts[9]==house)
                    rows.append({**probe,'blockedByHome':blocked,'blocker':parts[9].get_actor_label() if parts and parts[0] and parts[9] else None})
                checks.append(dict(study=label,zone=zone['id'],home=home['id'],probes=rows,
                                   openEaveRays=sum(not r['blockedByHome'] for r in rows)))
finally:
    verify_protected(ROOT,protected)
for package,digest in {**receipt['inputs']['parentPackages'],**receipt['packageHashes']}.items():
    if sha(ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap'))!=digest:
        raise RuntimeError('Shell review changed a saved candidate')
refits=[c for c in checks if c['study']=='refit']; originals=[c for c in checks if c['study']=='parent']
result=dict(signature=receipt['signature'],checks=checks,openParentRays=sum(c['openEaveRays'] for c in originals),
    openRefitRays=sum(c['openEaveRays'] for c in refits),savedCandidatesUnchanged=True,
    visualApproved=False,roofLodAppearanceAccepted=False,cameraAccepted=False,walkDriveAccepted=False)
result['seamRaysClosed']=len(refits)==4 and result['openRefitRays']==0
(DIRECTORY/'shell-seam-review.json').write_text(json.dumps(result,indent=2)+'\n')
unreal.log('WAR_T1_SHELL_SEAMS='+str(result['openParentRays'])+'->'+str(result['openRefitRays']))
if not result['seamRaysClosed']: raise RuntimeError('Open roof rays remain; inspect native geometry and pictures')
