"""Read actual ground beneath the isolated wing and end-tower footprints.

No Content is saved. The survey ignores only the exact owned architecture layer,
retains all underlying scenery, and checks its complete package closure afterward.
It is ground evidence, not structural, traversal or visual approval.
"""
import datetime
import json
import os
from pathlib import Path
import re
import sys

import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from aegis_citadel_blueprint import OUT,sha,validate
from shared_city_sources import package_file,protected_source_file
from world_actor_state import transform
from citadel_wing_support_evidence import survey_points,checked_ground_summary

revision=os.environ.get('WAR_CITADEL_INSPECT_REVISION','')
if not re.fullmatch('[a-f0-9]{12}',revision):
    raise RuntimeError('An explicit private citadel revision is required')
run=OUT/revision
candidate=json.loads((run/'candidate.json').read_text())
blueprint=json.loads((run/'blueprint.json').read_text())
validate(blueprint)
prefix='/Game/WorldRebuild/AegisCitadel_'+revision
if candidate['published'] or candidate['revision']!=revision or candidate['map']!=prefix+'/ReviewCandidate':
    raise RuntimeError('Survey requires the exact unpublished capital candidate')
expected={**candidate['sourceHashes'],**candidate['packageHashes']}


def package_hashes():
    return {p:sha(protected_source_file(ROOT,p,h) if p.startswith('/Engine/') else package_file(ROOT,p))
            for p,h in expected.items()}


if package_hashes()!=expected:
    raise RuntimeError('Preserve independently changed source or candidate packages')
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(candidate['map']):
    raise RuntimeError('Cannot load the isolated capital survey map')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
unreal.WarImportLibrary.prepare_world_preview_frame(world)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
layer=prefix+'/Layers/GothicCitadel'
ignored=[a for a in actors if a.get_outer().get_path_name().split('.')[0]==layer]
if not ignored:
    raise RuntimeError('The exact new architecture layer must be loaded before tracing')
points=survey_points()
rows=[]
hit_actors={}
for (x,y),regions in sorted(points.items()):
    hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,20000),
        unreal.Vector(x,y,-5000),unreal.TraceTypeQuery.ECC_VISIBILITY,True,ignored,
        unreal.DrawDebugTrace.NONE,True)
    values=hit.to_tuple() if hit else None
    row=dict(xCm=x,yCm=y,regions=regions,groundFound=bool(values and values[0]))
    if row['groundFound']:
        actor,component=values[9],values[10]
        if not actor or not component:
            raise RuntimeError('A blocking ground hit has no exact actor/component identity')
        mesh=component.static_mesh if isinstance(component,unreal.StaticMeshComponent) else None
        p,n=values[5],values[7]
        row.update(pointCm=[p.x,p.y,p.z],normal=[n.x,n.y,n.z],
            actor=actor.get_path_name(),component=component.get_path_name(),
            mesh=mesh.get_path_name() if mesh else None,
            gapBelowCurrentEditFloorCm=max(0,2400-p.z))
        hit_actors.setdefault(actor.get_path_name(),dict(actor=actor.get_path_name(),
            actorTransform=transform(actor.get_actor_transform()),
            hidden=bool(actor.get_editor_property('hidden')),
            package=actor.get_outer().get_path_name().split('.')[0]))
    rows.append(row)
if package_hashes()!=expected:
    raise RuntimeError('Native packages changed during the read-only support survey')
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
report=dict(schemaVersion=1,samplingVersion=2,revision=revision,signature=blueprint['signature'],
    map=candidate['map'],mapSha256=expected[candidate['map']],
    ignoredArchitectureLayer=layer,ignoredActors=sorted(a.get_path_name() for a in ignored),
    trace=dict(startZCm=20000,endZCm=-5000,channel='Visibility',complex=True),
    samples=rows,groundActors=list(hit_actors.values()),sourceAndCandidateHashesUnchanged=True,
    packageHashes=expected,diagnosticOnly=True,groundContactApproved=False,
    traversalApproved=False,visualApproved=False,published=False)
report['summary']=checked_ground_summary(report)
output=run/('wing-support-survey-'+stamp+'.json')
output.write_text(json.dumps(report,indent=2)+'\n')
unreal.log('WAR_CITADEL_WING_SUPPORT_SURVEY='+str(output))
