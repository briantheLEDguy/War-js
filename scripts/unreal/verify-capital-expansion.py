"""Fresh-process saved-scene verification, separate from rendered walking proof."""
import hashlib
import json
from pathlib import Path
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_expansion import ZONES, validate_plan, require_unchanged, canonical_actor_state
from world_actor_state import snapshot
OUT=ROOT/'artifacts/unreal/capital-expansion'
receipt=json.loads((OUT/'applied.json').read_text())
baseline=json.loads((OUT/'baseline.json').read_text())
plan=json.loads((OUT/'plan.json').read_text());validate_plan(plan)
(OUT/'saved-scene.json').write_text(json.dumps({'passed':False,'stage':'verification running','planSignature':plan['signature']})+'\n')
require_unchanged(receipt['planSignature'],plan['signature'])
for p,expected in receipt['packageHashes'].items():
    file=ROOT/'unreal/AegisWar/Content'/(p.removeprefix('/Game/')+'.umap')
    require_unchanged(expected,hashlib.sha256(file.read_bytes()).hexdigest())
build=json.loads((ROOT/'artifacts/unreal/world-portals/build.json').read_text())
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(build['map']): raise RuntimeError('World missing')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
preserved=0;added=0;palette=0
edits={(r['package'],r['actor']):r for r in receipt['paletteEdits']}
replacements=json.loads((OUT/'replacements.json').read_text())['edits'] if (OUT/'replacements.json').exists() else []
edits.update({(r['package'],r['actor']):r for r in replacements})
for zone in ZONES:
    packages=set(baseline[zone]['levels'].values())
    current={(a.get_outer().get_path_name().split('.')[0],a.get_name()):a for a in actors if a.get_outer().get_path_name().split('.')[0] in packages}
    for row in baseline[zone]['actors']:
        if (row['package'],row['name']) not in current: raise RuntimeError('Original actor disappeared: '+row['name'])
        expected=edits[(row['package'],row['name'])]['after'] if zone=='aegis_capital' and (row['package'],row['name']) in edits else row['state']
        require_unchanged(canonical_actor_state(expected),canonical_actor_state(snapshot(current[(row['package'],row['name'])])))
        preserved+=1
    for row in receipt['added']:
        if row['zone']!=zone: continue
        if (row['package'],row['actor']) not in current: raise RuntimeError('Expansion actor missing: '+row['id'])
        actor=current[(row['package'],row['actor'])]
        actual=snapshot(actor)
        if canonical_actor_state(row['state'])!=canonical_actor_state(actual):
            (OUT/'saved-scene-mismatch.json').write_text(json.dumps({'id':row['id'],'expected':row['state'],'actual':actual},indent=2)+'\n')
            raise RuntimeError('Saved expansion actor changed: '+row['id'])
        if row.get('attachedTo'):
            parent=next(r for r in receipt['added'] if r['id']==row['attachedTo'])
            if actor.get_attach_parent_actor()!=current[(parent['package'],parent['actor'])]:
                raise RuntimeError('Interior light lost its building attachment')
        if isinstance(actor,unreal.StaticMeshActor):
            mesh=actor.static_mesh_component.static_mesh
            if not mesh or mesh.get_num_lods()<3: raise RuntimeError('Missing mesh or LODs')
            if str(actor.static_mesh_component.get_collision_profile_name())!='BlockAll': raise RuntimeError('Building collision lost')
        added+=1
report={'schemaVersion':1,'passed':True,'originalActorsPreserved':preserved,
        'expansionActorsVerified':added,'existingHousesRecolored':len(edits),
        'newBuildings':len(plan['placements']),'newInteriors':sum(p['interior'] for p in plan['placements']),
        'existingHousesRecomposed':len(replacements),
        'visualApproved':False,'nativeWalkingVerified':False}
(OUT/'saved-scene.json').write_text(json.dumps(report,indent=2)+'\n')
unreal.log('WAR_EXPANSION_RELOADED='+str(report))
