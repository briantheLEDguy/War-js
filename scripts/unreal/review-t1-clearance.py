"""Read-only native obstacle sweeps. This is neither walking nor driving acceptance."""
import hashlib
import json
import math
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from t1_clearance import clearance_routes, segment_samples

DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
receipt = json.loads((DIRECTORY/'native-latest.json').read_text())
plan = json.loads((DIRECTORY/'plan.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if sha(DIRECTORY/'plan.json') != receipt['planSha256']:
    raise RuntimeError('Native candidates and source plan differ')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
checks = []
for zone in receipt['zones']:
    identity = zone['id']
    for suffix, hashes in [('', 'candidateHashes'), ('_modules', 'moduleHashes')]:
        if sha(DIRECTORY/(identity+suffix+'.json')) != plan[hashes][identity]:
            raise RuntimeError('Clearance input changed: '+identity+suffix)
    source = json.loads((DIRECTORY/(identity+'.json')).read_text())
    village = json.loads((DIRECTORY/(identity+'_modules.json')).read_text())
    routes, points = clearance_routes(source, village)
    if not levels.load_level(zone['map']):
        raise RuntimeError('Saved prototype unavailable')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    unreal.WarImportLibrary.prepare_world_preview_frame(world)
    scenery = [a for a in actors.get_all_level_actors() if 'WarT1PrototypeScenery' in map(str, a.tags)]
    terrain = [a for a in actors.get_all_level_actors() if 'WarT1PrototypeTerrain' in map(str, a.tags)]
    if len(terrain) != 2 or len(scenery) != zone['placedSourceModels']:
        raise RuntimeError('Native clearance inventory differs from receipt')
    blockers, rows = [], []
    total = 0

    def floor(p):
        location = unreal.Vector(p['z']*100, p['x']*100, 0)
        hit = unreal.SystemLibrary.line_trace_single(world, location+unreal.Vector(0, 0, 20000),
            location-unreal.Vector(0, 0, 20000), unreal.TraceTypeQuery.ECC_VISIBILITY,
            True, scenery, unreal.DrawDebugTrace.NONE, True)
        parts = hit.to_tuple() if hit else None
        if not parts or not parts[0]:
            raise RuntimeError('No terrain at clearance position: '+str(p))
        return parts[5], parts[7]

    def record(hit, probe_id, shape, p, direction):
        parts = hit.to_tuple() if hit else None
        if parts and parts[0]:
            actor = parts[9]
            blockers.append(dict(id=probe_id, shape=shape, direction=direction, point=p,
                blocker=actor.get_actor_label() if actor else 'unknown',
                nativeActor=actor.get_path_name() if actor else None))
            return False
        return True

    # Terrain was separately sampled at full road width. Ignore it here so an
    # upright diagnostic box does not pretend to simulate terrain-aligned wheels.
    def capsule(a, b, probe_id, p, direction):
        hit = unreal.SystemLibrary.capsule_trace_single(world, a, b, 42, 96,
            unreal.TraceTypeQuery.ECC_VISIBILITY, True, terrain, unreal.DrawDebugTrace.NONE, True)
        return record(hit, probe_id, 'native_character_42_96_cm', p, direction)

    def center(p):
        ground, normal = floor(p)
        return ground+unreal.Vector(0, 0, 96-42+42/max(normal.z, .1)+3)

    for route in routes:
        count, clear = 0, True
        for a, b in zip(route['points'], route['points'][1:]):
            dx, dz = b['x']-a['x'], b['z']-a['z']
            length = math.hypot(dx, dz)
            normal = dict(x=-dz/length, z=dx/length)
            samples = segment_samples(a, b)
            lane_extent = min(4.5, route.get('width', 12)/2-.52)
            for lane in ([-lane_extent, 0, lane_extent] if route['vehicle'] else [0]):
                positions = [center(dict(x=p['x']+normal['x']*lane, z=p['z']+normal['z']*lane)) for p in samples]
                for i, (start, end) in enumerate(zip(positions, positions[1:])):
                    for direction, begin, finish in [('forward', start, end), ('reverse', end, start)]:
                        clear = capsule(begin, finish, route['id'], samples[i], direction) and clear
                        count += 1
            if route['vehicle']:
                # Preserve the six-metre gates: reserve 30 cm on either side.
                # Wide roads use the nine-metre corridor. Neither box certifies
                # turning, actual hull fit or navigation.
                half_width = min(450, route['width']*50-30)
                positions = [floor(p)[0]+unreal.Vector(0, 0, 168) for p in samples]
                yaw = math.degrees(math.atan2(dx, dz))
                for i, (start, end) in enumerate(zip(positions, positions[1:])):
                    for direction, begin, finish in [('forward', start, end), ('reverse', end, start)]:
                        hit = unreal.SystemLibrary.box_trace_single(world, begin, finish,
                            unreal.Vector(300, half_width, 165), unreal.Rotator(yaw=yaw),
                            unreal.TraceTypeQuery.ECC_VISIBILITY, True, terrain, unreal.DrawDebugTrace.NONE, True)
                        clear = record(hit, route['id'], f'authoring_corridor_6x{half_width/50:g}x3.3_m', samples[i], direction) and clear
                        count += 1
        total += count
        rows.append(dict(id=route['id'], kind=route['kind'], obstacleSweeps=count, obstacleClear=clear))
    for p in points:
        location = center(p['point'])
        clear = capsule(location, location+unreal.Vector(0, 0, 1), p['id'], p['point'], 'standing')
        total += 1
        rows.append(dict(id=p['id'], kind=p['kind'], obstacleSweeps=1, obstacleClear=clear))
    # Retain every blocking witness; compact summaries name unique obstacles.
    checks.append(dict(zone=identity, obstacleSweeps=total, probes=rows, blockers=blockers,
        blockedProbes=sum(not p['obstacleClear'] for p in rows), obstacleClear=not blockers,
        walkDriveAccepted=False, navigationAccepted=False, doorsAccepted=False))
for package, digest in receipt['packageHashes'].items():
    file = ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')
    if sha(file) != digest:
        raise RuntimeError('Read-only clearance review changed a saved candidate')
result = dict(planSha256=receipt['planSha256'], zones=checks, savedCandidatesUnchanged=True,
    unplacedSourceModels=receipt['pending'], gateStatesAccepted=False,
    walkDriveAccepted=False, visualApproved=False, obstacleClear=all(p['obstacleClear'] for p in checks))
(DIRECTORY/'clearance.json').write_text(json.dumps(result, indent=2)+'\n')
unreal.log('WAR_T1_CLEARANCE_RECORDED='+str(sum(p['obstacleSweeps'] for p in checks)))
if not result['obstacleClear']:
    raise RuntimeError('Native obstacles block T1 candidate probes; see clearance.json')
unreal.log('WAR_T1_CLEARANCE_PASSED=2')
