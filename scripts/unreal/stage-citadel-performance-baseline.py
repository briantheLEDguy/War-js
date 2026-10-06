"""Survey and stage an isolated crowd benchmark of the unchanged published city.

Only the new benchmark overlay may be saved. Original city, scenery, gameplay,
native models and legacy rounds are preserved. This receipt grants no admission.
Root serializes this commandlet with every other Unreal/Content writer.
"""
import json
import math
import os
import re
import sys
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from aegis_citadel_blueprint import digest, sha
from shared_city_sources import package_file, source_plan
from world_actor_state import snapshot
from citadel_stage_contract import OVERLAY_LIGHT_FIXTURES, expected_overlay_light

OUTPUT = ROOT / 'artifacts/unreal/aegis-citadel/performance-baseline'
CITY_PATH = '/Game/Cities/Shared/aegis_capital/City'
CITY_REVISION = '6ffd751f94efa5aa261779a6853262a6ca5128376c7a65a369e69943de9f6a2f'
SOURCE_MAP = '/Game/Capitals/Siege/AegisCapital_Siege'
FIXTURE_MODE = 'earned_progression'
NEGATIVE_FLAGS = ('progressionAcceptance', 'victoryAcceptance', 'conquestAcceptance',
                  'routeAcceptance', 'visualApproval', 'productionAdmission',
                  'steamAdmission', 'fullSiegeAdmission')
MODE = os.environ.get('WAR_CITADEL_BASELINE_MODE', 'survey')
if MODE not in ('survey', 'stage'):
    raise RuntimeError('Use explicit survey or stage mode')
OUTPUT.mkdir(parents=True, exist_ok=True)
city = next(row for row in source_plan(ROOT)['cities'] if row['id'] == 'aegis_capital')
if city['definition'] != CITY_PATH or city['revision'] != CITY_REVISION:
    raise RuntimeError('Benchmark baseline requires the unchanged published Aegis city')
source_hashes = {**city['packageHashes'], SOURCE_MAP: sha(package_file(ROOT, SOURCE_MAP))}
expected = {**source_hashes, **city['dependencyHashes']}

def native_package_file(package):
    if package.startswith('/Game/'):
        return package_file(ROOT,package)
    if not re.fullmatch(r'/Engine/[A-Za-z0-9_/-]+',package) or '..' in package:
        raise RuntimeError('Invalid native baseline package identity: '+package)
    content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.engine_content_dir())).resolve()
    base = (content/package[8:]).resolve()
    base.relative_to(content)
    for extension in ('.uasset','.umap'):
        file=base.with_suffix(extension)
        if file.is_file():return file
    raise RuntimeError('Missing actual original engine dependency: '+package)

# The published receipt binds project scenery dependencies. The benchmark also
# binds unchanged engine content and gameplay references used by its copied overlay.
registry = unreal.AssetRegistryHelpers.get_asset_registry()
options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
    include_hard_package_references=True,include_searchable_names=False,
    include_soft_management_references=False,include_hard_management_references=False)
pending = list(source_hashes)
visited = set()
while pending:
    package = pending.pop()
    if package in visited:continue
    visited.add(package)
    if len(visited)>8192:raise RuntimeError('Original baseline package closure exceeds bound')
    if package not in expected:
        source_hashes[package]=sha(native_package_file(package))
        expected[package]=source_hashes[package]
    for child in registry.get_dependencies(package,options):
        child=str(child)
        if child.startswith(('/Game/','/Engine/')):pending.append(child)

def check_sources():
    for package, expected_hash in expected.items():
        if sha(native_package_file(package)) != expected_hash:
            raise RuntimeError('Preserve independently edited source package: ' + package)

