"""Survey saved native ground and produce a collision-aware expansion placement plan."""
import hashlib
import json
from pathlib import Path
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_expansion import ZONES, plan_city, rectangle, validate_plan, digest, require_unchanged
OUT=ROOT/'artifacts/unreal/capital-expansion'


def main():
    baseline=json.loads((OUT/'baseline.json').read_text())
    assets=json.loads((OUT/'assets.json').read_text())
    if len(assets['templates'])!=72: raise RuntimeError('All 72 building templates are required')
    for zone in ZONES:
        current={p:hashlib.sha256((ROOT/'unreal/AegisWar/Content'/(p.removeprefix('/Game/')+'.umap')).read_bytes()).hexdigest()
                 for p in baseline[zone]['hashes']}
        require_unchanged(baseline[zone]['hashes'],current)
    build=json.loads((ROOT/'artifacts/unreal/world-portals/build.json').read_text())
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(build['map']): raise RuntimeError('World missing')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    unreal.WarImportLibrary.prepare_world_preview_frame(world)
    plan={'schemaVersion':1,'baselineSha256':hashlib.sha256((OUT/'baseline.json').read_bytes()).hexdigest(),
          'assetsSha256':hashlib.sha256((OUT/'assets.json').read_bytes()).hexdigest(),
          'placements':[],'failed':{},'nativeGroundSurveyed':True,'visualApproved':False}
    for zone in ZONES:
        origin=baseline[zone]['origin']; cache={}
        def support(xy,yaw,template,expected):
            polygon=rectangle(xy,[max(20,e*2-80) for e in template['extent'][:2]],yaw)
            heights=[]
            for px,py in [xy,*polygon]:
                key=tuple(round(v,1) for v in (px,py,expected))
                if key not in cache:
                    hit=unreal.SystemLibrary.line_trace_single(world,
                        unreal.Vector(origin[0]+px,origin[1]+py,expected+350),
                        unreal.Vector(origin[0]+px,origin[1]+py,expected-350),
                        unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,True)
                    parts=hit.to_tuple() if hit else None
                    cache[key]=parts[5].z if parts and parts[0] and parts[7].z>.8 else None
                if cache[key] is None: return None
                heights.append(cache[key])
            if max(heights)-min(heights)>45: return None
            return max(heights)+2
        source=json.loads((ROOT/'public/assets/maps'/(zone+'.json')).read_text())
        rows,failed=plan_city(zone,source,baseline[zone],assets['templates'],support)
        plan['placements'].extend(rows);plan['failed'][zone]=failed
        unreal.log('WAR_EXPANSION_SURVEY='+zone+':'+str(len(rows)))
        (OUT/'plan-candidate.json').write_text(json.dumps(plan,indent=2)+'\n')
    validate_plan(plan)
    plan['signature']=digest(plan)
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    unreal.log('WAR_EXPANSION_PLANNED='+str(len(plan['placements'])))


main()