def point(value):
    return [value.x, value.y, value.z]

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets = unreal.EditorAssetLibrary
if not levels.load_level(SOURCE_MAP):
    raise RuntimeError('Published baseline siege overlay is unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
unreal.WarImportLibrary.prepare_world_preview_frame(world)
fields = [actor for actor in actors.get_all_level_actors() if isinstance(actor, unreal.WarSiegeBattlefield)
          and actor.get_outer().get_path_name().split('.')[0] == SOURCE_MAP]
if len(fields) != 1:
    raise RuntimeError('Original native battlefield identity is ambiguous')
field = fields[0]
layout = {name: [point(p) for p in field.get_editor_property(property_name)]
          for name, property_name in [('objectives', 'objectives'),
                                     ('optionalObjectives', 'optional_objectives'),
                                     ('teamSpawns', 'team_spawns')]}
if [len(layout[name]) for name in ('objectives', 'optionalObjectives', 'teamSpawns')] != [8, 3, 6]:
    raise RuntimeError('Original eight-position native battlefield is required')

def standing_point(p):
    start = unreal.Vector(p[0], p[1], p[2] + 25)
    end = unreal.Vector(p[0], p[1], p[2] - 25)
    trace = unreal.SystemLibrary.line_trace_single(world, start, end,
        unreal.TraceTypeQuery.ECC_VISIBILITY, True, [], unreal.DrawDebugTrace.NONE, True)
    hit = trace.to_tuple() if trace else None
    floor = point(hit[5]) if hit and hit[0] else None
    normal = point(hit[7]) if floor else None
    clear = False
    blocker = None
    if floor and normal[2] >= math.sqrt(.5):
        center = unreal.Vector(p[0], p[1], floor[2] + 101)
        capsule = unreal.SystemLibrary.capsule_trace_single(world, center, center + unreal.Vector(0,0,1),
            42, 96, unreal.TraceTypeQuery.ECC_VISIBILITY, True, [], unreal.DrawDebugTrace.NONE, True)
        obstruction = capsule.to_tuple() if capsule else None
        clear = not obstruction or not obstruction[0]
        blocker = obstruction[9].get_path_name() if obstruction and obstruction[0] and obstruction[9] else None
    return dict(point=p, actualFloor=floor, normal=normal, capsuleClear=clear,
                capsuleRadiusCm=42, capsuleHalfHeightCm=96, blocker=blocker,
                floorClear=bool(floor and normal[2] >= math.sqrt(.5)), navigationVerified=False,
                visualExposureVerified=False)

if MODE == 'survey':
    # Proposed positions are diagnostic until every individual native standing point clears.
    specs = [(0, [-14625,-150,10], [-14625,-150,3500]),
             (1, [15160,0,4210], [13600,0,7000]),
             (2, [19800,-1200,4210], [16850,0,5500])]
    formations = []
    for stage, center, eye in specs:
        points = ([[ -15450+column*150, -300+row*150, 10] for row in range(3) for column in range(12)]
                  if stage==0 else [[center[0] + (column - 2.5) * 160, center[1] + (row - 2.5) * 160, center[2]]
                  for row in range(6) for column in range(6)])
        pool = ([[19000+column*160,-1800+row*160,4210] for row in range(12) for column in range(9)]
                if stage==2 else points)
        excluded=[layout['objectives'][i] for i in ([0,1,2,3] if stage==0 else [4,5,6] if stage==1 else [7])]
        excluded.append(layout['optionalObjectives'][stage])
        candidates=[]
        for p in pool:
            witness=standing_point(p)
            witness['captureExclusion']=all(math.dist(p[:2],q[:2])>=700 for q in excluded)
            ray=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(*eye),unreal.Vector(p[0],p[1],p[2]+120),
                unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,True)
            values=ray.to_tuple() if ray else None
            # The source overlay has closed gates. The benchmark later earns
            # their opening through normal capture; this ray proves neither state.
            witness['sourceClosedGateCameraLineOfSightClear']=not values or not values[0]
            candidates.append(witness)
        formations.append(dict(id='preserved_city_stage_' + str(stage), stage=stage,
            minimumCaptureGapCm=50, positions=points,
            camera=dict(eye=eye, target=[center[0],center[1],center[2]+100], horizontalFovDegrees=68),
            standingPoints=[standing_point(p) for p in points], candidatePool=candidates,
            nativeFloorAndTraversalVerified=False))
    check_sources()
    diagnostic = dict(schemaVersion=1, diagnosticOnly=True, passed=False, readOnly=True,
        fixtureMode=FIXTURE_MODE, isolatedStageWindows=False,
        sourceCity=dict(path=CITY_PATH, revision=CITY_REVISION), sourceHashes=source_hashes,
        dependencyHashes=city['dependencyHashes'], **layout, performanceFormations=formations,
        sourceHashesUnchanged=True, **{flag: False for flag in NEGATIVE_FLAGS})
    output = OUTPUT / 'survey.json'
    output.write_text(json.dumps(diagnostic, indent=2) + '\n')
    unreal.log('WAR_CITADEL_PERFORMANCE_BASELINE_SURVEY=' + str(output))
else:
    plan_file = OUTPUT / 'plan.json'
    plan = json.loads(plan_file.read_text(encoding='utf-8-sig'))
    if plan.get('fixtureMode') != FIXTURE_MODE or plan.get('sourceCity') != dict(path=CITY_PATH, revision=CITY_REVISION) or any(
            plan.get(name) != value for name, value in layout.items()):
        raise RuntimeError('Fresh baseline plan must preserve the actual original anchor/spawn positions')
    formations = plan.get('performanceFormations', [])
    if len(formations) != 3 or {f['stage'] for f in formations} != {0,1,2}:
        raise RuntimeError('Three signed functional stage formations are required')
    for formation in formations:
        if len(formation['positions']) != 36 or formation['minimumCaptureGapCm'] != 50:
            raise RuntimeError('Each stage needs exactly36 independently checked crowd positions')
        camera=formation.get('camera',{})
        if camera.get('horizontalFovDegrees')!=68 or any(
                not isinstance(camera.get(name),list) or len(camera[name])!=3 or
                any(not isinstance(value,(int,float)) or not math.isfinite(value) for value in camera[name])
                for name in ('eye','target')):
            raise RuntimeError('Actual functional baseline camera must be signed explicitly')
        excluded = [layout['objectives'][i] for i in ([0,1,2,3] if formation['stage']==0 else [4,5,6] if formation['stage']==1 else [7])]
        excluded.append(layout['optionalObjectives'][formation['stage']])
        for index, p in enumerate(formation['positions']):
            witness = standing_point(p)
            if not witness['floorClear'] or not witness['capsuleClear'] or any(
                    math.dist(p[:2], q[:2]) < 700 for q in excluded) or any(
                    math.dist(p[:2], q[:2]) < 134 for q in formation['positions'][index+1:]):
                raise RuntimeError('Baseline formation has an obstructed, overlapping or capture-ring position: ' + str(witness))
    payload = dict(fixtureMode=FIXTURE_MODE, sourceCity=dict(path=CITY_PATH, revision=CITY_REVISION),
        sourceHashes=source_hashes, dependencyHashes=city['dependencyHashes'], **layout,
        performanceFormations=formations)
    signature_payload = canonical(payload)
    import hashlib
    signature = hashlib.sha256(signature_payload.encode('utf-8')).hexdigest()
    revision = signature[:12]
    run = OUTPUT / revision
    destination = '/Game/WorldRebuild/AegisCitadel_' + revision + '/PerformanceBaseline'
    check_sources()
    if assets.does_asset_exist(destination) or (run/'baseline.json').exists():
        raise RuntimeError('Existing baseline staging must be inspected and preserved; no replacement')
    run.mkdir(parents=True, exist_ok=True)
    journal = run/'pending.json'
    journal.write_text(json.dumps(dict(destination=destination, signature=signature,
        sourceHashes=expected, visualApproval=False), indent=2)+'\n')
    if not assets.duplicate_asset(SOURCE_MAP, destination) or not levels.load_level(destination):
        raise RuntimeError('Cannot create isolated baseline gameplay overlay')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    if not levels.set_current_level_by_name('PerformanceBaseline'):
        raise RuntimeError('Cannot select exact baseline overlay owner')
    owned = [a for a in actors.get_all_level_actors() if a.get_outer().get_path_name().split('.')[0]==destination]
    field = next(a for a in owned if isinstance(a,unreal.WarSiegeBattlefield))
    field.set_editor_property('definition_version',2)
    field.set_editor_property('city_definition',assets.load_asset(CITY_PATH))
    field.set_editor_property('reviewed_city_revision','')
    for property_name in ('traversal_reviewed','lower_city_reviewed','equipped_roster_reviewed'):
        field.set_editor_property(property_name,False)
    field.tags = [*field.tags,'WarCitadelPerformanceBaseline']
    removed_lights = []
    for name in OVERLAY_LIGHT_FIXTURES:
        matches = [a for a in owned if a.get_name()==name]
        if len(matches)!=1 or not expected_overlay_light(name,snapshot(matches[0])):
            raise RuntimeError('Unknown original benchmark overlay environment fixture: '+name)
        removed_lights.append(dict(actor=matches[0].get_path_name(),sourceStateHash=digest(snapshot(matches[0]))))
        if not actors.destroy_actor(matches[0]):
            raise RuntimeError('Cannot remove exact duplicate baseline overlay lighting')
    if not levels.save_current_level():
        raise RuntimeError('Cannot save new isolated performance baseline')
    check_sources()
    native_city = field.get_editor_property('city_definition')
    native = dict(actor=field.get_path_name(),definitionVersion=field.get_editor_property('definition_version'),
        cityDefinition=native_city.get_path_name(),cityRevision=native_city.get_editor_property('revision'))
    if native['definitionVersion']!=2 or native['cityRevision']!=CITY_REVISION:
        raise RuntimeError('Native baseline owner or city definition differs after saving')
    receipt = dict(schemaVersion=1, performanceBaseline=True, isolatedStageWindows=False,
        revision=revision, signature=signature, signaturePayload=signature_payload,
        map=destination, geometrySignature=CITY_REVISION, packageHashes={destination:sha(package_file(ROOT,destination))},
        nativeImported=True, stageBaselineRecipeSha256=sha(Path(__file__)), sourceHashesUnchanged=True,
        nativeBattlefield=native, removedOverlayLights=removed_lights, sourceCityRevisionPayload=city.get('revisionPayload'),
        **payload, **{flag:False for flag in NEGATIVE_FLAGS})
    (run/'baseline.json').write_text(json.dumps(receipt,indent=2)+'\n')
    journal.rename(run/'completed.json')
    unreal.log('WAR_CITADEL_PERFORMANCE_BASELINE_STAGED='+str(run/'baseline.json'))
